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
