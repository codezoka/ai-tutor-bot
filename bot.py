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
from httpx import AsyncClient
from dotenv import load_dotenv
import pytz
import openai

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

print("✅ OpenAI SDK version:", openai.__version__)

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

http_client = AsyncClient(trust_env=False, timeout=60.0)
client = AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
tz = pytz.timezone("America/New_York")

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

with open("prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)


# === Helper Functions ===
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
        f"You are AI Tutor Pro Bot, an intelligent mentor for {category}. "
        "Provide clear, structured, and professional insights. "
        "Always end with: 💡 Ask Smart. Think Smart. — AI Tutor Pro Bot"
    )
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question}
            ],
            max_tokens=600
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ OpenAI error:", e)
        return "⚠️ AI is currently busy. Please try again shortly."


def build_menu(buttons):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=b[0], callback_data=b[1])] for b in buttons]
    )


# === Menus ===
def upgrade_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Upgrade to Pro", url=PRO_MONTHLY_URL)],
        [InlineKeyboardButton(text="🔥 Upgrade to Elite", url=ELITE_MONTHLY_URL)],
    ])


# === Commands ===
@dp.message(Command("start"))
async def start_cmd(msg: Message):
    text = (
        "👋 <b>Welcome to AI Tutor Pro Bot</b> — your intelligent mentor for mastering AI, Business, and Crypto.\n\n"
        "Choose your plan below to begin 👇\n\n"
        "💡 Ask Smart. Think Smart."
    )
    kb = build_menu([
        ("🆓 Free Plan", "plan_free"),
        ("⚡ Pro Plan", "plan_pro"),
        ("🔥 Elite Plan", "plan_elite")
    ])
    await msg.answer(text, reply_markup=kb)


@dp.message(Command("help"))
async def help_cmd(msg: Message):
    text = (
        "🧠 <b>How to use AI Tutor Pro Bot</b>\n\n"
        "• /start – Choose your plan and begin\n"
        "• /questions – Explore categories\n"
        "• /upgrade – Unlock higher levels\n"
        "• /status – Check your usage\n\n"
        "💬 You can also type your own question anytime — AI Tutor Pro Bot will respond instantly!\n\n"
        "💡 Ask Smart. Think Smart."
    )
    await msg.answer(text)


@dp.message(Command("upgrade"))
async def upgrade_cmd(msg: Message):
    text = (
        "🔥 <b>Upgrade your AI journey!</b>\n\n"
        "Unlock smarter, faster insights and exclusive business tools.\n\n"
        "💡 Ask Smart. Think Smart."
    )
    await msg.answer(text, reply_markup=upgrade_buttons())


@dp.message(Command("status"))
async def status_cmd(msg: Message):
    user = get_user(msg.from_user.id, msg.from_user.username)
    plan = user[2]
    text = (
        f"📊 <b>Your Status</b>\n\n"
        f"Plan: <b>{plan.capitalize()}</b>\n"
        f"AI: {user[3]}/{get_limits(plan)}\n"
        f"Business: {user[4]}/{get_limits(plan)}\n"
        f"Crypto: {user[5]}/{get_limits(plan)}\n\n"
        f"Upgrade anytime via /upgrade"
    )
    await msg.answer(text)


@dp.message(Command("questions"))
async def questions_cmd(msg: Message):
    kb = build_menu([
        ("🤖 AI Path", "free_ai"),
        ("💼 Business Path", "free_business"),
        ("💰 Crypto Path", "free_crypto"),
        ("⬅️ Back", "back_start")
    ])
    await msg.answer("📚 Choose your category:", reply_markup=kb)


# === Callbacks ===
@dp.callback_query(F.data == "back_start")
async def back_start(call: CallbackQuery):
    kb = build_menu([
        ("🆓 Free Plan", "plan_free"),
        ("⚡ Pro Plan", "plan_pro"),
        ("🔥 Elite Plan", "plan_elite")
    ])
    await call.message.edit_text("🏠 Back to main menu. Choose your plan 👇", reply_markup=kb)


@dp.callback_query(F.data.startswith("plan_"))
async def plan_select(call: CallbackQuery):
    plan = call.data.split("_")[1]
    kb = build_menu([
        ("🤖 AI Path", f"{plan}_ai"),
        ("💼 Business Path", f"{plan}_business"),
        ("💰 Crypto Path", f"{plan}_crypto"),
        ("⬅️ Back", "back_start")
    ])
    await call.message.edit_text(f"✅ {plan.capitalize()} Plan selected.\nChoose your path 👇", reply_markup=kb)


@dp.callback_query(F.data.contains("_ai") | F.data.contains("_business") | F.data.contains("_crypto"))
async def category_select(call: CallbackQuery):
    parts = call.data.split("_")
    plan, category = parts[0], parts[1]
    kb = build_menu([
        ("🧠 Starter", f"{plan}_{category}_starter"),
        ("💰 Profit", f"{plan}_{category}_profit"),
        ("⬅️ Back", f"plan_{plan}")
    ])
    intro = PROMPTS.get(category, {}).get("intro", f"Welcome to the {category.capitalize()} Path!")
    await call.message.edit_text(f"{intro}\n\nWhere would you like to begin?", reply_markup=kb)


@dp.callback_query(F.data.endswith("starter") | F.data.endswith("profit"))
async def section_select(call: CallbackQuery):
    parts = call.data.split("_")
    plan, category, section = parts[0], parts[1], parts[2]
    content = PROMPTS.get(category, {}).get(plan, {}).get(section, {})
    questions = content.get("questions", [])
    if not questions:
        await call.message.answer("⚠️ No questions available in this section yet.", reply_markup=upgrade_buttons())
        return
    kb = build_menu([(f"{i+1}. {q}", f"ask_{plan}_{category}_{section}_{i}") for i, q in enumerate(questions)] + [("⬅️ Back", f"{plan}_{category}")])
    await call.message.edit_text("Choose a question below 👇", reply_markup=kb)


@dp.callback_query(F.data.startswith("ask_"))
async def handle_question(call: CallbackQuery):
    _, plan, category, section, idx = call.data.split("_")
    idx = int(idx)
    content = PROMPTS.get(category, {}).get(plan, {}).get(section, {})
    questions = content.get("questions", [])
    if idx >= len(questions):
        await call.message.answer("⚠️ Question not found.")
        return
    question = questions[idx]
    await call.message.answer("💭 Thinking...")
    answer = await ai_reply(plan, category, question)
    await call.message.answer(f"Q: {question}\n\n{answer}", reply_markup=upgrade_buttons())


@dp.message()
async def handle_free_text(msg: Message):
    user = get_user(msg.from_user.id, msg.from_user.username)
    plan = user[2]
    await msg.answer("💬 Thinking...")
    answer = await ai_reply(plan, "general", msg.text)
    await msg.answer(answer, reply_markup=upgrade_buttons())


async def main():
    print("🤖 Bot connected successfully. Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

