#!/usr/bin/env bash
# ============================================================
# Guzo Guest Assist - Safe Launcher (Git Bash version)
# Author: Gedan Kacha
# ============================================================

# Exit immediately on any error
set -e

echo "Ì∑π Stopping any running Python processes..."
pkill -f "python" || echo "No python processes found."

echo "Ì∫´ Disabling old cron or task schedulers (if any)..."
# For Windows task check - optional; no-op in Git Bash
schtasks /Query /FO TABLE | grep python || echo "No Windows task found using Python."

# ============================================================
# ‚úÖ Load and test the Telegram Bot Token
# ============================================================
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "‚ùå TELEGRAM_BOT_TOKEN is not set!"
  read -p "Please paste your Telegram bot token: " TOKEN_INPUT
  export TELEGRAM_BOT_TOKEN="$TOKEN_INPUT"
fi

echo "Ì¥ë Testing Telegram Bot Token..."
TEST_RESPONSE=$(curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe")

if echo "$TEST_RESPONSE" | grep -q '"ok":true'; then
  echo "‚úÖ Token verified successfully!"
  BOT_USERNAME=$(echo "$TEST_RESPONSE" | grep -o '"username":"[^"]*' | cut -d'"' -f4)
  echo "Ì¥ñ Connected as @$BOT_USERNAME"
else
  echo "‚ùå Token test failed. Please check or regenerate your bot token with @BotFather."
  echo "Response: $TEST_RESPONSE"
  exit 1
fi

# ============================================================
# Ì∫Ä Activate virtual environment & launch bot
# ============================================================
cd "$(dirname "$0")"
source ./venv/Scripts/activate

echo "Ì≥° Starting Guzo Guest Assist Bot..."
python -m guzo_booking_bot.modules.message_router

echo "‚úÖ Bot has started successfully. Press Ctrl + C to stop."
