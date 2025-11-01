import os
import asyncio
import telegram
from dotenv import load_dotenv

load_dotenv(".env", override=True)

async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Missing TELEGRAM_BOT_TOKEN in .env")
        return
    bot = telegram.Bot(token)
    me = await bot.get_me()
    print(f"🤖 Bot connected successfully as: {me.first_name} (@{me.username})")

asyncio.run(main())
