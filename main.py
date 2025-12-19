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

    # STRICT ICT PROMPT
    prompt = """
Generate EXACTLY 25 MCQs strictly from ICT (Information and Communication Technology).

Difficulty distribution:
- 8 Easy
- 15 Moderate
- 2 Hard

Target exams:
EMRS, KVS, NVS, DSSSB

Allowed topics ONLY:
- Computer Fundamentals
- Hardware & Software
- CPU, ALU, CU
- Memory
- Input / Output devices
- Operating System
- MS Word, Excel, PowerPoint
- Internet, Email, WWW
- Networking
- Cyber Security
- ICT in Education

Language:
Hindi + English (exam oriented)

Return ONLY valid JSON array:
[
  {
    "question": "",
    "options": ["", "", "", ""],
    "correct": 0,
    "difficulty": "Easy | Moderate | Hard",
    "explanation": ""
  }
]
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
    mcqs = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])

    async with bot:
        for i, mcq in enumerate(mcqs, start=1):
            message = f"""📘 *ICT MCQ {i}/25*

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
