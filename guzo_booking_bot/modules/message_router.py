# -*- coding: utf-8 -*-
"""
message_router_v65_trilingual_complete.py – Guzo Guest Assist Conversational Bot
------------------------------------------------------------------------------
🌍 Luxury Hospitality Edition (English 🇬🇧 | Amharic 🇪🇹 | Afaan Oromo 🇪🇹)
• Auto-language detection & preference storage in Google Sheets
• Dynamic per-hotel data (Bookings, Room_Rates, Hotel_Profile, Weekly_Summary)
• SendGrid email confirmation (guest + hotel)
• Central dashboard sync
• Global five-star concierge tone 🛎️✨

This version is upgraded for multi-bot:
• Each hotel has its own Telegram bot (property_code)
• Guests of a property bot NEVER see a list of other hotels

This version is also upgraded to:
• Save every confirmed booking into PostgreSQL (public.bookings)
"""

import os
import re
import json
import datetime
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    CommandHandler,
    filters,
)
from guzo_backend.modules import google_sheets, email_sender
from guzo_backend.modules.central_sync import sync_booking_to_central  # noqa: F401
from guzo_backend.modules.postgres_hotels import get_hotel_by_property_code
from guzo_backend.modules import postgres_bookings  # ✅ use module, not function
from guzo_backend.modules.postgres_bookings import save_booking_to_postgres


# =====================================================
# ENVIRONMENT – ROOT + PER-BOT OVERRIDE
# =====================================================

# 1) Load shared/root .env (Google Sheets, SendGrid, etc.)
ROOT_ENV_PATH = os.path.join(os.path.dirname(__file__), "../../.env")
print(f"[ENV] Loading ROOT env from: {ROOT_ENV_PATH}")
load_dotenv(dotenv_path=ROOT_ENV_PATH)

# 2) Optional per-bot .env override (central, Dream Big, N&N)
BOT_ENV_PATH = os.getenv("GUZO_BOT_ENV_PATH")
print(f"[ENV] GUZO_BOT_ENV_PATH={BOT_ENV_PATH}")
if BOT_ENV_PATH and os.path.exists(BOT_ENV_PATH):
    print(f"[ENV] Loading BOT env override from: {BOT_ENV_PATH}")
    load_dotenv(dotenv_path=BOT_ENV_PATH, override=True)

# 3) Read mode + property code + tokens AFTER envs are loaded
BOT_MODE = os.getenv("BOT_MODE", "CENTRAL").strip().upper()
HOTEL_PROPERTY_CODE = os.getenv("HOTEL_PROPERTY_CODE", "ALL").strip().upper()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HOTEL_CONTACT_SHEET_ID = os.getenv("HOTEL_CONTACT_SHEET_ID")
DEFAULT_SENDER = "no-reply@guzoassist.com"

print(f"[ENV] BOT_MODE={BOT_MODE}, HOTEL_PROPERTY_CODE={HOTEL_PROPERTY_CODE}")

# Used by multi-bot runner to pin each chat to one hotel
PROPERTY_CODE_KEY = "property_code"

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment.")

# Optional per-property fallback if master sheet is empty
PROPERTY_FALLBACK_NAME = os.getenv("HOTEL_NAME")
PROPERTY_FALLBACK_SHEET_ID = os.getenv("HOTEL_SHEET_ID")
PROPERTY_FALLBACK_RES_EMAIL = os.getenv("HOTEL_RESERVATION_EMAIL")
PROPERTY_FALLBACK_PHONE = os.getenv("HOTEL_PHONE")

# Path to JSON fallback (already used by your runner)
HOTELS_CONFIG_JSON = os.path.join(os.path.dirname(__file__), "../../hotels_config.json")


# =====================================================
# HOTEL ROW HELPERS (unify Sheet + JSON keys)
# =====================================================

def get_hotel_property_code(row: dict) -> str:
    """
    Normalize property code from either:
    - 'Property Code' (Google Sheet style)
    - 'property_code' / 'Property_Code' (JSON style)
    """
    if not isinstance(row, dict):
        return ""
    code = (
        row.get("Property Code")
        or row.get("property_code")
        or row.get("Property_Code")
        or ""
    )
    return str(code).strip().upper()


def get_hotel_name(row: dict) -> str:
    """
    Normalize hotel name from:
    - 'Hotel Name'
    - 'hotel_name'
    - 'name'
    """
    if not isinstance(row, dict):
        return ""
    name = row.get("Hotel Name") or row.get("hotel_name") or row.get("name") or ""
    return str(name).strip()


def get_hotel_sheet_id(row: dict) -> str:
    """
    Normalize sheet id from:
    - 'Sheet ID'
    - 'sheet_id'
    - 'Hotel Sheet ID' / 'Hotel_Sheet_ID'
    """
    if not isinstance(row, dict):
        return ""
    sheet_id = (
        row.get("Sheet ID")
        or row.get("sheet_id")
        or row.get("Hotel Sheet ID")
        or row.get("Hotel_Sheet_ID")
        or ""
    )
    return str(sheet_id).strip()


# =====================================================
# INITIAL SETUP
# =====================================================
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)

print("🛎️ Launching Guzo Guest Assist – Luxury Hospitality Edition v65")


# =====================================================
# GOOGLE SHEETS CLIENT
# =====================================================
def init_sheets_client():
    """Initialize Google Sheets service account client safely."""
    try:
        creds_path = os.path.join(
            os.path.dirname(__file__), "../../creds/guzo_service.json"
        )
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
        client = google_sheets.init_client()
        logging.info("✅ Google Sheets service account initialized.")
        return client
    except Exception as e:
        logging.error(f"❌ Failed to initialize Sheets client: {e}")
        raise


