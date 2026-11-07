"""Deterministic decisions behind model-selected reads and protected writes."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from .contracts import Assessment, Entitlement, Intent, Option
from .core.policy import evaluate
from .core.reconcile import reconcile
from .models import EventsDocument, OptionsDocument, PolicyDocument, TripContext
from .privacy import trip_view

PRIORITY = {"OPS_CORE": 3, "AIRPORT_FEED": 2, "LEGACY_MIRROR": 1}
READS = {"get_trip_context", "get_operational_events", "get_policy_rules", "get_eligible_options"}


def digest(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


class Engine:
    def __init__(self, systems, clock, store):
        self.systems, self.clock, self.store = systems, clock, store

    def open_case(self, booking: str, reason: str, refs: list[str]) -> dict:
        key = digest("case", booking, reason, refs)
        claimed, previous = self.store.claim(key)
        if not claimed:
            return previous
        try:
            code, payload = self.systems.create_human_case(reason, {"evidence_refs": refs})
            result = {k: payload[k] for k in ("case_id", "queue", "sla_minutes") if k in payload}
            status = "OPEN" if code == 201 and result.get("case_id") else "INDETERMINATE"
        except Exception:
            result, status = {}, "INDETERMINATE"
        self.store.finish(key, status, result)
        return {"status": status, **result}

    def notify(self, booking: str, response: Assessment) -> dict | None:
        if not response.policy_refs:
            return None
        key = digest("notify", booking, response.reply, response.policy_refs)
        claimed, previous = self.store.claim(key)
        if not claimed:
            return previous
        try:
            code, payload = self.systems.notify_passenger({
                "body": response.reply, "policy_ref": response.policy_refs[0],
                "channel": "PUSH", "booking_id": booking,
            })
            result = {k: payload[k] for k in ("notification_id", "channel") if k in payload}
            status = "QUEUED" if code == 202 and result.get("notification_id") else "INDETERMINATE"
        except Exception:
            status, result = "INDETERMINATE", {}
        self.store.finish(key, status, result)
        return {"status": status, **result}

    def assess(self, context: ReadContext, intent: Intent, *, effects: bool = True) -> Assessment:
        if not READS <= context.seen:
            raise ValueError("Required model-selected reads are incomplete")
        trip, events, policy, options = context.trip, context.events, context.policy, context.options
        if any(value is None for value in (events, policy, options)):
            raise ValueError("Required evidence unavailable")
        now = self.clock.now()
        recon = reconcile(events.events, events.meta.sources_degraded, now, PRIORITY, timedelta(minutes=30))
        trusted = [e for e in events.events if e.source in PRIORITY and
                   e.source not in events.meta.sources_degraded and timedelta(0) <= now-e.recorded_at <= timedelta(minutes=30)]
        # Contradictory equally authoritative facts remain unresolved, even if newer.
        for first in trusted:
            for second in trusted:
                if first.segment_id != second.segment_id or PRIORITY[first.source] != PRIORITY[second.source]:
                    continue
                if first.type == "DELAY" and second.type == "STATUS" and second.status == "ON_TIME" and first.delay_minutes:
                    recon.unresolved = True
                if first.type == second.type == "DELAY" and first.delay_minutes != second.delay_minutes:
                    recon.unresolved = True
        # Missing, future-dated or unrecognized sources cannot imply an on-time flight.
        complete = all(any(e.segment_id == s.segment_id and e.type in {"DELAY", "STATUS"} for e in trusted) for s in trip.segments)
        known = complete and not recon.unresolved
        delays = [state.delay_minutes for state in recon.segments.values()]
        for segment in trip.segments:
            state = recon.segments.get(segment.segment_id)
            if state and state.new_departure:
                actual_shift = (datetime.combine(segment.date, state.new_departure) -
                                datetime.combine(segment.date, segment.scheduled_departure)).total_seconds()/60
                if actual_shift != state.delay_minutes:
                    known = False
        delay = max(delays, default=0) if known else None
        risk = False
        if known and len(trip.segments) > 1:
            first, second = trip.segments[:2]
            arrival = datetime.combine(first.date, first.scheduled_arrival) + timedelta(minutes=recon.segments[first.segment_id].delay_minutes)
            departure = datetime.combine(second.date, second.scheduled_departure) + timedelta(minutes=recon.segments[second.segment_id].delay_minutes)
            risk = (departure-arrival).total_seconds() < 45*60
        facts = {
            "delay_minutes": delay, "missed_connection": None,
            "international": True if {s.origin for s in trip.segments} | {s.destination for s in trip.segments} <= {"SCL", "LIM", "MEX"} else None,
            "group_includes_minor": any(p.is_minor for p in trip.passengers),
            "compensation_requested": intent.compensation_requested,
        }
        outcome = evaluate(policy, facts, now.date())
        valid_policy = not outcome.issues
        entitlements = [Entitlement(
            entitlement=e.entitlement, rule_id=e.rule_id, policy_ref=e.policy_version,
            status="PENDING_HUMAN_REVIEW" if e.requires_human_approval else "ELIGIBLE",
        ) for e in outcome.triggered]
        no_fee = any(e.entitlement == "REBOOK_NO_FEE" and e.status == "ELIGIBLE" for e in entitlements)
        material_unknown = any(rule != "R3" or (risk and not no_fee) for rule in outcome.unevaluable)
        human = (not known or not valid_policy or material_unknown or any(e.status == "PENDING_HUMAN_REVIEW" for e in entitlements)
                 or ((risk or intent.rebooking_requested) and not no_fee))
        refs = [policy.version] if valid_policy else []
        candidates = []
        age = (now-options.meta.retrieved_at).total_seconds()
        last = trip.segments[-1]
        if valid_policy and known and 0 <= age < options.meta.ttl_seconds:
            for item in options.options:
                if (item.type != "REBOOK" or item.policy_ref not in refs or (item.seats_available or 0) < len(trip.passengers)
                        or item.origin != last.origin or item.destination != last.destination or item.confidence != "HIGH"
                        or not item.date or not item.departure or not item.flight_number or item.fare_difference != 0
                        or not trip.fare_conditions.changeable):
                    continue
                candidate_time = datetime.combine(item.date, item.departure)
                if candidate_time <= datetime.combine(last.date, last.scheduled_departure):
                    continue
                if len(trip.segments) > 1 and candidate_time < arrival + timedelta(minutes=45):
                    continue
                candidates.append(Option(
                    option_id=item.option_id, flight_number=item.flight_number, origin=item.origin,
                    destination=item.destination, date=str(item.date), departure=item.departure.strftime("%H:%M"),
                    fare_difference=item.fare_difference, policy_ref=item.policy_ref,
                    status="CONFIRMABLE" if no_fee and not human else "CANDIDATE"))
        if intent.rebooking_requested and not candidates:
            human = True
        if human:
            candidates = [o.model_copy(update={"status": "CANDIDATE"}) for o in candidates]
        happened = ([f"Verified departure delay: {delay} minutes."] if known else ["Operational information could not be verified."])
        if known:
            happened.extend(f"Gate change: {e.gate}." for e in trusted if e.type == "GATE_CHANGE")
        evidence_refs = sorted(e.event_id for e in trusted)
        case = self.open_case(trip.booking_id, "policy_or_evidence_review", evidence_refs + refs) if human and effects else None
        text = [f"El retraso verificado es de {delay} minutos." if known else "No pude verificar el estado operativo; hay datos faltantes o contradictorios."]
        if risk:
            text.append("La conexión está en riesgo según la llegada estimada; todavía no está confirmada su pérdida.")
        if candidates:
            item = candidates[0]
            text.append(f"La alternativa {item.flight_number} del {item.date} a las {item.departure} tiene cupos para el grupo.")
            text.append("Es una candidata; sus condiciones y costos requieren revisión." if item.status == "CANDIDATE" else "Es elegible para cambio sin cargo; confirma esta opción antes de solicitarla.")
        if intent.compensation_requested:
            text.append("La compensación requiere revisión humana; no hay un monto aprobado.")
        if human:
            text.append("Abrí un caso para revisión humana." if case and case["status"] == "OPEN" else "Se necesita revisión humana; la apertura del caso no está confirmada.")
        text.append("No se ha cambiado tu reserva.")
        response = Assessment(
            what_happened=happened, entitlements=entitlements, options=candidates,
            next_step="HUMAN_REVIEW" if human else "CONFIRM_OPTION" if candidates else "INFORM_ONLY",
            policy_refs=refs, human_required=human, reply=" ".join(text),
            connection_status="UNKNOWN" if not known else "AT_RISK" if risk else "NO_RISK_IDENTIFIED",
            evidence_refs=evidence_refs, human_case=case,
        )
        self.check_faithfulness(response, policy, facts)
        if effects:
            if not human and candidates:
                response.confirmation_token = self.store.offer(context.owner, {
                    "booking": trip.booking_id, "expires": (options.meta.retrieved_at + timedelta(seconds=options.meta.ttl_seconds)).isoformat(),
                    "intent": intent.model_dump(), "options": [o.model_dump() for o in candidates],
                })
            response.notification = self.notify(trip.booking_id, response)
        return Assessment.model_validate(response.model_dump())

    def check_faithfulness(self, response, policy, facts):
        permitted = {(e.rule_id, e.entitlement, e.policy_version, e.requires_human_approval)
                     for e in evaluate(policy, facts, self.clock.now().date()).triggered}
        for item in response.entitlements:
            key = (item.rule_id, item.entitlement, item.policy_ref, item.status == "PENDING_HUMAN_REVIEW")
            if key not in permitted:
                raise ValueError("Entitlement is not backed by an applicable policy rule")

    def confirm(self, owner: str, token: str, option_id: str, confirmed: bool) -> dict:
        if not confirmed:
            raise ValueError("Explicit passenger confirmation is required")
        offer = self.store.get_offer(token, owner)
        original = next((o for o in offer["options"] if o["option_id"] == option_id), None)
        if not original:
            raise ValueError("Option was not presented")
        # The key survives changed events, new offers and process restarts.
        key = digest("rebooking", offer["booking"],
                     {field: original[field] for field in ("flight_number", "origin", "destination", "date", "departure")})
        prior = self.store.lookup(key)
        if prior:
            return self._write_result(offer["booking"], prior)
        if self.clock.now() >= datetime.fromisoformat(offer["expires"]):
            raise ValueError("Presented option expired; request a new assessment")
        context = ReadContext(self, offer["booking"], owner)
        context.get_trip_context()
        context.get_operational_events()
        context.get_policy_rules()
        context.get_eligible_options()
        fresh = self.assess(context, Intent.model_validate(offer["intent"]), effects=False)
        if fresh.human_required or original not in [o.model_dump() for o in fresh.options]:
            raise ValueError("Option or approval conditions changed")
        claimed, prior = self.store.claim(key)
        if not claimed:
            return self._write_result(offer["booking"], prior)
        try:
            code, payload = self.systems.create_rebooking_request({"booking_id": offer["booking"], **original}, key)
            if code == 201 and payload.get("status") == "PENDING_CONFIRMATION" and payload.get("request_id"):
                status = "PENDING_CONFIRMATION"
            else:
                status = "INDETERMINATE"
            data = {k: payload[k] for k in ("request_id", "expires_at") if k in payload}
        except Exception:
            status, data = "INDETERMINATE", {}
        self.store.finish(key, status, data)
        return self._write_result(offer["booking"], {"status": status, **data})

    def _write_result(self, booking, data):
        if data["status"] == "INDETERMINATE":
            return {**data, "reply": "El resultado de la solicitud es desconocido. No confirmamos un cambio ni repetimos la reserva.",
                    "human_case": self.open_case(booking, "indeterminate_rebooking", [])}
        return {**data, "reply": "La solicitud fue recibida y está pendiente de confirmación; el cambio no está confirmado."}


class ReadContext:
    """Per-run private state: the model receives only minimized tool results."""
    def __init__(self, engine: Engine, booking: str, owner: str):
        self.engine, self.owner = engine, owner
        # Authorization is checked before constructing this context.
        self.trip = TripContext.model_validate(engine.systems.get_trip_context(booking))
        self.seen: set[str] = set()
        self.trajectory: list[str] = []
        self.events = self.policy = self.options = None

    def mark(self, name: str):
        if name != "get_trip_context" and "get_trip_context" not in self.seen:
            raise ValueError("Read trip context first")
        self.seen.add(name)
        self.trajectory.append(name)

    def get_trip_context(self) -> dict:
        """Read the authorized itinerary, party size, minor flag and missing fields."""
        self.mark("get_trip_context")
        return trip_view(self.trip)

    def get_operational_events(self) -> dict:
        """Read operational events and deterministic connection-risk evidence for this trip."""
        self.mark("get_operational_events")
        self.events = EventsDocument.model_validate(self.engine.systems.get_operational_events([s.segment_id for s in self.trip.segments]))
        r = reconcile(self.events.events, self.events.meta.sources_degraded, self.engine.clock.now(), PRIORITY, timedelta(minutes=30))
        return {"event_count": len(self.events.events), "requires_deterministic_assessment": True,
                "unresolved_conflict": r.unresolved, "sources_degraded": [s for s in self.events.meta.sources_degraded if s in PRIORITY]}

    def get_policy_rules(self) -> dict:
        """Read the current delay policy. Code evaluates all eligibility and approval rules."""
        self.mark("get_policy_rules")
        self.policy = PolicyDocument.model_validate(self.engine.systems.get_policy_rules("DELAY"))
        return {"policy_available": True, "rule_count": len(self.policy.rules), "requires_deterministic_assessment": True}

    def get_eligible_options(self) -> dict:
        """Read candidate alternatives for the whole party; candidates are not reservations."""
        self.mark("get_eligible_options")
        self.options = OptionsDocument.model_validate(self.engine.systems.get_eligible_options(self.trip.model_dump(mode="json")))
        return {"candidate_count": len(self.options.options), "ttl_seconds": self.options.meta.ttl_seconds,
                "requires_deterministic_assessment": True}
