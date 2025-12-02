# Guzo Guest Assist – Demo Runbook

End-to-end demo: Front Desk & Housekeeping Portfolio Console.

---

## 1. Start backend (FastAPI)

Open a terminal (Git Bash or CMD) and run:

```bash
cd C:/Users/Gedan/Desktop/Guzo
source venv/Scripts/activate
uvicorn guzo_backend.main:app --reload --port 8000
