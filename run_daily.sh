#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/c/Users/Gedan/Desktop/Guzo"
PY="$PROJECT_DIR/venv/Scripts/python.exe"
LOG="$PROJECT_DIR/logs/daily_run.log"

mkdir -p "$(dirname "$LOG")"
cd "$PROJECT_DIR"

echo "[$(date '+%F %T')] Starting daily run" >> "$LOG"

# Run tasks (add more as needed)
"$PY" retry_summary.py    >> "$LOG" 2>&1
# "$PY" send_hotels_email.py >> "$LOG" 2>&1
# "$PY" retry_logs.py        >> "$LOG" 2>&1

echo "[$(date '+%F %T')] Daily run complete" >> "$LOG"
echo "✅ All daily tasks complete."
