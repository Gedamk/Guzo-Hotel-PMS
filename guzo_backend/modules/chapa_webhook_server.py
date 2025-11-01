# -*- coding: utf-8 -*-
"""
chapa_webhook_server.py – Secure Webhook Receiver for Guzo Guest Assist
-----------------------------------------------------------------------
Receives Chapa payment confirmations, validates authenticity,
updates booking status in Google Sheets, and securely logs all payloads.
"""

import os
import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from guzo_backend.modules.google_sheets import update_payment_status

# ---------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------
load_dotenv(dotenv_path="C:/Users/Gedan/Desktop/Guzo/.env", override=True)

HOST = os.getenv("CHAPA_WEBHOOK_HOST", "0.0.0.0")
PORT = int(os.getenv("CHAPA_WEBHOOK_PORT", 8000))
WEBHOOK_SECRET = os.getenv("CHAPA_WEBHOOK_SECRET", "guzo_webhook_secret")

# ---------------------------------------------------------------------
# File & Directory Setup
# ---------------------------------------------------------------------
BASE_DIR = os.path.join(os.path.dirname(__file__), "../../")
LOG_DIR = os.path.join(BASE_DIR, "logs/webhooks")
FAILED_DIR = os.path.join(LOG_DIR, "failed")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)

write_lock = threading.Lock()  # prevents simultaneous writes

# ---------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------
def save_webhook_log(payload: dict, filename_prefix="webhook", status="received"):
    """Save webhook payload safely into JSON log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    day_log_file = os.path.join(LOG_DIR, f"{datetime.now().date()}.json")

    entry = {
        "timestamp": timestamp,
        "status": status,
        "payload": payload,
    }

    try:
        with write_lock:
            if os.path.exists(day_log_file):
                with open(day_log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = []

            data.append(entry)
            with open(day_log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"💾 Log write error: {e}")


def save_failed_update(payload: dict, reason: str):
    """Save failed updates for later re-processing."""
    filename = os.path.join(
        FAILED_DIR, f"failed_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    )
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"reason": reason, "payload": payload}, f, indent=2, ensure_ascii=False)
    print(f"⚠️ Saved failed update → {filename}")


# ---------------------------------------------------------------------
# Webhook Handler
# ---------------------------------------------------------------------
class ChapaWebhookHandler(BaseHTTPRequestHandler):
    """Handles secure POST requests from Chapa."""

    def _set_response(self, code=200):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def log_message(self, format, *args):
        """Silence default HTTP logs."""
        return

    def do_GET(self):
        """Health check route."""
        self._set_response(200)
        self.wfile.write(b'{"status": "Webhook server running"}')

    def do_POST(self):
        """Process incoming Chapa payment notifications."""
        try:
            # Read and parse JSON
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="ignore")
            data = json.loads(body)

            # Validate secret
            received_secret = self.headers.get("X-Webhook-Secret", "")
            if not received_secret or received_secret != WEBHOOK_SECRET:
                print("🚫  Unauthorized webhook attempt detected.")
                self._set_response(403)
                self.wfile.write(b'{"error": "Forbidden"}')
                save_webhook_log(data, status="forbidden")
                return

            print(f"✅ Webhook received → {datetime.now().isoformat()}")
            print(f"🧾 Reference: {data.get('reference') or data.get('tx_ref', 'N/A')}")

            # Always log incoming webhook
            save_webhook_log(data, status="received")

            # Extract info
            confirmation_id = (
                data.get("customization", {}).get("title")
                or data.get("reference")
                or data.get("tx_ref")
            )
            amount = data.get("amount", "")
            currency = data.get("currency", "ETB")

            if not confirmation_id:
                print("⚠️ No confirmation ID found.")
                save_failed_update(data, "missing_confirmation_id")
                self._set_response(400)
                self.wfile.write(b'{"error": "Missing confirmation ID"}')
                return

            # Update Google Sheets
            print(f"🔄 Updating Google Sheet for: {confirmation_id}")
            success = update_payment_status(confirmation_id, amount, currency)

            if success:
                print(f"✅ Payment update successful for {confirmation_id}")
                save_webhook_log(data, status="success")
                self._set_response(200)
                self.wfile.write(b'{"status": "Payment updated successfully"}')
            else:
                print(f"⚠️ Payment update failed for {confirmation_id}")
                save_failed_update(data, "sheet_update_failed")
                self._set_response(500)
                self.wfile.write(b'{"error": "Payment update failed"}')

        except json.JSONDecodeError:
            print("❌ Invalid JSON payload received.")
            self._set_response(400)
            self.wfile.write(b'{"error": "Invalid JSON"}')

        except Exception as e:
            print(f"💥 Unexpected server error: {e}")
            save_failed_update({"error": str(e)}, "unexpected_exception")
            self._set_response(500)
            self.wfile.write(b'{"error": "Internal server error"}')


# ---------------------------------------------------------------------
# Run Server
# ---------------------------------------------------------------------
def run_server():
    """Start secure webhook listener."""
    try:
        server = HTTPServer((HOST, PORT), ChapaWebhookHandler)
        print("🚀 Guzo Secure Chapa Webhook Server")
        print(f"🌐 Listening on http://{HOST}:{PORT}")
        print("📡 Waiting for incoming POST requests... (Ctrl+C to stop)\n")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user.")
    except Exception as e:
        print(f"💥 Critical startup error: {e}")


# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    run_server()

