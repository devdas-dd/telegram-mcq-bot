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
Generate EXACTLY 5 MCQs from ICT (Information & Communication Technology).

Difficulty:
- 1 Easy
- 3 Moderate
- 1 Hard

Rules:
- Hindi with English technical terms
- Short questions
- One-line explanation
- Return ONLY valid JSON array

[
  {
    "question": "",
    "options": ["", "", "", ""],
    "correct": 0,
    "difficulty": "Easy | Moderate | Hard",
    "explanation": "one short line"
  }
]
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/",
            "X-Title": "ICT MCQ Bot"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You generate exam MCQs."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        },
        timeout=60
    )

    data = response.json()
    print("OPENROUTER RESPONSE:", data)

    if "choices" not in data:
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ OpenRouter did not return MCQs today."
            )
        return

    try:
        mcqs = json.loads(data["choices"][0]["message"]["content"])
    except Exception:
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ Invalid MCQ format. Will retry tomorrow."
            )
        return

    async with bot:
        for i, mcq in enumerate(mcqs, start=1):
            message = f"""📘 *ICT MCQ {i}/5*

❓ {mcq["question"]}

A️⃣ {mcq["options"][0]}
B️⃣ {mcq["options"][1]}
C️⃣ {mcq["options"][2]}
D️⃣ {mcq["options"][3]}

✅ Answer: {chr(65 + mcq["correct"])}
📝 {mcq["explanation"]}
"""
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode="Markdown"
            )

if __name__ == "__main__":
    asyncio.run(main())
