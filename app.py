# ========================================
# 🤖 AI Tutor Pro Bot - Final Full Version
# ========================================

import os
import json
import logging
import random
import asyncio
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from openai import AsyncOpenAI
import threading

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Webhook route for DigitalOcean (with BOT_TOKEN)
APP_URL = "https://ai-tutor-bot-83opf.ondigitalocean.app"
WEBHOOK_URL = f"{APP_URL}/{BOT_TOKEN}"

# ---------------------------
# Validate critical env vars
# ---------------------------
if not BOT_TOKEN:
    raise ValueError("❌ Missing BOT_TOKEN in .env")
if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env")

# ---------------------------
# Initialize logging
# ---------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_tutor_pro_bot")

# ---------------------------
# Flask App
# ---------------------------
flask_app = Flask(__name__)

# ---------------------------
# Telegram & OpenAI Clients
# ---------------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ---------------------------
# SQLite Database
# ---------------------------
DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            plan TEXT DEFAULT 'free',
            last_reset TEXT,
            crypto_used INTEGER DEFAULT 0,
            ai_used INTEGER DEFAULT 0,
            business_used INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id, username):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, username, plan, last_reset) VALUES (?, ?, 'free', ?)",
            (user_id, username, datetime.utcnow().isoformat())
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = cursor.fetchone()
    conn.close()
    return user

def update_usage(user_id, category):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {category}_used = {category}_used + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def reset_daily_usage():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.utcnow()
    cursor.execute("SELECT user_id, last_reset FROM users")
    users = cursor.fetchall()
    for user_id, last_reset in users:
        if last_reset:
            last = datetime.fromisoformat(last_reset)
            if (now - last).days >= 1:
                cursor.execute("""
                    UPDATE users
                    SET crypto_used=0, ai_used=0, business_used=0, last_reset=?
                    WHERE user_id=?
                """, (now.isoformat(), user_id))
    conn.commit()
    conn.close()

# ---------------------------
# Plan Settings
# ---------------------------
PLAN_LIMITS = {"free": 5, "pro": 15, "elite": 25}
PAYMENT_LINKS = {
    "pro_monthly": "https://t.me/send?start=IVdixIeFSP3W",
    "pro_yearly": "https://t.me/send?start=IVRnAnXOWzRM",
    "elite_monthly": "https://t.me/send?start=IVfwy1t6hcu9",
    "elite_yearly": "https://t.me/send?start=IVxMW0UNvl7d"
}

# ---------------------------
# Motivation Quotes
# ---------------------------
MOTIVATIONAL_QUOTES = [
    "💡 Success begins with smart questions — ask boldly, act wisely.",
    "🚀 Discipline outperforms motivation every single day.",
    "🔥 Learn, build, repeat — your AI journey has just started.",
    "💼 Great business minds don’t wait, they create.",
    "🌎 Every answer you need is one smart question away.",
]

def get_random_quote():
    return random.choice(MOTIVATIONAL_QUOTES)

# ---------------------------
# Helper: Read prompts.json
# ---------------------------
def load_prompts():
    with open("prompts.json", "r", encoding="utf-8") as f:
        return json.load(f)

PROMPTS = load_prompts()

# ---------------------------
# Helper: Category Keyboards
# ---------------------------
def main_menu_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Crypto", callback_data="cat_crypto")],
        [InlineKeyboardButton(text="🤖 AI", callback_data="cat_ai")],
        [InlineKeyboardButton(text="💼 Business", callback_data="cat_business")],
        [InlineKeyboardButton(text="📈 Upgrade", callback_data="upgrade")],
        [InlineKeyboardButton(text="💬 Motivation", callback_data="motivation")]
    ])
    return kb

def plan_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Go Pro (Monthly)", url=PAYMENT_LINKS["pro_monthly"])],
        [InlineKeyboardButton(text="🏆 Go Pro (Yearly)", url=PAYMENT_LINKS["pro_yearly"])],
        [InlineKeyboardButton(text="👑 Go Elite (Monthly)", url=PAYMENT_LINKS["elite_monthly"])],
        [InlineKeyboardButton(text="💎 Go Elite (Yearly)", url=PAYMENT_LINKS["elite_yearly"])]
    ])
    return kb
# ========================================
# 📱 Telegram Bot Handlers & Logic
# ========================================

# ---------------------------
# /start Command
# ---------------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.username)
    welcome = (
        "🤖 *Welcome to the AI Path — let’s turn intelligence into freedom.*\n"
        "💡 *Ask Smart. Think Smart.*\n"
        f"Guided by AI Tutor Pro Bot (@ai_tutor_pro_bot)\n\n"
        "💬 You can chat freely with AI anytime, or explore smart questions below.\n"
    )
    await message.answer(welcome, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# ---------------------------
# /help Command
# ---------------------------
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "💬 *How to use AI Tutor Pro:*\n"
        "- Choose a category: Crypto, AI, or Business.\n"
        "- Select *Starter* or *Profit* level.\n"
        "- Free plan: 5 questions per category.\n"
        "- Pro plan: 15 questions per category.\n"
        "- Elite plan: 25 questions per category.\n"
        "You can also type your own questions anytime!\n\n"
        "⚡ Upgrade to unlock faster, deeper GPT-4o insights."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=plan_keyboard())

