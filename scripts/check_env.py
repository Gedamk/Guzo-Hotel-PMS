import os
from dotenv import load_dotenv

def check_env():
    load_dotenv()  # Load variables from .env if present

    issues = []

    # Required for Gmail
    gmail_email = os.getenv("GMAIL_EMAIL")
    gmail_pass = os.getenv("GMAIL_PASSWORD")

    if not gmail_email:
        issues.append("Ã¢ÂÂ GMAIL_EMAIL is missing.")
    elif "@" not in gmail_email:
        issues.append("Ã¢ÂÂ GMAIL_EMAIL does not look like a valid email.")

    if not gmail_pass:
        issues.append("Ã¢ÂÂ GMAIL_PASSWORD is missing.")
    elif len(gmail_pass) != 16:
        issues.append("Ã¢ÂÂ Ã¯Â¸Â GMAIL_PASSWORD should be a 16-character App Password.")

    # Optional checks for other services
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    if not telegram_token:
        issues.append("Ã¢ÂÂ Ã¯Â¸Â TELEGRAM_TOKEN is missing (Telegram bot wonÃ¢ÂÂt work).")

    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not twilio_sid or not twilio_token:
        issues.append("Ã¢ÂÂ Ã¯Â¸Â Twilio credentials are missing (SMS/WhatsApp wonÃ¢ÂÂt work).")

    stripe_key = os.getenv("STRIPE_API_KEY")
    if not stripe_key:
        issues.append("Ã¢ÂÂ Ã¯Â¸Â STRIPE_API_KEY is missing (payments wonÃ¢ÂÂt work).")

    # Summary
    if not issues:
        print("Ã¢ÂÂ All required environment variables look valid!")
    else:
        print("\n".join(issues))


if __name__ == "__main__":
    print("Ã°ÂÂÂ Checking environment configuration...\n")
    check_env()
