from __future__ import annotations

from contextvars import ContextVar


_current_user_email: ContextVar[str | None] = ContextVar("current_user_email", default=None)


def set_current_user_email(email: str | None):
    return _current_user_email.set(email.strip().lower() if email else None)


def reset_current_user_email(token) -> None:
    _current_user_email.reset(token)


def get_current_user_email() -> str | None:
    return _current_user_email.get()
