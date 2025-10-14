# -*- coding: utf-8 -*-
"""
Guzo Guest Assist Dashboard v13.5
--------------------------------------------
Unified live hospitality control center for Ethiopian hotels.
Now includes:
úÖ Google Sheets & Multi-Channel Sync
úÖ Weather, Exchange, and Flight updates
úÖ Bilingual AI Auto-Reply
úÖ Live System Health Monitor
úÖ Hotel Directory Analytics
úÖ Auto-Refresh every 60 seconds
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
import os, json, requests, pandas as pd, streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from streamlit_option_menu import option_menu
from streamlit_lottie import st_lottie
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_autorefresh import st_autorefresh # üîÑ auto-refresh

# Fix imports for root-level modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from guzo_booking_bot.reply_flow import generate_auto_reply
from guzo_booking_bot.utils import email_sender

# ======================================================
# öô ENVIRONMENT VARIABLES
# ======================================================
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), override=True)

CITY = os.getenv("CITY", "Addis Ababa")
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY", "")
EXCHANGE_URL = "https://api.exchangerate.host/latest?base=USD&symbols=ETB,EUR,GBP"
GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials_prod.json")

HOTEL_NAME = os.getenv("HOTEL_NAME", "Guzo Guest Assist")
MANAGER_NAME = os.getenv("MANAGER_NAME", "Manager")
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "+251900000000")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "info@guzoassist.com")

# ======================================================
# üîÑ AUTO REFRESH (every 60 seconds)
# ======================================================
refresh_interval = int(os.getenv("REFRESH_INTERVAL", 60)) # default = 60 seconds
st_autorefresh(interval=refresh_interval * 1000, key="data_refresh")
st.caption(f" Dashboard auto-refreshes every {refresh_interval} seconds.")

# ======================================================
# üß© SYSTEM STATUS
# ======================================================
def system_status():
  """Check connection status for all APIs."""
  status = {
    "Google Sheets": os.path.exists(GOOGLE_CREDS),
    "Weather API": bool(WEATHER_API_KEY),
    "Flights API": bool(AVIATIONSTACK_API_KEY),
    "Email (SendGrid)": bool(os.getenv("SENDGRID_API_KEY")),
    "Telegram Bot": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
    "Twilio SMS": bool(os.getenv("TWILIO_ACCOUNT_SID")),
  }
  return status

# ======================================================
# üßæ GOOGLE SHEETS CONNECTION
# ======================================================
def get_sheet_data():
  """Fetch guest data safely from Google Sheets with clear error messages."""
  try:
    if not os.path.exists(GOOGLE_CREDS):
      st.warning("ö Google credentials file missing.")
      return pd.DataFrame()

    scope = [
      "https://spreadsheets.google.com/feeds",
      "https://www.googleapis.com/auth/spreadsheets",
      "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS, scope)
    client = gspread.authorize(creds)

    sheet_name = os.getenv("SHEET_NAME", "Guest_Bookings")
    spreadsheet = client.open(sheet_name)
    worksheet = spreadsheet.sheet1
    data = worksheet.get_all_records()

    if not data:
      st.info("Ñπ Google Sheet is empty or has no headers yet.")
      return pd.DataFrame()

    df = pd.DataFrame(data)
    if "Timestamp" in df.columns:
      df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

    st.success(f"úÖ Loaded {len(df)} records from Google Sheet: {sheet_name}")
    return df

  except gspread.SpreadsheetNotFound:
    st.error("ö Could not find spreadsheet. Check the name and sharing permissions.")
    return pd.DataFrame()
  except Exception as e:
    st.error(f"ö Google Sheets Error: {str(e)}")
    return pd.DataFrame()

# ======================================================
# üóÇ LOCAL LOGS
# ======================================================
def get_local_logs():
  """Read messages from the local log CSV (Telegram, Email, etc.)"""
  try:
    log_path = os.path.join("guzo_booking_bot", "utils", "messages_log.csv")
    if not os.path.exists(log_path):
      return pd.DataFrame(columns=["timestamp", "source", "sender", "message"])
    df = pd.read_csv(log_path, names=["timestamp", "source", "sender", "message"], header=None)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df
  except Exception as e:
    st.error(f"ö Error reading messages_log.csv: {e}")
    return pd.DataFrame()

# ======================================================
# òÄ WEATHER
# ======================================================
def get_weather(city=CITY):
  if not WEATHER_API_KEY:
    return {"error": "Missing OpenWeather API key."}
  try:
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    r = requests.get(url, timeout=5)
    data = r.json()
    if r.status_code == 200:
      return {
        "city": city,
        "temp": data["main"]["temp"],
        "desc": data["weather"][0]["description"].capitalize(),
        "humidity": data["main"]["humidity"],
        "wind": data["wind"]["speed"],
      }
    return {"error": data.get("message", "Failed to fetch weather")}
  except Exception as e:
    return {"error": str(e)}

# ======================================================
# ü± EXCHANGE RATES
# ======================================================
def get_exchange_rates():
  try:
    r = requests.get(EXCHANGE_URL, timeout=5)
    data = r.json()
    rates = data.get("rates", {})
    return {
      "USD_ETB": float(rates.get("ETB", 0)),
      "EUR_ETB": float(rates.get("EUR", 0)),
      "GBP_ETB": float(rates.get("GBP", 0)),
    }
  except Exception:
    return {"USD_ETB": 0, "EUR_ETB": 0, "GBP_ETB": 0}

# ======================================================
# úà FLIGHTS
# ======================================================
def get_flights():
  if not AVIATIONSTACK_API_KEY:
    return {"error": "Missing AviationStack API key."}
  try:
    url = (
      f"http://api.aviationstack.com/v1/flights?"
      f"access_key={AVIATIONSTACK_API_KEY}&airline_name=Ethiopian Airlines&limit=5"
    )
    r = requests.get(url, timeout=8)
    data = r.json()
    if "data" not in data:
      return {"error": data.get("error", {}).get("message", "No flight data")}
    flights = []
    for f in data["data"]:
      flights.append({
        "flight": f.get("flight", {}).get("iata", "N/A"),
        "to": f.get("arrival", {}).get("airport", "Unknown"),
        "status": f.get("flight_status", "N/A"),
      })
    return flights
  except Exception as e:
    return {"error": str(e)}

# ======================================================
# ü® STREAMLIT CONFIG + STYLES
# ======================================================
st.set_page_config(page_title="Guzo Guest Assist", page_icon="üå", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
html,body,[class*="css"]{font-family:'Poppins',sans-serif;}
h1,h2,h3,h4{color:#004225;letter-spacing:0.5px;}
.card{background:#fff9f0;border-radius:14px;padding:15px;margin-bottom:10px;
box-shadow:0 2px 6px rgba(0,0,0,0.05);}
.status-card{background-color:#fefaf5;border-radius:10px;padding:12px 15px;margin:6px;
box-shadow:0 2px 5px rgba(0,0,0,0.05);font-weight:500;}
.status-ok{color:#008000;font-weight:700;}
.status-bad{color:#d00000;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ======================================================
# üå HEADER & SYSTEM STATUS
# ======================================================
st.title(f"üå {HOTEL_NAME} Äî Hospitality Control Center")
st.caption(f"Managed by {MANAGER_NAME} | üìû {SUPPORT_PHONE} | úâ {SUPPORT_EMAIL}")
st.markdown("---")

st.subheader("üõ System Connection Status")
statuses = system_status()
cols = st.columns(3)
for i, (service, connected) in enumerate(statuses.items()):
  with cols[i % 3]:
    badge = "üü Online" if connected else "üî Offline"
    badge_class = "status-ok" if connected else "status-bad"
    st.markdown(
      f"""
      <div class="status-card">
        <span style='font-size:16px'>{service}</span><br>
        <span class='{badge_class}'>{badge}</span>
      </div>
      """,
      unsafe_allow_html=True,
    )
st.caption(f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("---")

# ======================================================
# üîò NAVIGATION MENU
# ======================================================
selected = option_menu(
  None,
  ["ü Overview", "üì Insights", "ü Guests", "öô Settings"],
  icons=["house", "bar-chart", "chat-dots", "gear"],
  orientation="horizontal",
  styles={
    "container": {"background-color": "#fefcf8"},
    "icon": {"color": "#004225", "font-size": "18px"},
    "nav-link": {"font-size": "16px","text-align":"center",
           "margin":"0px 8px","border-radius":"8px",
           "color":"#222","background-color":"#f8f0e3"},
    "nav-link-selected": {"background-color":"#004225","color":"white"},
  },
)

# ======================================================
# üì LOAD DATA
# ======================================================
sheet_df = get_sheet_data()
local_df = get_local_logs()
if not sheet_df.empty and "Timestamp" not in sheet_df.columns:
  sheet_df.rename(columns={"timestamp":"Timestamp"}, inplace=True)
if not local_df.empty and "timestamp" in local_df.columns:
  local_df.rename(columns={"timestamp":"Timestamp"}, inplace=True)
df_msgs = pd.concat([sheet_df, local_df], ignore_index=True).drop_duplicates()

# ======================================================
# ü OVERVIEW
# ======================================================
if selected == "ü Overview":
  st.subheader("ü® Hotel Overview & Live Insights")
  col1,col2,col3,col4 = st.columns(4)
  col1.metric("ü Properties", 1)
  col2.metric("ü Messages", len(df_msgs))
  col3.metric("üë• Guests", len(df_msgs["sender"].unique()) if not df_msgs.empty else 0)
  col4.metric("üï Last Sync", datetime.now().strftime("%Y-%m-%d %H:%M"))

  st.markdown("### òÄ Weather Ä ü± Exchange Ä úà Flights")
  wcol, ecol, fcol = st.columns(3)

  with wcol:
    weather = get_weather()
    if "error" in weather:
      st.error(weather["error"])
    else:
      st.metric("üå° Temp", f"{weather['temp']}∞C", weather["desc"])

  with ecol:
    rates = get_exchange_rates()
    st.metric("USDÜETB", f"{rates['USD_ETB']:.2f}")
    st.metric("EURÜETB", f"{rates['EUR_ETB']:.2f}")

  with fcol:
    flights = get_flights()
    if isinstance(flights, dict) and "error" in flights:
      st.error(flights["error"])
    elif flights:
      st.write("úà Ethiopian Airlines:")
      for f in flights:
        st.write(f"**{f['flight']}** Ü {f['to']} ({f['status']})")

# ======================================================
# üìà INSIGHTS
# ======================================================
elif selected == "üì Insights":
  st.subheader("üìÖ Daily Message Trends")
  if not df_msgs.empty and "Timestamp" in df_msgs.columns:
    df_msgs["date"] = df_msgs["Timestamp"].dt.date
    daily = df_msgs.groupby("date").size().reset_index(name="Messages")
    st.line_chart(daily.set_index("date"))
  else:
    st.info("No message data available yet.")

# ======================================================
# ü GUESTS
# ======================================================
elif selected == "ü Guests":
  st.subheader("üìñ Guest Communication Log")
  if df_msgs.empty:
    st.warning("No chat data yet.")
  else:
    st.dataframe(df_msgs.sort_values("Timestamp", ascending=False).head(25), width="stretch")
    st.markdown("### ü§ñ Auto-Reply Intelligence")
    example_msg = st.text_input("Enter guest message:", "Hi, do you have available rooms for tomorrow?")
    if st.button("Generate Reply"):
      reply = generate_auto_reply(example_msg)
      st.success("úÖ Bilingual Auto-Reply:")
      st.write(reply)

# ======================================================
# öô SETTINGS
# ======================================================
elif selected == "öô Settings":
  st.subheader("öô Dashboard Settings")
  st.text_input("Hotel Manager Email", SUPPORT_EMAIL)
  st.checkbox("Enable Dark Mode (coming soon)")

# ======================================================
# üßæ FOOTER
# ======================================================
st.markdown("---")
st.caption("© 2025 Guzo Guest Assist Ä Real-time Insights Ä Designed for Ethiopian Hospitality Excellence üº")
