import os
import logging
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import AsyncOpenAI

# ========================
# 🔧 Configuration
# ========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://ai-tutor-bot-83opf.ondigitalocean.app/webhook")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("❌ Missing BOT_TOKEN or OPENAI_API_KEY in environment variables!")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Tutor_Pro")

# ========================
# 🚀 Core Setup
# ========================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

# ========================
# 📩 Bot Handlers
# ========================
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Welcome to *AI Tutor Pro*! 🚀\n"
        "I can help with learning, business, and AI insights.\n\n"
        "Use /help to see all commands.",
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "📘 *Available Commands:*\n"
        "/start - Start the bot\n"
        "/questions - Get AI prompts\n"
        "/upgrade - View subscription plans\n"
        "/status - Check your plan",
        parse_mode="Markdown"
    )

@dp.message(Command("questions"))
async def questions_handler(message: types.Message):
    await message.answer(
        "💡 *Smart Prompts:*\n"
        "• What’s trending in AI?\n"
        "• How can I grow my business?\n"
        "• Send me a motivational quote!",
        parse_mode="Markdown"
    )

@dp.message(Command("upgrade"))
async def upgrade_handler(message: types.Message):
    await message.answer(
        "💎 *Upgrade Plans:*\n"
        "Free: 5 messages/day\n"
        "Pro: Unlimited + Fast replies\n"
        "Elite: AI business strategy access\n\n"
        "Crypto payments supported soon.",
        parse_mode="Markdown"
    )

@dp.message(Command("status"))
async def status_handler(message: types.Message):
    await message.answer("🧾 You’re on the Free Plan (5 messages/day).")

@dp.message()
async def ai_chat(message: types.Message):
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a friendly, motivational AI tutor."},
                {"role": "user", "content": message.text},
            ]
        )
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"AI Error: {e}")
        await message.answer("⚠️ Sorry, something went wrong.")

# ========================
# 🌐 Flask Webhook Routes
# ========================
@app.route("/", methods=["GET"])
def home():
    return "✅ AI Tutor Pro bot is running.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = types.Update.model_validate(request.json)
        asyncio.get_event_loop().create_task(dp.feed_update(bot, update))
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": False}, 500

# ========================
# 🧠 Webhook Setup
# ========================
async def setup_webhook():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook set to {WEBHOOK_URL}")

# ========================
# 🚀 Run Application
# ========================
if __name__ == "__main__":
    asyncio.run(setup_webhook())
    logger.info("🤖 AI Tutor Pro is online!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

