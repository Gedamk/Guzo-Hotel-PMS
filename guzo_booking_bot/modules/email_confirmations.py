# guzo_booking_bot/modules/email_confirmations.py
#
# Centralized SendGrid email sender for booking confirmations.
# - Reads SENDGRID_API_KEY and DEFAULT_FROM_EMAIL from env
# - Builds a nice HTML confirmation email
# - Handles errors and logs them clearly

from __future__ import annotations

import os
import logging
from typing import List, Optional, Dict, Any

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger(__name__)


def _get_sendgrid_client() -> SendGridAPIClient:
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        raise RuntimeError("SENDGRID_API_KEY is not set in environment")
    return SendGridAPIClient(api_key)


def _build_booking_html(
    *,
    hotel_name: str,
    property_code: str,
    guest_name: str,
    check_in: str,
    check_out: str,
    nights: int,
    total_amount_etb: float,
    payment_method: Optional[str] = None,
    confirmation_id: Optional[str] = None,
) -> str:
    """
    Simple HTML template for booking confirmation.
    Uses .format(), so double-curly braces are used for CSS blocks.
    """

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Booking Confirmation - {hotel_name}</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      background-color: #f5f5f5;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 600px;
      margin: 24px auto;
      background-color: #ffffff;
      border-radius: 8px;
      padding: 24px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }}
    .header {{
      border-bottom: 1px solid #e5e5e5;
      padding-bottom: 16px;
      margin-bottom: 16px;
    }}
    .hotel-name {{
      font-size: 20px;
      font-weight: bold;
      margin: 0;
    }}
    .property-code {{
      color: #888888;
      font-size: 12px;
    }}
    .section-title {{
      font-size: 16px;
      font-weight: bold;
      margin-top: 16px;
      margin-bottom: 8px;
    }}
    .details-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    .details-table th,
    .details-table td {{
      text-align: left;
      padding: 4px 0;
    }}
    .details-label {{
      width: 40%;
      color: #666666;
    }}
    .details-value {{
      width: 60%;
      font-weight: 500;
    }}
    .total-amount {{
      font-size: 18px;
      font-weight: bold;
      color: #2c7a7b;
      margin-top: 8px;
    }}
    .footer {{
      margin-top: 24px;
      font-size: 12px;
      color: #777777;
      border-top: 1px solid #e5e5e5;
      padding-top: 12px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <p class="hotel-name">{hotel_name}</p>
      <p class="property-code">Property Code: {property_code}</p>
    </div>

    <p>Dear {guest_name},</p>

    <p>Thank you for choosing <strong>{hotel_name}</strong>. Your booking has been confirmed.</p>

    <div class="section">
      <p class="section-title">Booking Details</p>
      <table class="details-table">
        <tr>
          <td class="details-label">Check-in</td>
          <td class="details-value">{check_in}</td>
        </tr>
        <tr>
          <td class="details-label">Check-out</td>
          <td class="details-value">{check_out}</td>
        </tr>
        <tr>
          <td class="details-label">Nights</td>
          <td class="details-value">{nights}</td>
        </tr>
        <tr>
          <td class="details-label">Total Amount</td>
          <td class="details-value">{total_amount_etb} ETB</td>
        </tr>
        {payment_row}
        {confirmation_row}
      </table>
    </div>

    <p class="total-amount">
      Total: {total_amount_etb} ETB
    </p>

    <p>
      If you have any questions or need to adjust your reservation, please reply to this email
      or contact the hotel directly.
    </p>

    <div class="footer">
      <p>Powered by Guzo Guest Assist – Luxury Hospitality Edition</p>
    </div>
  </div>
</body>
</html>
"""

    if payment_method:
        payment_row = f"""
        <tr>
          <td class="details-label">Payment Method</td>
          <td class="details-value">{payment_method}</td>
        </tr>
        """
    else:
        payment_row = ""

    if confirmation_id:
        confirmation_row = f"""
        <tr>
          <td class="details-label">Confirmation #</td>
          <td class="details-value">{confirmation_id}</td>
        </tr>
        """
    else:
        confirmation_row = ""

    return html_template.format(
        hotel_name=hotel_name,
        property_code=property_code,
        guest_name=guest_name,
        check_in=check_in,
        check_out=check_out,
        nights=nights,
        total_amount_etb=f"{total_amount_etb:,.2f}",
        payment_row=payment_row,
        confirmation_row=confirmation_row,
    )


def send_booking_confirmation_email(
    *,
    to_emails: List[str],
    hotel_name: str,
    property_code: str,
    guest_name: str,
    check_in: str,
    check_out: str,
    nights: int,
    total_amount_etb: float,
    payment_method: Optional[str] = None,
    confirmation_id: Optional[str] = None,
) -> bool:
    """
    Send a booking confirmation email via SendGrid.
    Returns True if 2xx, False otherwise.
    """

    if not to_emails:
        logger.warning("[EmailConfirmations] No recipients provided, skipping email.")
        return False

    default_from = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@guzoassist.com")

    html_body = _build_booking_html(
        hotel_name=hotel_name,
        property_code=property_code,
        guest_name=guest_name,
        check_in=check_in,
        check_out=check_out,
        nights=nights,
        total_amount_etb=total_amount_etb,
        payment_method=payment_method,
        confirmation_id=confirmation_id,
    )

    subject = f"Booking Confirmation – {hotel_name} ({property_code})"

    message = Mail(
        from_email=Email(default_from, name="Guzo Guest Assist"),
        to_emails=[To(email) for email in to_emails],
        subject=subject,
        html_content=Content("text/html", html_body),
    )

    try:
        sg = _get_sendgrid_client()
        response = sg.send(message)
        logger.info(
            "[EmailConfirmations] ✅ Email sent to %s | Status: %s",
            to_emails,
            response.status_code,
        )
        # Treat 2xx as success
        return 200 <= response.status_code < 300

    except Exception as exc:
        logger.error(
            "[EmailConfirmations] ❌ Failed to send email to %s: %s", to_emails, exc
        )
        return False
def send_test_email(to_emails: list[str], hotel_name: str, property_code: str) -> bool:
    """
    Simple smoke-test email (no booking required).
    """
    return send_booking_confirmation_email(
        to_emails=to_emails,
        hotel_name=hotel_name,
        property_code=property_code,
        guest_name="Test Guest (Smoke Test)",
        check_in="2025-11-28",
        check_out="2025-11-29",
        nights=1,
        total_amount_etb=0,   # 0 ETB for testing
        payment_method="N/A",
        confirmation_id="TEST-EMAIL",
    )
