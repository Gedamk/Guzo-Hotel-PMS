#!/usr/bin/env bash
cd "$(dirname "$0")"

# Start backend in background
source venv/Scripts/activate
uvicorn guzo_backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start React dashboard
cd dashboard_ui
npm start

# When React stops, kill backend
kill $BACKEND_PID 2>/dev/null || true
