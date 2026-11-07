"""Allowlist context and redact known identifiers before invoking the model."""
import re
import unicodedata

from .models import TripContext


def _plain(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value) if not unicodedata.combining(c))


def sanitize_message(message: str, trip: TripContext) -> str:
    text = _plain(message[:4000])
    secrets = [trip.booking_id]
    for passenger in trip.passengers:
        secrets.extend(filter(None, [passenger.name, passenger.email, passenger.phone, passenger.document_id]))
        secrets.extend(passenger.name.split())
    for secret in sorted(secrets, key=len, reverse=True):
        text = re.sub(re.escape(_plain(secret)), "[REDACTED]", text, flags=re.I)
    text = re.sub(r"[\w.+-]+@[\w.-]+", "[EMAIL]", text)
    text = re.sub(r"\b\d{1,2}\s*(?:anos|years old)\b", "minor", text, flags=re.I)
    text = re.sub(r"\+?\d[\d .()-]{6,}\d", "[IDENTIFIER]", text)
    text = re.sub(r"\b(?:soy|me llamo|my name is)\s+[A-Za-z]+(?:\s+[A-Z][a-z]+)*", "[IDENTITY]", text, flags=re.I)
    return text


def trip_view(trip: TripContext) -> dict:
    return {
        "segments": [s.model_dump(mode="json") for s in trip.segments],
        "party_size": len(trip.passengers),
        "includes_minor": any(p.is_minor for p in trip.passengers),
        "changeable": trip.fare_conditions.changeable,
        "refundable": trip.fare_conditions.refundable,
        "completeness": trip.meta.completeness,
        "missing_fields": [field for field in trip.meta.missing_fields if field in {"fare_conditions.change_penalty_amount"}],
        "retrieved_at": trip.meta.retrieved_at.isoformat(),
    }
