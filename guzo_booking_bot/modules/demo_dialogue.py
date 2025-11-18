# -*- coding: utf-8 -*-
"""
demo_dialogue.py – Guzo Guest Assist Booking Demo (v3.0)
---------------------------------------------------------
🧾 Simulates a full hotel booking conversation directly
in Telegram for demonstration and training purposes.

Used by the /demo command inside message_router.py
"""

import asyncio
from telegram import Update


async def simulate_conversation(update: Update):
    """
    Sends a simulated hotel booking conversation flow
    as if between a guest and the Guzo bot.
    """

    messages = [
        "👋 Welcome to *Guzo Guest Assist Demo!*",
        "🏨 *Guest:* Hi, I’d like to book a room at Sofi Hotel.",
        "🤖 *Guzo Bot:* Wonderful! May I have your check-in date?",
        "🏨 *Guest:* November 10, 2025.",
        "🤖 *Guzo Bot:* Great. And how many nights will you be staying?",
        "🏨 *Guest:* 3 nights.",
        "🤖 *Guzo Bot:* Excellent. Which room type would you prefer?\n• Standard – 3,200 ETB\n• Deluxe – 4,500 ETB\n• Suite – 7,200 ETB",
        "🏨 *Guest:* Deluxe – 4,500 ETB",
        "🤖 *Guzo Bot:* Noted. Please choose your payment method: Cash / Card / Bank Transfer.",
        "🏨 *Guest:* Card.",
        "🤖 *Guzo Bot:* 💳 Processing your booking... please wait a moment.",
        "🤖 *Guzo Bot:* ✅ Booking confirmed!\n\n"
        "📅 Check-In: 2025-11-10\n"
        "📆 Nights: 3\n"
        "🏨 Hotel: Sofi Hotel\n"
        "🛏️ Room Type: Deluxe Room – 4,500 ETB/night\n"
        "💰 Total: 13,500 ETB\n\n"
        "📩 Confirmation email sent to your registered address.\n"
        "Thank you for choosing *Guzo Guest Assist!* 🌍"
    ]

    for msg in messages:
        await update.message.reply_text(msg, parse_mode="Markdown")
        await asyncio.sleep(1.2)  # smooth delay between messages

    await update.message.reply_text("✨ Demo completed successfully. 🌍")
