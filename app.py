import os
import logging
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import AsyncOpenAI

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("❌ Missing BOT_TOKEN or OPENAI_API_KEY!")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Tutor_Pro")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Flask app
app = Flask(__name__)

# ====== Handlers ======
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Hello! I’m *AI Tutor Pro*, your study and business assistant.\n"
        "Type /help to see what I can do.",
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "📘 *Help Menu*\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/questions - Show smart prompts\n"
        "/upgrade - Subscription options\n"
        "/status - Check your subscription",
        parse_mode="Markdown"
    )

@dp.message(Command("questions"))
async def question_handler(message: types.Message):
    await message.answer(
        "💡 Smart prompts:\n"
        "• What are top AI trends?\n"
        "• How can I grow my business?\n"
        "• Give me a motivation quote!"
    )

@dp.message(Command("upgrade"))
async def upgrade_handler(message: types.Message):
    await message.answer(
        "💎 *Upgrade Options*\n\n"
        "Free Plan: 5 questions/day\n"
        "Pro Plan: Fast & unlimited\n"
        "Elite Plan: Includes AI insights\n\n"
        "Crypto payments coming soon!",
        parse_mode="Markdown"
    )

@dp.message(Command("status"))
async def status_handler(message: types.Message):
    await message.answer("🔍 You’re currently on the Free Plan (5 messages/day).")

@dp.message()
async def chat_handler(message: types.Message):
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a friendly AI tutor and business mentor."},
                {"role": "user", "content": message.text},
            ],
        )
        answer = response.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        logger.error(f"AI Error: {e}")
        await message.answer("⚠️ Sorry, something went wrong. Please try again later.")

# ====== Flask webhook route ======
@app.route("/webhook", methods=["POST"])
async def webhook():
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

# ====== Set webhook ======
async def on_startup():
    webhook_url = os.getenv("WEBHOOK_URL", "https://ai-tutor-bot-83opf.ondigitalocean.app/webhook")
    await bot.set_webhook(webhook_url)
    logger.info(f"✅ Webhook set to {webhook_url}")

if __name__ == "__main__":
    asyncio.run(on_startup())
    logger.info("🚀 AI Tutor Pro Bot is online!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

