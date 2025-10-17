import os
import asyncio
import threading
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from flask import Flask
from datetime import datetime
from dotenv import load_dotenv

# =====================================================
# 🚀 Load environment variables
# =====================================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
MOTIVATION_TIME = int(os.getenv("MOTIVATION_TIME", 15))
FREE_QUESTION_LIMIT = int(os.getenv("FREE_QUESTION_LIMIT", 3))

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
# 🧠 Basic Commands
# =====================================================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Welcome to **AI Tutor Pro!**\nAsk me anything!")

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer("🧭 Commands:\n/start - Start bot\n/help - Show help\nAsk your AI Tutor anything!")

# =====================================================
# 🧘 Motivation message sender
# =====================================================
async def send_daily_motivation():
    while True:
        try:
            await bot.send_message(
                chat_id=os.getenv("ADMIN_CHAT_ID", message.chat.id if 'message' in locals() else None),
                text="🌞 Stay motivated — keep learning and improving!"
            )
        except Exception as e:
            logger.warning(f"Motivation task error: {e}")
        await asyncio.sleep(MOTIVATION_TIME * 60)

# =====================================================
# 🧩 Startup sequence
# =====================================================
async def on_startup():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"✅ Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")

# =====================================================
# 🌐 Flask heartbeat (to keep alive)
# =====================================================
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "✅ AI Tutor Pro Bot is running."

# =====================================================
# 🏁 Main runner (DigitalOcean safe)
# =====================================================
if __name__ == "__main__":
    async def start_bot():
        await on_startup()
        asyncio.create_task(send_daily_motivation())
        logger.info("🤖 AI Tutor Pro Bot is fully online!")
        await dp.start_polling(bot)

    def run_flask():
        flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

    # Run Flask in a separate thread
    threading.Thread(target=run_flask, daemon=True).start()

    # Run Telegram bot
    asyncio.run(start_bot())

