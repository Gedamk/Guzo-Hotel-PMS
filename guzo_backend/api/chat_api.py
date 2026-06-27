from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessageRequest(BaseModel):
    message: str
    property_code: str
    guest_name: Optional[str] = None
    channel: Optional[str] = "web"


@router.get("/health")
def chat_health():
    return {
        "status": "ok",
        "service": "guzo-chat",
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/message")
def create_chat_message(payload: ChatMessageRequest):
    """
    Stable chat endpoint for PMS and booking-assistant integrations.

    The response is intentionally conservative until a full assistant service
    is wired in, but it prevents backend startup from failing when the router is
    included by guzo_backend.main.
    """

    return {
        "status": "received",
        "property_code": payload.property_code,
        "guest_name": payload.guest_name,
        "channel": payload.channel,
        "reply": "Message received. A hotel team member can review this conversation.",
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }
