import os
import json
import asyncio
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from openai import AsyncOpenAI
from dotenv import load_dotenv

# ──────────────  Load Environment  ──────────────
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ──────────────  Load Smart Questions  ──────────────
with open("prompts.json", "r", encoding="utf-8") as f:
    SMART_QUESTIONS = json.load(f)

# ──────────────  User Data  ──────────────
user_data = {}  # {user_id: {"plan": "Free", "used": 0}}

# ──────────────  Helper: Build Buttons  ──────────────
def build_keyboard(buttons, back_to=None):
    kb = InlineKeyboardBuilder()
    for b in buttons:
        kb.button(text=b, callback_data=b)
    if back_to:
        kb.button(text="🔙 Back", callback_data=back_to)
    kb.adjust(2)
    return kb.as_markup()

# ──────────────  /start  ──────────────
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_data[message.from_user.id] = {"plan": "Free", "used": 0}
    text = (
        "🤖 **AI Tutor Bot – Ask Smart, Think Smart**\n\n"
        "Welcome! I’m your personal AI tutor that helps you ask **smarter questions** "
        "in **Business**, **AI**, and **Crypto** to think like a CEO.\n\n"
        "✨ Free plan: 5 smart questions total.\n"
        "⚡️ Pro = faster responses + 30 questions.\n"
        "🚀 Elite = fastest AI + 50 questions and priority support.\n\n"
        "Ready? Choose your plan below 👇"
    )
    await message.answer(
        text,
        reply_markup=build_keyboard(["🆓 Free Plan", "⚡ Pro Plan", "🚀 Elite Plan"])
    )

# ──────────────  /help  ──────────────
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(
        "🧭 **How to use AI Tutor Bot**\n\n"
        "1️⃣ Use /start to choose your plan and category.\n"
        "2️⃣ Use /questions to see smart questions.\n"
        "3️⃣ Type your own question anytime – no limits for manual chat.\n"
        "4️⃣ Use /upgrade to go Pro or Elite for faster replies and more questions.\n"
        "5️⃣ Use /status to see your plan and remaining questions."
    )

# ──────────────  /upgrade  ──────────────
@dp.message(Command("upgrade"))
async def upgrade_handler(message: types.Message):
    text = (
        "💎 **Upgrade Your AI Tutor Experience**\n\n"
        "⚡ Pro Plan – $9.99/mo or $99.99/yr (20 % off)\n"
        "   – Faster AI responses + 30 smart questions.\n\n"
        "🚀 Elite Plan – $19.99/mo or $199.99/yr (20 % off)\n"
        "   – Fastest AI + 50 smart questions + priority support.\n\n"
        "Choose your plan below 👇"
    )
    buttons = [
        ("⚡ Pro Monthly", PRO_MONTHLY_URL),
        ("⚡ Pro Yearly (20 % off)", PRO_YEARLY_URL),
        ("🚀 Elite Monthly", ELITE_MONTHLY_URL),
        ("🚀 Elite Yearly (20 % off)", ELITE_YEARLY_URL),
    ]
    kb = InlineKeyboardBuilder()
    for text_btn, url in buttons:
        kb.button(text=text_btn, url=url)
    await message.answer(text, reply_markup=kb.as_markup())

# ──────────────  /status  ──────────────
@dp.message(Command("status"))
async def status_handler(message: types.Message):
    data = user_data.get(message.from_user.id, {"plan": "Free", "used": 0})
    remaining = 5 - data["used"] if data["plan"] == "Free" else "Unlimited"
    await message.answer(
        f"📊 **Your Status**\n\n"
        f"Plan: {data['plan']}\n"
        f"Smart Questions Left: {remaining}\n"
        f"Used: {data['used']}"
    )

# ──────────────  /ask  ──────────────
@dp.message(Command("ask"))
async def ask_handler(message: types.Message):
    prompt = message.text.replace("/ask", "").strip()
    if not prompt:
        await message.answer("Please type something after /ask (e.g. /ask What is AI?)")
        return
    await generate_answer(message, prompt)

# ──────────────  Handle text (free typing)  ──────────────
@dp.message()
async def handle_text(message: types.Message):
    prompt = message.text.strip()
    if not prompt:
        return
    await generate_answer(message, prompt)

# ──────────────  Core AI Logic  ──────────────
async def generate_answer(message: types.Message, prompt: str):
    user_id = message.from_user.id
    plan = user_data.get(user_id, {"plan": "Free", "used": 0})
    if plan["plan"] == "Free" and plan["used"] >= 5:
        await message.answer("🔒 You used all 5 smart questions. Upgrade to unlock more!")
        return
    await message.answer("🤖 Thinking...")
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        await message.answer(response.choices[0].message.content)
        if plan["plan"] == "Free":
            plan["used"] += 1
            user_data[user_id] = plan
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

# ──────────────  Motivational Quotes  ──────────────
QUOTES = [
    "💭 Success starts with smart questions. Ask one today!",
    "🚀 Upgrade your mind — upgrade your AI power.",
    "🔥 Every question you ask is a step toward mastery.",
    "💡 Pro and Elite users think bigger — be one of them!",
    "✨ Don’t wait for success — ask for it. /upgrade now."
]

async def send_daily_quotes():
    while True:
        now = datetime.utcnow()
        target = datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=15)
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        for uid in user_data.keys():
            try:
                await bot.send_message(uid, f"🌞 {QUOTES[now.day % len(QUOTES)]}")
            except:
                pass

# ──────────────  Webhook Setup  ──────────────
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_daily_quotes())

async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()

