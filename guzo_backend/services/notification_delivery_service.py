from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from guzo_backend.services.guest_profile_service import ensure_guest_notification_outbox, ensure_manager_alerts_table
from guzo_backend.services.pms_security_service import record_pms_audit_log


SUPPORTED_EMAIL_ACTIONS = {
    "reservation_confirmation",
    "pre_arrival_reminder",
    "checkout_receipt",
    "feedback_request",
    "guest_feedback_request",
    "booking_cancellation",
    "failed_message_manager_alert",
}


@dataclass
class EmailMessagePayload:
    to_email: str
    subject: str
    body_text: str
    body_html: str | None = None


class EmailDeliveryError(RuntimeError):
    pass


class EmailDeliveryClient:
    def send(self, payload: EmailMessagePayload) -> dict[str, Any]:
        provider = os.getenv("GUZO_EMAIL_PROVIDER", "smtp").strip().lower()
        if provider == "disabled":
            return {"provider": "disabled", "message_id": "dry-run"}
        if provider != "smtp":
            raise EmailDeliveryError(f"Unsupported email provider: {provider}")

        host = os.getenv("GUZO_SMTP_HOST")
        port = int(os.getenv("GUZO_SMTP_PORT", "587"))
        username = os.getenv("GUZO_SMTP_USERNAME")
        password = os.getenv("GUZO_SMTP_PASSWORD")
        from_email = os.getenv("GUZO_EMAIL_FROM", username or "noreply@guzo.local")
        use_tls = os.getenv("GUZO_SMTP_USE_TLS", "true").strip().lower() not in {"0", "false", "no"}
        if not host:
            raise EmailDeliveryError("GUZO_SMTP_HOST is not configured")

        message = EmailMessage()
        message["From"] = from_email
        message["To"] = payload.to_email
        message["Subject"] = payload.subject
        message.set_content(payload.body_text)
        if payload.body_html:
            message.add_alternative(payload.body_html, subtype="html")

        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
        return {"provider": "smtp", "message_id": None}


def _max_retries() -> int:
    try:
        return max(int(os.getenv("GUZO_EMAIL_MAX_RETRIES", "3")), 1)
    except ValueError:
        return 3


def render_email_template(row: dict[str, Any]) -> EmailMessagePayload:
    action = str(row.get("action") or "").strip().lower()
    guest_name = row.get("guest_name") or "Guest"
    property_code = row.get("property_code") or "Guzo PMS"
    message = row.get("message") or ""
    confirmation_id = row.get("confirmation_id") or row.get("booking_id") or ""
    business_date = row.get("business_date")

    templates = {
        "reservation_confirmation": (
            f"Reservation confirmation {confirmation_id}",
            f"Dear {guest_name},\n\n{message}\n\nWe look forward to welcoming you.\n\n{property_code}",
        ),
        "pre_arrival_reminder": (
            "Your upcoming stay reminder",
            f"Dear {guest_name},\n\nThis is a reminder for your upcoming arrival on {business_date or 'your arrival date'}.\n\n{message}\n\n{property_code}",
        ),
        "checkout_receipt": (
            "Your checkout receipt",
            f"Dear {guest_name},\n\n{message}\n\nThank you for staying with us.\n\n{property_code}",
        ),
        "feedback_request": (
            "Tell us about your stay",
            f"Dear {guest_name},\n\n{message or 'Please share feedback about your recent stay.'}\n\n{property_code}",
        ),
        "guest_feedback_request": (
            "Tell us about your stay",
            f"Dear {guest_name},\n\n{message or 'Please share feedback about your recent stay.'}\n\n{property_code}",
        ),
        "booking_cancellation": (
            "Booking cancellation notice",
            f"Dear {guest_name},\n\n{message or 'Your booking has been cancelled.'}\n\n{property_code}",
        ),
        "failed_message_manager_alert": (
            "Guest message delivery failure",
            f"Manager alert:\n\n{message or 'A guest message could not be delivered.'}\n\n{property_code}",
        ),
    }
    subject, body = templates.get(
        action,
        ("Guzo PMS notification", f"Dear {guest_name},\n\n{message}\n\n{property_code}"),
    )
    return EmailMessagePayload(to_email=str(row["recipient"]).strip(), subject=subject, body_text=body)


