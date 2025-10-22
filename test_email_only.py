# -*- coding: utf-8 -*-
"""
Plain-text SendGrid email test for Guzo Guest Assist (clean version)
"""
import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv(dotenv_path=".env", override=True)

api_key = os.getenv("SENDGRID_API_KEY")
from_email = os.getenv("SENDER_EMAIL")
to_email = os.getenv("TEST_EMAIL", from_email)

print("\n--- Testing SendGrid Email Communication ---\n")

if not api_key:
    print("Missing SENDGRID_API_KEY in .env")
elif not from_email:
    print("Missing SENDER_EMAIL in .env")
else:
    try:
        print(f"Using sender: {from_email}")
        print(f"Sending test email to: {to_email}\n")

        sg = SendGridAPIClient(api_key)
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject="Guzo Guest Assist Email Test",
            html_content="<strong>This is a test email from Guzo Guest Assist.</strong>",
        )
        response = sg.send(message)

        if response.status_code == 202:
            print("Email sent successfully via SendGrid!")
        else:
            print(f"SendGrid returned HTTP {response.status_code}: {response.body.decode()}")
    except Exception as e:
        print("SendGrid Email error:", e)

print("\n--- Test Complete ---\n")
