"""Pydantic contracts for the external systems.

Every payload is validated at the boundary: a source that breaks its contract is
treated as unavailable instead of silently producing a wrong decision.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    @model_validator(mode="before")
    @classmethod
    def _accept_underscore_meta(cls, data: Any) -> Any:
        if isinstance(data, dict) and "_meta" in data and "meta" not in data:
            data = {**data, "meta": data["_meta"]}
        return data


# ---- get_trip_context -------------------------------------------------------
class Passenger(_Base):
    passenger_id: str
    name: str
    type: str
    age: int | None = None
    email: str | None = None
    phone: str | None = None
    document_id: str | None = None
    loyalty_tier: str | None = None

    @property
    def is_minor(self) -> bool:
        return self.type.upper() in {"CHILD", "INFANT"} or (self.age is not None and self.age < 18)


class Segment(_Base):
    segment_id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{0,15}$")
    flight_number: str = Field(pattern=r"^[A-Z0-9]{2,3}\d{1,5}$")
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    date: dt.date
    scheduled_departure: dt.time
    scheduled_arrival: dt.time


class FareConditions(_Base):
    changeable: bool
    refundable: bool
    fare_family: str | None = None


class TripMeta(_Base):
    retrieved_at: dt.datetime
    completeness: Literal["COMPLETE", "PARTIAL"] = "COMPLETE"
    missing_fields: list[str] = Field(default_factory=list)


class TripContext(_Base):
    booking_id: str
    passengers: list[Passenger]
    segments: list[Segment]
    fare_conditions: FareConditions
    meta: TripMeta


# ---- get_operational_events -------------------------------------------------
class OperationalEvent(_Base):
    event_id: str
    segment_id: str
    type: str
    source: str
    recorded_at: dt.datetime
    delay_minutes: int | None = Field(default=None, ge=0)
    new_departure: dt.time | None = None
    gate: str | None = Field(default=None, pattern=r"^[A-Z0-9-]{1,8}$")
    status: str | None = None


class EventsMeta(_Base):
    retrieved_at: dt.datetime
    sources_available: list[str] = Field(default_factory=list)
    sources_degraded: list[str] = Field(default_factory=list)


class EventsDocument(_Base):
    events: list[OperationalEvent]
    meta: EventsMeta


# ---- get_eligible_options ---------------------------------------------------
class RebookingOption(_Base):
    option_id: str = Field(pattern=r"^[A-Z0-9-]{1,32}$")
    type: str
    policy_ref: str
    confidence: str
    flight_number: str | None = Field(default=None, pattern=r"^[A-Z0-9]{2,3}\d{1,5}$")
    origin: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    destination: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    date: dt.date | None = None
    departure: dt.time | None = None
    fare_difference: int | None = Field(default=None, ge=0)
    currency: str | None = None
    seats_available: int | None = Field(default=None, ge=0)


class OptionsMeta(_Base):
    retrieved_at: dt.datetime
    ttl_seconds: int


class OptionsDocument(_Base):
    options: list[RebookingOption]
    meta: OptionsMeta


# ---- get_policy_rules -------------------------------------------------------
class PolicyRule(_Base):
    rule_id: str
    condition: str
    entitlement: str
    requires_human_approval: bool


class PolicyMeta(_Base):
    retrieved_at: dt.datetime
    superseded_versions: list[str] = Field(default_factory=list)


class PolicyDocument(_Base):
    scenario: str
    version: str
    effective_from: dt.date
    rules: list[PolicyRule]
    meta: PolicyMeta
