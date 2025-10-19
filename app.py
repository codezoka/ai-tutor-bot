import os
import sys
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from dotenv import load_dotenv

# 🧩 Force reload OpenAI to prevent version conflicts
sys.modules.pop("openai", None)
import openai
print("🧩 OpenAI version in runtime:", openai.__version__)
if not openai.__version__.startswith("1."):
    raise RuntimeError(f"❌ Wrong OpenAI version detected ({openai.__version__}). Must be >=1.0.0")

from openai import AsyncOpenAI

# 🔑 Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# 🧠 Initialize clients
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# -------------------- Telegram Bot Commands --------------------

@dp.message(commands=["start"])
async def start_handler(message: types.Message):
    await message.answer("👋 Hello! I’m your AI Tutor Bot. Type /ask followed by your question!")

@dp.message(commands=["help"])
async def help_handler(message: types.Message):
    await message.answer("💡 Commands:\n/start - Welcome message\n/ask - Ask AI a question")

@dp.message(commands=["ask"])
async def ask_handler(message: types.Message):
    prompt = message.text.replace("/ask", "").strip()
    if not prompt:
        await message.answer("Please ask something after /ask, e.g. /ask What is AI?")
        return
    await message.answer("🤖 Thinking...")
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

# -------------------- Webhook Setup --------------------

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook set to {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    print("🛑 Webhook deleted")

def main():
    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

# -------------------- Entry Point --------------------
if __name__ == "__main__":
    main()

