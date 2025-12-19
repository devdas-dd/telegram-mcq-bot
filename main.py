import os
import asyncio
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

async def main():
    print("BOT_TOKEN exists:", bool(BOT_TOKEN))
    print("CHANNEL_ID exists:", bool(CHANNEL_ID))

    bot = Bot(token=BOT_TOKEN)

    async with bot:
        await bot.send_message(
            chat_id=int(CHANNEL_ID),
            text="✅ PRIVATE MESSAGE TEST: Bot is working."
        )

if __name__ == "__main__":
    asyncio.run(main())
