#!/usr/bin/env bash
cd "$(dirname "$0")"
source venv/Scripts/activate
uvicorn guzo_backend.main:app --reload --port 8000
