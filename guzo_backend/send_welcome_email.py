# -*- coding: utf-8 -*-
"""
send_welcome_email.py – Guzo Guest Assist
-----------------------------------------
Sends a high-standard bilingual (English + Amharic) welcome email
to new partner hotels upon onboarding.

Attachments:
 - Guzo_Guest_Assist_Hotel_Partnership_Brochure.pdf
 - Guzo_Guest_Assist_Hotel_Onboarding_Guide.pdf

Uses the upgraded SendGrid-based email_sender.py module.
"""

import os
from guzo_backend.modules.email_sender import send_email as send_invoice_email



def send_welcome_email(hotel_name: str, recipient_email: str):
    """Send a bilingual hospitality-standard welcome email with attachments."""

    subject = f"🌟 እንኳን ወደ ጉዞ ገስት አሲስት መጡ | Welcome to Guzo Guest Assist, {hotel_name} 🌍"

    # Load attachments
    base_path = "guzo_backend/reports"
    brochure_path = os.path.join(base_path, "Guzo_Guest_Assist_Hotel_Partnership_Brochure.pdf")
    guide_path = os.path.join(base_path, "Guzo_Guest_Assist_Hotel_Onboarding_Guide.pdf")

    body_html = f"""
    <html>
    <body style="font-family:Arial,'Noto Sans Ethiopic',sans-serif;background-color:#f9f9f9;color:#333;padding:30px;">
    <div style="max-width:700px;margin:auto;background:#fff;border:1px solid #ddd;border-radius:10px;padding:30px;">
      <h2 style="color:#002147;text-align:center;">🏨 Welcome to Guzo Guest Assist</h2>
      <p style="font-size:15px;line-height:1.7;">
        Dear <b>{hotel_name}</b> Team,<br><br>
        It is our great pleasure to welcome you to <b>Guzo Guest Assist</b> — your hotel’s digital companion for
        guest communication, reporting, and performance visibility.<br><br>
        Our commitment is to bring you the same standard of excellence practiced by
        the world’s top hotels, powered by automation and hospitality intelligence.
      </p>

      <h3 style="color:#b8860b;">📘 Your Next Steps:</h3>
      <ol style="font-size:15px;line-height:1.7;">
        <li>Access your personalized Google Sheet (Bookings_Log, Rack_Rates, Weekly_Summary).</li>
        <li>Connect on Telegram: Search <b>@GuzoGuestAssistBot</b> and send “Start”.</li>
        <li>Check your inbox for your first test report from <b>reports@guzoassist.com</b>.</li>
      </ol>

      <p style="font-size:15px;">📎 <b>Attached:</b></p>
      <ul style="font-size:15px;">
        <li>🏨 Hotel Partnership Brochure</li>
        <li>📘 Hotel Onboarding Guide</li>
      </ul>

      <div style="background-color:#002147;color:white;border-radius:6px;text-align:center;padding:15px;margin-top:25px;">
        <h3 style="margin:0;">💬 Schedule Your Free Demo</h3>
        <a href="https://www.guzoassist.com/demo"
           style="display:inline-block;margin-top:10px;background:#b8860b;color:#fff;padding:10px 20px;border-radius:5px;text-decoration:none;font-weight:bold;">
           Schedule a Demo Session
        </a>
      </div>

      <hr style="border:none;border-top:2px solid #b8860b;margin:40px 0 20px;">
      <h2 style="color:#002147;text-align:center;">እንኳን ወደ ጉዞ ገስት አሲስት በደህና መጡ!</h2>
      <p style="font-size:15px;line-height:1.7;">
        እንኳን ወደ ጉዞ ገስት አሲስት መጡ። ይህ ፕላትፎርም ለሆቴሎች የቀን እና የሳምንት ሪፖርቶችን በራስ-ሰር የሚያዘጋጅ እና የእንግዶችን ግንኙነት የሚያሳድግ ነው።<br>
        በጉዞ ገስት አሲስት የእንግዶችን ግንኙነት እና የአፈፃፀም ሪፖርት በቀላሉ ትቆጣጠራለህ።<br><br>
        እንኳን ደህና መጡ፣ እና በተሻለ አገልግሎት እንዲታወቁ እናመናለን።
      </p>

      <p style="font-size:13px;margin-top:25px;color:#555;">
        Warm regards,<br>
        <b>Gedam Kacha</b><br>
        Founder & Project Lead<br>
        📧 owner@guzoassist.com | 🌐 www.guzoassist.com | 📍 Addis Ababa, Ethiopia
      </p>
    </div>
    </body></html>
    """

    body_text = f"""
    Welcome to Guzo Guest Assist, {hotel_name}!

    We're delighted to have your hotel join our automation platform for guest communication and reporting.

    Next Steps:
    1. Access your Google Sheet (Bookings_Log, Rack_Rates, Weekly_Summary)
    2. Connect on Telegram: @GuzoGuestAssistBot → Send “Start”
    3. Check your inbox for a test report from reports@guzoassist.com

    እንኳን ወደ ጉዞ ገስት አሲስት በደህና መጡ።
    ይህ ፕላትፎርም ለሆቴሎች የእንግዶችን ግንኙነት እና የሪፖርት ሥራዎችን በራስ ሰር የሚያከናውን ነው።

    Warm regards,
    Gedam Kacha
    Founder & Project Lead
    www.guzoassist.com
    """

    send_invoice_email(
    recipient_email,
    subject,
    body_html,
    html=True
)


    print(f"✅ Bilingual welcome email sent successfully to {hotel_name} ({recipient_email})")


if __name__ == "__main__":
    send_welcome_email("Sofi Hotel", "manager@sofihotel.com")
