# guzo_backend/core/auth.py

import os
from fastapi import HTTPException

def verify_admin_token(token: str) -> None:
  expected = os.getenv("GUZO_API_ADMIN_TOKEN", "<REDACTED_DEMO_BEARER_TOKEN>")
  if token != expected:
    raise HTTPException(status_code=401, detail="Invalid or missing admin token")
