from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.agent_harness_service import run_agent_task
from guzo_backend.services.pms_security_service import require_property_access


router = APIRouter(prefix="/agent-harness", tags=["agent-harness"])


class AgentHarnessTaskRequest(BaseModel):
    task_name: str = Field(..., min_length=1)
    property_code: str = Field(..., min_length=1, max_length=20)
    data: dict[str, Any] = Field(default_factory=dict)


@router.post("/tasks")
def run_agent_harness_task(
    payload: AgentHarnessTaskRequest,
    db: Session = Depends(get_db),
    x_pms_user_email: str | None = Header(None),
):
    property_code = payload.property_code.strip().upper()
    require_property_access(db, property_code=property_code, user_email=x_pms_user_email)
    result = run_agent_task(
        db,
        task_name=payload.task_name,
        property_code=property_code,
        payload=payload.data,
        actor_email=x_pms_user_email,
    )
    db.commit()
    return result