# ---------------------------
# /status Command
# ---------------------------
@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.username)
    user_id, username, plan, last_reset, crypto_used, ai_used, business_used = user
    limit = PLAN_LIMITS.get(plan, 5)
    text = (
        f"📊 *Your Plan:* {plan.title()}\n"
        f"💰 Crypto: {crypto_used}/{limit}\n"
        f"🤖 AI: {ai_used}/{limit}\n"
        f"💼 Business: {business_used}/{limit}\n\n"
        "Upgrade below for more smart questions ⬇️"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=plan_keyboard())

# ---------------------------
# Callback: Category Selection
# ---------------------------
@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username
    data = callback.data
    user = get_user(user_id, username)
    plan = user[2]
    limit = PLAN_LIMITS.get(plan, 5)

    # Category choice
    if data.startswith("cat_"):
        cat = data.split("_")[1]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Starter", callback_data=f"{cat}_starter")],
            [InlineKeyboardButton(text="🚀 Profit", callback_data=f"{cat}_profit")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")]
        ])
        await callback.message.edit_text(f"Choose your {cat.title()} level:", reply_markup=kb)

    # Level choice
    elif any(x in data for x in ["starter", "profit"]):
        category, level = data.split("_")
        _, _, plan, _, crypto_used, ai_used, business_used = user
        used = {"crypto": crypto_used, "ai": ai_used, "business": business_used}[category]

        if used >= limit and plan == "free":
            await callback.message.answer(
                f"⚠️ You reached your Free Plan limit of {limit} questions in {category.title()}.\n"
                "Upgrade to continue learning smarter!", reply_markup=plan_keyboard()
            )
            return

        # Load questions
        questions = PROMPTS[category][level][plan]
        kb = InlineKeyboardBuilder()
        for q in questions:
            kb.add(InlineKeyboardButton(text=q, callback_data=f"q_{category}_{level}_{questions.index(q)}"))
        kb.adjust(1)
        kb.add(InlineKeyboardButton(text="⬅️ Back", callback_data=f"cat_{category}"))
        await callback.message.edit_text(f"📚 {category.title()} ({level.title()}) Questions:", reply_markup=kb.as_markup())

    # Question selected
    elif data.startswith("q_"):
        _, category, level, index = data.split("_")
        index = int(index)
        plan = get_user(user_id, username)[2]
        question = PROMPTS[category][level][plan][index]
        update_usage(user_id, category)

        # Generate AI response
        await callback.message.answer(f"🤔 *{question}*", parse_mode="Markdown")
        await callback.message.answer("💭 Thinking…")
        response = await generate_ai_answer(question, plan)
        await callback.message.answer(response, parse_mode="Markdown")

    # Back navigation
    elif data == "back_main":
        await callback.message.edit_text("🏠 Main Menu:", reply_markup=main_menu_keyboard())

    elif data == "upgrade":
        await callback.message.answer("💳 Choose your upgrade plan:", reply_markup=plan_keyboard())

    elif data == "motivation":
        quote = get_random_quote()
        await callback.message.answer(quote)

# ---------------------------
# /motivation Command
# ---------------------------
@dp.message(Command("motivation"))
async def cmd_motivation(message: types.Message):
    quote = get_random_quote()
    await message.answer(f"✨ {quote}")

# ---------------------------
# Message Handler (Free Chat)
# ---------------------------
@dp.message()
async def free_chat(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.username)
    plan = user[2]
    prompt = message.text.strip()
    await message.answer("🤖 Thinking…")
    response = await generate_ai_answer(prompt, plan)
    await message.answer(response, parse_mode="Markdown")
# ========================================
# 🧠 AI Response Generator
# ========================================
async def generate_ai_answer(prompt, plan):
    try:
        model = "gpt-4o-mini" if plan == "free" else "gpt-4o"
        completion = await openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are AI Tutor Pro, a powerful mentor helping people master Crypto, AI, and Business. Respond like a strategist and teacher combined."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.8
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "⚠️ Sorry, AI is busy right now. Please try again in a moment."

# ========================================
# 🌅 Daily Motivation Scheduler
# ========================================
async def send_daily_motivation():
    await bot.send_message(6263328760, "🕒 Starting daily motivation job...")  # Optional log to your admin ID
    while True:
        now = datetime.now(ZoneInfo("America/New_York"))
        if now.hour == 15 and now.minute == 0:  # 3 PM Eastern
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users")
                users = cursor.fetchall()
                conn.close()

                quote = get_random_quote()
                for (uid,) in users:
                    try:
                        await bot.send_message(uid, f"🌟 Daily Motivation:\n\n{quote}")
                    except Exception as e:
                        logger.warning(f"Could not send to {uid}: {e}")

                logger.info("✅ Sent daily motivation to all users.")
            except Exception as e:
                logger.error(f"Motivation scheduler error: {e}")

            await asyncio.sleep(60)  # Wait one minute to avoid double sending
        await asyncio.sleep(30)  # Check every 30 seconds

# ========================================
# 🌐 Flask Webhook Endpoint
# ========================================
@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def telegram_webhook():
    try:
        update = types.Update.model_validate(await request.get_json())
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return "ok", 200

@flask_app.route("/", methods=["GET"])
def home():
    return "✅ AI Tutor Pro Bot is running."

# ========================================
# 🚀 Startup
# ========================================
async def on_startup():
    init_db()
    reset_daily_usage()
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook set to {WEBHOOK_URL}")

# ========================================
# 🏁 Main Run
# ========================================
if __name__ == "__main__":
    async def start_bot():
        await on_startup()
        asyncio.create_task(send_daily_motivation())
        logger.info("🤖 AI Tutor Pro Bot is fully online!")

    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8080)).start()
    asyncio.run(start_bot())