# =====================================================
# HOTEL HELPERS (normalize to list-of-dicts + JSON fallback)
# =====================================================
def _normalize_hotels(raw):
    """
    Normalize whatever google_sheets.read_hotels_master() returns into
    a list of dictionaries.

    Handles:
    • pandas.DataFrame (has .to_dict)
    • list[dict]
    • None / other -> []
    """
    if raw is None:
        return []

    # If it's a DataFrame-like object
    if hasattr(raw, "to_dict"):
        try:
            return raw.to_dict("records")
        except Exception:
            pass

    # If it's already list-like
    if isinstance(raw, list):
        return raw

    return []


def _load_hotels_from_json():
    """Fallback: load hotel configs from hotels_config.json if master is empty."""
    if not os.path.exists(HOTELS_CONFIG_JSON):
        logging.warning(f"[HotelJSON] No JSON config found at {HOTELS_CONFIG_JSON}")
        return []
    try:
        with open(HOTELS_CONFIG_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            logging.info(f"[HotelJSON] Loaded {len(data)} hotel(s) from JSON fallback.")
            return data
        logging.error("[HotelJSON] JSON root is not a list; ignoring.")
        return []
    except Exception as e:
        logging.error(f"[HotelJSON] Failed to read {HOTELS_CONFIG_JSON}: {e}")
        return []


def get_hotels_for_this_bot():
    """
    Return the list of hotels this bot is allowed to see.

    CENTRAL / ALL  -> all hotels (from Sheets master or JSON)
    PROPERTY BOT   -> only the hotel matching HOTEL_PROPERTY_CODE (Sheet/JSON filter)
    """

    # 1) Read from master sheet (may return DataFrame or list)
    try:
        raw = google_sheets.read_hotels_master()
    except Exception as e:
        logging.error(f"[HotelMaster] Error reading hotels master: {e}")
        raw = None

    hotels = _normalize_hotels(raw)

    # 2) If nothing in master, fall back to hotels_config.json
    if not hotels:
        logging.warning("[HotelMaster] No rows in master; using JSON fallback.")
        hotels = _load_hotels_from_json()

    # 3) Ensure property_code is always set on each row
    for h in hotels:
        h["property_code"] = get_hotel_property_code(h)

    # CENTRAL bot sees everything
    if BOT_MODE == "CENTRAL" or HOTEL_PROPERTY_CODE == "ALL":
        return hotels

    # PROPERTY bot: filter down to its own property_code
    filtered = [h for h in hotels if get_hotel_property_code(h) == HOTEL_PROPERTY_CODE]

    # If misconfigured, we still fall back to full list
    if not filtered:
        logging.error(
            f"[HotelMaster] No hotel row matches property_code={HOTEL_PROPERTY_CODE}."
        )
    return filtered or hotels


# =====================================================
# HOTEL FETCHER (for CENTRAL bot UI & info lists)
# =====================================================
def fetch_hotels(client):
    """
    Used mainly by CENTRAL bot for listing hotels & hotel info screens.
    PROPERTY bots **bind via Postgres** and do not rely on master for binding.
    """
    try:
        hotels = get_hotels_for_this_bot()
        print("[DEBUG] Hotels visible to this bot:")
        for h in hotels:
            print("   -", get_hotel_name(h), "| code =", get_hotel_property_code(h))
        return hotels
    except Exception as e:
        logging.error(f"[HotelFetch] {e}")
        return []


# =====================================================
# MULTILINGUAL DICTIONARY
# =====================================================
LANGUAGES = {
    "en": {
        "welcome": "🌟 Good day {guest}, and welcome to Guzo Guest Assist! It’s a pleasure to serve you today.",
        "choose_language": "Please choose your preferred language 🌍:",
        "main_menu": "How may I assist you today 🛎️?",
        "book_room": "🏨 Book a Room",
        "concierge_help": "💁 Concierge Assistance",
        "hotel_info": "🏙️ Hotel Information",
        "farewell": "✨ Thank you for choosing Guzo Guest Assist. We wish you a wonderful stay!",
        "invalid": "⚠️ I’m sorry — I didn’t catch that. Please select one of the options below.",
    },
    "am": {
        "welcome": "🌟 ውድ {guest}, እንኳን ወደ Guzo Guest Assist በደህና መጡ። እንግዶችን ለመርዳት ደስ ይላል።",
        "choose_language": "እባክዎን የሚመኝዎትን ቋንቋ ይምረጡ 🌍።",
        "main_menu": "ዛሬ እንዴት እንርዳዎታለን 🛎️?",
        "book_room": "🏨 መያዣ",
        "concierge_help": "💁 ኮንሲየርጅ እርዳታ",
        "hotel_info": "🏙️ የሆቴል መረጃ",
        "farewell": "✨ Guzo Guest Assistን የመረጡትን ስለሆነ እናመሰግናለን። መልካም ቆይታ ይኑርዎት።",
        "invalid": "⚠️ ይቅርታ፣ አልገባኝም። ከታች ያሉትን አማራጮች ይምረጡ።",
    },
    "om": {
        "welcome": "🌟 {guest} kabajamoo, Baga nagaan Guzo Guest Assist dhaqan!",
        "choose_language": "Mee afaan filatamaa kee filadhu 🌍:",
        "main_menu": "Akka si tajaajiluu nuti dandeenyu mee jedhi 🛎️?",
        "book_room": "🏨 Kireeffachuuf",
        "concierge_help": "💁 Tajaajila Koonsiyeerii",
        "hotel_info": "🏙️ Odeeffannoo Hooteelaa",
        "farewell": "✨ Guzo Guest Assist filachuun si galateeffanna.",
        "invalid": "⚠️ Dhiifama, hubachuu dideen. Filannoo armaan gadii keessaa filadhu.",
    },
}


# =====================================================
# SESSION UTILITIES
# =====================================================
user_sessions = {}


def get_user_session(uid):
    """Return or create session dict for user."""
    return user_sessions.setdefault(uid, {"step": "start", "lang": "en", "data": {}})


def reset_session(uid):
    user_sessions.pop(uid, None)


def get_text(lang, key, **kw):
    """Get multilingual text safely."""
    lang_dict = LANGUAGES.get(lang, LANGUAGES["en"])
    return lang_dict.get(key, LANGUAGES["en"].get(key, "")).format(**kw)


def main_menu_keyboard(lang="en"):
    """Return localized main menu buttons."""
    if lang == "am":
        buttons = [
            ["🏨 መያዣ", "💁 ኮንሲየርጅ እርዳታ"],
            ["🏙️ የሆቴል መረጃ", "🌐 ቋንቋ ቀይር"],
        ]
    elif lang == "om":
        buttons = [
            ["🏨 Kireeffachuuf", "💁 Tajaajila Koonsiyeerii"],
            ["🏙️ Odeeffannoo Hooteelaa", "🌐 Afaan Jijjiiri"],
        ]
    else:
        buttons = [
            ["🏨 Book a Room", "💁 Concierge Assistance"],
            ["🏙️ Hotel Information", "🌐 Change Language"],
        ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


# =====================================================
# /START COMMAND
# =====================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    session = get_user_session(uid)
    session["step"] = "choose_language"

    kb = ReplyKeyboardMarkup(
        [["🇬🇧 English"], ["🇪🇹 አማርኛ"], ["🇪🇹 Afaan Oromo"]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    msg = (
        "🌍 *Welcome to Guzo Guest Assist!*\n\n"
        "Please choose your preferred language to begin:\n\n"
        "🇬🇧 English | 🇪🇹 አማርኛ | 🇪🇹 Afaan Oromo"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)


# =====================================================
# BOOKING FLOW (STEP 1–5)
# =====================================================
async def handle_hotel_selection(update: Update, session, client, lang):
    """Used ONLY by a central multi-hotel bot (not property bots)."""
    text = update.message.text.strip().lower()
    hotels = fetch_hotels(client)
    match = next((h for h in hotels if get_hotel_name(h).lower() in text), None)
    if not match:
        await update.message.reply_text(
            {
                "en": "⚠️ Please choose a valid hotel.",
                "am": "⚠️ እባክዎን ትክክለኛ ሆቴል ይምረጡ።",
                "om": "⚠️ Mee hotel sirrii filadhu.",
            }[lang]
        )
        return

    session["data"].update(
        {
            "Hotel Name": get_hotel_name(match),
            "Sheet ID": get_hotel_sheet_id(match),
            "Reservation Email": match.get("Reservation Email", ""),
            "Phone (Front Desk)": match.get("Phone", ""),
            "Property Code": get_hotel_property_code(match),
        }
    )
    session["step"] = "check_in_date"

    await update.message.reply_text(
        {
            "en": f"📅 Please enter your *check-in date* (YYYY-MM-DD) for {get_hotel_name(match)}.",
            "am": "📅 እባክዎን የመግቢያ ቀንዎን ያስገቡ (YYYY-MM-DD)።",
            "om": f"📅 Mee guyyaa seensaa kee galchi (YYYY-MM-DD) kan {get_hotel_name(match)}.",
        }[lang],
        parse_mode="Markdown",
    )


async def handle_date_entry(update: Update, session, lang):
    text = update.message.text.strip()
    data = session["data"]

    try:
        date_obj = datetime.datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text(
            {
                "en": "⚠️ Invalid date format. Please use YYYY-MM-DD.",
                "am": "⚠️ ቅርጸት የተሳሳተ ነው። በ YYYY-MM-DD ይጻፉ።",
                "om": "⚠️ Sirna guyyaa dogoggore. Mee akka YYYY-MM-DD itti fayyadami.",
            }[lang]
        )
        return

    if session["step"] == "check_in_date":
        data["Check-In Date"] = str(date_obj)
        session["step"] = "check_out_date"
        await update.message.reply_text(
            {
                "en": "📆 Please enter your *check-out date* (YYYY-MM-DD):",
                "am": "📆 እባክዎን የመውጫ ቀንዎን ያስገቡ (YYYY-MM-DD):",
                "om": "📆 Mee guyyaa baʼii kee galchi (YYYY-MM-DD):",
            }[lang],
            parse_mode="Markdown",
        )
        return

    if session["step"] == "check_out_date":
        check_in = datetime.datetime.strptime(
            data["Check-In Date"], "%Y-%m-%d"
        ).date()
        if date_obj <= check_in:
            await update.message.reply_text(
                {
                    "en": "⚠️ Check-out must be after check-in.",
                    "am": "⚠️ መውጫ ከመግቢያ በኋላ መሆን አለበት።",
                    "om": "⚠️ Guyyaan baʼii dura taʼuu hin qabu.",
                }[lang]
            )
            return
        data["Check-Out Date"] = str(date_obj)
        data["Nights"] = (date_obj - check_in).days
        session["step"] = "room_type"
        await update.message.reply_text(
            {
                "en": f"🛏️ Great! You’ll stay for {data['Nights']} night(s). Now fetching available rooms...",
                "am": f"🛏️ ጥሩ! ለ {data['Nights']} ሌሊት ትቆያላችሁ።",
                "om": f"🛏️ Gaariidha! Halkanoota {data['Nights']} turtuuf.",
            }[lang]
        )


async def handle_room_selection(update: Update, client, session, lang):
    hotel_id = session["data"]["Sheet ID"]
    try:
        ws = client.open_by_key(hotel_id).worksheet("Room_Rates")
        records = ws.get_all_records()
    except Exception:
        records = [
            {"Room Type": "Standard Room", "Rate (ETB)": 3500},
            {"Room Type": "Deluxe Room", "Rate (ETB)": 4500},
            {"Room Type": "Suite", "Rate (ETB)": 6000},
        ]

    session["step"] = "room_choice"
    buttons = [
        [
            f"{r['Room Type']} – {r.get('Rate (ETB)', r.get('Rack Rate (ETB)', 0))} ETB"
        ]
        for r in records
    ]
    await update.message.reply_text(
        {
            "en": "Please choose your preferred room type:",
            "am": "እባክዎን የክፍል አይነት ይምረጡ።",
            "om": "Mee gosa kottuu filadhu:",
        }[lang],
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True),
    )


async def handle_room_choice(update: Update, session, lang):
    text = update.message.text.strip()
    if "–" not in text:
        await update.message.reply_text(
            {
                "en": "⚠️ Please select a valid room type.",
                "am": "⚠️ እባክዎን ትክክለኛ የክፍል አይነት ይምረጡ።",
                "om": "⚠️ Mee gosa kottuu sirrii filadhu.",
            }[lang]
        )
        return

    room_type, rate_text = text.split("–", 1)
    try:
        rate = int(re.findall(r"\d+", rate_text)[0])
    except Exception:
        rate = 0

    data = session["data"]
    data["Room Type"] = room_type.strip()
    data["Rate Per Night (ETB)"] = rate
    data["Total Revenue (ETB)"] = rate * int(data.get("Nights", 1))
    session["step"] = "payment"

    buttons = [["💵 Cash", "💳 Card", "🏦 Bank Transfer"]]
    await update.message.reply_text(
        {
            "en": f"💳 Total *{data['Total Revenue (ETB)']} ETB* for {data['Nights']} night(s). Choose payment method:",
            "am": f"💳 ጠቅላላ ዋጋ *{data['Total Revenue (ETB)']} ETB*። እባክዎን መንገድ ይምረጡ።",
            "om": f"💳 Waliigala *{data['Total Revenue (ETB)']} ETB*. Mala kaffaltii filadhu:",
        }[lang],
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True),
    )
    return


# =====================================================
# BOOKING FLOW (STEP 6 – PAYMENT → EMAIL CAPTURE)
# =====================================================
async def handle_payment(update: Update, session, lang):
    """Step 6 – Capture payment method → ask for guest email."""
    text = update.message.text.lower()
    data = session["data"]

    if any(k in text for k in ["cash", "💵", "ጥሬ"]):
        data["Payment Method"] = "💵 Cash"
    elif any(k in text for k in ["card", "💳", "ካርድ"]):
        data["Payment Method"] = "💳 Card"
    elif any(k in text for k in ["bank", "🏦", "ባንክ"]):
        data["Payment Method"] = "🏦 Bank Transfer"
    else:
        await update.message.reply_text(
            {
                "en": "⚠️ Please choose a valid payment method.",
                "am": "⚠️ እባክዎን ትክክለኛ መንገድ ይምረጡ።",
                "om": "⚠️ Mee mala kaffaltii sirrii filadhu.",
            }[lang]
        )
        return

    session["step"] = "guest_email"
    await update.message.reply_text(
        {
            "en": "📧 Please enter your email address to receive your booking confirmation:",
            "am": "📧 እባክዎን የኢሜል አድራሻዎን ያስገቡ እንደ መረጃ ያገኙ።",
            "om": "📧 Mee teessoo imeelii kee galchi mirkaneessaaf.",
        }[lang],
        reply_markup=ReplyKeyboardRemove(),
    )


# =====================================================
# STEP 7 – GUEST EMAIL, SAVE BOOKING, SEND CONFIRMATION
# =====================================================
async def handle_guest_email(update: Update, client, session, lang):
    """Step 7 – Validate guest email → save booking + send email + save to Postgres."""
    email = update.message.text.strip()
    if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        await update.message.reply_text(
            {
                "en": "⚠️ Invalid email address. Please enter a valid one.",
                "am": "⚠️ የተሳሳተ ኢሜል ነው። እባክዎ ትክክለኛ ኢሜል ይስጡ።",
                "om": "⚠️ Imeelii sirrii galchi.",
            }[lang]
        )
        return

    data = session["data"]
    data["Guest Email"] = email
    session["step"] = "confirmed"

    # Stamp metadata
    now = datetime.datetime.now()
    data["Confirmation ID"] = f"GZ-{now.strftime('%y%m%d%H%M')}"
    data["Guest Name"] = update.effective_user.full_name or "Guest"
    data["Source"] = "Telegram"
    data["Booking Status"] = "Confirmed"
    data["Payment Status"] = "Paid"
    data["Payment Date"] = now.strftime("%Y-%m-%d")
    data["Property Code"] = data.get("Property Code", "UNKNOWN")

    # ✅ Save booking to Google Sheets via helper
    google_sheets.append_booking(data)
    logging.info(f"✅ Booking saved for {data['Guest Name']}")
    google_sheets.sync_to_master(data)
    logging.info(f"[CentralSync] ✅ Booking synced for {data.get('Hotel Name', 'N/A')}")

    # ✅ Also save booking into PostgreSQL
    try:
        postgres_bookings.insert_booking_from_sheet_dict(data)
    except Exception as e:
        logging.error(f"[PostgresBookings] ❌ Failed to save booking to Postgres: {e}")
    
        # ✅ Also save booking into PostgreSQL
    try:
        save_booking_to_postgres(data)
    except Exception as e:
        logging.error(f"[PostgresBookings] ❌ Failed to save booking to Postgres: {e}")


    # Telegram confirmation message
    msg = {
        "en": (
            f"✅ *Booking Confirmed!*\n\n"
            f"🏨 Hotel: {data.get('Hotel Name', 'Hotel')}\n"
            f"🧾 Confirmation ID: {data['Confirmation ID']}\n"
            f"📅 {data['Check-In Date']} → {data['Check-Out Date']}\n"
            f"👤 Guest: {data['Guest Name']}\n"
            f"💰 Total: {data['Total Revenue (ETB)']} ETB\n\n"
            "📧 A confirmation email has been sent to your inbox."
        ),
        "am": (
            f"✅ *ቦኪንግዎ ተረጋገጠ!*\n\n"
            f"🏨 ሆቴል፡ {data.get('Hotel Name', 'Hotel')}\n"
            f"🧾 የቃል መጠየቂያ ቁጥር፡ {data['Confirmation ID']}\n"
            f"📅 {data['Check-In Date']} → {data['Check-Out Date']}\n"
            f"👤 እንግዳ፡ {data['Guest Name']}\n"
            f"💰 ጠቅላላ ዋጋ፡ {data['Total Revenue (ETB)']} ብር\n\n"
            "📧 የማረጋገጫ ኢሜል ወደ መልዕክት መልእክት ሳጥንዎ ተልኳል።"
        ),
        "om": (
            f"✅ *Turtin kee ni mirkanaa’e!*\n\n"
            f"🏨 Hoteela: {data.get('Hotel Name', 'Hotel')}\n"
            f"🧾 ID Mirkaneessaa: {data['Confirmation ID']}\n"
            f"📅 {data['Check-In Date']} → {data['Check-Out Date']}\n"
            f"👤 Daawataa: {data['Guest Name']}\n"
            f"💰 Waliigala Kaffaltii: {data['Total Revenue (ETB)']} ETB\n\n"
            "📧 Imeelii mirkaneessaa gara sanduuqa kee ergameera."
        ),
    }[lang]

    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["🏠 Main Menu"]], resize_keyboard=True),
    )

    # =====================================================
    # Send Email Confirmation (Guest + Hotel)
    # =====================================================
    subject = (
        f"Guzo Guest Assist – Booking Confirmation: "
        f"{data.get('Hotel Name', 'Hotel')} ({data['Confirmation ID']})"
    )

    booking_details = {
        "Guest Name": data.get("Guest Name", "Guest"),
        "Hotel Name": data.get("Hotel Name", "Hotel"),
        "Check-In Date": data.get("Check-In Date", ""),
        "Check-Out Date": data.get("Check-Out Date", ""),
        "Nights": data.get("Nights", ""),
        "Room Type": data.get("Room Type", ""),
        "Total Revenue (ETB)": data.get("Total Revenue (ETB)", ""),
        "Confirmation ID": data.get("Confirmation ID", ""),
        "Phone (Front Desk)": data.get("Phone (Front Desk)", "N/A"),
        "Payment Method": data.get("Payment Method", ""),
        "lang": lang,
    }

    recipients = [data["Guest Email"]]
    if data.get("Reservation Email"):
        recipients.append(data["Reservation Email"])

    try:
        email_sender.send_confirmation_email(
            to_emails=recipients,
            subject=subject,
            content=booking_details,
            from_email=DEFAULT_SENDER,
        )
        logging.info(f"📧 Confirmation email sent to {recipients}")
    except Exception as e:
        logging.error(f"[EmailSend] ⚠️ Failed to send email: {e}")


