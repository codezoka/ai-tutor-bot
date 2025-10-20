import os
import json
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
import openai
import datetime
import random

# --------------------- LOAD ENVIRONMENT VARIABLES ---------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("❌ BOT_TOKEN or OPENAI_API_KEY not set in environment variables")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
openai.api_key = OPENAI_API_KEY

# --------------------- WEBHOOK CONFIG ---------------------
WEBHOOK_URL = "https://ai-tutor-bot-83opf.ondigitalocean.app/webhook"

# --------------------- LOGGING ---------------------
logging.basicConfig(level=logging.INFO)

# --------------------- LOAD PROMPTS ---------------------
def load_prompts():
    try:
        with open("prompts.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading prompts: {e}")
        return {}

PROMPTS = load_prompts()

# --------------------- SUBSCRIPTION PLANS ---------------------
PLANS = {
    "free": {"limit": 5, "label": "🆓 Free Plan"},
    "pro": {"limit": 30, "label": "⚡ Pro Plan"},
    "elite": {"limit": 50, "label": "🚀 Elite Plan"}
}

# Payment Links
PAYMENT_LINKS = {
    "pro_monthly": "https://t.me/send?start=IVdixIeFSP3W",
    "pro_yearly": "https://t.me/send?start=IVRnAnXOWzRM",
    "elite_monthly": "https://t.me/send?start=IVfwy1t6hcu9",
    "elite_yearly": "https://t.me/send?start=IVxMW0UNvl7d"
}

# --------------------- USER DATABASE ---------------------
USERS = {}

def get_user_plan(user_id):
    return USERS.get(user_id, {"plan": "free", "used": 0})

# --------------------- START COMMAND ---------------------
@dp.message(F.text == "/start")
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        types.InlineKeyboardButton(text="🆓 Free Plan", callback_data="plan_free"),
        types.InlineKeyboardButton(text="⚡ Pro Plan", callback_data="plan_pro"),
        types.InlineKeyboardButton(text="🚀 Elite Plan", callback_data="plan_elite")
    )
    text = (
        "🤖 **AI Tutor Bot – Ask Smart, Think Smart**\n\n"
        "Welcome! I’m your AI tutor that helps you ask **smarter questions** "
        "in **Business**, **AI**, and **Crypto** to think like a CEO.\n\n"
        "✨ Free plan: 5 smart questions total.\n"
        "⚡ Pro = faster responses + 30 questions.\n"
        "🚀 Elite = fastest AI + 50 questions + priority support.\n\n"
        "Ready? Choose your plan below 👇"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard.as_markup())

# --------------------- UPGRADE COMMAND ---------------------
@dp.message(F.text == "/upgrade")
async def upgrade_handler(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        types.InlineKeyboardButton(text="⚡ Pro Monthly – $9.99", url=PAYMENT_LINKS["pro_monthly"]),
        types.InlineKeyboardButton(text="⚡ Pro Yearly – $99.99 (20% off)", url=PAYMENT_LINKS["pro_yearly"])
    )
    keyboard.row(
        types.InlineKeyboardButton(text="🚀 Elite Monthly – $19.99", url=PAYMENT_LINKS["elite_monthly"]),
        types.InlineKeyboardButton(text="🚀 Elite Yearly – $199.99 (20% off)", url=PAYMENT_LINKS["elite_yearly"])
    )
    text = (
        "💎 **Upgrade Your AI Tutor Experience**\n\n"
        "⚡ Pro Plan – $9.99/mo or $99.99/yr (20% off)\n"
        "– Faster AI responses + 30 smart questions.\n\n"
        "🚀 Elite Plan – $19.99/mo or $199.99/yr (20% off)\n"
        "– Fastest AI + 50 smart questions + priority support.\n\n"
        "Choose your plan below 👇"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard.as_markup())

# --------------------- QUESTIONS COMMAND ---------------------
@dp.message(F.text == "/questions")
async def questions_handler(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        types.InlineKeyboardButton(text="💼 Business", callback_data="cat_business"),
        types.InlineKeyboardButton(text="🤖 AI", callback_data="cat_ai"),
        types.InlineKeyboardButton(text="💰 Crypto", callback_data="cat_crypto")
    )
    await message.answer("📚 Choose a category below:", reply_markup=keyboard.as_markup())

# --------------------- CATEGORY HANDLERS ---------------------
@dp.callback_query(F.data.startswith("cat_"))
async def category_handler(callback: types.CallbackQuery):
    category = callback.data.split("_")[1]
    plan = get_user_plan(callback.from_user.id)["plan"]
    keyboard = InlineKeyboardBuilder()

    if category in PROMPTS:
        for question in PROMPTS[category].get("starter", []):
            keyboard.row(types.InlineKeyboardButton(text=question[:40], callback_data=f"ask_{category}_{question[:10]}"))

        await callback.message.answer(
            f"📘 {category.capitalize()} – Smart Questions for {plan.capitalize()} plan:\nChoose one below 👇",
            reply_markup=keyboard.as_markup()
        )
    else:
        await callback.message.answer("⚠️ Category not available.")

# --------------------- AI RESPONSE ---------------------
async def get_ai_answer(question):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": question}],
        max_tokens=300
    )
    return response.choices[0].message["content"]

# --------------------- CALLBACK HANDLER ---------------------
@dp.callback_query(F.data.startswith("ask_"))
async def smart_question_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user_plan(user_id)
    plan_info = PLANS[user["plan"]]

    if user["used"] >= plan_info["limit"]:
        await callback.message.answer("🔒 You've reached your question limit. Type /upgrade to unlock more!")
        return

    question = callback.data.split("_", 2)[2]
    await callback.message.answer("🤖 Thinking...")
    ai_answer = await get_ai_answer(question)
    USERS[user_id] = {"plan": user["plan"], "used": user["used"] + 1}
    await callback.message.answer(ai_answer)

# --------------------- HEALTH CHECK ---------------------
async def health_check(request):
    return web.Response(text="AI Tutor Bot alive and healthy!", status=200)

# --------------------- SCHEDULER (DAILY MOTIVATIONAL QUOTES) ---------------------
async def send_daily_quotes():
    quotes = [
        "💪 Keep pushing — success is closer than you think!",
        "🚀 Smart thinking creates smart results.",
        "🔥 You’re one great idea away from success!",
        "🧠 Every question you ask builds your future.",
        "🌟 CEOs aren’t born — they learn by asking better questions."
    ]
    while True:
        try:
            all_users = list(USERS.keys())
            if all_users:
                quote = random.choice(quotes)
                for uid in all_users:
                    await bot.send_message(uid, quote)
            await asyncio.sleep(24 * 60 * 60)  # every 24h
        except Exception as e:
            logging.error(f"Daily quote error: {e}")
            await asyncio.sleep(60)

# --------------------- WEBHOOK SETUP ---------------------
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_daily_quotes())

async def on_shutdown(app):
    await bot.delete_webhook()

# --------------------- MAIN APP ---------------------
def main():
    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")
    app.router.add_get("/", health_check)  # ✅ Health Check for DigitalOcean
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()

