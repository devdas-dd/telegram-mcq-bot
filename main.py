import os
import asyncio
import requests
import json
from telegram import Bot

# ===== Secrets from GitHub =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# ===============================

async def main():
    bot = Bot(token=BOT_TOKEN)

    prompt = """
Generate EXACTLY 10 MCQs strictly from ICT (Information & Communication Technology).

Difficulty distribution:
- 2 Easy
- 6 Moderate
- 2 Hard

Target exams:
EMRS, KVS, NVS, DSSSB

Language:
Hindi + English (exam oriented)

STRICT RULES:
- ONLY ICT topics
- Explanation must be ONE LINE only
- Return ONLY valid JSON ARRAY

[
  {
    "question": "",
    "options": ["", "", "", ""],
    "correct": 0,
    "difficulty": "Easy | Moderate | Hard",
    "explanation": "one line only"
  }
]
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    response = requests.post(
        url,
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        },
        timeout=60
    )

    data = response.json()
    print("GEMINI RESPONSE:", data)

    if "candidates" not in data:
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ MCQs will be posted in next cycle."
            )
        return

    try:
        mcqs = json.loads(
            data["candidates"][0]["content"]["parts"][0]["text"]
        )
    except Exception:
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ Will retry next cycle."
            )
        return

    async with bot:
        for i, mcq in enumerate(mcqs, start=1):
            message = f"""📘 *ICT MCQ {i}/10*

❓ *Question:*  
{mcq["question"]}

A️⃣ {mcq["options"][0]}  
B️⃣ {mcq["options"][1]}  
C️⃣ {mcq["options"][2]}  
D️⃣ {mcq["options"][3]}

🎯 *Level:* {mcq["difficulty"]}

✅ *Correct Answer:* {chr(65 + mcq["correct"])}

📝 *Explanation:*  
{mcq["explanation"]}
"""
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode="Markdown"
            )

if __name__ == "__main__":
    asyncio.run(main())
