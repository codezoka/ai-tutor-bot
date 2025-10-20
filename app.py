import os
import json
import random
import asyncio
import logging
import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from openai import AsyncOpenAI

# ================== ENV & SETUP ==================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = "https://ai-tutor-bot-83opf.ondigitalocean.app/webhook"

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("❌ BOT_TOKEN or OPENAI_API_KEY missing in environment variables!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
logging.basicConfig(level=logging.INFO)

# ================== LOAD PROMPTS ==================
def load_prompts():
    try:
        with open("prompts.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load prompts.json: {e}")
        return {}

PROMPTS = load_prompts()

# ================== USER DATA ==================
USERS = {}  # Example: {user_id: {"plan": "free", "used": 2, "renewal": "2025-11-01"}}

PLANS = {
    "free": {"limit": 5, "label": "🆓 Free Plan"},
    "pro": {"limit": 30, "label": "⚡ Pro Plan"},
    "elite": {"limit": 50, "label": "🚀 Elite Plan"}
}

PAYMENT_LINKS = {
    "pro_monthly": "https://t.me/send?start=IVdixIeFSP3W",
    "pro_yearly": "https://t.me/send?start=IVRnAnXOWzRM",
    "elite_monthly": "https://t.me/send?start=IVfwy1t6hcu9",
    "elite_yearly": "https://t.me/send?start=IVxMW0UNvl7d"
}

# ================== UTILITIES ==================
def get_user(user_id):
    if user_id not in USERS:
        USERS[user_id] = {
            "plan": "free",
            "used": 0,
            "renewal": None
        }
    return USERS[user_id]

async def get_ai_answer(prompt, model="gpt-3.5-turbo"):
    try:
        completion = await openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI Error: {e}"

# ================== COMMANDS ==================
@dp.message(F.text == "/start")
async def start_cmd(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        types.InlineKeyboardButton(text="🆓 Free", callback_data="plan_free"),
        types.InlineKeyboardButton(text="⚡ Pro", callback_data="plan_pro"),
        types.InlineKeyboardButton(text="🚀 Elite", callback_data="plan_elite")
    )
    text = (
        "🤖 **Welcome to AI Tutor Bot!**\n"
        "💡 *Ask Smart. Think Smart.*\n\n"
        "🌎 Your personal AI mentor that teaches you how to think, ask, and win.\n"
        "💼 Business | 🤖 AI | 💰 Crypto\n\n"
        "✨ Free: 5 smart questions lifetime\n"
        "⚡ Pro: 30 questions + faster responses\n"
        "🚀 Elite: 50 questions + full power AI (20% off yearly!)\n\n"
        "🗓 Daily Motivation at 15:00 UTC\n\n"
        "👇 Choose your plan to start your AI journey."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard.as_markup())

@dp.message(F.text == "/upgrade")
async def upgrade_cmd(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        types.InlineKeyboardButton(text="⚡ Pro Monthly – $9.99", url=PAYMENT_LINKS["pro_monthly"]),
        types.InlineKeyboardButton(text="⚡ Pro Yearly – $99.99 (20% off)", url=PAYMENT_LINKS["pro_yearly"])
    )
    keyboard.row(
        types.InlineKeyboardButton(text="🚀 Elite Monthly – $19.99", url=PAYMENT_LINKS["elite_monthly"]),
        types.InlineKeyboardButton(text="🚀 Elite Yearly – $199.99 (20% off)", url=PAYMENT_LINKS["elite_yearly"])
    )
    await message.answer(
        "💎 **Upgrade Your AI Power!**\n\n"
        "⚡ Pro → 30 smart questions + faster AI\n"
        "🚀 Elite → 50 questions + full AI + priority support\n\n"
        "🔥 Yearly plans save 20%!\n\n"
        "Choose your upgrade below 👇",
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

@dp.message(F.text == "/status")
async def status_cmd(message: types.Message):
    user = get_user(message.from_user.id)
    plan_info = PLANS[user["plan"]]
    remaining = max(0, plan_info["limit"] - user["used"])
    text = (
        f"📊 **Your AI Tutor Status**\n\n"
        f"👤 Plan: {plan_info['label']}\n"
        f"❓ Questions used: {user['used']} / {plan_info['limit']}\n"
        f"⏳ Remaining: {remaining}\n"
        f"📅 Renewal: {user['renewal'] or 'N/A'}\n\n"
        f"💬 You can always type your own question!"
    )
    await message.answer(text, parse_mode="Markdown")

# ================== BUTTON FLOWS ==================
@dp.callback_query(F.data.startswith("plan_"))
async def plan_choice(callback: types.CallbackQuery):
    plan = callback.data.split("_")[1]
    get_user(callback.from_user.id)["plan"] = plan

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        types.InlineKeyboardButton(text="💼 Business", callback_data=f"cat_{plan}_business"),
        types.InlineKeyboardButton(text="🤖 AI", callback_data=f"cat_{plan}_ai"),
        types.InlineKeyboardButton(text="💰 Crypto", callback_data=f"cat_{plan}_crypto")
    )
    keyboard.row(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_start"))
    await callback.message.answer(
        f"🎯 You chose {PLANS[plan]['label']}.\nSelect your learning path 👇",
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data.startswith("cat_"))
async def category_choice(callback: types.CallbackQuery):
    _, plan, category = callback.data.split("_")
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        types.InlineKeyboardButton(text="🌱 Starter", callback_data=f"level_{plan}_{category}_starter"),
        types.InlineKeyboardButton(text="💼 Profit", callback_data=f"level_{plan}_{category}_profit")
    )
    keyboard.row(types.InlineKeyboardButton(text="🔙 Back", callback_data=f"plan_{plan}"))
    await callback.message.answer(
        f"📘 {category.capitalize()} – Choose your level 👇",
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data.startswith("level_"))
async def level_choice(callback: types.CallbackQuery):
    _, plan, category, level = callback.data.split("_")
    user = get_user(callback.from_user.id)
    keyboard = InlineKeyboardBuilder()

    if user["plan"] == "free" and plan != "free":
        await callback.message.answer("🔒 Upgrade required for this plan. Type /upgrade to unlock!")
        return

    for q in PROMPTS.get(category, {}).get(level, [])[:PLANS[plan]["limit"]]:
        keyboard.row(types.InlineKeyboardButton(text=q[:40], callback_data=f"ask_{category}_{q[:10]}"))

    keyboard.row(types.InlineKeyboardButton(text="🔙 Back", callback_data=f"cat_{plan}_{category}"))
    await callback.message.answer(f"🧠 {category.capitalize()} – {level.capitalize()} Questions:", reply_markup=keyboard.as_markup())

# ================== AI ANSWERS ==================
@dp.callback_query(F.data.startswith("ask_"))
async def ask_ai(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    plan_info = PLANS[user["plan"]]

    if user["used"] >= plan_info["limit"]:
        await callback.message.answer("🔒 Limit reached! Type /upgrade to unlock more.")
        return

    question = callback.data.split("_", 2)[2]
    await callback.message.answer("🤖 Thinking...")
    reply = await get_ai_answer(question)
    user["used"] += 1
    await callback.message.answer(reply)

# ================== DAILY QUOTES ==================
async def send_daily_quotes():
    quotes = [
        "🚀 You’re one decision away from success.",
        "🔥 Consistency beats talent every day.",
        "💡 One smart question can change your life.",
        "🌍 Think like a CEO, act with purpose.",
        "🧠 Smart thoughts create smart futures."
    ]
    while True:
        try:
            for uid in USERS.keys():
                await bot.send_message(uid, random.choice(quotes))
            await asyncio.sleep(24 * 60 * 60)
        except Exception as e:
            logging.error(f"Quote error: {e}")
            await asyncio.sleep(60)

# ================== HEALTH CHECK ==================
async def health(request):
    return web.Response(text="AI Tutor Bot is alive ✅", status=200)

# ================== STARTUP ==================
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_daily_quotes())

async def on_shutdown(app):
    await bot.delete_webhook()

# ================== MAIN ==================
def main():
    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")
    app.router.add_get("/", health)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()

