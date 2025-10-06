#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/c/Users/Gedan/Desktop/Guzo"
PY="$PROJECT_DIR/venv/Scripts/python.exe"
LOG="$PROJECT_DIR/logs/health_check.log"

mkdir -p "$(dirname "$LOG")"
cd "$PROJECT_DIR"

echo "[$(date '+%F %T')] Running daily health check..." >> "$LOG"

# Run the system health check
"$PY" system_health.py >> "$LOG" 2>&1

echo "[$(date '+%F %T')] Health check finished." >> "$LOG"
echo "✅ Daily health check complete."