# =====================================================
# 🏨 HOTEL PROFILE – LIVE ROOM + OVERVIEW (Dual Currency)
# =====================================================
async def handle_hotel_profile(update: Update, client, session, lang):
    """Display hotel overview + live room rates from Room_Rates sheet."""
    text = update.message.text.strip()
    hotels = fetch_hotels(client)
    hotel = next(
        (h for h in hotels if get_hotel_name(h).lower() == text.lower()), None
    )

    # If text doesn't match, try using the current session's hotel (per-property bot)
    if not hotel:
        data = session["data"]
        current_name = data.get("Hotel Name")
        current_sheet = data.get("Sheet ID")
        if current_name and current_sheet:
            hotel = {
                "Hotel Name": current_name,
                "Sheet ID": current_sheet,
            }
        else:
            await update.message.reply_text(
                {
                    "en": "⚠️ Please select a valid hotel from the list.",
                    "am": "⚠️ እባክዎን ከዝርዝሩ ውስጥ ትክክለኛ ሆቴል ይምረጡ።",
                    "om": "⚠️ Mee hotel sirrii tarree keessaa filadhu.",
                }[lang]
            )
            return

    session["data"]["Hotel Name"] = hotel["Hotel Name"]
    session["data"]["Sheet ID"] = hotel["Sheet ID"]

    # ------------------------------------------------------------------
    # 1️⃣ Fetch hotel overview from "Hotel_Profile"
    # ------------------------------------------------------------------
    profile = {}
    try:
        ws = client.open_by_key(hotel["Sheet ID"]).worksheet("Hotel_Profile")
        rows = ws.get_all_records()
        if rows:
            profile = rows[0]
    except Exception as e:
        logging.error(f"[HotelProfileRead] {e}")

    # ------------------------------------------------------------------
    # 2️⃣ Fetch live room rates from "Room_Rates"
    # ------------------------------------------------------------------
    room_records = []
    try:
        ws_room = client.open_by_key(hotel["Sheet ID"]).worksheet("Room_Rates")
        room_records = ws_room.get_all_records()
    except Exception as e:
        logging.error(f"[RoomRatesRead] {e}")

    room_lines = []
    for r in room_records:
        room_lines.append(
            f"🏷 *{r['Room Type']}* — {r['Rack Rate (ETB)']} ETB (~${r['Rack Rate (USD)']})\n"
            f"👨‍👩‍👧 {r['Max Occupancy']} | {r['Notes'] or '—'} | {r['Availability']} | 🕒 {r['Last Updated']}"
        )
    room_text = "\n\n".join(room_lines) if room_lines else "⚠️ No room data available."

    msg = {
        "en": (
            f"🏨 *{hotel['Hotel Name']}* ({profile.get('Rating (Stars)', '—')}⭐)\n\n"
            f"📝 *Overview*: {profile.get('Hotel Overview','—')}\n"
            f"✨ *Amenities*: {profile.get('Amenities','—')}\n"
            f"📍 *Nearby*: {profile.get('Nearby Attractions','—')}\n"
            f"🌐 *Website*: {profile.get('Website','—')}\n\n"
            f"💰 *Room Rates:*\n{room_text}\n\n"
            f"💁 We look forward to welcoming you soon!"
        ),
        "am": (
            f"🏨 *{hotel['Hotel Name']}* ({profile.get('Rating (Stars)','—')}⭐)\n\n"
            f"📝 *አጠቃላይ መግለጫ*: {profile.get('Hotel Overview','—')}\n"
            f"✨ *አገልግሎቶች*: {profile.get('Amenities','—')}\n"
            f"📍 *ቅርብ መዳረሻዎች*: {profile.get('Nearby Attractions','—')}\n"
            f"🌐 *ድር ጣቢያ*: {profile.get('Website','—')}\n\n"
            f"💰 *የክፍል ዋጋዎች:*\n{room_text}\n\n"
            f"💁 እንኳን በደህና መጡ እንላለን!"
        ),
        "om": (
            f"🏨 *{hotel['Hotel Name']}* ({profile.get('Rating (Stars)','—')}⭐)\n\n"
            f"📝 *Ibsa Waliigalaa*: {profile.get('Hotel Overview','—')}\n"
            f"✨ *Tajaajiloota*: {profile.get('Amenities','—')}\n"
            f"📍 *Bakkawwan Dhiyoo*: {profile.get('Nearby Attractions','—')}\n"
            f"🌐 *Website*: {profile.get('Website','—')}\n\n"
            f"💰 *Gatiin Kottaa:*\n{room_text}\n\n"
            f"💁 Baga nagaan dhufte, si simachuuf ni gammanna!"
        ),
    }[lang]

    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        disable_web_page_preview=False,
        reply_markup=ReplyKeyboardMarkup(
            [["↩️ Return to Main Menu"]], resize_keyboard=True
        ),
    )


