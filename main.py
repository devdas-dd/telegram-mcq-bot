import os
import asyncio
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

async def generate_and_send_quiz():
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Missing environment variables")
        return

    bot = Bot(token=BOT_TOKEN)

    async with bot:
        await bot.send_message(
            chat_id=int(CHANNEL_ID),
            text="✅ PRIVATE TEST: Bot is working correctly."
        )

if __name__ == "__main__":
    asyncio.run(generate_and_send_quiz())
