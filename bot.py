import os
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from openai import AsyncOpenAI

# === Load environment variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM BOT_TOKEN not found in environment variables!")

# === Initialize bot and client ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# === Database setup ===
DB_FILE = "users.db"
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    plan TEXT DEFAULT 'Free',
    used_questions INTEGER DEFAULT 0,
    renewal_date TEXT
)
""")
conn.commit()

# === Load prompts ===
with open("prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

# === Constants ===
FREE_LIMIT = 10
PRO_MONTHLY_URL = "https://t.me/send?start=IVdixIeFSP3W"
PRO_YEARLY_URL = "https://t.me/send?start=IVRnAnXOWzRM"
ELITE_MONTHLY_URL = "https://t.me/send?start=IVfwy1t6hcu9"
ELITE_YEARLY_URL = "https://t.me/send?start=IVxMW0UNvl7d"

# === Utility functions ===
def get_user(user_id):
    cur.execute("SELECT plan, used_questions, renewal_date FROM users WHERE user_id=?", (user_id,))
    data = cur.fetchone()
    if data is None:
        cur.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return "Free", 0, None
    return data

def update_user(user_id, field, value):
    cur.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
    conn.commit()

# === Plan speed ===
def get_response_delay(plan):
    if plan == "Elite":
        return 0.5
    elif plan == "Pro":
        return 1
    else:
        return 2.5

# === Start Command ===
@router.message(Command("start"))
async def start_cmd(msg: Message):
    user_id = msg.from_user.id
    plan, used, _ = get_user(user_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Free Plan", callback_data="plan_Free")],
        [InlineKeyboardButton(text="💼 Pro Plan", callback_data="plan_Pro")],
        [InlineKeyboardButton(text="🔥 Elite Plan", callback_data="plan_Elite")]
    ])

    await msg.answer(
        "👋 Welcome to *AI Tutor Pro Bot* — your mentor for AI, Business, and Crypto.\n\n"
        "Choose your plan below to begin 👇",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# === Plan selection ===
@router.callback_query(F.data.startswith("plan_"))
async def plan_select(call: CallbackQuery):
    plan = call.data.split("_")[1]
    user_id = call.from_user.id

    update_user(user_id, "plan", plan)
    if plan == "Free":
        text = "✅ Free Plan selected. You can try up to 10 questions before upgrading."
    else:
        renewal = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        update_user(user_id, "renewal_date", renewal)
        text = f"🎉 {plan} Plan activated! Valid until {renewal}."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 AI Path", callback_data="path_AI")],
        [InlineKeyboardButton(text="💼 Business Path", callback_data="path_Business")],
        [InlineKeyboardButton(text="💰 Crypto Path", callback_data="path_Crypto")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back_start")]
    ])
    await call.message.edit_text(f"{text}\n\nChoose your learning path 👇", reply_markup=kb)

# === Back button ===
@router.callback_query(F.data == "back_start")
async def back_start(call: CallbackQuery):
    await start_cmd(call.message)

# === Category Path Selection ===
@router.callback_query(F.data.startswith("path_"))
async def category_select(call: CallbackQuery):
    path = call.data.split("_")[1]
    user_id = call.from_user.id
    plan, used, _ = get_user(user_id)

    questions = PROMPTS.get(path.lower(), [])
    buttons = []

    for i, q in enumerate(questions):
        if plan == "Free" and used >= FREE_LIMIT:
            buttons.append([InlineKeyboardButton(text=f"🔒 {q['title']}", callback_data="locked")])
        else:
            buttons.append([InlineKeyboardButton(text=q['title'], callback_data=f"q_{path}_{i}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_start")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.edit_text(f"📚 {path} Path — Choose a question:", reply_markup=kb)

# === Locked Feature Notice ===
@router.callback_query(F.data == "locked")
async def locked_feature(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Upgrade to Pro", url=PRO_MONTHLY_URL)],
        [InlineKeyboardButton(text="🔥 Upgrade to Elite", url=ELITE_MONTHLY_URL)]
    ])
    await call.message.answer("🔒 This feature is available for Pro and Elite users only.", reply_markup=kb)

# === Question handling ===
@router.callback_query(F.data.startswith("q_"))
async def handle_question(call: CallbackQuery):
    _, path, index = call.data.split("_")
    user_id = call.from_user.id
    plan, used, _ = get_user(user_id)
    index = int(index)
    q = PROMPTS[path.lower()][index]["question"]

    if plan == "Free":
        if used >= FREE_LIMIT:
            await locked_feature(call)
            return
        update_user(user_id, "used_questions", used + 1)

    await call.message.answer("🤖 Thinking...")
    delay = get_response_delay(plan)
    await asyncio.sleep(delay)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an intelligent tutor specializing in AI, Business, and Crypto."},
            {"role": "user", "content": q}
        ]
    )
    answer = response.choices[0].message.content
    await call.message.answer(answer)

# === Handle custom questions ===
@router.message()
async def custom_chat(msg: Message):
    user_id = msg.from_user.id
    plan, used, _ = get_user(user_id)

    await msg.answer("💭 Thinking...")
    delay = get_response_delay(plan)
    await asyncio.sleep(delay)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI Tutor answering personalized questions on AI, Business, and Crypto."},
                {"role": "user", "content": msg.text}
            ]
        )
        await msg.answer(response.choices[0].message.content)
    except Exception as e:
        await msg.answer("⚠️ Something went wrong. Please try again later.")
        print(e)

# === Upgrade Command ===
@router.message(Command("upgrade"))
async def upgrade_cmd(msg: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Upgrade to Pro (Monthly)", url=PRO_MONTHLY_URL)],
        [InlineKeyboardButton(text="🔥 Upgrade to Elite (Monthly)", url=ELITE_MONTHLY_URL)]
    ])
    await msg.answer("🚀 Unlock full access with Pro or Elite plans!", reply_markup=kb)

# === Status Command ===
@router.message(Command("status"))
async def status_cmd(msg: Message):
    user_id = msg.from_user.id
    plan, used, renewal = get_user(user_id)
    remaining = "Unlimited" if plan in ["Pro", "Elite"] else f"{FREE_LIMIT - used} of {FREE_LIMIT}"
    renewal = renewal if renewal else "Lifetime"

    await msg.answer(
        f"📊 *Your Status:*\n"
        f"Plan: {plan}\n"
        f"Remaining questions: {remaining}\n"
        f"Renewal date: {renewal}",
        parse_mode="Markdown"
    )

# === Help Command ===
@router.message(Command("help"))
async def help_cmd(msg: Message):
    await msg.answer(
        "🧠 *How to use AI Tutor Pro Bot:*\n"
        "/start — Choose your plan and begin\n"
        "/questions — Explore categories\n"
        "/upgrade — Unlock Pro or Elite features\n"
        "/status — Check your plan and usage\n\n"
        "💬 You can also type your own question anytime!",
        parse_mode="Markdown"
    )

# === Launch ===
async def main():
    dp.include_router(router)
    print("🤖 AI Tutor Pro Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

