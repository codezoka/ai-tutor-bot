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

# === Load environment variables ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = "https://ai-tutor-bot-83opf.ondigitalocean.app/webhook"

# === Initialize clients ===
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# === Load prompts ===
with open("prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

# === User Data ===
user_data = {}

# === Motivational Quotes ===
QUOTES = [
    "🚀 Success starts with the right question.",
    "💡 Smart questions lead to powerful answers.",
    "🔥 Every day is a new chance to grow smarter.",
    "🏆 Think big. Start small. Act now.",
    "📈 Your potential grows with every question you ask.",
    "✨ Knowledge is the new currency — invest in it.",
    "🤖 Let AI be your smartest business partner."
]

# === Helper ===
def make_keyboard(buttons):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=b[0], callback_data=b[1])] for b in buttons]
    )

# === /start Command ===
@dp.message(F.text == "/start")
async def start(message: types.Message):
    text = (
        "🤖 *Welcome to AI Tutor Bot — Ask Smart, Think Smart!*\n\n"
        "✨ Choose your plan to unlock the full power of AI:\n\n"
        "🆓 *Free* – 5 Smart Questions Lifetime\n"
        "⚡ *Pro* – 15 Smart Questions + Faster AI Responses\n"
        "💎 *Elite* – 25 Smart Questions + Full Power AI + 20% OFF Yearly\n\n"
        "💬 You can *always* type your own questions anytime!"
    )
    buttons = [("🆓 Free", "plan_free"), ("⚡ Pro", "plan_pro"), ("💎 Elite", "plan_elite")]
    await message.answer(text, reply_markup=make_keyboard(buttons), parse_mode="Markdown")

# === /help Command ===
@dp.message(F.text == "/help")
async def help(message: types.Message):
    text = (
        "🧭 *How to use AI Tutor Bot:*\n\n"
        "💬 Type any question — the AI will answer you instantly!\n"
        "💡 Use Smart Questions to learn faster:\n"
        "   - /start — Choose plan & explore questions\n"
        "   - /upgrade — Unlock Pro or Elite\n"
        "   - /status — See your current plan\n\n"
        "📈 Pro & Elite members enjoy *faster responses* and *exclusive questions!*"
    )
    await message.answer(text, parse_mode="Markdown")

