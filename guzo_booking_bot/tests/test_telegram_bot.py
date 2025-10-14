# guzo_booking_bot/tests/test_telegram_bot.py
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from guzo_booking_bot.modules import telegram_bot

class TestTelegramBot(unittest.IsolatedAsyncioTestCase):

    @patch("guzo_booking_bot.modules.telegram_bot.handle_booking")  # <-- patch the import inside telegram_bot
    async def test_handle_message_triggers_log(self, mock_log_booking):
        message = MagicMock()
        message.from_user = "Demo Guest"
        message.reply_text = MagicMock()
        update = MagicMock()
        update.message = message

        await telegram_bot.handle_message(update)

        mock_log_booking.assert_called_once()
        message.reply_text.assert_called_once_with("Booking triggered ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ")
