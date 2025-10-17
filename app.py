import os
import asyncio
import threading
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from flask import Flask
from dotenv import load_dotenv

# =====================================================
# 🚀 Load environment variables
# =====================================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
MOTIVATION_TIME = int(os.getenv("MOTIVATION_TIME", 15))

# =====================================================
# ⚙️ Logging setup
# =====================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Tutor_Pro")

# =====================================================
# 🤖 Telegram Bot setup
# =====================================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =====================================================
# 🧠 Commands
# =====================================================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Welcome to **AI Tutor Pro!** Your AI tutor is ready to help!")

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer("🧭 Use /start to begin and ask me any question!")

# =====================================================
# 🧘 Motivation message sender
# =====================================================
async def send_daily_motivation():
    if not ADMIN_CHAT_ID:
        logger.warning("⚠️ ADMIN_CHAT_ID not set — skipping motivation messages.")
        return

    while True:
        try:
            await bot.send_message(
                chat_id=int(ADMIN_CHAT_ID),
                text="🌞 Stay motivated — keep learning and improving!"
            )
        except Exception as e:
            logger.warning(f"Motivation task error: {e}")
        await asyncio.sleep(MOTIVATION_TIME * 60)

# =====================================================
# 🌐 Flask heartbeat (DigitalOcean ping)
# =====================================================
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "✅ AI Tutor Pro Bot is running."

# =====================================================
# 🚀 Webhook Setup (No Polling)
# =====================================================
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook set to {WEBHOOK_URL}")

async def main():
    await on_startup()
    asyncio.create_task(send_daily_motivation())

    # Aiohttp server for webhook handling
    app = web.Application()
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    setup_application(app, handler, path="/webhook")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    await site.start()

    logger.info("🤖 AI Tutor Pro is fully online with webhook mode.")
    await asyncio.Event().wait()

# =====================================================
# 🏁 Main Entry
# =====================================================
if __name__ == "__main__":
    # Run Flask in background (optional)
    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8081)).start()

    # Run aiogram webhook server
    asyncio.run(main())

