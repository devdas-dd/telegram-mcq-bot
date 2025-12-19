import os
import requests
import json
import asyncio
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def generate_and_send_quiz():
    if not all([BOT_TOKEN, CHANNEL_ID, GEMINI_API_KEY]):
        print("Missing environment variables")
        return

    prompt = """
Generate 1 MCQ for EMRS exam.
Subject: Computer
Language: Hindi + English

Return ONLY raw JSON:
{
  "question": "",
  "options": ["", "", "", ""],
  "correct": 0,
  "explanation": ""
}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    response = requests.post(
        url,
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
    )

    data = response.json()
    print("Gemini response:", data)

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    mcq = json.loads(text)

    bot = Bot(token=BOT_TOKEN)
    async with bot:
        await bot.send_poll(
            chat_id=CHANNEL_ID,
            question=mcq["question"][:255],
            options=mcq["options"],
            type="quiz",
            correct_option_id=mcq["correct"],
            explanation=mcq["explanation"][:200],
            is_anonymous=False
        )

if __name__ == "__main__":
    asyncio.run(generate_and_send_quiz())
