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
Generate EXACTLY 15 MCQs strictly from ICT (Information & Communication Technology).

Difficulty distribution (STRICT):
- 3 Easy level questions
- 8 Moderate level questions
- 4 Hard (Advanced) level questions

Target exams:
EMRS, KVS, NVS, DSSSB

Allowed ICT topics ONLY:
- Computer Fundamentals
- Hardware & Software
- CPU (ALU, CU)
- Memory (Primary, Secondary)
- Input & Output Devices
- Operating System
- MS Word, Excel, PowerPoint
- Internet, Email, WWW
- Networking Basics
- Cyber Security
- Digital India / e-Governance
- ICT in Education

Language:
Hindi + English (exam-oriented keywords)

STRICT RULES:
- Do NOT include any non-ICT topic
- Do NOT add extra text outside JSON

Return ONLY valid JSON ARRAY:
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
        },
        timeout=60
    )

    data = response.json()
    print("FULL GEMINI RESPONSE:", data)

    # Safety check
    if "candidates" not in data:
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ Gemini API quota reached. MCQs will be posted in the next cycle."
            )
        return

    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

    try:
        mcqs = json.loads(raw_text)
    except Exception:
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ Gemini returned invalid format. Will retry in next cycle."
            )
        return

    async with bot:
        for i, mcq in enumerate(mcqs, start=1):
            message = f"""📘 *ICT MCQ {i}/15*

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
