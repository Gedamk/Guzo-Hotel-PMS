#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
send_daily_email.py

Send today's Guzo daily report (PDF + Excel) via SendGrid.

Env vars (in .env or system):
  SENDGRID_API_KEY
  REPORT_EMAIL_FROM
  REPORT_EMAIL_TO   (comma-separated list)
  REPORT_EMAIL_CC   (optional, comma-separated)
"""

import os
import base64
import logging
import datetime as dt

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Email,
    To,
    Cc,
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_env_var(name: str, required: bool = True, default: str | None = None):
    """Read an environment variable, optionally required."""
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"{name} is not set in environment/.env")
    return value


def build_attachment(path: str, mime_type: str) -> Attachment:
    """Create a SendGrid attachment from a file path."""
    logger.info(f"Preparing attachment: %s", path)
    with open(path, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode("utf-8")
    return Attachment(
        FileContent(encoded),
        FileName(os.path.basename(path)),
        FileType(mime_type),
        Disposition("attachment"),
    )


def send_daily_email():
    today = dt.date.today()
    date_str = today.isoformat()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(base_dir, f"daily-{date_str}.pdf")
    xlsx_path = os.path.join(base_dir, f"daily-{date_str}.xlsx")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"Excel file not found: {xlsx_path}")

    logger.info("Using PDF: %s", pdf_path)
    logger.info("Using Excel: %s", xlsx_path)

    api_key = read_env_var("SENDGRID_API_KEY")
    from_email = read_env_var("REPORT_EMAIL_FROM")
    to_emails_raw = read_env_var("REPORT_EMAIL_TO")
    cc_raw = os.getenv("REPORT_EMAIL_CC", "").strip()

    to_list = [e.strip() for e in to_emails_raw.split(",") if e.strip()]
    cc_list = [e.strip() for e in cc_raw.split(",") if e.strip()]

    subject = f"Guzo - Daily Report ({date_str})"
    body_text = (
        f"Dear Team,\n\n"
        f"Attached is your Guzo daily report for {date_str}.\n\n"
        f"Regards,\n"
        f"Guzo Guest Assist Automation"
    )

    message = Mail(
        from_email=Email(from_email),
        to_emails=[To(e) for e in to_list],
        subject=subject,
        plain_text_content=body_text,
    )

    if cc_list:
        message.cc = [Cc(e) for e in cc_list]

          # Add attachments using SendGrid API
    logger.info("Adding PDF attachment...")
    pdf_attachment = build_attachment(pdf_path, "application/pdf")
    message.add_attachment(pdf_attachment)

    logger.info("Adding Excel attachment...")
    xlsx_attachment = build_attachment(xlsx_path, "application/vnd.ms-excel")
    message.add_attachment(xlsx_attachment)


    logger.info("Sending email via SendGrid...")
    sg = SendGridAPIClient(api_key)

    try:
        response = sg.send(message)
        logger.info("Email sent. Status code: %s", response.status_code)
        try:
            body = getattr(response, "body", b"")
            if isinstance(body, bytes):
                body = body.decode("utf-8", errors="ignore")
            logger.info("Response body (truncated): %s", str(body)[:500])
        except Exception:
            pass
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        if hasattr(exc, "body"):
            try:
                err_body = exc.body
                if isinstance(err_body, bytes):
                    err_body = err_body.decode("utf-8", errors="ignore")
                logger.error("Error body: %s", err_body)
            except Exception:
                pass
        raise


if __name__ == "__main__":
    send_daily_email()
