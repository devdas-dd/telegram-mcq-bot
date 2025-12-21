import os
import asyncio
import requests
import json
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

async def main():
    bot = Bot(token=BOT_TOKEN)

    prompt = """
Generate EXACTLY 25 MCQs from ICT (Information & Communication Technology).

Rules:
- Hindi with English technical terms
- Exam oriented
- Short questions
- One line explanation
- Return ONLY valid JSON array

[
  {
    "question": "",
    "options": ["", "", "", ""],
    "correct": 0,
    "explanation": ""
  }
]
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/",
            "X-Title": "ICT MCQ Quiz Bot"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You create exam MCQs in JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        },
        timeout=60
    )

    data = response.json()

    if "choices" not in data:
        return

    mcqs = json.loads(data["choices"][0]["message"]["content"])

    async with bot:
        for i, mcq in enumerate(mcqs, start=1):
            await bot.send_poll(
                chat_id=CHANNEL_ID,
                question=f"Q{i}. {mcq['question']}",
                options=mcq["options"],
                type="quiz",
                correct_option_id=mcq["correct"],
                explanation=mcq["explanation"],
                is_anonymous=False
            )

if __name__ == "__main__":
    asyncio.run(main())
