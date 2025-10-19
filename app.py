import os
import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from openai import AsyncOpenAI
from dotenv import load_dotenv
import openai

print("🧩 OpenAI version in runtime:", openai.__version__)

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Initialize OpenAI and Telegram bot
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# --- COMMAND HANDLERS ---

@router.message(lambda message: message.text and message.text.startswith("/start"))
async def start_handler(message: types.Message):
    await message.answer("👋 Hello! I’m your AI Tutor Bot. Type /ask followed by your question!")

@router.message(lambda message: message.text and message.text.startswith("/help"))
async def help_handler(message: types.Message):
    await message.answer("💡 Commands:\n/start - Welcome message\n/ask - Ask AI a question")

@router.message(lambda message: message.text and message.text.startswith("/ask"))
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

# --- WEBHOOK SETUP ---

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    dp.include_router(router)

    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()

