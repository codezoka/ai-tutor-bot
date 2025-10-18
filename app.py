import os
import asyncio
import threading
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web
from flask import Flask
from dotenv import load_dotenv

# =====================================================
# 🚀 Load environment variables
# =====================================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
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
    await message.answer("👋 Welcome to **AI Tutor Pro!**\nYour tutor is ready to help you learn!")

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer("🧭 Commands:\n/start - Start the bot\n/help - Show help")

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
# 🌐 Flask heartbeat
# =====================================================
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ AI Tutor Pro Bot is running."

# =====================================================
# 🚀 Webhook app (aiohttp)
# =====================================================
async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook set to {WEBHOOK_URL}")
    asyncio.create_task(send_daily_motivation())

async def on_shutdown(app):
    await bot.session.close()

async def handle_webhook(request):
    update = await request.json()
    await dp.feed_update(bot, update)
    return web.Response(status=200)

def create_aiohttp_app():
    app = web.Application()
    
    # ✅ Health check route for DigitalOcean
    async def health_check(request):
        return web.Response(text="✅ OK", status=200)
    
    app.router.add_get("/", health_check)
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


# =====================================================
# 🏁 Entry point
# =====================================================
if __name__ == "__main__":
    # Run Flask heartbeat on background port 8081
    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8081)).start()

    # Run aiohttp webhook listener on main port 8080
    web.run_app(create_aiohttp_app(), host="0.0.0.0", port=int(os.getenv("PORT", 8080)))


