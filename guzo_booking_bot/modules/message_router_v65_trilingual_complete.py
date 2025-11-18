# -*- coding: utf-8 -*-
"""
Adapter: exposes handle_message() for multi-bot runner,
reusing the existing router in message_router.py
"""
from telegram import Update
from telegram.ext import ContextTypes
from .message_router import router  # your existing router

PROPERTY_CODE_KEY = "property_code"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, property_code: str):
    # keep chats 1:1 only
    if update.effective_chat and update.effective_chat.type != "private":
        return
    # stamp property code so downstream writes know which hotel this bot is
    context.chat_data[PROPERTY_CODE_KEY] = property_code
    # continue into your existing conversation router
    await router(update, context)
