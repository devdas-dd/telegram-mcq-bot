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
BOT_TOKEN          = os.getenv("BOT_TOKEN")
CHANNEL_ID         = os.getenv("CHANNEL_ID")
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")   # Free at aistudio.google.com

USED_FILE = "used_questions.json"

# ===== TOPIC ROTATION (7 days × 2 slots = covers entire week) =====
TOPICS = [
    "Operating System: Process Management, Memory Management, File System, Scheduling",
    "MS Office: MS Word, MS Excel Functions & Formulas, MS PowerPoint, MS Access",
    "Computer Networks: OSI Model, TCP/IP, IP Addressing, DNS, HTTP, FTP, Email Protocols",
    "Cyber Security: Virus, Malware, Ransomware, Firewall, Encryption, Digital Forensics",
    "IT Act 2000 & Amendments, Digital Signature, e-Governance, RTI, Cyber Laws",
    "Computer Organisation: CPU, ALU, Registers, Cache, RAM, ROM, BIOS, I/O Devices",
    "Mixed Revision: Database (SQL, Normalization), Data Structures, Python Basics, Number Systems"
]

# ===== EXAM TAGS (used in questions and hashtags) =====
EXAM_TAGS = "#UGC_NET #NVS #KVS #CTET #MPPSC #UPPSC #GovtExams #ICT #Computer_Quiz"

def get_today_topic():
    return TOPICS[datetime.utcnow().weekday()]

def load_used_hashes():
    """Load set of question hashes to avoid repeats across runs."""
    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_used_hashes(used):
    with open(USED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(used), f, ensure_ascii=False, indent=2)

def question_hash(q_text: str) -> str:
    """Stable hash of first 80 chars of a question for deduplication."""
    normalized = q_text.strip().lower()[:80]
    return hashlib.md5(normalized.encode()).hexdigest()

def is_similar(q_hash: str, used_hashes: set) -> bool:
    return q_hash in used_hashes

def validate_mcq(mcq: dict) -> bool:
    """Validate all required fields."""
    try:
        assert isinstance(mcq.get("question"), str) and len(mcq["question"].strip()) > 10
        assert isinstance(mcq.get("options"), list) and len(mcq["options"]) == 4
        assert all(isinstance(o, str) and len(o.strip()) > 0 for o in mcq["options"])
        assert isinstance(mcq.get("correct"), int) and 0 <= mcq["correct"] <= 3
        assert isinstance(mcq.get("explanation"), str) and len(mcq["explanation"].strip()) > 5
        return True
    except AssertionError:
        return False

