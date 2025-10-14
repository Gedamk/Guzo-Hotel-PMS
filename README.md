# 🌍 Guzo Booking / Guest Assist

AI-assisted hospitality & booking automation system tailored for Ethiopia, with global scalability.

---

## 🚀 Features
- ✅ Booking sync with Google Sheets  
- ✅ Secure multi-payment integration (Stripe, Telebirr, PayPal)  
- ✅ Automated multilingual receipts (Amharic, Afaan Oromo, English)  
- ✅ Alerts via Email, Telegram, SMS (Twilio), WhatsApp  
- ✅ Health & monitoring scripts (daily, weekly, system health)  
- ✅ Retry handling for failed notifications  
- ✅ Extensible for AI-driven guest support  

---

## 📦 Project Structure

guzo_booking_bot/
modules/
logs/
storage/
run_booking_bot.py
system_health.py
weekly_summary.py
---

## 🔧 Setup
```bash
# 1. Clone
git clone https://github.com/Gedamk/Guzo-Booking.git
cd Guzo-Booking

# 2. Virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env   # create your own .env with real keys
