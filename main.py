import os
import asyncio
import requests
import json
from datetime import datetime
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

USED_FILE = "used_questions.json"

# ===== TOPIC ROTATION (AUTOMATIC) =====
TOPICS = [
    "Operating System, RAM, ROM, Memory, File System",
    "MS Word, MS Excel (Spreadsheet), MS PowerPoint",
    "Computer Networks, Internet, Email, WWW",
    "Cyber Security, Virus, Malware, Firewall",
    "IT Act, Digital Signature, e-Governance",
    "Computer Hardware, Software, Input & Output Devices",
    "Mixed ICT Revision"
]

def get_today_topic():
    return TOPICS[datetime.utcnow().weekday()]

def load_used_questions():
    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_used_questions(used):
    with open(USED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(used), f, ensure_ascii=False, indent=2)

def is_similar(question, used):
    words = question.lower().split()[:6]
    for u in used:
        if sum(1 for w in words if w in u) >= 4:
            return True
    return False

async def main():
    bot = Bot(token=BOT_TOKEN)
    today_topic = get_today_topic()

    prompt = f"""
You MUST return ONLY a valid JSON array.
Do NOT add headings, markdown, or extra text.

Generate EXACTLY 25 MCQs from Computer / ICT syllabus.
Today's topic focus: {today_topic}

QUESTION FORMAT (MANDATORY):
English line
Hindi line

Example:
"ENIAC belongs to which generation of computers?
ENIAC कंप्यूटर की किस पीढ़ी से संबंधित है?"

RULES:
- Exam oriented (NVS, KVS, UGC NET, CTET, Govt Exams)
- Hindi + English in every question
- Avoid commonly repeated textbook questions
- Prefer less repeated, concept-based questions
- Explanation: ONE short line only
- Add 2–3 hashtags at end of explanation
  (#ICT #NVS #KVS #Computer_Quiz)

STRICT JSON FORMAT:
[
  {{
    "question": "",
    "options": ["", "", "", ""],
    "correct": 0,
    "explanation": ""
  }}
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
                {"role": "system", "content": "You generate exam MCQs in strict JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.25
        },
        timeout=60
    )

    data = response.json()
    if "choices" not in data:
        return

    raw_text = data["choices"][0]["message"]["content"].strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    if not raw_text.startswith("["):
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text="⚠️ MCQs not generated today. Will retry next cycle."
        )
        return

    try:
        mcqs = json.loads(raw_text)
    except json.JSONDecodeError:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text="⚠️ JSON parse error. Will retry next cycle."
        )
        return

    used_questions = load_used_questions()
    unique_mcqs = []
    new_questions = []

    for mcq in mcqs:
        q_text = mcq["question"].strip().lower()
        if q_text not in used_questions and not is_similar(q_text, used_questions):
            unique_mcqs.append(mcq)
            new_questions.append(q_text)

    if len(unique_mcqs) < 10:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text="⚠️ Not enough fresh questions today. Continuing tomorrow."
        )
        return

    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"📘 *Daily ICT Quiz*\n🧠 Topic: *{today_topic}*\n#ICT #GovtExams",
        parse_mode="Markdown"
    )

    async with bot:
        for i, mcq in enumerate(unique_mcqs[:25], start=1):
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
                await asyncio.sleep(3)
            except Exception as e:
                print(f"Poll {i} failed:", e)
                await asyncio.sleep(5)
                continue

    used_questions.update(new_questions)
    save_used_questions(used_questions)

if __name__ == "__main__":
    asyncio.run(main())
