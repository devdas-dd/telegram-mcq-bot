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
            chat_id=CHANNEL_ID,   # ✅ NO int()
            text="✅ CHANNEL TEST: Bot can post to channel."
        )

if __name__ == "__main__":
    asyncio.run(main())
