# Guzo Guest Assist – Demo Runbook

End-to-end demo: Front Desk & Housekeeping Portfolio Console.

---

## 1. Start backend (FastAPI)

Open a terminal (Git Bash or CMD) and run:

```bash
cd C:/Users/Gedan/Desktop/Guzo
source venv/Scripts/activate
uvicorn guzo_backend.main:app --reload --port 8000

## 1. Start backend

cd C:/Users/Gedan/Desktop/Guzo
source venv/Scripts/activate
uvicorn guzo_backend.main:app --reload --port 8000

## 2. Start frontend (production build)

cd C:/Users/Gedan/Desktop/Guzo/dashboard_ui
serve -s build -l 3000

## 3. Open in browser

http://localhost:3000


## 3. Create a demo booking via Telegram integration (simulated)

Instead of using a real Telegram bot, we simulate an incoming booking
by calling the FastAPI integration endpoint.

In a new terminal:

```bash
cd C:/Users/Gedan/Desktop/Guzo
source venv/Scripts/activate

curl -X POST "http://127.0.0.1:8000/integrations/telegram/bookings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-secret-123" \
  -d '{
    "property_code": "DRE001",
    "guest_name": "Telegram Demo Guest",
    "check_in_date": "2025-12-02",
    "check_out_date": "2025-12-04",
    "room_type": "Single",
    "room_number": "201",
    "total_amount_etb": 3000,
    "notes": "Test from curl"
  }'
