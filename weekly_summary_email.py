import os, datetime
from dotenv import load_dotenv
from guzo_backend.modules import google_sheets, email_sender

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
MASTER_ID = os.getenv("HOTEL_CONTACT_SHEET_ID")

def send_weekly_summaries():
    client = google_sheets.init_client()
    ws = client.open_by_key(MASTER_ID).sheet1
    for r in ws.get_all_records():
        name, sheet_id, email = r["Hotel Name"], r["Sheet ID"], r["Main Contact Email"]
        if not (sheet_id and email): continue
        try:
            tab = client.open_by_key(sheet_id).worksheet("Weekly_Summary")
            rows = tab.get_all_records()
            if not rows: continue
            last = rows[-1]
            msg = (
                f"🏨 Weekly Summary – {name}\n"
                f"📅 {last['Week Start']} → {last['Week End']}\n"
                f"Bookings: {last['Total Bookings']}\n"
                f"Revenue: {last['Total Revenue (ETB)']} ETB\n"
                f"Occupancy: {last['Occupancy (%)']} %\n"
                f"Notes: {last['Notes']}"
            )
            email_sender.send_email(email, f"Weekly Summary – {name}", msg)
            print(f"[Summary] Sent to {name}")
        except Exception as e:
            print(f"[Summary Error] {name}: {e}")

if __name__ == "__main__":
    print("[Weekly Summary] Running report job...")
    send_weekly_summaries()
