from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from guzo_backend.dependencies import get_db
from guzo_backend.services.pms_auth_service import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    ensure_auth_schema,
    get_user_by_email,
    pms_user_to_session,
)


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str
    property_code: str


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token is required.")
    return authorization.split(" ", 1)[1].strip()


def _current_user_from_header(db: Session, authorization: str | None) -> dict[str, Any]:
    claims = decode_access_token(_bearer_token(authorization))
    user = get_user_by_email(db, claims["email"], claims.get("property_code"))
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Authenticated PMS user is inactive or unavailable.")
    return user


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(
        db,
        email=payload.email,
        password=payload.password,
        property_code=payload.property_code,
    )
    token, expires_at = create_access_token(user)
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "user": pms_user_to_session(user),
    }


@router.get("/me")
def current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    ensure_auth_schema(db)
    user = _current_user_from_header(db, authorization)
    return pms_user_to_session(user)


@router.post("/logout")
def logout():
    return {"ok": True, "message": "Client should clear the stored access token."}
