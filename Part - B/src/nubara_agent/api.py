from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
from fastapi.staticfiles import StaticFiles

from .contracts import Assessment
from .runtime import build_service

app = FastAPI(title="Nubara ADK Disruption Companion", description="Local exam demo: mock identities and airline systems")
service = build_service()


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ConfirmationRequest(BaseModel):
    confirmation_token: str
    option_id: str
    confirmed: bool


@app.get("/health")
def health():
    return {"status": "ok", "mode": "exam_mock"}


@app.post("/v1/disruptions/{booking_id}/assess", response_model=Assessment)
async def assess(booking_id: str, body: MessageRequest, x_demo_user: str = Header()):
    try:
        result, _ = await service.assess(booking_id, body.message, x_demo_user)
        return result
    except PermissionError:
        raise HTTPException(403, "Booking access denied") from None


@app.post("/v1/disruptions/confirm")
def confirm(body: ConfirmationRequest, x_demo_user: str = Header()):
    try:
        return service.engine.confirm(x_demo_user, body.confirmation_token, body.option_id, body.confirmed)
    except ValueError:
        raise HTTPException(409, "Confirmation rejected: missing, expired, unauthorized or changed option") from None


# Same-origin UI: a single local process serves both the frontend and API.
app.mount("/", StaticFiles(directory=Path(__file__).parent / "web", html=True), name="frontend")
