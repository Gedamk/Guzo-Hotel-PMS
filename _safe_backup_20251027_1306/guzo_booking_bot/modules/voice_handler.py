# -*- coding: utf-8 -*-
"""
voice_handler.py – Guzo Guest Assist (v13.6)
--------------------------------------------
Handles voice messages:
- Transcribes speech → text
- Detects language
- Generates same-language hospitality reply
- Logs + triggers auto confirmation
"""

import os
import tempfile
from telegram import Update
from telegram.ext import ContextTypes
from openai import OpenAI
from langdetect import detect, DetectorFactory
from guzo_booking_bot.modules import google_sheets, auto_confirmation

DetectorFactory.seed = 0

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming Telegram voice messages."""
    user = update.effective_user
    guest_name = user.full_name or "Guest"
    voice = update.message.voice

    if not voice:
        await update.message.reply_text("No voice message detected.")
        return

    # Download temporary file
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tf:
        file = await voice.get_file()
        await file.download_to_drive(tf.name)
        temp_path = tf.name

    # Transcribe with OpenAI Whisper
    try:
        with open(temp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file
            )
        text = transcription.text.strip()
        lang = detect(text)
    except Exception as e:
        await update.message.reply_text(f"Could not transcribe audio: {e}")
        return

    # Detect intent + hotel name
    intent = auto_confirmation.detect_intent(text)
    words = text.split()
    hotel_name = " ".join([w for w in words if w.istitle()]) or "Your Hotel"

    # Build multilingual message
    response = auto_confirmation.build_multilingual_message(intent, hotel_name)
    if lang.startswith("am"):
        response = response.split("\n\n")[1]
    elif lang.startswith("en"):
        response = response.split("\n\n")[0]

    # Reply to guest
    await update.message.reply_text(response, parse_mode="Markdown")

    # Log + confirm
    google_sheets.log_new_request(guest_name, hotel_name, text, status=intent)
    await auto_confirmation.confirm_guest_request(
        guest_name=guest_name,
        hotel_name=hotel_name,
        message=text,
        recipient_email="manager@sofihotel.com",
    )

    os.remove(temp_path)