# === /upgrade Command (Enhanced UI) ===
@dp.message(F.text == "/upgrade")
async def upgrade(message: types.Message):
    text = (
        "💳 **Upgrade Your AI Tutor Experience**\n\n"
        "🧾 *Plan Comparison*\n"
        "🆓 **Free** – 5 Smart Questions | Standard speed\n"
        "⚡ **Pro** – 15 Smart Questions | 🚀 Fast AI | $9.99 /mo or $99.99 /yr (20 % off)\n"
        "💎 **Elite** – 25 Smart Questions | ⚡ Full Power AI | $19.99 /mo or $199.99 /yr (20 % off)\n\n"
        "🌟 *Pro and Elite users get faster responses, deeper prompts, and daily insights.*"
    )

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⚡ Pro Monthly", url="https://t.me/send?start=IVdixIeFSP3W"),
        InlineKeyboardButton("⚡ Pro Yearly (20 % OFF)", url="https://t.me/send?start=IVRnAnXOWzRM"),
        InlineKeyboardButton("💎 Elite Monthly", url="https://t.me/send?start=IVfwy1t6hcu9"),
        InlineKeyboardButton("💎 Elite Yearly (20 % OFF)", url="https://t.me/send?start=IVxMW0UNvl7d"),
    )
    keyboard.add(
        InlineKeyboardButton("🧾 Plan Comparison", callback_data="compare_plans"),
        InlineKeyboardButton("⬅️ Back", callback_data="back_start"),
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

# === Plan Comparison Popup ===
@dp.callback_query(F.data == "compare_plans")
async def compare_plans(callback: types.CallbackQuery):
    await callback.message.answer(
        "🧾 **Plan Comparison**\n\n"
        "🆓 *Free*: 5 Smart Questions | Standard Speed\n"
        "⚡ *Pro*: 15 Smart Questions | 🚀 Fast AI | Business-Level Prompts\n"
        "💎 *Elite*: 25 Smart Questions | ⚡ Full Power AI | Priority Support + Advanced Insights\n\n"
        "💡 Tip: Pro and Elite members get exclusive AI answers tailored for business growth!",
        parse_mode="Markdown"
    )


# === /status Command ===
@dp.message(F.text == "/status")
async def status(message: types.Message):
    uid = message.from_user.id
    user = user_data.get(uid, {"plan": "Free", "remaining": 5})
    text = (
        f"📊 *Your Status:*\n\n"
        f"👤 Plan: *{user['plan']}*\n"
        f"🕓 Remaining Smart Questions: *{user['remaining']}*\n"
        f"📅 Renewal Date: *{(datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')}*\n\n"
        "💬 You can always type your own questions for free!"
    )
    await message.answer(text, parse_mode="Markdown")

# === Handle plan selection ===
@dp.callback_query(F.data.startswith("plan_"))
async def plan_selected(callback: types.CallbackQuery):
    plan = callback.data.replace("plan_", "").capitalize()
    user_data[callback.from_user.id] = {
        "plan": plan,
        "remaining": 5 if plan == "Free" else 15 if plan == "Pro" else 25,
    }
    buttons = [("🤖 AI", f"{plan}_ai"), ("💼 Business", f"{plan}_business"), ("💰 Crypto", f"{plan}_crypto"), ("⬅️ Back", "back_start")]
    await callback.message.edit_text(
        f"📚 *{plan} Plan Selected!*\n\nChoose your category:",
        reply_markup=make_keyboard(buttons),
        parse_mode="Markdown",
    )

# === Category Selection (AI, Business, Crypto) ===
@dp.callback_query(F.data.endswith(("_ai", "_business", "_crypto")))
async def category_selected(callback: types.CallbackQuery):
    plan, category = callback.data.split("_", 1)
    buttons = [
        ("🌱 Starter", f"{plan}_{category}_starter"),
        ("🚀 Profit", f"{plan}_{category}_profit"),
        ("⬅️ Back", f"plan_{plan.lower()}"),
    ]
    await callback.message.edit_text(
        f"📘 *{category.capitalize()} ({plan} Plan)*\nChoose your level:",
        reply_markup=make_keyboard(buttons),
        parse_mode="Markdown",
    )

# === Show Smart Questions ===
@dp.callback_query(F.data.endswith(("_starter", "_profit")))
async def show_questions(callback: types.CallbackQuery):
    plan, category, level = callback.data.split("_", 2)
    questions = PROMPTS.get(plan, {}).get(category, {}).get(level, [])[:10]
    if not questions:
        await callback.message.answer("⚠️ No questions found.")
        return
    buttons = [(q, f"ask_{plan}_{category}_{level}_{i}") for i, q in enumerate(questions)]
    buttons.append(("⬅️ Back", f"{plan}_{category}"))
    await callback.message.edit_text(
        f"💡 *{category.capitalize()} - {level.capitalize()}*\nSelect a question to ask:",
        reply_markup=make_keyboard(buttons),
        parse_mode="Markdown",
    )

# === Ask Smart Question ===
@dp.callback_query(F.data.startswith("ask_"))
async def ask_question(callback: types.CallbackQuery):
    _, plan, category, level, idx = callback.data.split("_", 4)
    uid = callback.from_user.id
    question = PROMPTS[plan][category][level][int(idx)]
    user = user_data.get(uid, {"plan": "Free", "remaining": 5})

    if user["remaining"] <= 0 and user["plan"] == "Free":
        await callback.message.answer("❌ You’ve used all your free Smart Questions. Please /upgrade to continue.")
        return

    user["remaining"] -= 1
    user_data[uid] = user
    await callback.message.answer(f"🤔 *You asked:* {question}", parse_mode="Markdown")

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question}],
        )
        await callback.message.answer(f"💬 {response.choices[0].message.content}")
    except Exception as e:
        await callback.message.answer(f"⚠️ Error: {e}")

# === Handle callback for Back and Payments ===
@dp.callback_query()
async def generic_callback(callback: types.CallbackQuery):
    data = callback.data
    if data == "back_start":
        await start(callback.message)
    elif data == "buy_pro_monthly":
        await callback.message.answer("💳 Pay here: https://t.me/send?start=IVdixIeFSP3W")
    elif data == "buy_pro_yearly":
        await callback.message.answer("💳 Pay here: https://t.me/send?start=IVRnAnXOWzRM")
    elif data == "buy_elite_monthly":
        await callback.message.answer("💎 Pay here: https://t.me/send?start=IVfwy1t6hcu9")
    elif data == "buy_elite_yearly":
        await callback.message.answer("💎 Pay here: https://t.me/send?start=IVxMW0UNvl7d")
    else:
        await callback.answer("⏳ Please wait...")

# === Handle normal chat messages ===
@dp.message()
async def chat_with_ai(message: types.Message):
    prompt = message.text.strip()
    await message.answer("🤖 Thinking...")
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        await message.answer(f"⚠️ Error: {e}")

# === Daily Motivational Message ===
async def daily_quote():
    while True:
        now = datetime.utcnow()
        target = datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=15)
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

# === Webhook setup for DigitalOcean ===
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(daily_quote())

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
