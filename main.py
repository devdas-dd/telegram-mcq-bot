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
Do NOT add explanations, headings, markdown, or code fences.
Do NOT write any text before or after JSON.

Generate EXACTLY 25 MCQs from ICT (Information & Communication Technology).

Rules:
- Hindi with English technical terms
- Exam oriented
- One line explanation
- Short questions
- Strict JSON only

FORMAT (STRICT):
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
