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
• Use FastAPI backend endpoints (/bot/availability, /bot/bookings)
  as the single source of truth for room availability + DB bookings.
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

from guzo_backend.modules import email_sender
from guzo_backend.modules.central_sync import sync_booking_to_central  # noqa: F401
from guzo_backend.modules.postgres_hotels import get_hotel_by_property_code

# ✅ NEW: use backend client to talk to FastAPI /bot endpoints
from guzo_booking_bot.modules.backend_client import (
    check_availability_for_bot,
    create_booking_for_bot,
)

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
HOTELS_CONFIG_JSON = os.path.join(
    os.path.dirname(__file__), "../../hotels_config.json"
)

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
    """
    Google Sheets is disabled for the Telegram bot.
    The bot now creates canonical bookings through the FastAPI/PostgreSQL backend.
    """
    return None


# =====================================================
# HOTEL HELPERS (normalize to list-of-dicts + JSON fallback)
# =====================================================
def _normalize_hotels(raw):
    """
    Normalize any hotel source into
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
            logging.info(
                f"[HotelJSON] Loaded {len(data)} hotel(s) from JSON fallback."
            )
            return data
        logging.error("[HotelJSON] JSON root is not a list; ignoring.")
        return []
    except Exception as e:
        logging.error(f"[HotelJSON] Failed to read {HOTELS_CONFIG_JSON}: {e}")
        return []


def get_hotels_for_this_bot():
    """
    Return the list of hotels this bot is allowed to see.

    CENTRAL / ALL  -> all configured hotels
    PROPERTY BOT   -> only the hotel matching HOTEL_PROPERTY_CODE
    """
    hotels = [
        {
            "Hotel Name": "Dream Big Hotel",
            "Property Code": "DRE001",
            "property_code": "DRE001",
            "Sheet ID": None,
        },
        {
            "Hotel Name": "N&N Luxury Hotel",
            "Property Code": "NN002",
            "property_code": "NN002",
            "Sheet ID": None,
        },
    ]

    # 3) Ensure property_code is always set on each row
    for h in hotels:
        h["property_code"] = get_hotel_property_code(h)

    # CENTRAL bot sees everything
    if BOT_MODE == "CENTRAL" or HOTEL_PROPERTY_CODE == "ALL":
        return hotels

    # PROPERTY bot: filter down to its own property_code
    filtered = [h for h in hotels if get_hotel_property_code(h) == HOTEL_PROPERTY_CODE]

    # Property bots must never expose another hotel's inventory or profile.
    if not filtered:
        logging.error(
            f"[HotelMaster] No hotel row matches property_code={HOTEL_PROPERTY_CODE}."
        )
        if PROPERTY_FALLBACK_NAME and HOTEL_PROPERTY_CODE != "ALL":
            return [
                {
                    "Hotel Name": PROPERTY_FALLBACK_NAME,
                    "Property Code": HOTEL_PROPERTY_CODE,
                    "property_code": HOTEL_PROPERTY_CODE,
                    "Sheet ID": PROPERTY_FALLBACK_SHEET_ID,
                    "Reservation Email": PROPERTY_FALLBACK_RES_EMAIL,
                    "Phone": PROPERTY_FALLBACK_PHONE,
                }
            ]
        return []
    return filtered


def get_room_rates_from_postgres_fallback(property_code: str = "DRE001"):
    """Temporary room-rate fallback until room rates are exposed by backend API."""
    return [
        {"Room Type": "Standard Room", "Rate (ETB)": 4500, "Rack Rate (USD)": 40},
        {"Room Type": "Deluxe Room", "Rate (ETB)": 6500, "Rack Rate (USD)": 58},
        {"Room Type": "Family Room", "Rate (ETB)": 9500, "Rack Rate (USD)": 85},
        {"Room Type": "Suite", "Rate (ETB)": 9500, "Rack Rate (USD)": 85},
    ]


def get_hotel_profile_from_postgres_fallback(property_code: str = "DRE001"):
    """Temporary hotel profile fallback until hotel profile data is exposed by backend API."""
    profiles = {
        "DRE001": {
            "Hotel Name": "Dream Big Hotel",
            "Rating (Stars)": "5",
            "Hotel Overview": "A luxury hospitality property managed through Guzo PMS.",
            "Amenities": "Front desk support, room booking support, housekeeping, restaurant, and local information.",
            "Nearby Attractions": "Addis Ababa business and leisure destinations.",
            "Website": "N/A",
        },
        "NN002": {
            "Hotel Name": "N&N Luxury Hotel",
            "Rating (Stars)": "5",
            "Hotel Overview": "A luxury hospitality property managed through Guzo PMS.",
            "Amenities": "Front desk support, room booking support, housekeeping, restaurant, and local information.",
            "Nearby Attractions": "Nearby city attractions and guest services.",
            "Website": "N/A",
        },
    }
    return profiles.get(property_code, profiles["DRE001"])


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
    "fr": {
        "welcome": "🌟 Bonjour {guest}, bienvenue sur Guzo Guest Assist ! Nous sommes ravis de vous aider aujourd’hui.",
        "choose_language": "Veuillez choisir votre langue préférée 🌍 :",
        "main_menu": "Comment pouvons-nous vous aider aujourd’hui 🛎️ ?",
        "book_room": "🏨 Réserver une chambre",
        "concierge_help": "💁 Assistance concierge",
        "hotel_info": "🏙️ Informations sur l’hôtel",
        "farewell": "✨ Merci d’avoir choisi Guzo Guest Assist. Nous vous souhaitons un excellent séjour !",
        "invalid": "⚠️ Désolé, je n’ai pas compris. Veuillez sélectionner l’une des options ci-dessous.",
    },
}

LANGUAGE_BUTTONS = [
    ["🇬🇧 English"],
    ["🇪🇹 አማርኛ"],
    ["🇪🇹 Afaan Oromo"],
    ["🇫🇷 Français"],
]

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


def localized(options: dict, lang: str):
    """Return a localized value with English fallback."""
    return options.get(lang) or options["en"]


def normalized_text(value: str) -> str:
    """Normalize button text while preserving Amharic and Afaan Oromo words."""
    value = (value or "").strip().lower()
    value = re.sub(r"^[^\w\u1200-\u137F]+", "", value)
    return re.sub(r"\s+", " ", value).strip()


def is_booking_request(text: str) -> bool:
    value = normalized_text(text)
    labels = [normalized_text(cfg["book_room"]) for cfg in LANGUAGES.values()]
    aliases = [
        "book",
        "book a room",
        "book room",
        "booking",
        "make a booking",
        "መያዣ",
        "kireeffachuuf",
        "réserver",
        "reserver",
        "réserver une chambre",
        "reserver une chambre",
    ]
    return value in labels or any(alias in value for alias in aliases)


def is_concierge_request(text: str) -> bool:
    value = normalized_text(text)
    labels = [normalized_text(cfg["concierge_help"]) for cfg in LANGUAGES.values()]
    aliases = ["concierge", "help", "ኮንሲየርጅ", "tajaajila", "assistance"]
    return value in labels or any(alias in value for alias in aliases)


def is_hotel_info_request(text: str) -> bool:
    value = normalized_text(text)
    labels = [normalized_text(cfg["hotel_info"]) for cfg in LANGUAGES.values()]
    aliases = ["hotel", "information", "መረጃ", "odeeffannoo", "hôtel", "hotel"]
    return value in labels or any(alias in value for alias in aliases)


def is_language_change_request(text: str) -> bool:
    value = normalized_text(text)
    aliases = ["change language", "language", "ቋንቋ", "afaan", "langue", "changer"]
    return any(alias in value for alias in aliases)


def is_main_menu_request(text: str) -> bool:
    value = normalized_text(text)
    aliases = [
        "main menu",
        "menu",
        "home",
        "return to main menu",
        "back",
        "cancel",
        "menu principal",
        "annuler",
        "retour",
        "deebi",
        "haqi",
    ]
    return value in aliases or any(alias in value for alias in aliases)


def is_availability_request(text: str) -> bool:
    value = normalized_text(text)
    aliases = [
        "check availability",
        "availability",
        "available rooms",
        "room availability",
        "argama",
        "disponibilite",
        "disponibilitÃ©",
        "disponibilité",
        "verifier la disponibilite",
        "vÃ©rifier la disponibilitÃ©",
        "vérifier la disponibilité",
    ]
    return value in aliases or any(alias in value for alias in aliases)


def is_amenities_request(text: str) -> bool:
    value = normalized_text(text)
    aliases = [
        "amenities",
        "hotel amenities",
        "services",
        "facilities",
        "tajaajila",
        "equipements",
        "Ã©quipements",
        "équipements",
        "services hotel",
    ]
    return value in aliases or any(alias in value for alias in aliases)


def is_frontdesk_request(text: str) -> bool:
    value = normalized_text(text)
    aliases = [
        "contact front desk",
        "front desk",
        "reception",
        "help desk",
        "fuuldura",
        "accueil",
        "contacter la reception",
        "contacter la rÃ©ception",
        "contacter la réception",
    ]
    return value in aliases or any(alias in value for alias in aliases)


def language_keyboard(one_time_keyboard=False):
    return ReplyKeyboardMarkup(
        LANGUAGE_BUTTONS,
        resize_keyboard=True,
        one_time_keyboard=one_time_keyboard,
    )


def hotel_selection_keyboard(hotels):
    buttons = [
        [f"{get_hotel_name(h)} - {get_hotel_property_code(h)}"]
        for h in hotels
        if get_hotel_name(h) and get_hotel_property_code(h)
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)


def main_menu_keyboard(lang="en"):
    """Return localized main menu buttons with stable PMS service actions."""
    if lang == "am":
        buttons = [
            ["🏨 መያዣ", "📅 Check Availability"],
            ["🏨 Amenities", "☎️ Contact Front Desk"],
            ["🏙️ የሆቴል መረጃ", "🌐 ቋንቋ ቀይር"],
            ["🏠 Main Menu", "❌ Cancel"],
        ]
    elif lang == "om":
        buttons = [
            ["🏨 Kireeffachuuf", "📅 Check Availability"],
            ["🏨 Amenities", "☎️ Contact Front Desk"],
            ["🏙️ Odeeffannoo Hooteelaa", "🌐 Afaan Jijjiiri"],
            ["🏠 Main Menu", "❌ Cancel"],
        ]
    elif lang == "fr":
        buttons = [
            ["🏨 Réserver une chambre", "📅 Check Availability"],
            ["🏨 Amenities", "☎️ Contact Front Desk"],
            ["🏙️ Informations sur l’hôtel", "🌐 Changer de langue"],
            ["🏠 Main Menu", "❌ Cancel"],
        ]
    else:
        buttons = [
            ["🏨 Book a Room", "📅 Check Availability"],
            ["🏨 Amenities", "☎️ Contact Front Desk"],
            ["🏙️ Hotel Information", "🌐 Change Language"],
            ["🏠 Main Menu", "❌ Cancel"],
        ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def payment_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["Pay at Hotel", "Card"],
            ["Cash", "Mobile Payment"],
            ["🏦 Bank Transfer"],
            ["Back", "Cancel"],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def executive_booking_confirmation_text(data: dict, booking_id: str | int | None, lang: str) -> str:
    guest_name = data.get("Guest Name") or data.get("guest_name") or "Guest"
    hotel_name = data.get("Hotel Name") or "our hotel"
    confirmation = booking_id or data.get("Booking ID") or "pending"
    stay = f"{data.get('Check-In Date', '')} to {data.get('Check-Out Date', '')}".strip()
    room_type = data.get("Room Type") or "selected room"
    payment_method = data.get("Payment Method") or "selected payment method"

    messages = {
        "en": (
            f"Dear {guest_name},\n\n"
            f"Thank you for choosing {hotel_name}. It is our pleasure to confirm that your reservation request has been received.\n\n"
            f"Confirmation: {confirmation}\n"
            f"Stay dates: {stay}\n"
            f"Room type: {room_type}\n"
            f"Payment method: {payment_method}\n\n"
            "Our Reservations team will review the guarantee/payment status and prepare your arrival with the Front Desk. "
            "We look forward to welcoming you with warm hospitality."
        ),
        "am": (
            f"Dear {guest_name},\n\n"
            f"{hotel_name}ን ስለመረጡ እናመሰግናለን። የመያዣ ጥያቄዎ ተቀብሏል።\n\n"
            f"Confirmation: {confirmation}\n"
            f"Stay dates: {stay}\n"
            f"Room type: {room_type}\n"
            f"Payment method: {payment_method}\n\n"
            "የReservations ቡድናችን የክፍያ/guarantee ሁኔታውን ይገመግማል እና መድረሻዎን ከFront Desk ጋር ያዘጋጃል።"
        ),
        "om": (
            f"Dear {guest_name},\n\n"
            f"{hotel_name} filachuu keessaniif galatoomaa. Gaaffiin booking keessanii fudhatameera.\n\n"
            f"Confirmation: {confirmation}\n"
            f"Stay dates: {stay}\n"
            f"Room type: {room_type}\n"
            f"Payment method: {payment_method}\n\n"
            "Gareen Reservations haala guarantee/payment ni ilaala, Front Desk waliin imala keessan ni qopheessa."
        ),
        "fr": (
            f"Cher/Chère {guest_name},\n\n"
            f"Merci d’avoir choisi {hotel_name}. Nous avons le plaisir de confirmer la réception de votre demande de réservation.\n\n"
            f"Confirmation : {confirmation}\n"
            f"Dates du séjour : {stay}\n"
            f"Type de chambre : {room_type}\n"
            f"Mode de paiement : {payment_method}\n\n"
            "Notre équipe Réservations vérifiera la garantie/le paiement et préparera votre arrivée avec la réception."
        ),
    }
    return messages.get(lang, messages["en"])


# =====================================================
# /START COMMAND
# =====================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    session = get_user_session(uid)
    session["step"] = "choose_language"

    kb = language_keyboard(one_time_keyboard=True)
    msg = (
        "🌍 *Welcome to Guzo Guest Assist!*\n\n"
        "Please choose your preferred language to begin:\n\n"
        "🇬🇧 English | 🇪🇹 አማርኛ | 🇪🇹 Afaan Oromo | 🇫🇷 Français"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)


# =====================================================
# BOOKING FLOW (STEP 1–5)
# =====================================================
async def handle_hotel_selection(update: Update, session, client, lang):
    """Used ONLY by a central multi-hotel bot (not property bots)."""
    text = normalized_text(update.message.text)
    selected_code = text.upper().replace("&", "").replace(" ", "")
    hotels = fetch_hotels(client)
    match = next(
        (
            h
            for h in hotels
            if get_hotel_property_code(h) == selected_code
            or normalized_text(get_hotel_name(h)) in text
            or get_hotel_property_code(h).lower() in text
        ),
        None,
    )
    if not match:
        await update.message.reply_text(
            {
                "en": "⚠️ Please choose a valid hotel.",
                "am": "⚠️ እባክዎን ትክክለኛ ሆቴል ይምረጡ።",
                "om": "⚠️ Mee hotel sirrii filadhu.",
                "fr": "⚠️ Veuillez choisir un hôtel valide.",
            }[lang],
            reply_markup=hotel_selection_keyboard(hotels),
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
            "fr": f"📅 Veuillez entrer votre *date d’arrivée* (YYYY-MM-DD) pour {get_hotel_name(match)}.",
        }[lang],
        parse_mode="Markdown",
    )


async def handle_date_entry(update: Update, session, lang):
    """
    Handle check-in and check-out dates.

    ✅ NEW:
       After check-out date is valid, we call FastAPI /bot/availability via
       check_availability_for_bot() to ensure rooms exist in Postgres.
    """
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
                "fr": "⚠️ Format de date invalide. Veuillez utiliser YYYY-MM-DD.",
            }[lang]
        )
        return

    # Step 1: Check-in date
    if session["step"] == "check_in_date":
        data["Check-In Date"] = str(date_obj)
        session["step"] = "check_out_date"
        await update.message.reply_text(
            {
                "en": "📆 Please enter your *check-out date* (YYYY-MM-DD):",
                "am": "📆 እባክዎን የመውጫ ቀንዎን ያስገቡ (YYYY-MM-DD):",
                "om": "📆 Mee guyyaa baʼii kee galchi (YYYY-MM-DD):",
                "fr": "📆 Veuillez entrer votre *date de départ* (YYYY-MM-DD) :",
            }[lang],
            parse_mode="Markdown",
        )
        return

    # Step 2: Check-out date
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
                    "fr": "⚠️ La date de départ doit être après la date d’arrivée.",
                }[lang]
            )
            return

        data["Check-Out Date"] = str(date_obj)
        data["Nights"] = (date_obj - check_in).days

        # ✅ NEW: Check real availability via backend /bot/availability
        property_code = data.get("Property Code")
        if property_code:
            try:
                avail = check_availability_for_bot(
                    property_code=property_code,
                    check_in=data["Check-In Date"],
                    check_out=data["Check-Out Date"],
                    rooms=1,
                )
                if not avail.get("available"):
                    # If backend returns nice message, reuse it
                    backend_msg = avail.get("message") or ""
                    human_msg = {
                        "en": (
                            "❌ Unfortunately, there is no availability for those dates.\n\n"
                            f"{backend_msg}\n\n"
                            "Please try different dates."
                        ),
                        "am": (
                            "❌ ያስገቡት ቀናት ላይ ክፍት ክፍሎች የሉም።\n\n"
                            f"{backend_msg}\n\n"
                            "እባክዎ ሌሎች ቀናት ይሞክሩ።"
                        ),
                        "om": (
                            "❌ Guyyoota kanaaf kottuun hin jiruu.\n\n"
                            f"{backend_msg}\n\n"
                            "Mee guyyaa biro yaali.",
                        ),
                        "fr": (
                            "❌ Malheureusement, il n’y a pas de disponibilité pour ces dates.\n\n"
                            f"{backend_msg}\n\n"
                            "Veuillez essayer d’autres dates."
                        ),
                    }[lang]
                    # Reset step back to check_in_date so they can retry
                    session["step"] = "check_in_date"
                    await update.message.reply_text(human_msg)
                    return
                else:
                    # Optionally show backend's positive message
                    backend_msg = avail.get("message")
                    if backend_msg:
                        await update.message.reply_text(backend_msg)
            except Exception as e:
                logging.error(f"[AvailabilityCheck] Error calling backend: {e}")
                # Fail gracefully: continue with old flow, no crash
                await update.message.reply_text(
                    {
                        "en": "ℹ️ We could not verify live availability right now, but we’ll continue your request.",
                        "am": "ℹ️ በአሁኑ ጊዜ ቀጥታ ክፍትነትን ማረጋገጥ አልቻልንም፣ ግን መርሃ ግብሩን እንቀጥላለን።",
                        "om": "ℹ️ Amma haala kallattiin sakattaʼuu hin dandeenye, garuu itti fufna.",
                        "fr": "ℹ️ Nous ne pouvons pas vérifier la disponibilité en direct maintenant, mais nous allons continuer votre demande.",
                    }[lang]
                )

        # If availability is OK or check failed gracefully → collect occupancy.
        session["step"] = "guest_count"
        await update.message.reply_text(
            {
                "en": f"🛏️ Great! You’ll stay for {data['Nights']} night(s). How many adults will be staying?",
                "am": f"🛏️ ጥሩ! ለ {data['Nights']} ሌሊት ትቆያላችሁ። ስንት አዋቂዎች ይቆያሉ?",
                "om": f"🛏️ Gaariidha! Halkanoota {data['Nights']} turtuuf. Namoonni gurguddoon meeqa turu?",
                "fr": f"🛏️ Parfait ! Vous séjournerez {data['Nights']} nuit(s). Combien d’adultes séjourneront ?",
            }[lang]
        )


async def handle_guest_count(update: Update, session, lang):
    text = update.message.text.strip()
    match = re.search(r"\d+", text)
    if not match:
        await update.message.reply_text(
            {
                "en": "⚠️ Please enter the number of adults, for example: 2.",
                "am": "⚠️ እባክዎን የአዋቂዎችን ብዛት ያስገቡ፣ ለምሳሌ፦ 2።",
                "om": "⚠️ Mee lakkoofsa namoota gurguddoo galchi, fakkeenyaaf: 2.",
                "fr": "⚠️ Veuillez entrer le nombre d’adultes, par exemple : 2.",
            }[lang]
        )
        return

    adults = int(match.group(0))
    if adults < 1 or adults > 12:
        await update.message.reply_text(
            {
                "en": "⚠️ Please enter an adult count between 1 and 12.",
                "am": "⚠️ እባክዎን ከ1 እስከ 12 ያለ የአዋቂዎች ብዛት ያስገቡ።",
                "om": "⚠️ Mee lakkoofsa namoota gurguddoo 1 hanga 12 gidduutti galchi.",
                "fr": "⚠️ Veuillez entrer un nombre d’adultes entre 1 et 12.",
            }[lang]
        )
        return

    session["data"]["Adults"] = adults
    session["step"] = "children_count"
    await update.message.reply_text(
        {
            "en": "Thank you. How many children will be staying? Please enter 0 if none.",
            "am": "እናመሰግናለን። ስንት ልጆች ይቆያሉ? ከሌለ 0 ያስገቡ።",
            "om": "Galatoomi. Daa'imman meeqa turu? Yoo hin jirre 0 galchi.",
            "fr": "Merci. Combien d’enfants séjourneront ? Entrez 0 s’il n’y en a pas.",
        }[lang]
    )


async def handle_children_count(update: Update, session, lang):
    text = update.message.text.strip()
    match = re.search(r"\d+", text)
    if not match:
        await update.message.reply_text(
            {
                "en": "⚠️ Please enter the number of children, or 0 if none.",
                "am": "⚠️ እባክዎን የልጆችን ብዛት ያስገቡ፣ ከሌለ 0።",
                "om": "⚠️ Mee lakkoofsa daa'immanii galchi, yoo hin jirre 0.",
                "fr": "⚠️ Veuillez entrer le nombre d’enfants, ou 0 s’il n’y en a pas.",
            }[lang]
        )
        return

    children = int(match.group(0))
    if children < 0 or children > 12:
        await update.message.reply_text(
            {
                "en": "⚠️ Please enter a children count between 0 and 12.",
                "am": "⚠️ እባክዎን ከ0 እስከ 12 ያለ የልጆች ብዛት ያስገቡ።",
                "om": "⚠️ Mee lakkoofsa daa'immanii 0 hanga 12 gidduutti galchi.",
                "fr": "⚠️ Veuillez entrer un nombre d’enfants entre 0 et 12.",
            }[lang]
        )
        return

    adults = int(session["data"].get("Adults") or 1)
    session["data"]["Children"] = children
    session["data"]["Guest Count"] = adults + children
    session["step"] = "room_type"
    await update.message.reply_text(
        {
            "en": "Thank you. Now fetching available room types...",
            "am": "እናመሰግናለን። አሁን የሚገኙ የክፍል አይነቶችን እንመልከታለን...",
            "om": "Galatoomi. Amma gosoota kottuu jiran ilaalla...",
            "fr": "Merci. Nous recherchons maintenant les types de chambres disponibles...",
        }[lang]
    )
    await handle_room_selection(update, None, session, lang)


def _session_property_code(session) -> str:
    property_code = session["data"].get("Property Code") or HOTEL_PROPERTY_CODE
    if not property_code or property_code == "ALL":
        property_code = "DRE001"
    return property_code


def _room_type_keyboard(session):
    property_code = _session_property_code(session)
    records = get_room_rates_from_postgres_fallback(property_code)
    buttons = [
        [
            f"{r['Room Type']} – {r.get('Rate (ETB)', r.get('Rack Rate (ETB)', 0))} ETB"
        ]
        for r in records
    ]
    buttons.append(["Back", "Cancel"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)


async def handle_availability_dates(update: Update, session, lang):
    text = update.message.text.strip()
    parts = re.findall(r"\d{4}-\d{2}-\d{2}", text)
    if len(parts) < 2:
        await update.message.reply_text(
            {
                "en": "Please send your dates like this: 2026-06-01 to 2026-06-02.",
                "am": "እባክዎን ቀኖቹን በዚህ መልኩ ይላኩ: 2026-06-01 to 2026-06-02.",
                "om": "Mee guyyoota akkana ergi: 2026-06-01 to 2026-06-02.",
                "fr": "Veuillez envoyer vos dates ainsi : 2026-06-01 to 2026-06-02.",
            }[lang]
        )
        return

    check_in, check_out = parts[0], parts[1]
    try:
        datetime.datetime.strptime(check_in, "%Y-%m-%d")
        datetime.datetime.strptime(check_out, "%Y-%m-%d")
        if check_out <= check_in:
            raise ValueError("checkout must be after checkin")
    except ValueError:
        await update.message.reply_text(
            {
                "en": "Please use valid dates, with check-out after check-in.",
                "am": "እባክዎን ትክክለኛ ቀኖችን ይጠቀሙ፤ የመውጫ ቀን ከመግቢያ ቀን በኋላ መሆን አለበት።",
                "om": "Mee guyyaa sirrii galchi; guyyaan bahumsaa guyyaa galumsaa booda ta'uu qaba.",
                "fr": "Veuillez utiliser des dates valides, avec le départ après l'arrivée.",
            }[lang]
        )
        return

    property_code = _session_property_code(session)
    try:
        result = check_availability_for_bot(property_code, check_in, check_out)
        available = result.get("available", False)
        backend_msg = result.get("message") or ""
        reply = {
            "en": "Rooms are available for those dates." if available else "No rooms are available for those dates.",
            "am": "ለእነዚህ ቀኖች ክፍሎች አሉ።" if available else "ለእነዚህ ቀኖች ክፍሎች አይገኙም።",
            "om": "Guyyoota kanaaf kottuun ni jira." if available else "Guyyoota kanaaf kottuun hin jiru.",
            "fr": "Des chambres sont disponibles pour ces dates." if available else "Aucune chambre n'est disponible pour ces dates.",
        }[lang]
        if backend_msg:
            reply = f"{reply}\n\n{backend_msg}"
    except Exception as e:
        logging.error(f"[AvailabilityButton] Error checking availability: {e}")
        reply = {
            "en": "I could not verify live availability right now. Please try again shortly or contact the front desk.",
            "am": "በአሁኑ ጊዜ ቀጥታ ክፍትነትን ማረጋገጥ አልቻልኩም። እባክዎን ትንሽ ቆይተው ይሞክሩ ወይም ሪሴፕሽን ያግኙ።",
            "om": "Amma kallattiin sakatta'uu hin dandeenye. Mee boodarra yaali yookaan fuuldura qunnami.",
            "fr": "Je ne peux pas vérifier la disponibilité en direct maintenant. Veuillez réessayer ou contacter la réception.",
        }[lang]

    session["step"] = "main_menu"
    await update.message.reply_text(reply, reply_markup=main_menu_keyboard(lang))


async def handle_frontdesk_request(update: Update, session, lang):
    request_text = update.message.text.strip()
    data = session["data"]
    logging.info(
        "[FrontDesk] Telegram request | guest=%s | property=%s | message=%s",
        update.effective_user.full_name,
        data.get("Property Code") or HOTEL_PROPERTY_CODE,
        request_text,
    )
    session["step"] = "main_menu"
    await update.message.reply_text(
        {
            "en": "Thank you. Your front desk request has been received. A team member will follow up shortly.",
            "am": "እናመሰግናለን። የሪሴፕሽን ጥያቄዎ ተቀብሏል። የቡድን አባል በቅርቡ ይከታተላል።",
            "om": "Galatoomi. Gaaffiin kee fuulduraaf fudhatameera. Miseensi garee yeroo dhihootti si qunnama.",
            "fr": "Merci. Votre demande à la réception a été reçue. Un membre de l'équipe vous répondra bientôt.",
        }[lang],
        reply_markup=main_menu_keyboard(lang),
    )


async def handle_room_selection(update: Update, client, session, lang):
    session["step"] = "room_choice"
    await update.message.reply_text(
        {
            "en": "Please choose your preferred room type:",
            "am": "እባክዎን የክፍል አይነት ይምረጡ።",
            "om": "Mee gosa kottuu filadhu:",
            "fr": "Veuillez choisir votre type de chambre préféré :",
        }[lang],
        reply_markup=_room_type_keyboard(session),
    )


async def handle_room_choice(update: Update, session, lang):
    text = update.message.text.strip()
    room_type_map = {
        "standard room": "Standard Room",
        "standard": "Standard Room",
        "deluxe room": "Deluxe Room",
        "deluxe": "Deluxe Room",
        "family room": "Family Room",
        "family": "Family Room",
        "suite": "Suite",
    }

    if "–" in text:
        room_type, rate_text = text.split("–", 1)
        room_type = room_type.strip()
        try:
            rate = int(re.findall(r"\d+", rate_text)[0])
        except Exception:
            rate = 0
    else:
        room_type = room_type_map.get(normalized_text(text))
        if room_type:
            property_code = session["data"].get("Property Code", HOTEL_PROPERTY_CODE)
            records = get_room_rates_from_postgres_fallback(property_code)
            rate = next(
                (
                    int(r.get("Rate (ETB)", r.get("Rack Rate (ETB)", 0)) or 0)
                    for r in records
                    if normalized_text(r.get("Room Type")) == normalized_text(room_type)
                ),
                0,
            )

    if not room_type:
        await update.message.reply_text(
            {
                "en": "⚠️ Please select a valid room type.",
                "am": "⚠️ እባክዎን ትክክለኛ የክፍል አይነት ይምረጡ።",
                "om": "⚠️ Mee gosa kottuu sirrii filadhu.",
                "fr": "⚠️ Veuillez sélectionner un type de chambre valide.",
            }[lang],
            reply_markup=_room_type_keyboard(session),
        )
        return

    data = session["data"]
    data["Room Type"] = room_type
    data["Rate Per Night (ETB)"] = rate
    data["Total Revenue (ETB)"] = rate * int(data.get("Nights", 1))
    guest_count = int(data.get("Guest Count") or 1)
    if guest_count >= 3 and "family" not in data["Room Type"].lower():
        await update.message.reply_text(
            {
                "en": "ℹ️ For 3 or more guests, a Family Room or Suite is usually recommended under hotel reservation SOP.",
                "am": "ℹ️ ለ3 ወይም ከዚያ በላይ እንግዶች በሆቴል መያዣ SOP መሰረት Family Room ወይም Suite ይመከራል።",
                "om": "ℹ️ Keessummoota 3 fi isaa oliif, SOP hoteelaa jalatti Family Room yookaan Suite ni gorfama.",
                "fr": "ℹ️ Pour 3 clients ou plus, une Family Room ou une Suite est généralement recommandée selon les SOP hôtelières.",
            }[lang]
        )
    session["step"] = "payment"

    await update.message.reply_text(
        {
            "en": f"💳 Total *{data['Total Revenue (ETB)']} ETB* for {data['Nights']} night(s). Choose payment method:",
            "am": f"💳 ጠቅላላ ዋጋ *{data['Total Revenue (ETB)']} ETB*። እባክዎን መንገድ ይምረጡ።",
            "om": f"💳 Waliigala *{data['Total Revenue (ETB)']} ETB*. Mala kaffaltii filadhu:",
            "fr": f"💳 Total *{data['Total Revenue (ETB)']} ETB* pour {data['Nights']} nuit(s). Choisissez le mode de paiement :",
        }[lang],
        parse_mode="Markdown",
        reply_markup=payment_keyboard(),
    )
    return


# =====================================================
# BOOKING FLOW (STEP 6 – PAYMENT → EMAIL CAPTURE)
# =====================================================
async def handle_payment(update: Update, session, lang):
    """Step 6 – Capture payment method → ask for guest email."""
    text = normalized_text(update.message.text)
    data = session["data"]

    if any(k in text for k in ["pay at hotel", "hotel", "arrival"]):
        data["Payment Method"] = "Pay at Hotel"
        data["Payment Status"] = "Pending"
    elif any(k in text for k in ["cash", "ጥሬ"]):
        data["Payment Method"] = "💵 Cash"
        data["Payment Status"] = "Pending"
    elif any(k in text for k in ["card", "ካርድ"]):
        data["Payment Method"] = "💳 Card"
        data["Payment Status"] = "Pending"
    elif any(k in text for k in ["mobile", "telebirr", "m-pesa", "mpesa"]):
        data["Payment Method"] = "Mobile Payment"
        data["Payment Status"] = "Pending"
    elif any(k in text for k in ["bank", "ባንክ"]):
        data["Payment Method"] = "🏦 Bank Transfer"
        data["Payment Status"] = "Pending"
    else:
        await update.message.reply_text(
            {
                "en": "⚠️ Please choose a valid payment method.",
                "am": "⚠️ እባክዎን ትክክለኛ መንገድ ይምረጡ።",
                "om": "⚠️ Mee mala kaffaltii sirrii filadhu.",
                "fr": "⚠️ Veuillez choisir un mode de paiement valide.",
            }[lang],
            reply_markup=payment_keyboard(),
        )
        return

    session["step"] = "guest_name"
    await update.message.reply_text(
        {
            "en": "👤 Please enter the guest's full legal name for the reservation:",
            "am": "👤 እባክዎን ለመያዣው የእንግዳውን ሙሉ ስም ያስገቡ።",
            "om": "👤 Mee maqaa guutuu keessummaa galchi.",
            "fr": "👤 Veuillez entrer le nom complet du client pour la réservation :",
        }[lang],
        reply_markup=ReplyKeyboardRemove(),
    )


# =====================================================
# STEP 7 – GUEST PROFILE, SAVE BOOKING, SEND CONFIRMATION
# =====================================================
async def handle_guest_name(update: Update, session, lang):
    guest_name = re.sub(r"\s+", " ", update.message.text.strip())
    if len(guest_name) < 3 or not re.search(r"[A-Za-z\u1200-\u137F]", guest_name):
        await update.message.reply_text(
            {
                "en": "⚠️ Please enter a valid full guest name.",
                "am": "⚠️ እባክዎን ትክክለኛ ሙሉ የእንግዳ ስም ያስገቡ።",
                "om": "⚠️ Mee maqaa keessummaa sirrii galchi.",
                "fr": "⚠️ Veuillez entrer un nom complet valide.",
            }[lang]
        )
        return

    session["data"]["Guest Name"] = guest_name
    session["step"] = "guest_phone"
    await update.message.reply_text(
        {
            "en": "📱 Please enter the guest phone number with country code if available:",
            "am": "📱 እባክዎን የእንግዳውን ስልክ ቁጥር ከአገር ኮድ ጋር ያስገቡ።",
            "om": "📱 Mee lakkoofsa bilbilaa keessummaa, yoo danda'ame koodii biyya waliin, galchi.",
            "fr": "📱 Veuillez entrer le numéro de téléphone du client avec l’indicatif du pays si possible :",
        }[lang]
    )


async def handle_guest_phone(update: Update, session, lang):
    phone = update.message.text.strip()
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 7 or len(digits) > 15:
        await update.message.reply_text(
            {
                "en": "⚠️ Please enter a valid phone number, for example +251911000000.",
                "am": "⚠️ እባክዎን ትክክለኛ ስልክ ቁጥር ያስገቡ፣ ለምሳሌ +251911000000።",
                "om": "⚠️ Mee lakkoofsa bilbilaa sirrii galchi, fakkeenyaaf +251911000000.",
                "fr": "⚠️ Veuillez entrer un numéro de téléphone valide, par exemple +251911000000.",
            }[lang]
        )
        return

    session["data"]["Guest Phone"] = phone
    session["step"] = "guest_email"
    await update.message.reply_text(
        {
            "en": "📧 Please enter the guest email address for the booking confirmation:",
            "am": "📧 እባክዎን ለመያዣ ማረጋገጫ የእንግዳውን ኢሜል አድራሻ ያስገቡ።",
            "om": "📧 Mee teessoo imeelii keessummaa mirkaneessaaf galchi.",
            "fr": "📧 Veuillez entrer l’adresse e-mail du client pour la confirmation :",
        }[lang]
    )


async def handle_guest_email(update: Update, client, session, lang):
    """
    Step 7 – Validate guest email → save booking + send email.

    ✅ NEW:
      • Use FastAPI /bot/bookings via create_booking_for_bot() to create the
        canonical booking record in Postgres.
      • Google Sheets writes are disabled; PostgreSQL backend is source of truth.
      • Removed double direct Postgres inserts (#3 fix).
    """
    email = update.message.text.strip()
    if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        await update.message.reply_text(
            {
                "en": "⚠️ Invalid email address. Please enter a valid one.",
                "am": "⚠️ የተሳሳተ ኢሜል ነው። እባክዎ ትክክለኛ ኢሜል ይስጡ።",
                "om": "⚠️ Imeelii sirrii galchi.",
                "fr": "⚠️ Adresse e-mail invalide. Veuillez entrer une adresse valide.",
            }[lang]
        )
        return

    data = session["data"]
    data["Guest Email"] = email
    session["step"] = "confirmed"

    # Stamp metadata
    now = datetime.datetime.now()
    data["Confirmation ID"] = f"GZ-{now.strftime('%y%m%d%H%M')}"
    data["Guest Name"] = data.get("Guest Name") or update.effective_user.full_name or "Guest"
    data["Source"] = "Telegram"
    data["Booking Status"] = "Confirmed"
    data["Payment Status"] = data.get("Payment Status", "Pending")
    data["Payment Date"] = now.strftime("%Y-%m-%d")
    data["Property Code"] = data.get("Property Code", "UNKNOWN")

    # ✅ Create canonical booking via FastAPI backend (/bot/bookings)
    booking_id = None
    try:
        backend_booking = create_booking_for_bot(
            property_code=data.get("Property Code", "UNKNOWN"),
            check_in=data.get("Check-In Date"),
            check_out=data.get("Check-Out Date"),
            guest_name=data.get("Guest Name", "Guest"),
            channel="telegram",
            total_amount_etb=data.get("Total Revenue (ETB)"),
            room_type=data.get("Room Type"),
            guest_email=data.get("Guest Email"),
            guest_count=data.get("Guest Count"),
            payment_method=data.get("Payment Method"),
            payment_status=data.get("Payment Status"),
            guest_phone=data.get("Guest Phone"),
            adults=data.get("Adults"),
            children=data.get("Children"),
            purpose_of_visit="Leisure",
            notes=(
                "Five-star online reservation captured via Telegram | "
                f"Telegram Chat ID: {update.effective_chat.id} | "
                f"Guest phone: {data.get('Guest Phone', '')} | "
                f"Adults: {data.get('Adults', 1)} | "
                f"Children: {data.get('Children', 0)}"
            ),
        )
        booking_id = backend_booking.get("booking_id")
        # Optional: override hotel name / property code if backend returns them
        if backend_booking.get("hotel_name"):
            data["Hotel Name"] = backend_booking["hotel_name"]
        if backend_booking.get("property_code"):
            data["Property Code"] = backend_booking["property_code"]

        data["Backend Booking ID"] = booking_id
        logging.info(
            f"[BotBookings] ✅ Created backend booking id={booking_id} for guest={data['Guest Name']}"
        )
    except Exception as e:
        logging.error(f"[BotBookings] ❌ Failed to create backend booking: {e}")
        session["step"] = "guest_email"
        await update.message.reply_text(
            {
                "en": "⚠️ I could not save this reservation in Guzo PMS yet. Please try again in a moment or contact the front desk.",
                "am": "⚠️ ይህን መያዣ በGuzo PMS ውስጥ ማስቀመጥ አልቻልኩም። እባክዎን ትንሽ ቆይተው ይሞክሩ ወይም ሪሴፕሽን ያግኙ።",
                "om": "⚠️ Turtina kana amma Guzo PMS keessatti olkaa'uu hin dandeenye. Mee boodarra yaali yookaan fuuldura qunnami.",
                "fr": "⚠️ Je n’ai pas pu enregistrer cette réservation dans Guzo PMS. Veuillez réessayer ou contacter la réception.",
            }[lang],
            reply_markup=main_menu_keyboard(lang),
        )
        return

    logging.info(
        "[BotBookings] Google Sheets disabled; booking source of truth is backend id=%s",
        booking_id,
    )

    # Telegram confirmation message
    ref_line = f"🧾 Confirmation ID: {data['Confirmation ID']}"
    if booking_id:
        ref_line += f"\n🔢 Backend Ref: {booking_id}"

    msg = executive_booking_confirmation_text(data, booking_id or data["Confirmation ID"], lang)
    legacy_msg = {
        "en": (
            f"✅ *Booking Confirmed!*\n\n"
            f"🏨 Hotel: {data.get('Hotel Name', 'Hotel')}\n"
            f"{ref_line}\n"
            f"📅 {data.get('Check-In Date','')} → {data.get('Check-Out Date','')}\n"
            f"👥 Guests: {data.get('Guest Count', 1)} "
            f"(Adults {data.get('Adults', 1)}, Children {data.get('Children', 0)})\n"
            f"👤 Guest: {data['Guest Name']}\n"
            f"📱 Phone: {data.get('Guest Phone', '')}\n"
            f"💰 Total: {data.get('Total Revenue (ETB)',0)} ETB\n\n"
            "📧 A confirmation email has been sent to your inbox."
        ),
        "am": (
            f"✅ *ቦኪንግዎ ተረጋገጠ!*\n\n"
            f"🏨 ሆቴል፡ {data.get('Hotel Name', 'Hotel')}\n"
            f"{ref_line}\n"
            f"📅 {data.get('Check-In Date','')} → {data.get('Check-Out Date','')}\n"
            f"👥 እንግዶች፡ {data.get('Guest Count', 1)} "
            f"(አዋቂዎች {data.get('Adults', 1)}, ልጆች {data.get('Children', 0)})\n"
            f"👤 እንግዳ፡ {data['Guest Name']}\n"
            f"📱 ስልክ፡ {data.get('Guest Phone', '')}\n"
            f"💰 ጠቅላላ ዋጋ፡ {data.get('Total Revenue (ETB)',0)} ብር\n\n"
            "📧 የማረጋገጫ ኢሜል ወደ መልዕክት ሳጥንዎ ተልኳል።"
        ),
        "om": (
            f"✅ *Turtin kee ni mirkanaa’e!*\n\n"
            f"🏨 Hoteela: {data.get('Hotel Name', 'Hotel')}\n"
            f"{ref_line}\n"
            f"📅 {data.get('Check-In Date','')} → {data.get('Check-Out Date','')}\n"
            f"👥 Keessummoota: {data.get('Guest Count', 1)} "
            f"(Gurguddoo {data.get('Adults', 1)}, Daa'imman {data.get('Children', 0)})\n"
            f"👤 Daawataa: {data['Guest Name']}\n"
            f"📱 Bilbila: {data.get('Guest Phone', '')}\n"
            f"💰 Waliigala Kaffaltii: {data.get('Total Revenue (ETB)',0)} ETB\n\n"
            "📧 Imeelii mirkaneessaa gara sanduuqa kee ergameera."
        ),
        "fr": (
            f"✅ *Réservation confirmée !*\n\n"
            f"🏨 Hôtel : {data.get('Hotel Name', 'Hotel')}\n"
            f"{ref_line}\n"
            f"📅 {data.get('Check-In Date','')} → {data.get('Check-Out Date','')}\n"
            f"👥 Clients : {data.get('Guest Count', 1)} "
            f"(Adultes {data.get('Adults', 1)}, Enfants {data.get('Children', 0)})\n"
            f"👤 Client : {data['Guest Name']}\n"
            f"📱 Téléphone : {data.get('Guest Phone', '')}\n"
            f"💰 Total : {data.get('Total Revenue (ETB)',0)} ETB\n\n"
            "📧 Un e-mail de confirmation a été envoyé dans votre boîte de réception."
        ),
    }[lang]

    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["🏠 Main Menu"]], resize_keyboard=True),
    )
    session["step"] = "main_menu"

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
        "Guests": data.get("Guest Count", ""),
        "Adults": data.get("Adults", ""),
        "Children": data.get("Children", ""),
        "Guest Phone": data.get("Guest Phone", ""),
        "Room Type": data.get("Room Type", ""),
        "Total Revenue (ETB)": data.get("Total Revenue (ETB)", ""),
        "Confirmation ID": data.get("Confirmation ID", ""),
        "Backend Booking ID": booking_id,
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
    """Display hotel overview and room rates from backend-mode fallbacks."""
    text = update.message.text.strip()
    hotels = fetch_hotels(client)
    hotel = next(
        (h for h in hotels if get_hotel_name(h).lower() == text.lower()), None
    )

    # If text doesn't match, try using the current session's hotel (per-property bot)
    if not hotel:
        data = session["data"]
        current_name = data.get("Hotel Name")
        if current_name:
            hotel = {
                "Hotel Name": current_name,
                "Property Code": data.get("Property Code", HOTEL_PROPERTY_CODE),
                "Sheet ID": None,
            }
        else:
            await update.message.reply_text(
                {
                    "en": "⚠️ Please select a valid hotel from the list.",
                    "am": "⚠️ እባክዎን ከዝርዝሩ ውስጥ ትክክለኛ ሆቴል ይምረጡ።",
                    "om": "⚠️ Mee hotel sirrii tarree keessaa filadhu.",
                    "fr": "⚠️ Veuillez sélectionner un hôtel valide dans la liste.",
                }[lang]
            )
            return

    session["data"]["Hotel Name"] = hotel["Hotel Name"]
    session["data"]["Sheet ID"] = hotel["Sheet ID"]

    property_code = (
        get_hotel_property_code(hotel)
        or session["data"].get("Property Code")
        or HOTEL_PROPERTY_CODE
    )
    profile = get_hotel_profile_from_postgres_fallback(property_code)
    room_records = get_room_rates_from_postgres_fallback(property_code)

    room_lines = []
    for r in room_records:
        room_lines.append(
            f"🏷 *{r['Room Type']}* — {r.get('Rate (ETB)', 0)} ETB (~${r.get('Rack Rate (USD)', 'N/A')})"
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
        "fr": (
            f"🏨 *{hotel['Hotel Name']}* ({profile.get('Rating (Stars)', '—')}⭐)\n\n"
            f"📝 *Aperçu* : {profile.get('Hotel Overview','—')}\n"
            f"✨ *Services* : {profile.get('Amenities','—')}\n"
            f"📍 *À proximité* : {profile.get('Nearby Attractions','—')}\n"
            f"🌐 *Site web* : {profile.get('Website','—')}\n\n"
            f"💰 *Tarifs des chambres :*\n{room_text}\n\n"
            f"💁 Nous serons ravis de vous accueillir bientôt !"
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

    profile = get_hotel_profile_from_postgres_fallback(
        data.get("Property Code", HOTEL_PROPERTY_CODE)
    )
    amenities = str(profile.get("Amenities", "")).lower()

    def respond(msg_en, msg_am, msg_om, msg_fr=None):
        return {"en": msg_en, "am": msg_am, "om": msg_om, "fr": msg_fr or msg_en}[lang]

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
    elif any(
        k in text for k in ["dining", "restaurant", "food", "ምግብ", "ሬስቶራንት"]
    ):
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
        if not data.get("Hotel Name"):
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
                if BOT_MODE == "PROPERTY":
                    name = PROPERTY_FALLBACK_NAME or f"Hotel {property_code}"
                    data.setdefault("Hotel Name", name)
                    data.setdefault("Sheet ID", PROPERTY_FALLBACK_SHEET_ID)
                    if PROPERTY_FALLBACK_RES_EMAIL:
                        data.setdefault(
                            "Reservation Email", PROPERTY_FALLBACK_RES_EMAIL
                        )
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
    if is_main_menu_request(text):
        reset_session(uid)
        s = get_user_session(uid)
        s["lang"] = lang
        s["step"] = "main_menu"
        await update.message.reply_text(
            get_text(lang, "main_menu"), reply_markup=main_menu_keyboard(lang)
        )
        return

    if session["step"] == "choose_language":
        lower = text.lower()
        if "english" in lower:
            session["lang"] = "en"
        elif "አማርኛ" in text or "amharic" in lower:
            session["lang"] = "am"
        elif "afaan" in lower or "oromo" in lower:
            session["lang"] = "om"
        elif "français" in lower or "francais" in lower or "french" in lower:
            session["lang"] = "fr"
        else:
            await update.message.reply_text(
                "⚠️ Please tap one of the language options."
            )
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
    if session["step"] == "guest_count":
        await handle_guest_count(update, session, lang)
        return
    if session["step"] == "children_count":
        await handle_children_count(update, session, lang)
        return
    if session["step"] == "availability_dates":
        await handle_availability_dates(update, session, lang)
        return
    if session["step"] == "frontdesk_request":
        await handle_frontdesk_request(update, session, lang)
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
    if session["step"] == "guest_name":
        await handle_guest_name(update, session, lang)
        return
    if session["step"] == "guest_phone":
        await handle_guest_phone(update, session, lang)
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

        # 1️⃣ Booking
        if is_booking_request(text):

            # 🔒 PROPERTY BOT: always use its own hotel, never show list
            if BOT_MODE == "PROPERTY":
                # Make sure this session is bound to a hotel row (via Postgres)
                if not data.get("Hotel Name"):
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
                        logging.error(
                            "[BOOK] Property bot could not resolve a hotel row."
                        )
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
                        "fr": f"📅 Veuillez entrer votre *date d’arrivée* (YYYY-MM-DD) pour {data['Hotel Name']}.",
                    }[lang],
                    parse_mode="Markdown",
                )
                return

            # 🌐 CENTRAL BOT: if already have hotel in session, skip list
            if data.get("Hotel Name"):
                session["step"] = "check_in_date"
                await update.message.reply_text(
                    {
                        "en": f"📅 Please enter your *check-in date* (YYYY-MM-DD) for {data['Hotel Name']}.",
                        "am": "📅 እባክዎን የመግቢያ ቀንዎን ያስገቡ (YYYY-MM-DD)።",
                        "om": f"📅 Mee guyyaa seensaa kee galchi (YYYY-MM-DD) kan {data['Hotel Name']}.",
                        "fr": f"📅 Veuillez entrer votre *date d’arrivée* (YYYY-MM-DD) pour {data['Hotel Name']}.",
                    }[lang],
                    parse_mode="Markdown",
                )
                return

            session["step"] = "select_hotel"
            await update.message.reply_text(
                {
                    "en": "Great! Which hotel would you like to book?",
                    "am": "ጥሩ! የትኛውን ሆቴል መያዝ ይፈልጋሉ?",
                    "om": "Gaariidha! Hoteela kamiif kireeffachuu barbaadda?",
                    "fr": "Parfait ! Dans quel hôtel souhaitez-vous réserver ?",
                }[lang],
                reply_markup=hotel_selection_keyboard(hotels),
            )
            return

        # 2️⃣ Concierge
        if is_availability_request(text):
            session["step"] = "availability_dates"
            await update.message.reply_text(
                {
                    "en": "Please send your dates like this: 2026-06-01 to 2026-06-02.",
                    "am": "Please send your dates like this: 2026-06-01 to 2026-06-02.",
                    "om": "Mee guyyoota akkana ergi: 2026-06-01 to 2026-06-02.",
                    "fr": "Veuillez envoyer vos dates ainsi : 2026-06-01 to 2026-06-02.",
                }[lang]
            )
            return

        if is_amenities_request(text):
            profile = get_hotel_profile_from_postgres_fallback(_session_property_code(session))
            await update.message.reply_text(
                {
                    "en": f"Our hotel amenities include: {profile.get('Amenities', 'front desk support, housekeeping, room service information, maintenance request, and local guidance')}.",
                    "am": f"Our hotel amenities include: {profile.get('Amenities', 'front desk support, housekeeping, room service information, maintenance request, and local guidance')}.",
                    "om": f"Tajaajiloonni hoteelaa: {profile.get('Amenities', 'front desk support, housekeeping, room service information, maintenance request, and local guidance')}.",
                    "fr": f"Nos services incluent : {profile.get('Amenities', 'front desk support, housekeeping, room service information, maintenance request, and local guidance')}.",
                }[lang],
                reply_markup=main_menu_keyboard(lang),
            )
            return

        if is_frontdesk_request(text):
            session["step"] = "frontdesk_request"
            await update.message.reply_text(
                {
                    "en": "Front desk has been notified. Please describe what you need help with.",
                    "am": "Front desk has been notified. Please describe what you need help with.",
                    "om": "Fuuldurri beeksifameera. Mee waan gargaarsa barbaaddu ibsi.",
                    "fr": "La reception a ete informee. Veuillez decrire votre demande.",
                }[lang]
            )
            return

        if is_concierge_request(text):
            session["step"] = "concierge"
            await handle_concierge_request(update, session, lang, client)
            return

        # 3️⃣ Hotel Info
        if is_hotel_info_request(text):
            # For per-property bot, show this hotel's info directly
            if data.get("Hotel Name"):
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
                    "fr": "🏨 Veuillez sélectionner un hôtel pour afficher ses informations complètes :",
                }[lang],
                reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True),
            )
            return

        # 4️⃣ Change Language
        if is_language_change_request(text):
            session["step"] = "choose_language"
            await update.message.reply_text(
                get_text(lang, "choose_language"), reply_markup=language_keyboard()
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
    print("✅ PostgreSQL backend mode enabled. Google Sheets disabled.")
    print("🤖 Starting Guzo Guest Assist Bot...")

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(60)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(
        CommandHandler("test", lambda u, c: u.message.reply_text("✅ System operational."))
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    print("✅ Bot is live and ready.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
