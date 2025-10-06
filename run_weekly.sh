#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/c/Users/Gedan/Desktop/Guzo"
PY="$PROJECT_DIR/venv/Scripts/python.exe"
LOG="$PROJECT_DIR/logs/weekly_summary.log"

echo "[$(date '+%F %T')] Running weekly summary..." >> "$LOG"

cd "$PROJECT_DIR"
"$PY" weekly_summary.py >> "$LOG" 2>&1

echo "[$(date '+%F %T')] Weekly summary complete." >> "$LOG"
echo "✅ Weekly summary tasks finished."
