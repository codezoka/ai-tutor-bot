import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiohttp import web
from flask import Flask, request
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram and OpenAI credentials
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("❌ BOT_TOKEN or OPENAI_API_KEY missing in environment variables!")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Tutor_Pro")

# Initialize clients
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)  # ✅ Fixed: no 'proxies' argument

# Flask app for health check
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ AI Tutor Pro bot is running!"

# Telegram webhook handler
@flask_app.route('/webhook', methods=['POST'])
async def telegram_webhook():
    update = types.Update(**request.json)
    await dp.feed_update(bot, update)
    return {"ok": True}

# Simple AI response handler
@dp.message()
async def handle_message(message: Message):
    user_text = message.text.strip()

    # Respond using OpenAI
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI tutor."},
                {"role": "user", "content": user_text}
            ],
            max_tokens=150
        )
        reply = response.choices[0].message.content.strip()
        await message.answer(reply)
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        await message.answer("⚠️ Sorry, I couldn’t process that right now.")

# Start-up logic
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook set to {WEBHOOK_URL}")

# Run bot + Flask server together
async def start_bot():
    await on_startup()
    logger.info("🤖 AI Tutor Pro Bot is fully online!")

    loop = asyncio.get_running_loop()
    loop.create_task(flask_app.run(host="0.0.0.0", port=8080))
    await asyncio.Future()  # Keep running

if __name__ == "__main__":
    asyncio.run(start_bot())

