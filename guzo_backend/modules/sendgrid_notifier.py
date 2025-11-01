# guzo_backend/modules/sendgrid_notifier.py
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from guzo_backend import config

logger = logging.getLogger(__name__)

def send_sendgrid_email(to_email: str, subject: str, plain_text: str, html: str | None = None) -> bool:
    """
    Send an email via SendGrid.
    Returns True if send is accepted (202) or 200.
    """
    api_key = config.SENDGRID_API_KEY
    if not api_key:
        logger.error("SendGrid API key not configured.")
        return False

    if not config.SENDGRID_SENDER_EMAIL:
        logger.error("SendGrid sender email not configured.")
        return False

    message = Mail(
        from_email=(config.SENDGRID_SENDER_EMAIL, config.SENDGRID_SENDER_NAME),
        to_emails=to_email,
        subject=subject,
        plain_text_content=plain_text,
        html_content=html or f"<pre>{plain_text}</pre>",
    )

    try:
        client = SendGridAPIClient(api_key)
        response = client.send(message)
        logger.info("SendGrid response: %s %s", response.status_code, response.body)
        # 202 Accepted is normal for SendGrid
        return response.status_code in (200, 202)
    except Exception as e:
        logger.exception("Failed to send SendGrid email: %s", e)
        return False
