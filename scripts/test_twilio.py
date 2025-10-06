# scripts/test_twilio.py
from guzo_booking_bot import config as cfg
from twilio.rest import Client

def test_sms():
    client = Client(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
    try:
        msg = client.messages.create(
            body="✅ Test SMS from Guzo Guest Assist",
            from_=cfg.TWILIO_PHONE_NUMBER,
            to=input("Enter your phone (+countrycode): ").strip()
        )
        print("✅ SMS sent:", msg.sid)
    except Exception as e:
        print("❌ SMS failed:", e)

def test_whatsapp():
    client = Client(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
    try:
        msg = client.messages.create(
            body="✅ Test WhatsApp from Guzo Guest Assist",
            from_=cfg.TWILIO_WHATSAPP_FROM,
            to="whatsapp:" + input("Enter your WhatsApp (+countrycode): ").strip()
        )
        print("✅ WhatsApp sent:", msg.sid)
    except Exception as e:
        print("❌ WhatsApp failed:", e)

if __name__ == "__main__":
    print("Testing Twilio SMS...")
    test_sms()
    print("\nTesting Twilio WhatsApp...")
    test_whatsapp()
