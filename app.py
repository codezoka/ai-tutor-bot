import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from openai import AsyncOpenAI
from dotenv import load_dotenv

# ────────────── Load environment ──────────────
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://ai-tutor-bot-83opf.ondigitalocean.app/webhook")

PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

MOTIVATION_HOUR = int(os.getenv("MOTIVATION_HOUR", 15))

# ────────────── Init clients ──────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ────────────── Load prompts ──────────────
with open("prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

# ────────────── User data ──────────────
user_data = {}

# ────────────── Motivation quotes ──────────────
QUOTES = [
    "🚀 Success starts with the right question.",
    "💡 Smart questions lead to powerful answers.",
    "🔥 Every day is a new chance to grow smarter.",
    "🏆 Think big. Start small. Act now.",
    "📈 Your potential grows with every question you ask.",
    "✨ Knowledge is the new currency — invest in it.",
    "🤖 Let AI be your smartest business partner."
]

# ────────────── Helper ──────────────
def keyboard(buttons):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in buttons]])

# ────────────── /start ──────────────
@dp.message(F.text == "/start")
async def start(message: types.Message):
    text = (
        "🤖 *Welcome to AI Tutor Bot — Ask Smart, Think Smart!*\n\n"
        "✨ Choose your plan:\n"
        "🆓 Free – 5 smart questions\n"
        "⚡ Pro – Faster responses + 30 questions\n"
        "💎 Elite – Fastest + 50 questions + priority support\n\n"
        "💬 Type your own questions anytime!"
    )
    buttons = [("🆓 Free", "plan_free"), ("⚡ Pro", "plan_pro"), ("💎 Elite", "plan_elite")]
    await message.answer(text, reply_markup=keyboard(buttons), parse_mode="Markdown")

# ────────────── /help ──────────────
@dp.message(F.text == "/help")
async def help_cmd(message: types.Message):
    text = (
        "🧭 *How to use AI Tutor Bot*\n\n"
        "1️⃣ /start – choose your plan\n"
        "2️⃣ /questions – explore smart questions\n"
        "3️⃣ /upgrade – unlock Pro or Elite\n"
        "4️⃣ /status – check your progress\n\n"
        "💡 Type anything for instant AI help!"
    )
    await message.answer(text, parse_mode="Markdown")

# ────────────── /upgrade ──────────────
@dp.message(F.text == "/upgrade")
async def upgrade(message: types.Message):
    text = (
        "💎 **Upgrade Your AI Tutor Experience**\n\n"
        "⚡ Pro – $9.99/mo or $99.99/yr (20 % off)\n"
        "🚀 Elite – $19.99/mo or $199.99/yr (20 % off)\n\n"
        "Choose your plan below 👇"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("⚡ Pro Monthly", url=PRO_MONTHLY_URL),
         InlineKeyboardButton("⚡ Pro Yearly (20 % off)", url=PRO_YEARLY_URL)],
        [InlineKeyboardButton("🚀 Elite Monthly", url=ELITE_MONTHLY_URL),
         InlineKeyboardButton("🚀 Elite Yearly (20 % off)", url=ELITE_YEARLY_URL)],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_start")]
    ])
    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

# ────────────── /status ──────────────
@dp.message(F.text == "/status")
async def status(message: types.Message):
    uid = message.from_user.id
    user = user_data.get(uid, {"plan": "Free", "remaining": 5})
    text = (
        f"📊 *Your Status:*\n\n"
        f"👤 Plan: *{user['plan']}*\n"
        f"🧠 Remaining Smart Questions: *{user['remaining']}*\n"
        f"📅 Renewal: {(datetime.utcnow()+timedelta(days=30)).strftime('%Y-%m-%d')}\n\n"
        "💬 You can always type your own questions!"
    )
    await message.answer(text, parse_mode="Markdown")

# ────────────── Plan selection ──────────────
@dp.callback_query(F.data.startswith("plan_"))
async def plan_selected(callback: types.CallbackQuery):
    plan = callback.data.replace("plan_", "").capitalize()
    user_data[callback.from_user.id] = {
        "plan": plan,
        "remaining": 5 if plan == "Free" else 30 if plan == "Pro" else 50
    }
    buttons = [("💼 Business", f"{plan}_business"),
               ("🤖 AI", f"{plan}_ai"),
               ("💰 Crypto", f"{plan}_crypto"),
               ("⬅️ Back", "back_start")]
    await callback.message.edit_text(
        f"📚 *{plan} Plan Selected!*\nChoose your category 👇",
        reply_markup=keyboard(buttons),
        parse_mode="Markdown"
    )

# ────────────── Category selection ──────────────
@dp.callback_query(F.data.endswith(("_business", "_ai", "_crypto")))
async def category_selected(callback: types.CallbackQuery):
    plan, category = callback.data.split("_", 1)
    buttons = [("🌱 Starter", f"{plan}_{category}_starter"),
               ("💼 Profit", f"{plan}_{category}_profit"),
               ("⬅️ Back", "back_start")]
    await callback.message.edit_text(
        f"{PROMPTS[category]['intro']}\n\nChoose your level 👇",
        reply_markup=keyboard(buttons),
        parse_mode="Markdown"
    )

# ────────────── Level selection ──────────────
@dp.callback_query(F.data.endswith(("_starter", "_profit")))
async def level_selected(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    plan, category, level = parts[0], parts[1], parts[2]
    try:
        qset = PROMPTS[category][plan.lower()][level]
        for q in qset:
            await callback.message.answer(f"💡 {q}")
    except Exception as e:
        await callback.message.answer(f"⚠️ Error loading prompts: {e}")
    await callback.message.answer("⬅️ Type /questions anytime to return!")

# ────────────── Back navigation ──────────────
@dp.callback_query(F.data == "back_start")
async def go_back(callback: types.CallbackQuery):
    await start(callback.message)

# ────────────── /questions ──────────────
@dp.message(F.text == "/questions")
async def show_questions(message: types.Message):
    buttons = [("💼 Business", "Free_business"),
               ("🤖 AI", "Free_ai"),
               ("💰 Crypto", "Free_crypto"),
               ("⬅️ Back", "back_start")]
    await message.answer("📚 Choose a category 👇", reply_markup=keyboard(buttons))

# ────────────── AI chat fallback ──────────────
@dp.message()
async def chat_with_ai(message: types.Message):
    prompt = message.text.strip()
    await message.answer("🤖 Thinking...")
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        await message.answer(f"⚠️ Error: {e}")

# ────────────── Daily motivation ──────────────
async def daily_motivation():
    while True:
        now = datetime.utcnow()
        target = datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=MOTIVATION_HOUR)
        wait = (target - now).total_seconds()
        if wait < 0:
            wait += 86400
        await asyncio.sleep(wait)
        quote = random.choice(QUOTES)
        for uid in user_data:
            try:
                await bot.send_message(uid, f"🌟 *Daily Motivation:* {quote}", parse_mode="Markdown")
            except:
                pass

# ────────────── Webhook entrypoint ──────────────
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(daily_motivation())

async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()


