import os
import logging
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from openai import AsyncOpenAI
import asyncio

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("❌ Missing BOT_TOKEN or OPENAI_API_KEY in environment variables!")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Tutor_Pro")

# Initialize bot, dispatcher, and OpenAI client
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Create Flask app
app = Flask(__name__)

# === Telegram Commands ===
@dp.message(commands=["start"])
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Hello! I'm *AI Tutor Pro*, your study and business assistant.\n"
        "I can answer questions, motivate you, and help you grow.\n\n"
        "Type /help to see what I can do!",
        parse_mode="Markdown"
    )

@dp.message(commands=["help"])
async def help_handler(message: types.Message):
    await message.answer(
        "📘 *Help Menu*\n\n"
        "Available commands:\n"
        "/start - Start the bot\n"
        "/questions - Ask me smart prompts\n"
        "/upgrade - Subscription info\n"
        "/status - Check your account status",
        parse_mode="Markdown"
    )

@dp.message(commands=["questions"])
async def question_handler(message: types.Message):
    await message.answer(
        "💡 Here are some ideas:\n"
        "• What are the top AI business trends?\n"
        "• How can I start an online business?\n"
        "• Give me a daily motivation quote!"
    )

@dp.message(commands=["upgrade"])
async def upgrade_handler(message: types.Message):
    await message.answer(
        "💎 *Upgrade Options*\n\n"
        "• Free Plan — 5 daily questions.\n"
        "• Pro Plan — Fast & unlimited access.\n"
        "• Elite Plan — Includes AI business insights.\n\n"
        "Coming soon: integrated crypto payments!"
    )

@dp.message(commands=["status"])
async def status_handler(message: types.Message):
    await message.answer("🔍 You are currently on the Free Plan (limit 5 daily messages).")

@dp.message()
async def chat_handler(message: types.Message):
    """Handles normal user messages and sends AI responses"""
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are AI Tutor Pro, a friendly AI tutor and business mentor."},
                {"role": "user", "content": message.text},
            ],
        )
        answer = response.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        logger.error(f"AI error: {e}")
        await message.answer("⚠️ Sorry, something went wrong. Please try again later.")


# === Flask Webhook Route ===
@app.route("/webhook", methods=["POST"])
async def handle_webhook():
    """Main webhook endpoint for Telegram"""
    try:
        update = types.Update.model_validate(request.json)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": False}, 500


@app.route("/", methods=["GET"])
def index():
    return "🤖 AI Tutor Pro bot is running!", 200


# === Webhook Setup (runs when deployed) ===
async def set_webhook():
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        webhook_url = "https://ai-tutor-bot-83opf.ondigitalocean.app/webhook"
    await bot.set_webhook(webhook_url)
    logger.info(f"✅ Webhook set to {webhook_url}")


if __name__ == "__main__":
    asyncio.run(set_webhook())
    logger.info("🤖 AI Tutor Pro Bot is fully online!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