def fetch_mcqs_gemini(today_topic: str, batch_num: int = 1) -> list | None:
    """
    Call Gemini 1.5 Flash (FREE tier) to generate 25 MCQs.
    Call twice for 50 total MCQs.
    """
    prompt = f"""
You MUST return ONLY a valid JSON array. No markdown, no extra text, no explanation outside JSON.

Generate EXACTLY 25 UNIQUE MCQs on Computer Science / ICT for Indian competitive exams.
Today's focus topic: {today_topic}
Batch number: {batch_num} (make sure questions in this batch are DIFFERENT from batch 1)

TARGET EXAMS: UGC NET JRF, NVS TGT/PGT, KVS TGT/PGT, CTET, MPPSC, UPPSC, DSSSB, REET, HTET

QUESTION FORMAT (MANDATORY - both languages):
English question line
Hindi question line (translation)

Example:
"Which layer of the OSI model handles routing of packets?
OSI मॉडल की कौन सी परत पैकेट रूटिंग संभालती है?"

STRICT RULES:
1. Each question must appear in BOTH English AND Hindi
2. Avoid very common/repeated textbook questions
3. Include concept-based, application-level questions
4. Options must be clearly distinct (no trick/confusing wording)
5. Explanation: 1-2 lines maximum + exam hashtags
6. Hashtags at end of explanation: #UGC_NET #NVS #KVS #MPPSC #UPPSC #ICT

STRICT JSON FORMAT (return ONLY this, nothing else):
[
  {{
    "question": "English question?\\nHindi question?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0,
    "explanation": "Short explanation here. #UGC_NET #KVS #ICT"
  }}
]
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API request failed (batch {batch_num}): {e}")
        return None

    data = response.json()

    try:
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected Gemini response structure: {e}\n{data}")
        return None

    # Strip markdown if present
    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    if not raw_text.startswith("["):
        logger.error(f"Gemini response not a JSON array: {raw_text[:200]}")
        return None

    try:
        mcqs = json.loads(raw_text)
        logger.info(f"Batch {batch_num}: Parsed {len(mcqs)} MCQs")
        return mcqs
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in batch {batch_num}: {e}\nRaw: {raw_text[:300]}")
        return None

async def main():
    request = HTTPXRequest(connect_timeout=15, read_timeout=30)
    bot = Bot(token=BOT_TOKEN, request=request)

    today_topic = get_today_topic()
    logger.info(f"Today's topic: {today_topic}")

    # ===== FETCH 50 MCQs in 2 batches of 25 =====
    all_mcqs = []
    for batch in range(1, 3):
        logger.info(f"Fetching batch {batch}...")
        mcqs = fetch_mcqs_gemini(today_topic, batch_num=batch)
        if mcqs:
            all_mcqs.extend(mcqs)
        await asyncio.sleep(3)  # Small pause between API calls

    if not all_mcqs:
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ MCQs could not be generated today (API error). Retrying tomorrow."
            )
        return

    # ===== FILTER: validate + deduplicate =====
    used_hashes = load_used_hashes()
    unique_mcqs = []
    new_hashes = []

    for mcq in all_mcqs:
        if not validate_mcq(mcq):
            logger.warning(f"Skipping invalid MCQ: {str(mcq)[:80]}")
            continue
        q_hash = question_hash(mcq["question"])
        if not is_similar(q_hash, used_hashes):
            unique_mcqs.append(mcq)
            new_hashes.append(q_hash)

    logger.info(f"Unique valid MCQs after dedup: {len(unique_mcqs)}")

    if len(unique_mcqs) < 10:
        async with bot:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text="⚠️ Not enough fresh questions generated today. Retrying tomorrow."
            )
        return

    # Limit to 50
    unique_mcqs = unique_mcqs[:50]

    # ===== SEND EVERYTHING in ONE async with block =====
    async with bot:

        # Header message
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
            # Telegram poll limits
            question_text = f"Q{i}. {mcq['question'].strip()}"
            if len(question_text) > 295:
                question_text = question_text[:292] + "..."

            options = [opt.strip()[:99] for opt in mcq["options"]]
            explanation = mcq["explanation"].strip()[:200]

            try:
                await bot.send_poll(
                    chat_id=CHANNEL_ID,
                    question=question_text,
                    options=options,
                    type="quiz",
                    correct_option_id=int(mcq["correct"]),
                    explanation=explanation,
                    is_anonymous=True
                )
                sent += 1
                logger.info(f"✅ Poll {i}/{len(unique_mcqs)} sent")

                # Avoid Telegram flood limits (30 messages/sec global limit)
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"❌ Poll {i} failed: {e}")
                await asyncio.sleep(5)
                continue

            # Section break every 10 questions
            if i % 10 == 0 and i < len(unique_mcqs):
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=f"✅ *{i} questions done!* Keep going... 💪\n{EXAM_TAGS}",
                    parse_mode="Markdown"
                )
                await asyncio.sleep(2)

        # Summary
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"🏁 *Quiz Complete!*\n"
                f"📊 *{sent} questions sent today*\n"
                f"📅 Next quiz tomorrow — same time!\n\n"
                f"🔔 Share with your friends preparing for:\n"
                f"UGC NET | KVS | NVS | CTET | MPPSC | UPPSC\n\n"
                f"{EXAM_TAGS}"
            ),
            parse_mode="Markdown"
        )

    # Save hashes after successful run
    used_hashes.update(new_hashes)
    save_used_hashes(used_hashes)
    logger.info(f"Saved {len(new_hashes)} new question hashes. Total stored: {len(used_hashes)}")

if __name__ == "__main__":
    asyncio.run(main())
