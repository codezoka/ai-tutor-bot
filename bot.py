import asyncio
import json
import os
import random
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from openai import AsyncOpenAI
from dotenv import load_dotenv
import pytz

# === Load environment variables ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

# === Initialize services ===
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)
tz = pytz.timezone("America/New_York")

# === Database ===
db = sqlite3.connect("users.db")
cur = db.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    plan TEXT DEFAULT 'free',
    used_ai INTEGER DEFAULT 0,
    used_business INTEGER DEFAULT 0,
    used_crypto INTEGER DEFAULT 0,
    last_reset TEXT
)
""")
db.commit()

# === Load prompts.json ===
with open("ai_tutor_pro/prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

# === Helper functions ===
def get_user(user_id, username):
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    data = cur.fetchone()
    if not data:
        cur.execute("INSERT INTO users (user_id, username, last_reset) VALUES (?, ?, ?)",
                    (user_id, username, datetime.now(tz).strftime("%Y-%m-%d")))
        db.commit()
    return cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

def update_usage(user_id, category):
    field = f"used_{category}"
    cur.execute(f"UPDATE users SET {field} = {field} + 1 WHERE user_id=?", (user_id,))
    db.commit()

def reset_if_new_day():
    today = datetime.now(tz).strftime("%Y-%m-%d")
    cur.execute("SELECT user_id, last_reset FROM users")
    for u_id, last_reset in cur.fetchall():
        if last_reset != today:
            cur.execute("""
            UPDATE users SET used_ai=0, used_business=0, used_crypto=0, last_reset=?
            WHERE user_id=?""", (today, u_id))
    db.commit()

def get_limits(plan):
    return {"free": 5, "pro": 10, "elite": 20}.get(plan, 5)

def get_model(plan):
    if plan == "elite":
        return "gpt-4o"
    elif plan == "pro":
        return "gpt-4-turbo"
    return "gpt-3.5-turbo"

async def ai_reply(plan, category, question):
    model = get_model(plan)
    system = (
        f"You are AI Tutor Pro Bot, an expert mentor for {category}. "
        "Give structured, actionable answers with clear steps, examples, and motivation. "
        "Always end with: 💡 Ask Smart. Think Smart. — AI Tutor Pro Bot"
    )
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": question}],
        max_tokens=500
    )
    return resp.choices[0].message.content.strip()

def build_menu(buttons):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=b[0], callback_data=b[1])] for b in buttons
    ])
    return kb

# === Commands ===
@dp.message(Command("start"))
async def start_cmd(msg: Message):
    reset_if_new_day()
    get_user(msg.from_user.id, msg.from_user.username)
    text = (
        "👋 Welcome to <b>AI Tutor Pro Bot</b> — your intelligent mentor for mastering AI, Business, and Crypto.\n\n"
        "Here’s where your journey begins: choose your path, unlock smarter systems, and build your future.\n\n"
        "💡 Ask Smart. Think Smart."
    )
    await msg.answer(text)

@dp.message(Command("help"))
async def help_cmd(msg: Message):
    text = (
        "🧠 Need a little guidance?\n\n"
        "Here’s how to get the most from AI Tutor Pro Bot:\n"
        "• /start — Begin your learning path\n"
        "• /questions — Explore AI, Business, and Crypto\n"
        "• /upgrade — Unlock more features\n"
        "• /status — Check your plan & usage\n\n"
        "💬 Pro Tip:\n“Ask Smart. Think Smart.”\n— AI Tutor Pro Bot"
    )
    await msg.answer(text)

@dp.message(Command("upgrade"))
async def upgrade_cmd(msg: Message):
    text = (
        "🔥 Ready to unlock your next level?\n\n"
        "Choose your plan below and let AI Tutor Pro Bot guide you to smarter systems, deeper learning, and greater freedom.\n\n"
        "💡 Ask Smart. Think Smart."
    )
    buttons = [
        ("💼 Pro Plan — Monthly", f"url:{PRO_MONTHLY_URL}"),
        ("💼 Pro Plan — Yearly (20% Off)", f"url:{PRO_YEARLY_URL}"),
        ("👑 Elite Plan — Monthly", f"url:{ELITE_MONTHLY_URL}"),
        ("👑 Elite Plan — Yearly (20% Off)", f"url:{ELITE_YEARLY_URL}")
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=b[0], url=b[1].replace("url:", ""))] for b in buttons
    ])
    await msg.answer(text, reply_markup=kb)

@dp.message(Command("status"))
async def status_cmd(msg: Message):
    user = get_user(msg.from_user.id, msg.from_user.username)
    plan = user[2]
    text = (
        f"📊 <b>Your Status</b>\n\n"
        f"Plan: <b>{plan.capitalize()}</b>\n"
        f"AI Questions Used: {user[3]}/{get_limits(plan)}\n"
        f"Business Questions Used: {user[4]}/{get_limits(plan)}\n"
        f"Crypto Questions Used: {user[5]}/{get_limits(plan)}\n\n"
        f"Need more? <b><a href='https://t.me/{msg.from_user.username}?start=upgrade'>Upgrade here</a></b>"
    )
    await msg.answer(text, disable_web_page_preview=True)

@dp.message(Command("questions"))
async def questions_cmd(msg: Message):
    kb = build_menu([
        ("🆓 Free Plan", "plan_free"),
        ("💼 Pro Plan", "plan_pro"),
        ("👑 Elite Plan", "plan_elite")
    ])
    await msg.answer("📚 Choose your learning level 👇", reply_markup=kb)

# === Callbacks ===
@dp.callback_query(F.data.startswith("plan_"))
async def plan_select(call: CallbackQuery):
    plan = call.data.split("_")[1]
    kb = build_menu([
        ("🤖 AI Path", f"{plan}_ai"),
        ("💼 Business Path", f"{plan}_business"),
        ("💰 Crypto Path", f"{plan}_crypto"),
        ("⬅️ Back", "questions")
    ])
    await call.message.edit_text(
        f"✅ {plan.capitalize()} Plan Selected.\nChoose your path 👇",
        reply_markup=kb
    )

@dp.callback_query(F.data.contains("_ai") | F.data.contains("_business") | F.data.contains("_crypto"))
async def category_select(call: CallbackQuery):
    plan, category = call.data.split("_")
    kb = build_menu([
        ("🧠 Starter", f"{plan}_{category}_starter"),
        ("💰 Profit", f"{plan}_{category}_profit"),
        ("⬅️ Back", f"plan_{plan}")
    ])
    intro = PROMPTS[category]["intro"]
    await call.message.edit_text(intro + "\n\nWhere would you like to begin?", reply_markup=kb)

@dp.callback_query(F.data.endswith("starter") | F.data.endswith("profit"))
async def section_select(call: CallbackQuery):
    parts = call.data.split("_")
    plan, category, section = parts[0], parts[1], parts[2]
    content = PROMPTS[category][plan][section]
    notice = ""
    questions = content
    if isinstance(content, dict):
        notice = content.get("notice", "")
        questions = content.get("questions", [])

    buttons = []
    for i, q in enumerate(questions, 1):
        buttons.append((f"{i}. {q}", f"ask_{plan}_{category}_{section}_{i}"))
    kb = build_menu(buttons + [("⬅️ Back", f"{plan}_{category}")])

    text = f"{notice}\nChoose a question below 👇" if notice else "Choose a question below 👇"
    await call.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("ask_"))
async def handle_question(call: CallbackQuery):
    _, plan, category, section, idx = call.data.split("_")
    idx = int(idx)
    content = PROMPTS[category][plan][section]
    questions = content.get("questions", content)
    question = questions[idx - 1]

    user = get_user(call.from_user.id, call.from_user.username)
    used = user[3 + ["ai", "business", "crypto"].index(category)]
    limit = get_limits(user[2])

    if used >= limit and user[2] == "free":
        await call.message.answer(
            "⚠️ You’ve reached your Free plan limit. Upgrade to unlock more questions.\n\n"
            "🔥 Ready to unlock your next level?\n💡 Ask Smart. Think Smart."
        )
        return

    update_usage(call.from_user.id, category)
    await call.message.answer("💬 Thinking...")
    answer = await ai_reply(plan, category, question)
    await call.message.answer(f"Q: {question}\n\n{answer}")

# === Daily Motivation ===
MOTIVATIONAL_QUOTES = [
    "Success starts with a single smart question.",
    "Small wins daily create unstoppable momentum.",
    "Systems build freedom. Focus builds fortune.",
    "Think smarter. Act faster. Grow stronger.",
    "Every expert was once curious. Stay curious."
]

async def send_daily_motivation():
    while True:
        now = datetime.now(tz)
        target = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        cur.execute("SELECT user_id FROM users")
        for (uid,) in cur.fetchall():
            quote = random.choice(MOTIVATIONAL_QUOTES)
            try:
                await bot.send_message(uid, f"💭 {quote}\n— AI Tutor Pro Bot")
            except Exception:
                continue

# === Run ===
async def main():
    asyncio.create_task(send_daily_motivation())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

