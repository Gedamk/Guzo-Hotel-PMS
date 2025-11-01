from twilio.rest import Client
import os

def send_message(to, text):
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    client.messages.create(
        body=text,
        from_=os.getenv("TWILIO_SMS_NUMBER"),
        to=to
    )
