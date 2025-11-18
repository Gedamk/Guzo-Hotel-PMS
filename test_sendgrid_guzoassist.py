# -*- coding: utf-8 -*-
"""
Test SendGrid integration for Guzo Guest Assist
"""

import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

FROM_EMAIL = "info@guzoassist.com"
TO_EMAIL = "yourpersonal@gmail.com"  # replace with a real inbox you can check

message = Mail(
    from_email=FROM_EMAIL,
    to_emails=TO_EMAIL,
    subject="✅ Guzo Guest Assist Email Test",
    html_content="""
    <h2>Guzo Guest Assist System Test</h2>
    <p>Your domain authentication is working perfectly.</p>
    <p>All guest confirmations and weekly reports will now be sent from <b>info@guzoassist.com</b>.</p>
    """
)

try:
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print("✅ Email sent successfully!")
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print("❌ Error sending email:")
    print(e)