def _notification_row(db: Session, notification_id: int, property_code: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT n.*,
                   b.guest_name AS booking_guest_name,
                   b.confirmation_id
            FROM guest_notification_outbox n
            LEFT JOIN bookings b ON b.id = n.booking_id AND b.property_code = n.property_code
            WHERE n.id = :notification_id
              AND n.property_code = :property_code
            LIMIT 1
            """
        ),
        {"notification_id": notification_id, "property_code": property_code},
    ).mappings().first()
    return dict(row) if row else None


def _mark_skipped(db: Session, row: dict[str, Any], reason: str, actor_email: str | None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    db.execute(
        text(
            """
            UPDATE guest_notification_outbox
            SET status = 'skipped',
                failure_reason = :reason,
                last_attempt_at = :now
            WHERE id = :id
            """
        ),
        {"id": row["id"], "reason": reason, "now": now},
    )
    record_pms_audit_log(
        db,
        property_code=row.get("property_code"),
        user_email=actor_email,
        module="notifications",
        action="notification_skipped",
        record_type="guest_notification_outbox",
        record_id=row["id"],
        new_value={"reason": reason, "action": row.get("action")},
    )
    return {"id": row["id"], "status": "skipped", "reason": reason}


def _manager_alert_for_failure(db: Session, row: dict[str, Any], reason: str) -> None:
    ensure_manager_alerts_table(db)
    db.execute(
        text(
            """
            INSERT INTO manager_alerts (
                property_code, alert_type, severity, message, guest_profile_id, guest_id,
                booking_id, public_request_id, business_date, status
            )
            VALUES (
                :property_code, 'failed_guest_message', 'high', :message, :guest_profile_id, :guest_id,
                :booking_id, :public_request_id, :business_date, 'open'
            )
            """
        ),
        {
            "property_code": row.get("property_code"),
            "message": f"Guest notification {row['id']} failed repeatedly: {reason}",
            "guest_profile_id": row.get("guest_profile_id"),
            "guest_id": row.get("guest_id"),
            "booking_id": row.get("booking_id"),
            "public_request_id": row.get("public_request_id"),
            "business_date": row.get("business_date"),
        },
    )


def deliver_notification(
    db: Session,
    row: dict[str, Any],
    *,
    actor_email: str | None,
    email_client: EmailDeliveryClient | None = None,
) -> dict[str, Any]:
    ensure_guest_notification_outbox(db)
    action = str(row.get("action") or "").strip().lower()
    channel = str(row.get("channel") or "").strip().lower()
    recipient = str(row.get("recipient") or "").strip()
    max_retries = _max_retries()
    retry_count = int(row.get("retry_count") or 0)

    if action not in SUPPORTED_EMAIL_ACTIONS:
        return _mark_skipped(db, row, "unsupported_notification_type", actor_email)
    if channel != "email":
        return _mark_skipped(db, row, "unsupported_channel", actor_email)
    if not recipient:
        return _mark_skipped(db, row, "no_recipient", actor_email)
    if retry_count >= max_retries:
        return _mark_skipped(db, row, "max_retries_exceeded", actor_email)

    now = datetime.now(timezone.utc)
    try:
        client = email_client or EmailDeliveryClient()
        delivery = client.send(render_email_template(row))
        db.execute(
            text(
                """
                UPDATE guest_notification_outbox
                SET status = 'sent',
                    sent_at = :now,
                    last_attempt_at = :now,
                    attempt_count = COALESCE(attempt_count, 0) + 1,
                    failure_reason = NULL
                WHERE id = :id
                """
            ),
            {"id": row["id"], "now": now},
        )
        record_pms_audit_log(
            db,
            property_code=row.get("property_code"),
            user_email=actor_email,
            module="notifications",
            action="notification_sent",
            record_type="guest_notification_outbox",
            record_id=row["id"],
            new_value={"action": action, "recipient": recipient, **delivery},
        )
        return {"id": row["id"], "status": "sent", "delivery": delivery}
    except Exception as exc:
        reason = str(exc)
        next_retry_count = retry_count + 1
        db.execute(
            text(
                """
                UPDATE guest_notification_outbox
                SET status = 'failed',
                    failed_at = :now,
                    last_attempt_at = :now,
                    attempt_count = COALESCE(attempt_count, 0) + 1,
                    retry_count = COALESCE(retry_count, 0) + 1,
                    failure_reason = :reason
                WHERE id = :id
                """
            ),
            {"id": row["id"], "now": now, "reason": reason},
        )
        if next_retry_count >= max_retries:
            _manager_alert_for_failure(db, row, reason)
        record_pms_audit_log(
            db,
            property_code=row.get("property_code"),
            user_email=actor_email,
            module="notifications",
            action="notification_failed",
            record_type="guest_notification_outbox",
            record_id=row["id"],
            new_value={"action": action, "recipient": recipient, "failure_reason": reason, "retry_count": next_retry_count},
        )
        return {"id": row["id"], "status": "failed", "reason": reason, "retry_count": next_retry_count}


def process_email_outbox(
    db: Session,
    *,
    property_code: str,
    actor_email: str | None = None,
    limit: int = 25,
    email_client: EmailDeliveryClient | None = None,
) -> dict[str, Any]:
    ensure_guest_notification_outbox(db)
    clauses = [
        "LOWER(COALESCE(n.channel, '')) = 'email'",
        "LOWER(COALESCE(n.status, 'queued')) IN ('queued', 'failed')",
        "COALESCE(n.retry_count, 0) < :max_retries",
    ]
    params: dict[str, Any] = {"limit": limit, "max_retries": _max_retries()}
    property_code = property_code.strip().upper()
    if not property_code or property_code in {"ALL", "*"}:
        raise ValueError("A specific property_code is required to process notifications")
    clauses.append("n.property_code = :property_code")
    params["property_code"] = property_code
    rows = db.execute(
        text(
            f"""
            SELECT n.*,
                   b.guest_name AS booking_guest_name,
                   b.confirmation_id
            FROM guest_notification_outbox n
            LEFT JOIN bookings b ON b.id = n.booking_id
            WHERE {" AND ".join(clauses)}
            ORDER BY COALESCE(n.last_attempt_at, n.created_at) ASC, n.id ASC
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()
    results = [
        deliver_notification(db, dict(row), actor_email=actor_email, email_client=email_client)
        for row in rows
    ]
    return {
        "queued_found": len(rows),
        "sent_count": sum(1 for item in results if item["status"] == "sent"),
        "failed_count": sum(1 for item in results if item["status"] == "failed"),
        "skipped_count": sum(1 for item in results if item["status"] == "skipped"),
        "results": results,
    }


def retry_notification(
    db: Session,
    *,
    notification_id: int,
    property_code: str,
    actor_email: str | None,
    email_client: EmailDeliveryClient | None = None,
) -> dict[str, Any]:
    ensure_guest_notification_outbox(db)
    property_code = property_code.strip().upper()
    row = _notification_row(db, notification_id, property_code)
    if not row:
        raise ValueError("Notification not found")
    if str(row.get("status") or "").lower() == "skipped":
        return {"id": notification_id, "status": "skipped", "reason": "skipped_messages_are_not_retried"}
    db.execute(
        text(
            """
            UPDATE guest_notification_outbox
            SET status = 'queued',
                failure_reason = NULL
            WHERE id = :id
              AND property_code = :property_code
            """
        ),
        {"id": notification_id, "property_code": property_code},
    )
    row["status"] = "queued"
    row["failure_reason"] = None
    return deliver_notification(db, row, actor_email=actor_email, email_client=email_client)
