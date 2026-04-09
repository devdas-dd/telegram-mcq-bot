import os
import asyncio
import requests
import json
import logging
import hashlib
from datetime import datetime
from telegram import Bot
from telegram.request import HTTPXRequest

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== CONFIG =====
BOT_TOKEN      = os.getenv("BOT_TOKEN")
CHANNEL_ID     = os.getenv("CHANNEL_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

USED_FILE = "used_questions.json"

# Try models in order — all FREE on Google AI Studio
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

# ===== TOPIC ROTATION =====
TOPICS = [
    "Operating System: Process Management, Memory Management, File System, Scheduling",
    "MS Office: MS Word, MS Excel Functions Formulas, MS PowerPoint, MS Access",
    "Computer Networks: OSI Model, TCP/IP, IP Addressing, DNS, HTTP, FTP, Email Protocols",
    "Cyber Security: Virus, Malware, Ransomware, Firewall, Encryption, Digital Forensics",
    "IT Act 2000 and Amendments, Digital Signature, e-Governance, RTI, Cyber Laws",
    "Computer Organisation: CPU, ALU, Registers, Cache, RAM, ROM, BIOS, I/O Devices",
    "Mixed Revision: Database SQL Normalization, Data Structures, Python Basics, Number Systems"
]

EXAM_TAGS = "#UGC_NET #NVS #KVS #CTET #MPPSC #UPPSC #GovtExams #ICT #Computer_Quiz"

def get_today_topic():
    return TOPICS[datetime.utcnow().weekday()]

def load_used_hashes():
    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_used_hashes(used):
    with open(USED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(used), f, ensure_ascii=False, indent=2)

def question_hash(q_text: str) -> str:
    normalized = q_text.strip().lower()[:80]
    return hashlib.md5(normalized.encode()).hexdigest()

def validate_mcq(mcq: dict) -> bool:
    try:
        assert isinstance(mcq.get("question"), str) and len(mcq["question"].strip()) > 10
        assert isinstance(mcq.get("options"), list) and len(mcq["options"]) == 4
        assert all(isinstance(o, str) and len(o.strip()) > 0 for o in mcq["options"])
        assert isinstance(mcq.get("correct"), int) and 0 <= mcq["correct"] <= 3
        assert isinstance(mcq.get("explanation"), str) and len(mcq["explanation"].strip()) > 5
        return True
    except AssertionError:
        return False

def call_gemini(prompt: str, model: str) -> str | None:
    """Call one Gemini model. Returns raw text or None on any error."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192
        }
    }
    try:
        resp = requests.post(url, json=payload, timeout=90)
        if not resp.ok:
            logger.warning(f"[{model}] HTTP {resp.status_code}: {resp.text[:400]}")
            return None
        data = resp.json()
        if "candidates" not in data:
            logger.warning(f"[{model}] No candidates: {json.dumps(data)[:400]}")
            return None
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        logger.info(f"[{model}] Got {len(text)} chars")
        return text
    except Exception as e:
        logger.warning(f"[{model}] Exception: {e}")
        return None

def parse_mcq_json(raw: str, model: str) -> list | None:
    if "```" in raw:
        raw = raw.replace("```json", "").replace("```", "").strip()
    start = raw.find("[")
    end   = raw.rfind("]")
    if start == -1 or end == -1:
        logger.warning(f"[{model}] No JSON array. Sample: {raw[:200]}")
        return None
    try:
        mcqs = json.loads(raw[start:end+1])
        logger.info(f"[{model}] Parsed {len(mcqs)} MCQs")
        return mcqs
    except json.JSONDecodeError as e:
        logger.warning(f"[{model}] JSON error: {e} | sample: {raw[start:start+200]}")
        return None

def fetch_mcqs(topic: str, batch_num: int = 1) -> list | None:
    """Try all Gemini models until one works."""
    prompt = f"""You MUST return ONLY a valid JSON array. No markdown, no extra text.

Generate EXACTLY 25 UNIQUE MCQs on Computer Science / ICT for Indian competitive exams.
Topic: {topic}
Batch: {batch_num} — questions must differ from other batches.

TARGET EXAMS: UGC NET JRF, NVS TGT/PGT, KVS TGT/PGT, CTET, MPPSC, UPPSC, DSSSB, REET, HTET

Write BOTH English and Hindi for every question on separate lines.
Example question field: "What is RAM?\\nRAM क्या है?"

RULES:
- Both English + Hindi in every question
- Concept-based questions, less common ones
- 4 clearly distinct options
- Explanation: 1-2 lines + hashtags #UGC_NET #KVS #NVS #MPPSC #UPPSC #ICT

RETURN ONLY THIS JSON:
[
  {{
    "question": "English?\\nHindi?",
    "options": ["A", "B", "C", "D"],
    "correct": 0,
    "explanation": "Brief explanation. #UGC_NET #KVS #ICT"
  }}
]"""

    for model in GEMINI_MODELS:
        logger.info(f"Trying [{model}] batch {batch_num}...")
        raw = call_gemini(prompt, model)
        if not raw:
            continue
        mcqs = parse_mcq_json(raw, model)
        if mcqs:
            return mcqs
        logger.warning(f"[{model}] no valid MCQs, trying next model...")

    logger.error("All Gemini models failed.")
    return None

async def main():
    logger.info(f"BOT_TOKEN set:      {bool(BOT_TOKEN)}")
    logger.info(f"CHANNEL_ID set:     {bool(CHANNEL_ID)}")
    logger.info(f"GEMINI_API_KEY set: {bool(GEMINI_API_KEY)}")

    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY missing — check GitHub Secrets!")
        return

    request = HTTPXRequest(connect_timeout=15, read_timeout=30)
    bot = Bot(token=BOT_TOKEN, request=request)

    today_topic = get_today_topic()
    logger.info(f"Today topic: {today_topic}")

    all_mcqs = []
    for batch in range(1, 3):
        logger.info(f"--- Batch {batch}/2 ---")
        mcqs = fetch_mcqs(today_topic, batch_num=batch)
        if mcqs:
            all_mcqs.extend(mcqs)
        await asyncio.sleep(4)

    if not all_mcqs:
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ MCQs could not be generated today (API error). Retrying tomorrow."
            )
        return

    used_hashes = load_used_hashes()
    unique_mcqs = []
    new_hashes  = []

    for mcq in all_mcqs:
        if not validate_mcq(mcq):
            logger.warning(f"Invalid MCQ: {str(mcq)[:80]}")
            continue
        h = question_hash(mcq["question"])
        if h not in used_hashes:
            unique_mcqs.append(mcq)
            new_hashes.append(h)

    logger.info(f"Unique valid MCQs: {len(unique_mcqs)}")

    if len(unique_mcqs) < 10:
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ Not enough fresh questions today. Retrying tomorrow."
            )
        return

    unique_mcqs = unique_mcqs[:50]

    async with bot:
        day_name = datetime.utcnow().strftime("%A")
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"📘 *Daily ICT Quiz — {day_name}*\n"
                f"🧠 *Topic:* {today_topic}\n"
                f"📝 *Total Questions:* {len(unique_mcqs)}\n\n"
                f"🎯 *Target Exams:*\n"
                f"UGC NET JRF | NVS | KVS | CTET\n"
                f"MPPSC | UPPSC | DSSSB | REET\n\n"
                f"{EXAM_TAGS}"
            ),
            parse_mode="Markdown"
        )
        await asyncio.sleep(2)

        sent = 0
        for i, mcq in enumerate(unique_mcqs, start=1):
            q_text = f"Q{i}. {mcq['question'].strip()}"
            if len(q_text) > 295:
                q_text = q_text[:292] + "..."
            options     = [o.strip()[:99] for o in mcq["options"]]
            explanation = mcq["explanation"].strip()[:200]

            try:
                await bot.send_poll(
                    chat_id=CHANNEL_ID,
                    question=q_text,
                    options=options,
                    type="quiz",
                    correct_option_id=int(mcq["correct"]),
                    explanation=explanation,
                    is_anonymous=True
                )
                sent += 1
                logger.info(f"Poll {i}/{len(unique_mcqs)} sent")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Poll {i} failed: {e}")
                await asyncio.sleep(5)
                continue

            if i % 10 == 0 and i < len(unique_mcqs):
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=f"✅ *{i} done!* Keep going 💪\n{EXAM_TAGS}",
                    parse_mode="Markdown"
                )
                await asyncio.sleep(2)

        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"🏁 *Quiz Complete!*\n"
                f"📊 *{sent} questions sent today*\n"
                f"📅 Next quiz tomorrow!\n\n"
                f"🔔 Share with friends preparing for:\n"
                f"UGC NET | KVS | NVS | CTET | MPPSC | UPPSC\n\n"
                f"{EXAM_TAGS}"
            ),
            parse_mode="Markdown"
        )

    used_hashes.update(new_hashes)
    save_used_hashes(used_hashes)
    logger.info(f"Saved {len(new_hashes)} new hashes. Total: {len(used_hashes)}")

if __name__ == "__main__":
    asyncio.run(main())
