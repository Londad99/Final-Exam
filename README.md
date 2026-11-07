# Engineering README — Part A

**Decision status.** Google ADK is approved by the student. Other assistant-authored design choices below remain unapproved draft proposals, not agreed decisions. Important decisions require student acceptance before implementation or documentation. The agent architecture and orchestration details await review.

**Scope.** Proposed design; Part B is not implemented here. The previous submission provides mock contracts and deterministic components, but its optional AI composer does not meet the final exam's mandatory tool-calling agent requirement. Goal: reduce passenger uncertainty and avoidable contacts without unsupported promises or uncontrolled writes.

## 1. Autonomy boundary

| Step | Classification | Reason | Risk | Control / fallback |
|---|---|---|---|---|
| Authorize booking access | Deterministic | Access is not a language decision | Data disclosure | Backend authorization; booking reference alone is insufficient |
| Interpret request and choose reads | Agentic | Identify connection, rebooking and compensation intents | Missed intent; injection | Read-only tool allowlist, typed calls, bounded loop; clarify ambiguity |
| Retrieve and reconcile evidence | Deterministic | Trust and freshness must be reproducible | Contradictory facts | Schema, timestamp and source checks; unresolved conflict escalates |
| Calculate connection risk | Deterministic | Schedule arithmetic | Estimate presented as fact | Distinguish projected arrival from confirmed outcome |
| Apply rules and filter options | Deterministic | Eligibility and capacity are constraints | Unsupported entitlement; split party | Versioned rules, three-valued evaluation, route/capacity/TTL/fare checks |
| Draft explanation | AI-assisted | Adapt wording to the passenger | Invented amount or guarantee | Factual claims rendered from validated fields; template fallback |
| Validate and notify | Deterministic | Only supported content may leave | Unsupported notification | Evidence and policy-reference validation; report only tool-confirmed status |
| Open human case | Deterministic | Policy flags require referral | Lost or duplicate case | Minimal evidence, deduplication; acknowledge only confirmed creation |
| Decide reserved outcomes | Human | R4/R5 require approval | Unauthorized compensation or handling | Record operator decision; no model approval |
| Choose and confirm option | Human | Passenger authorizes a concrete change | Vague request treated as consent | Present itinerary and price; explicit confirmation |
| Execute rebooking | Deterministic | Controlled side effect | Expiry, duplication, false success | Revalidate approvals and availability; stable idempotency; reconcile uncertainty |

**Target outcome.** Explain the verified 160-minute S1 delay. Adding it to 17:55 gives an estimated 20:35 arrival against a 19:05 connection: connection risk, not verified connection loss. R1's 180-minute and R2's 240-minute thresholds are unmet; R3 remains unknown until loss is verified. R4 (compensation requested) and R5 (minor in party) require human review under `POL-DELAY-2026-03`, without granting a payment amount. O2 has one seat for two passengers and a CLP 180,000 difference. O1 has four seats but is only a next-day candidate: zero fare difference does not resolve the missing change penalty. O3 has an unverified refund policy and is not offered. Open a case; do not rebook or promise payment.

## 2. Agent pattern

**Approved framework: Google ADK.** The student selected Google ADK instead of the assistant-proposed LangGraph. Agent structure, tool permissions, orchestration, confirmation controls and LLM-call budget must be reviewed and accepted before being documented as the chosen design.

## 3. Context and personal data

Allowlist trip-derived fields: segment/flight references, airports, dates and schedules; derived `party_size` and `includes_minor`; changeable/refundable flags; completeness, missing-field indicators and retrieval timestamps. Exclude names, passenger IDs, email, phone, document number, loyalty tier, exact age, fare family, raw booking ID and `remarks`. Backend-owned opaque handles bind calls to the booking. Minimized itinerary information remains sensitive.

Enforce separate typed model-facing DTOs, never raw-object serialization. Redact names and identifiers from passenger input before submission; replace child age with the minor flag. Drop malicious remarks entirely. Treat all other tool strings as data, never instructions; parse rules without executing text. Test forbidden-field absence in model requests, checkpoints and traces; masking alone is insufficient.

No cross-session model memory. Persist restricted workflow state only for confirmation, approval, case references and idempotency; exclude raw conversations and contact details. Apply access control and expiry, with production retention agreed with the privacy owner. Logs use random correlation IDs and evidence/rule references.

## 4. Tools, RAG and assumptions

`get_policy_rules` returns exact, versioned, effective rules for deterministic evaluation. Vector similarity cannot establish applicability, completeness or precedence. RAG could explain airport transfer facilities using approved guides: cite document, section and version; verify currency; abstain without evidence. It must not authorize eligibility, compensation or booking changes.

Relevant change: delay of at least 30 minutes, connection risk, or an informative gate change. Assume a configurable 45-minute minimum connection for risk estimation; operations must supply airport-specific minima and timezone-aware schedules. Prefer OPS_CORE, then AIRPORT_FEED, then LEGACY_MIRROR; discard degraded sources and events older than 30 minutes. Thresholds are design assumptions, not supplied policy. Use the injected sample clock for replay and current UTC in production. Unresolved equal-authority conflicts block affected claims, not unrelated verified facts.

Automatically communicate verified facts and labeled estimates; present candidates without asserting eligibility. Humans resolve reserved outcomes, material unknowns and uncertain writes. Options expire after 120 seconds. A rebooking 201 means PENDING_CONFIRMATION, not a completed booking; reconcile 409 against the existing request; keep 503 indeterminate. Never create a new idempotency key to retry the same logical action.

**Validation and next steps.** Reviewed all three exam photos and the prior README, design, models, privacy and connection logic. No runtime tests or real-model execution occurred for this documentation change. Part B must implement the approved ADK design and persistent guards, test target/conflicting-source/injection/failed-write trajectories, check entitlement policy references and save a PII-free trace. Earlier reported tests do not validate this design. More human referrals are the cost of avoiding unsupported eligibility claims.

