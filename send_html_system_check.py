# -*- coding: utf-8 -*-
"""
send_html_system_check.py – Guzo Guest Assist
---------------------------------------------
Reads the system_check_run.log and sends a branded
daily HTML email summarizing health status.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()

LOG_PATH = os.path.join("logs", "system_check_run.log")
TEMPLATE_PATH = os.path.join("backend", "email_templates", "system_health.html")


def build_html_body():
    """Build table rows dynamically from log content."""
    if not os.path.exists(LOG_PATH):
        return "<tr><td colspan='3'>❌ No system_check_run.log found</td></tr>"

    with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    table_rows = ""
    for line in lines[-20:]:  # last 20 lines for daily summary
        if "OK" in line or "✅" in line:
            status_class = "ok"
        elif "ERROR" in line or "❌" in line:
            status_class = "fail"
        elif "WARN" in line or "⚠️" in line:
            status_class = "warn"
        else:
            status_class = ""
        table_rows += f"<tr><td colspan='3' class='{status_class}'>{line.strip()}</td></tr>"

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html_template = f.read()

    return (
        html_template
        .replace("{{ table_rows }}", table_rows)
        .replace("{{ report_date }}", datetime.now().strftime("%A, %B %d, %Y"))
        .replace("{{ generated_time }}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )


def send_health_report():
    """Send HTML system check email via SendGrid."""
    sg_key = os.getenv("SENDGRID_API_KEY")
    to_email = os.getenv("ALERT_EMAIL")
    from_email = os.getenv("SENDER_EMAIL")

    if not sg_key:
        print("❌ Missing SENDGRID_API_KEY")
        return

    html_body = build_html_body()
    subject = f"[Guzo System] Daily Health Report – {datetime.now():%b %d, %Y}"

    try:
        sg = SendGridAPIClient(sg_key)
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_body,
        )
        sg.send(message)
        print(f"✅ System health email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send system health email: {e}")


if __name__ == "__main__":
    send_health_report()
