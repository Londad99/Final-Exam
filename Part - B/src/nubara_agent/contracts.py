from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Intent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    connection_requested: bool
    rebooking_requested: bool
    compensation_requested: bool


class Entitlement(BaseModel):
    entitlement: str
    rule_id: str
    policy_ref: str
    status: Literal["ELIGIBLE", "PENDING_HUMAN_REVIEW"]


class Option(BaseModel):
    option_id: str
    flight_number: str
    origin: str
    destination: str
    date: str
    departure: str
    fare_difference: int
    policy_ref: str
    status: Literal["CANDIDATE", "CONFIRMABLE"]


class Assessment(BaseModel):
    what_happened: list[str]
    entitlements: list[Entitlement]
    options: list[Option]
    next_step: Literal["HUMAN_REVIEW", "CONFIRM_OPTION", "INFORM_ONLY", "RETRY_OR_CONTACT_SUPPORT"]
    policy_refs: list[str]
    human_required: bool
    reply: str
    connection_status: Literal["AT_RISK", "UNKNOWN", "NO_RISK_IDENTIFIED"]
    evidence_refs: list[str] = Field(default_factory=list)
    human_case: dict | None = None
    notification: dict | None = None
    confirmation_token: str | None = None
    agent_status: Literal["COMPLETED", "UNAVAILABLE", "INCOMPLETE"] = "COMPLETED"
    trace_id: str = ""

    @model_validator(mode="after")
    def require_policy_evidence(self):
        for item in [*self.entitlements, *self.options]:
            if item.policy_ref not in self.policy_refs:
                raise ValueError("Missing policy reference")
        if any(e.status == "PENDING_HUMAN_REVIEW" for e in self.entitlements) and not self.human_required:
            raise ValueError("Human-reserved outcome cannot bypass review")
        if self.human_required and self.confirmation_token:
            raise ValueError("Human review blocks passenger confirmation")
        return self
