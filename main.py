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
You MUST return ONLY a valid JSON array.
Do NOT add headings, markdown, or any text outside JSON.

Generate EXACTLY 25 MCQs strictly from Computer / ICT syllabus for Indian competitive exams.

SYLLABUS FOCUS (STRICT):
- Fundamentals of Computer System
- Computer characteristics
- Computer organization (CPU, RAM, ROM, File System)
- Input & Output Devices
- Computer Hardware & Software and their relationship
- Operating System (Basics)
- MS Office (Word, Excel/Spreadsheet, PowerPoint)
- Keyboard shortcuts and their uses
- Important computer terms & abbreviations
- Computer Networks
- Internet & Email
- Cyber Security
- Information Technology & Society
- IT Act, Digital Signature
- e-Governance & use of IT in Government
- Mobile / Smartphone technology
- Information Kiosk

QUESTION FORMAT (MANDATORY):
- First line: English
- Second line: Hindi
Example:
"ENIAC belongs to which generation of computers?
ENIAC कंप्यूटर की किस पीढ़ी से संबंधित है?"

RULES:
- Exam oriented (NVS, KVS, UGC NET, CTET, Govt Exams)
- Language: English + Hindi in every question
- Options can be English
- Explanation: ONE short line only
- Include 2–3 exam hashtags at the END of explanation
  (example: #NVS #KVS #Computer_Quiz)

HASHTAGS TO ROTATE:
#ICT #NVS #KVS #UGCNET #CTET #GovtExams #Computer_Quiz

STRICT JSON FORMAT:
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

    raw_text = data["choices"][0]["message"]["content"].strip()

    # Remove markdown code blocks if present
    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    # Safety: ensure JSON array
    if not raw_text.startswith("["):
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ AI response was not valid JSON today. Will retry next cycle."
            )
        return

    try:
        mcqs = json.loads(raw_text)
    except json.JSONDecodeError:
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ JSON parse failed. Will retry next cycle."
            )
        return

    async with bot:
        for i, mcq in enumerate(mcqs, start=1):
            try:
                await bot.send_poll(
                    chat_id=CHANNEL_ID,
                    question=f"Q{i}. {mcq['question']}",
                    options=mcq["options"],
                    type="quiz",
                    correct_option_id=int(mcq["correct"]),
                    explanation=mcq["explanation"],
                    is_anonymous=True
                )

                # Telegram rate-limit protection
                await asyncio.sleep(3)

            except Exception as e:
                print(f"Poll {i} failed:", e)
                await asyncio.sleep(5)
                continue

if __name__ == "__main__":
    asyncio.run(main())