# =====================================================
# 💁 CONCIERGE HELP – SMART CONTEXTUAL RESPONSES
# =====================================================
async def handle_concierge_request(update: Update, session, lang, client):
    """Smart, context-aware concierge replies based on Hotel_Profile amenities."""
    text = update.message.text.lower()
    data = session["data"]
    hotel_name = data.get("Hotel Name", "Hotel")

    # Try to load amenities to personalize responses
    amenities = ""
    try:
        ws = client.open_by_key(data["Sheet ID"]).worksheet("Hotel_Profile")
        rows = ws.get_all_records()
        if rows:
            amenities = rows[0].get("Amenities", "").lower()
    except Exception as e:
        logging.error(f"[ConciergeAmenities] {e}")

    def respond(msg_en, msg_am, msg_om):
        return {"en": msg_en, "am": msg_am, "om": msg_om}[lang]

    # Contextual answers
    if any(k in text for k in ["airport", "taxi", "shuttle", "አየር", "ታክሲ"]):
        if "shuttle" in amenities or "airport" in amenities:
            reply = respond(
                f"🚖 Yes, {hotel_name} provides an airport shuttle every 30 minutes. Shall I help you schedule one?",
                f"🚖 አዎን፣ {hotel_name} የአየር ማረፊያ አውቶቡስ አገልግሎት አለው። እባክዎን እቀድሞ እርዳዎታለሁ?",
                f"🚖 Eeyyee, {hotel_name} tajaajila xiyyaaraa ni qaba. Si gargaaruu barbaadaa?",
            )
        else:
            reply = respond(
                "🚖 We can assist with arranging your airport or taxi transfer anytime.",
                "🚖 በማንኛውም ጊዜ የታክሲ ወይም የአየር ማረፊያ ስብሰባ እንረዳለን።",
                "🚖 Tajaajila xiyyaaraa yookaan taaksii siif ni qopheessina.",
            )
    elif any(k in text for k in ["spa", "massage", "ስፓ", "አዋቂ"]):
        if "spa" in amenities:
            reply = respond(
                f"💆‍♀️ {hotel_name} features a luxury spa and massage center open 9 AM – 9 PM daily.",
                f"💆‍♀️ {hotel_name} ላይ የስፓ እና የማሳጅ አገልግሎት አለ። በ9 ጠዋት – 9 ማታ ይከፈታል።",
                f"💆‍♀️ {hotel_name} tajaajila spa fi miidhagsa qaamaa qaba, banuu 9 AM – 9 PM.",
            )
        else:
            reply = respond(
                "💆‍♀️ We can arrange a nearby spa appointment for you.",
                "💆‍♀️ በአቅራቢያ የሚገኝ የስፓ አገልግሎት እንረዳለን።",
                "💆‍♀️ Spa dhiyoo siif ni qopheessina.",
            )
    elif any(k in text for k in ["dining", "restaurant", "food", "ምግብ", "ሬስቶራንት"]):
        if "restaurant" in amenities:
            reply = respond(
                f"🍽️ {hotel_name} offers all-day dining with local and international cuisine.",
                f"🍽️ {hotel_name} የቀኑን ሁሉ ሰዓት የምግብ አገልግሎት አለው፣ የአገር ውስጥና የውጭ ምግቦችን ይሰጣል።",
                f"🍽️ {hotel_name} nyaata idil-addunyaa fi kan biyya keessaa yeroo hunda ni kenna.",
            )
        else:
            reply = respond(
                "🍽️ We can recommend or order from partner restaurants nearby.",
                "🍽️ በአቅራቢያ የሚገኙ ሬስቶራንቶችን እንመክራለን።",
                "🍽️ Restaurant dhiyoo irraa nyaata siif ni qopheessina.",
            )
    else:
        reply = respond(
            "💁 Our concierge is happy to assist you with any request.",
            "💁 ኮንሲየርጅ ቡድናችን በማንኛውም ጥያቄ ይረዳዎታል።",
            "💁 Koonsiyeerii keenya si gargaaruuf qophii dha.",
        )

    await update.message.reply_text(
        reply,
        reply_markup=ReplyKeyboardMarkup(
            [
                ["🧳 Luggage Assistance", "🚖 Airport / Taxi Request"],
                ["🧼 Housekeeping", "🍽️ In-room Dining"],
                ["↩️ Return to Main Menu"],
            ],
            resize_keyboard=True,
        ),
    )


