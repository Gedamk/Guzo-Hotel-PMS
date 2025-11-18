#!/usr/bin/env bash
# =======================================================
# Guzo Guest Assist - Developer Debug Launcher
# -------------------------------------------------------
# Stops background bots, clears lock files, activates venv,
# and launches Telegram + Email router manually for testing.
# =======================================================

echo "Ì∫Ä Starting Guzo Developer Debug Mode..."

# 1Ô∏è‚É£ Go to project root
cd "$(dirname "$0")" || exit 1

# 2Ô∏è‚É£ Stop any background Python processes (auto-run bots)
echo "Ì∑π Stopping existing Python processes..."
taskkill //F //IM python.exe 2>/dev/null

# 3Ô∏è‚É£ Remove any leftover lock files
echo "Ì∑º Removing bot lock files..."
rm -f guzo_booking_bot/modules/bot.lock guzo_backend/modules/bot.lock

# 4Ô∏è‚É£ Activate virtual environment
if [ -f "venv/Scripts/activate" ]; then
    echo "Ì∞ç Activating virtual environment..."
    source venv/Scripts/activate
else
    echo "‚ùå Virtual environment not found! Please create it again with:"
    echo "   python -m venv venv && source venv/Scripts/activate"
    exit 1
fi

# 5Ô∏è‚É£ Run Telegram message router
echo "Ì¥ñ Launching Guzo Guest Assist Bot..."
python -m guzo_booking_bot.modules.message_router
