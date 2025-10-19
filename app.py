import os
import logging
import asyncio
import random
import threading
from datetime import datetime

from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from openai import AsyncOpenAI
from dotenv import load_dotenv

# ======================================================
# 🔧 Load environment variables
# ======================================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# CryptoBot links
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

# ======================================================
# 🚀 Logging setup
# ======================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Tutor_Pro")

# ======================================================
# 🧩 Initialize bot, dispatcher, and OpenAI client
# ======================================================
if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("❌ BOT_TOKEN or OPENAI_API_KEY missing in environment variables!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

logger.info("✅ OpenAI SDK initialized successfully.")

# ======================================================
# 💬 Simple user limit system
# ======================================================
user_usage = {}
MAX_FREE_MESSAGES = 5

# ======================================================
# 🌟 Motivational quotes
# ======================================================
quotes = [
    "Keep going — success is closer than you think!",
    "Every expert was once a beginner. 💪",
    "Dream big, start small, act now.",
    "Discipline beats motivation every time.",
    "Progress, not perfection. 🚀"
]

async def send_daily_motivation():
    """Send one motivational quote per day to all users."""
    while True:
        if user_usage:
            quote = random.choice(quotes)
            for user_id in user_usage.keys():
                try:
                    await bot.send_message(user_id, f"💡 Daily Motivation:\n\n{quote}")
                except Exception as e:
                    logger.warning(f"Could not send motivation to {user_id}: {e}")
        await asyncio.sleep(24 * 60 * 60)  # 1 day

# ======================================================
# 🤖 Commands
# ======================================================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_usage[message.from_user.id] = 0
    welcome = (
        "👋 Welcome to **AI Tutor Pro!**\n\n"
        "You can chat with AI, ask questions, and get answers instantly.\n"
        "Free users can send up to 5 messages per day.\n\n"
        "Upgrade anytime to unlock unlimited AI access:\n"
        f"💎 [Pro Monthly]({PRO_MONTHLY_URL})\n"
        f"💎 [Pro Yearly]({PRO_YEARLY_URL})\n"
        f"🚀 [Elite Monthly]({ELITE_MONTHLY_URL})\n"
        f"🚀 [Elite Yearly]({ELITE_YEARLY_URL})\n\n"
        "Let's get started — type your question below 👇"
    )
    await message.answer(welcome, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    help_text = (
        "🧠 **AI Tutor Pro Help**\n\n"
        "/start — Restart the bot\n"
        "/help — Show this help message\n"
        "/questions — View example smart prompts\n"
        "/upgrade — View upgrade options\n"
        "/status — Check your usage status"
    )
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("questions"))
async def questions_cmd(message: types.Message):
    examples = (
        "💡 Example Questions:\n"
        "- How do neural networks learn?\n"
        "- Write a short motivational message.\n"
        "- Suggest 3 AI business ideas.\n"
        "- Explain blockchain simply.\n"
        "- What's the best way to learn Python fast?"
    )
    await message.answer(examples)

@dp.message(Command("upgrade"))
async def upgrade_cmd(message: types.Message):
    upgrade_text = (
        "🌟 **Upgrade Your Plan**\n\n"
        f"💎 [Pro Monthly]({PRO_MONTHLY_URL})\n"
        f"💎 [Pro Yearly]({PRO_YEARLY_URL})\n"
        f"🚀 [Elite Monthly]({ELITE_MONTHLY_URL})\n"
        f"🚀 [Elite Yearly]({ELITE_YEARLY_URL})"
    )
    await message.answer(upgrade_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("status"))
async def status_cmd(message: types.Message):
    used = user_usage.get(message.from_user.id, 0)
    remaining = MAX_FREE_MESSAGES - used
    await message.answer(f"📊 You have {remaining} free messages left today.")

# ======================================================
# 💬 Chat handler
# ======================================================
@dp.message()
async def chat_with_ai(message: types.Message):
    user_id = message.from_user.id
    usage = user_usage.get(user_id, 0)

    if usage >= MAX_FREE_MESSAGES:
        await message.answer(
            "⚠️ You've reached your free message limit.\n"
            "Upgrade to Pro or Elite to continue chatting:\n"
            f"💎 [Pro Monthly]({PRO_MONTHLY_URL})\n"
            f"🚀 [Elite Monthly]({ELITE_MONTHLY_URL})",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    user_usage[user_id] = usage + 1

    try:
        reply = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message.text}],
        )
        answer = reply.choices[0].message.content.strip()
        await message.answer(answer)
    except Exception as e:
        logger.error(f"AI error: {e}")
        await message.answer("❌ Sorry, I couldn’t get a response from the AI right now.")

# ======================================================
# 🌐 Flask webhook setup
# ======================================================
flask_app = Flask(__name__)

@flask_app.route("/webhook", methods=["POST"])
async def handle_webhook():
    data = request.json
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return {"ok": True}

@flask_app.route("/")
def home():
    return "✅ AI Tutor Pro Bot is Running!"

# ======================================================
# 🚀 Startup
# ======================================================
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    webhook_url = f"https://{os.getenv('APP_URL')}/webhook"
    await bot.set_webhook(webhook_url)
    logger.info(f"✅ Webhook set to {webhook_url}")

# ======================================================
# 🧠 Main run
# ======================================================
if __name__ == "__main__":
    async def start_bot():
        await on_startup()
        asyncio.create_task(send_daily_motivation())
        logger.info("🤖 AI Tutor Pro Bot is fully online!")

    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8080)).start()
    asyncio.run(start_bot())

