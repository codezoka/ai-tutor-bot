# ============================================
#  AI TUTOR PRO BOT – FULL VERSION (PART 1/3)
# ============================================

import os
import asyncio
import logging
import threading
import random
import sqlite3
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from flask import Flask
from dotenv import load_dotenv
from openai import AsyncOpenAI

# -----------------------
# 🌍 Environment & Logging
# -----------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MOTIVATION_TIME = os.getenv("MOTIVATION_TIME", "15:00")

# CryptoBot links
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Tutor_Pro")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("❌ BOT_TOKEN or OPENAI_API_KEY missing in environment variables!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# -----------------------
# 💾 Database Setup
# -----------------------
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id TEXT PRIMARY KEY,
            username TEXT,
            tier TEXT DEFAULT 'free',
            questions_used INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            chat_id TEXT,
            role TEXT,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(chat_id, username):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (chat_id, username) VALUES (?, ?)", (chat_id, username))
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT tier, questions_used FROM users WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return ("free", 0)
    return row

def update_tier(chat_id, tier):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET tier=? WHERE chat_id=?", (tier, chat_id))
    conn.commit()
    conn.close()

def increment_questions(chat_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET questions_used = questions_used + 1 WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def reset_questions(chat_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET questions_used = 0 WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def save_message(chat_id, role, content):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("INSERT INTO history (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, role, content))
    conn.commit()
    conn.close()

def get_history(chat_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT role, content FROM history WHERE chat_id=?", (chat_id,))
    history = [{"role": r, "content": c} for r, c in c.fetchall()]
    conn.close()
    return history[-10:]
# ============================================
#  AI TUTOR PRO BOT – FULL VERSION (PART 2/3)
# ============================================

# -----------------------
# 💬 Keyboards
# -----------------------
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 Chat with AI", callback_data="chat_ai")
    kb.button(text="🚀 Upgrade", callback_data="upgrade_menu")
    kb.button(text="💼 Business", callback_data="business_menu")
    kb.button(text="🪙 Crypto", callback_data="crypto_menu")
    kb.button(text="📈 Profit", callback_data="profit_menu")
    return kb.adjust(2).as_markup()

def back_button():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data="back_main")
    return kb.as_markup()

# -----------------------
# 🏁 Commands
# -----------------------
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    add_user(message.chat.id, message.from_user.username)
    tier, used = get_user(message.chat.id)
    await message.answer(
        "🤖 <b>Welcome to the AI Path — let’s turn intelligence into freedom.</b>\n"
        "💡 Ask Smart. Think Smart.\n"
        "(Guided by AI Tutor Pro Bot)\n\n"
        f"🌟 Current plan: <b>{tier.title()}</b>\n"
        f"💬 Questions used: {used}/5 (Free limit)\n\n"
        "Choose below to start:",
        reply_markup=main_menu()
    )

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "🧭 <b>AI Tutor Pro Help</b>\n"
        "/start – Restart menu\n"
        "/status – Check plan & usage\n"
        "/upgrade – Upgrade to Pro or Elite\n"
        "/questions – Explore categories\n"
        "💬 You can also type any question directly!"
    )

@dp.message(Command("status"))
async def status_cmd(message: types.Message):
    tier, used = get_user(message.chat.id)
    await message.answer(
        f"⭐ Current Plan: <b>{tier.title()}</b>\n"
        f"💬 Questions used: {used}/5 (Free limit)"
    )

# -----------------------
# 🔘 Menu Navigation
# -----------------------
@dp.callback_query(lambda c: c.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    await callback.message.edit_text("🏠 Main Menu:", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "upgrade_menu")
async def upgrade_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🌟 Pro Monthly", url=PRO_MONTHLY_URL)
    kb.button(text="🌟 Pro Yearly", url=PRO_YEARLY_URL)
    kb.button(text="💎 Elite Monthly", url=ELITE_MONTHLY_URL)
    kb.button(text="💎 Elite Yearly", url=ELITE_YEARLY_URL)
    kb.button(text="⬅️ Back", callback_data="back_main")
    await callback.message.edit_text(
        "💳 <b>Upgrade Plans</b>\n\n"
        "🌟 Pro Plan – GPT-4 Turbo (10× faster)\n"
        "💎 Elite Plan – GPT-4o Mini (blazing speed + extra features)\n\n"
        "Choose a plan below to pay via CryptoBot:",
        reply_markup=kb.as_markup()
    )

@dp.callback_query(lambda c: c.data == "business_menu")
async def business_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💼 <b>Business Insights</b>\n"
        "Ask how AI can automate and grow your business.\n\n"
        "Example: ‘How to automate customer service with AI?’",
        reply_markup=back_button()
    )

@dp.callback_query(lambda c: c.data == "crypto_menu")
async def crypto_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🪙 <b>Crypto AI Insights</b>\n"
        "Ask about market trends, trading bots, or AI forecasting.\n\n"
        "Example: ‘How AI can analyze crypto market sentiment?’",
        reply_markup=back_button()
    )

@dp.callback_query(lambda c: c.data == "profit_menu")
async def profit_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📈 <b>Profit Tools</b>\n"
        "Ask how to build income streams with AI tools and automation.\n\n"
        "Example: ‘What digital product can AI help me create?’",
        reply_markup=back_button()
    )