# =====================================================
# MULTI-BOT ENTRY – CALLED BY RUNNER
# =====================================================
async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE, property_code: str
):
    """
    Entry point used by the multi-bot runner.
    It tags this chat/session with the hotel property_code, then calls router().
    """
    # 1: Force 1:1 isolation (ignore groups/supergroups/channels)
    if update.effective_chat and update.effective_chat.type != "private":
        return

    # 2: Remember which hotel this bot represents
    context.chat_data[PROPERTY_CODE_KEY] = property_code

    # 3: Continue into router
    await router(update, context)


# =====================================================
# MAIN ROUTER (Final, Multi-Bot Aware)
# =====================================================
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    session = get_user_session(uid)
    client = init_sheets_client()
    text = (update.message.text or "").strip()
    lang = session["lang"]
    data = session["data"]

    # 🔐 Bind this session to its hotel if property_code is set (per-property bot)
    property_code = context.chat_data.get(PROPERTY_CODE_KEY)

    # Fallback: if no property_code in chat_data but env says PROPERTY bot, use HOTEL_PROPERTY_CODE
    if not property_code and BOT_MODE == "PROPERTY" and HOTEL_PROPERTY_CODE and HOTEL_PROPERTY_CODE != "ALL":
        property_code = HOTEL_PROPERTY_CODE

    if property_code:
        data["Property Code"] = property_code
        # If hotel not yet stamped for this chat, look it up once (via Postgres)
        hotel_row = None
        if not data.get("Hotel Name") or not data.get("Sheet ID"):
            hotel_row = get_hotel_by_property_code(property_code)
            if hotel_row:
                name = get_hotel_name(hotel_row) or f"Hotel {property_code}"
                sheet_id = get_hotel_sheet_id(hotel_row)

                data.setdefault("Hotel Name", name)
                data.setdefault("Sheet ID", sheet_id)

                if hotel_row.get("email"):
                    # Postgres may have 'email' as reservation contact
                    data.setdefault("Reservation Email", hotel_row.get("email"))
                if hotel_row.get("phone"):
                    data.setdefault("Phone (Front Desk)", hotel_row.get("phone"))

                logging.info(
                    f"[BIND] Bound property bot to hotel='{name}', "
                    f"code={get_hotel_property_code(hotel_row)}, sheet_id={sheet_id}"
                )
            else:
                # Fallback: per-bot env if defined
                if BOT_MODE == "PROPERTY" and PROPERTY_FALLBACK_SHEET_ID:
                    name = PROPERTY_FALLBACK_NAME or f"Hotel {property_code}"
                    data.setdefault("Hotel Name", name)
                    data.setdefault("Sheet ID", PROPERTY_FALLBACK_SHEET_ID)
                    if PROPERTY_FALLBACK_RES_EMAIL:
                        data.setdefault("Reservation Email", PROPERTY_FALLBACK_RES_EMAIL)
                    if PROPERTY_FALLBACK_PHONE:
                        data.setdefault("Phone (Front Desk)", PROPERTY_FALLBACK_PHONE)

                    logging.warning(
                        f"[BIND] Using env fallback for property_code={property_code}: "
                        f"hotel='{name}', sheet_id={PROPERTY_FALLBACK_SHEET_ID}"
                    )
                else:
                    logging.error(
                        f"[BIND] Unable to bind property bot with property_code={property_code} to any hotel row."
                    )

    # 🏠 Return to Main Menu
    if text in ["↩️ Return to Main Menu", "🏠 Main Menu"]:
        reset_session(uid)
        s = get_user_session(uid)
        s["lang"] = lang
        s["step"] = "main_menu"
        await update.message.reply_text(
            get_text(lang, "main_menu"), reply_markup=main_menu_keyboard(lang)
        )
        return

    # 🌐 Language Selection
    if session["step"] == "choose_language":
        lower = text.lower()
        if "english" in lower:
            session["lang"] = "en"
        elif "አማርኛ" in text or "amharic" in lower:
            session["lang"] = "am"
        elif "afaan" in lower or "oromo" in lower:
            session["lang"] = "om"
        else:
            await update.message.reply_text("⚠️ Please tap one of the language options.")
            return

        session["step"] = "main_menu"
        await update.message.reply_text(
            get_text(session["lang"], "welcome", guest=user.full_name),
            reply_markup=main_menu_keyboard(session["lang"]),
        )
        return

    # 🔀 Step Routing
    if session["step"] == "select_hotel":
        await handle_hotel_selection(update, session, client, lang)
        return
    if session["step"] in ["check_in_date", "check_out_date"]:
        await handle_date_entry(update, session, lang)
        return
    if session["step"] == "room_type":
        await handle_room_selection(update, client, session, lang)
        return
    if session["step"] == "room_choice":
        await handle_room_choice(update, session, lang)
        return
    if session["step"] == "payment":
        await handle_payment(update, session, lang)
        return
    if session["step"] == "guest_email":
        await handle_guest_email(update, client, session, lang)
        return
    if session["step"] == "hotel_info_detail":
        await handle_hotel_profile(update, client, session, lang)
        return
    if session["step"] in ["concierge", "concierge_option"]:
        await handle_concierge_request(update, session, lang, client)
        return

    # 🧭 MAIN MENU LOGIC
    if session["step"] in ["start", "main_menu"]:
        hotels = fetch_hotels(client)
        lower = text.lower()

        # 1️⃣ Booking
        if any(k in lower for k in ["book", "መያዣ", "kireeffachuuf"]):

            # 🔒 PROPERTY BOT: always use its own hotel, never show list
            if BOT_MODE == "PROPERTY":
                # Make sure this session is bound to a hotel row (via Postgres)
                if not data.get("Hotel Name") or not data.get("Sheet ID"):
                    hotel_row = get_hotel_by_property_code(
                        data.get("Property Code") or HOTEL_PROPERTY_CODE
                    )
                    if hotel_row:
                        name = get_hotel_name(hotel_row) or f"Hotel {HOTEL_PROPERTY_CODE}"
                        sheet_id = get_hotel_sheet_id(hotel_row)

                        data.setdefault("Hotel Name", name)
                        data.setdefault("Sheet ID", sheet_id)

                        if hotel_row.get("email"):
                            data.setdefault(
                                "Reservation Email",
                                hotel_row.get("email"),
                            )
                        if hotel_row.get("phone"):
                            data.setdefault(
                                "Phone (Front Desk)",
                                hotel_row.get("phone"),
                            )

                        logging.info(
                            f"[BOOK] Property bot using hotel='{name}', "
                            f"property_code={get_hotel_property_code(hotel_row)}, "
                            f"sheet_id={sheet_id}"
                        )
                    else:
                        logging.error("[BOOK] Property bot could not resolve a hotel row.")
                        await update.message.reply_text(
                            "⚠️ Configuration issue: this hotel's booking profile is not connected yet."
                        )
                        return

                # Now go straight to check-in date for THIS hotel
                session["step"] = "check_in_date"
                await update.message.reply_text(
                    {
                        "en": f"📅 Please enter your *check-in date* (YYYY-MM-DD) for {data['Hotel Name']}.",
                        "am": "📅 እባክዎን የመግቢያ ቀንዎን ያስገቡ (YYYY-MM-DD)።",
                        "om": f"📅 Mee guyyaa seensaa kee galchi (YYYY-MM-DD) kan {data['Hotel Name']}.",
                    }[lang],
                    parse_mode="Markdown",
                )
                return

            # 🌐 CENTRAL BOT: show hotel list (old behavior)
            if data.get("Hotel Name") and data.get("Sheet ID"):
                session["step"] = "check_in_date"
                await update.message.reply_text(
                    {
                        "en": f"📅 Please enter your *check-in date* (YYYY-MM-DD) for {data['Hotel Name']}.",
                        "am": "📅 እባክዎን የመግቢያ ቀንዎን ያስገቡ (YYYY-MM-DD)።",
                        "om": f"📅 Mee guyyaa seensaa kee galchi (YYYY-MM-DD) kan {data['Hotel Name']}.",
                    }[lang],
                    parse_mode="Markdown",
                )
                return

        # 2️⃣ Concierge
        if any(k in lower for k in ["concierge", "help", "ኮንሲየርጅ", "tajaajila"]):
            session["step"] = "concierge"
            await handle_concierge_request(update, session, lang, client)
            return

        # 3️⃣ Hotel Info
        if any(k in lower for k in ["hotel", "information", "መረጃ", "odeeffannoo"]):
            # For per-property bot, show this hotel's info directly
            if data.get("Hotel Name") and data.get("Sheet ID"):
                await handle_hotel_profile(update, client, session, lang)
                return
            # Central bot: choose from list
            if not hotels:
                await update.message.reply_text("⚠️ No hotel info available.")
                return
            session["step"] = "hotel_info_detail"
            buttons = [[get_hotel_name(h)] for h in hotels if get_hotel_name(h)]
            await update.message.reply_text(
                {
                    "en": "🏨 Please select a hotel to view its full information:",
                    "am": "🏨 እባክዎን የሆቴሉን መረጃ ለማየት ሆቴል ይምረጡ።",
                    "om": "🏨 Mee hotel tokko filadhu odeeffannoo isaa argachuuf:",
                }[lang],
                reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True),
            )
            return

        # 4️⃣ Change Language
        if any(k in lower for k in ["change", "language", "ቋንቋ", "afaan"]):
            session["step"] = "choose_language"
            kb = ReplyKeyboardMarkup(
                [["🇬🇧 English"], ["🇪🇹 አማርኛ"], ["🇪🇹 Afaan Oromo"]],
                resize_keyboard=True,
            )
            await update.message.reply_text(
                get_text(lang, "choose_language"), reply_markup=kb
            )
            return

        # 5️⃣ Default Invalid
        await update.message.reply_text(
            get_text(lang, "invalid"), reply_markup=main_menu_keyboard(lang)
        )
        return


# =====================================================
# MAIN ENTRY POINT (optional single-bot run)
# =====================================================
def main():
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Missing TELEGRAM_BOT_TOKEN in env")
        return
    init_sheets_client()
    print("✅ Google Sheets connected.")
    print("🤖 Starting Guzo Guest Assist Bot...")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(
        CommandHandler("test", lambda u, c: u.message.reply_text("✅ System operational."))
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    print("✅ Bot is live and ready.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
