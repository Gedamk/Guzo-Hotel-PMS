# -*- coding: utf-8 -*-
"""
runner.py – Multi-Bot Launcher for Guzo Guest Assist
----------------------------------------------------
• Launches one Telegram bot per hotel property
• Prefers Google Sheet ('Hotel_Contacts_Master'); falls back to hotels_config.json
• Each bot runs concurrently and keeps polling until you stop the process
"""

import asyncio
import json
import os
import sys

from telegram.ext import ApplicationBuilder, MessageHandler, filters
from telegram.request import HTTPXRequest  # stable HTTP client with timeouts

# Ensure package root is importable when running as script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from guzo_booking_bot.modules.message_router_v65_trilingual_complete import (
    handle_message,
)


def _norm(s):
    return str(s).strip() if s is not None else ""


def load_hotels():
    """
    Load hotel list for multi-bot runner.
    Priority:
      1) Google Sheet 'Hotel_Contacts_Master'
      2) Local hotels_config.json fallback ({"HOTELS":[...]})

    Returns: [{"Property Code","Telegram Bot Token","Sheet ID"}, ...]
    """
    # 1) Try Google Sheet (flexible headers)
    try:
        from guzo_backend.modules import google_sheets

        df = google_sheets.read_hotels_master()
        rows = []
        if df is not None and not df.empty:
            for _, r in df.iterrows():
                code = _norm(r.get("Property Code") or r.get("id") or r.get("CODE"))
                token = _norm(
                    r.get("Telegram Bot Token")
                    or r.get("telegram_bot_token")
                    or r.get("TOKEN")
                )
                sid = _norm(r.get("Sheet ID") or r.get("sheet_id"))
                if code and token:
                    rows.append(
                        {
                            "Property Code": code,
                            "Telegram Bot Token": token,
                            "Sheet ID": sid,
                        }
                    )
        if rows:
            # de-dupe by property code
            rows = list({h["Property Code"]: h for h in rows}.values())
            print(f"[Runner] ✅ Loaded {len(rows)} hotel(s) from Google Sheet.")
            return rows
        else:
            print("[Runner] ⚠️ Sheet empty or headers mismatch; using JSON fallback.")
    except Exception as e:
        print(f"[Runner] ⚠️ Google Sheet not available ({e}); using JSON fallback.")

    # 2) JSON fallback
    cfg_path = os.path.join(ROOT, "hotels_config.json")
    print(f"[Runner] 🔎 Reading JSON fallback: {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    hotels = []
    for h in (data.get("HOTELS") or []):
        code = _norm(h.get("Property Code") or h.get("id"))
        token = _norm(h.get("Telegram Bot Token") or h.get("telegram_bot_token"))
        sid = _norm(h.get("Sheet ID") or h.get("sheet_id"))
        if code and token:
            hotels.append(
                {"Property Code": code, "Telegram Bot Token": token, "Sheet ID": sid}
            )

    # de-dupe by property code
    hotels = list({h["Property Code"]: h for h in hotels}.values())
    print(f"[Runner] ✅ Loaded {len(hotels)} hotel(s) from JSON fallback.")
    return hotels


async def launch_all_bots():
    """
    Initialize and start all hotel bots, then keep the process alive.
    We:
      • initialize + start each Application
      • call updater.start_polling() ONCE per bot
      • then just sleep forever until the program is interrupted
    PTB's internal retry logic will handle NetworkError (httpx.ReadError, etc).
    """
    hotels = load_hotels()
    if not hotels:
        raise RuntimeError("No hotels loaded.")

    apps = []

    # Shared HTTP client with generous timeouts
    request = HTTPXRequest(connect_timeout=20, read_timeout=120)

    for h in hotels:
        token = h["Telegram Bot Token"]
        property_code = h["Property Code"]

        app = (
            ApplicationBuilder()
            .token(token)
            .request(request)  # use HTTPX timeouts
            .build()
        )

        # One handler per app, bound to this property's code
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                lambda u, c, pc=property_code: handle_message(u, c, pc),
            )
        )

        try:
            # Initialize + start the Application
            await app.initialize()
            await app.start()

            # Start polling in the background.
            # In this async setup, start_polling() sets up the loop and returns
            # quickly; the internal updater loop runs in the background.
            await app.updater.start_polling(drop_pending_updates=True, timeout=60)

            print(f"🤖 Started bot for {property_code} — polling...")
            apps.append(app)
        except Exception as e:
            print(f"[Runner] ❌ Failed to start {property_code}: {e}")

    if not apps:
        raise RuntimeError("No bots could be started.")

    print(
        f"[Runner] ✅ All bots started: "
        f"{', '.join(h['Property Code'] for h in hotels)}"
    )
    print("[Runner] ⏳ Polling… Press Ctrl+C to stop.")

    try:
        # Keep the process alive; the actual update loops run inside PTB.
        while True:
            await asyncio.sleep(3600)
    finally:
        # Graceful shutdown for all apps when the task is cancelled / program exits
        print("[Runner] 🛑 Shutting down all bots...")
        for app in apps:
            try:
                await app.stop()
            except Exception:
                pass
            try:
                await app.shutdown()
            except Exception:
                pass
        print("[Runner] ✅ All bots stopped cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(launch_all_bots())
    except KeyboardInterrupt:
        # Nice message on Ctrl+C, everything else is cleaned in finally above
        print("\n[Runner] 🚪 Exit requested by user (Ctrl+C).")
