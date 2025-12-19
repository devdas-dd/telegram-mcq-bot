import requests
import json
from telegram import Bot

# ====== YOUR DETAILS (FILL CAREFULLY) ======
BOT_TOKEN = "8486433772:AAHJbN-weCbcH_vZT9aGgXsrC5AdrmvyEYM"
CHANNEL_ID = "@ictbydev"
GEMINI_API_KEY = "AIzaSyCELzVhga67Pt1KOwKd1L5qN2URPoISBow"

# ==========================================
bot = Bot(token=BOT_TOKEN)

# Prompt for Gemini
prompt = """
Generate 1 MCQ for EMRS exam.
Subject: Computer
Language: Hindi + English.
Difficulty: Moderate.
Give output ONLY in this JSON format:

{
  "question": "",
  "options": ["", "", "", ""],
  "correct": 0,
  "explanation": ""
}
"""

# Gemini API URL
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

response = requests.post(
    url,
    json={
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
)

# Convert response to text
result = response.json()

# Debug print (very important)
print("Gemini Response:", result)

if "candidates" not in result:
    raise Exception("Gemini did not return candidates. Check API key / quota.")

raw_text = result["candidates"][0]["content"]["parts"][0]["text"]

json_text = raw_text[raw_text.find("{"): raw_text.rfind("}") + 1]
mcq = json.loads(json_text)
)

# Send quiz to Telegram
bot.send_poll(
    chat_id=CHANNEL_ID,
    question=mcq["question"],
    options=mcq["options"],
    type="quiz",
    correct_option_id=mcq["correct"],
    explanation=mcq["explanation"],
    is_anonymous=False
)

print("Quiz sent successfully!")