@dp.callback_query(lambda c: c.data == "chat_ai")
async def chat_ai(callback: types.CallbackQuery):
    tier, _ = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"💬 <b>AI Chat Mode</b>\n"
        f"Type your question below. (Current plan: {tier.title()})\n\n"
        f"Free users can ask up to 5 questions in total.",
        reply_markup=back_button()
    )

# -----------------------
# 🧠 AI Chat Logic
# -----------------------
@dp.message()
async def ai_chat(message: types.Message):
    tier, used = get_user(message.chat.id)
    text = message.text.strip()

    if tier == "free" and used >= 5:
        await message.answer("⚠️ You’ve reached your free limit of 5 questions.\nUpgrade for unlimited access.", reply_markup=main_menu())
        return

    model = (
        "gpt-3.5-turbo" if tier == "free"
        else "gpt-4-turbo" if tier == "pro"
        else "gpt-4o-mini"
    )

    save_message(message.chat.id, "user", text)
    history = get_history(message.chat.id)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=history + [{"role": "user", "content": text}],
            max_tokens=400
        )
        answer = response.choices[0].message.content
        save_message(message.chat.id, "assistant", answer)

        if tier == "free":
            increment_questions(message.chat.id)

        await message.answer(answer)
    except Exception as e:
        await message.answer(f"⚠️ AI error: {e}")
# ============================================
#  AI TUTOR PRO BOT – FULL VERSION (PART 3/3)
# ============================================

# -----------------------
# 💬 Daily Motivational Quotes
# -----------------------
MOTIVATIONAL_QUOTES = [
    "🌟 Keep learning — your hard work will pay off!",
    "🚀 Every expert was once a beginner. Stay consistent.",
    "💡 Knowledge is your best investment — keep feeding it.",
    "🔥 Discipline beats motivation. Small steps every day!",
    "💪 You’re smarter than yesterday — keep pushing forward!"
]

async def send_daily_motivation():
    """Send one motivational quote per day to all users."""
    while True:
        now = datetime.utcnow().strftime("%H:%M")
        if now == MOTIVATION_TIME:
            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("SELECT chat_id FROM users")
            users = [row[0] for row in c.fetchall()]
            conn.close()

            quote = random.choice(MOTIVATIONAL_QUOTES)
            for uid in users:
                try:
                    await bot.send_message(uid, quote)
                except Exception as e:
                    logger.error(f"Failed to send motivation to {uid}: {e}")
            await asyncio.sleep(60)
        await asyncio.sleep(30)

# -----------------------
# 🌐 Webhook & Startup
# -----------------------
async def handle_webhook(request: web.Request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(status=500)

async def on_startup():
    init_db()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"✅ Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")

# -----------------------
# 🚀 Main Loop
# -----------------------
async def main():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    await on_startup()

    # Start daily motivation loop
    asyncio.create_task(send_daily_motivation())

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("🚀 AI Tutor Pro is fully online and ready!")
    while True:
        await asyncio.sleep(3600)

# -----------------------
# ❤️ Flask Health Check
# -----------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "✅ AI Tutor Pro is live and running!"

# -----------------------
# 🧵 Run Flask + Bot
# -----------------------
if __name__ == "__main__":
    def start_flask():
        flask_app.run(host="0.0.0.0", port=8080)

    threading.Thread(target=start_flask, daemon=True).start()

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot stopped manually.")
