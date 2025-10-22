import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import AsyncOpenAI
from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties

# ===== Load Environment Variables =====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

# CryptoBot links
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

# ===== Initialize Bot =====
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ===== Load Smart Questions =====
with open("prompts.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# ===== Load Motivational Quotes =====
with open("motivational_quotes.json", "r", encoding="utf-8") as f:
    MOTIVATIONAL_QUOTES = json.load(f)

# ===== Simple In-Memory User Tracking =====
USERS = {}  # {user_id: {"plan": "free", "used": 0, "renewal": "2025-11-01"}}

# ===== Helper Keyboards =====
def get_plan_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Free", callback_data="plan_free")],
        [InlineKeyboardButton(text="⚡ Pro (Fast AI, Unlimited Access)", callback_data="plan_pro")],
        [InlineKeyboardButton(text="🚀 Elite (Full Power AI, Instant Results)", callback_data="plan_elite")]
    ])

def get_category_keyboard(plan):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Business", callback_data=f"{plan}_business")],
        [InlineKeyboardButton(text="🤖 AI", callback_data=f"{plan}_ai")],
        [InlineKeyboardButton(text="💰 Crypto", callback_data=f"{plan}_crypto")],
        [InlineKeyboardButton(text="⬅ Back", callback_data="back_to_plans")]
    ])

def get_level_keyboard(plan, category):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌱 Starter", callback_data=f"{plan}_{category}_starter")],
        [InlineKeyboardButton(text="💼 Profit", callback_data=f"{plan}_{category}_profit")],
        [InlineKeyboardButton(text="⬅ Back", callback_data=f"back_to_{plan}")]
    ])

def get_upgrade_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Pro — $9.99/mo", url=PRO_MONTHLY_URL)],
        [InlineKeyboardButton(text="⚡ Pro — $99.99/year (Save 20%)", url=PRO_YEARLY_URL)],
        [InlineKeyboardButton(text="🚀 Elite — $19.99/mo", url=ELITE_MONTHLY_URL)],
        [InlineKeyboardButton(text="🚀 Elite — $199.99/year (Save 20%)", url=ELITE_YEARLY_URL)],
        [InlineKeyboardButton(text="⬅ Back to Menu", callback_data="back_to_menu")]
    ])

# ===== Commands =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    USERS.setdefault(message.from_user.id, {"plan": "free", "used": 0})
    text = (
        "🤖 <b>Welcome to AI Tutor Bot – Ask Like the 1%!</b>\n\n"
        "🚀 Ask like a CEO or expert — and get results that move you forward.\n\n"
        "💡 Learn faster in the world’s most powerful topics:\n"
        "🧠 <b>AI & Innovation</b> – Master cutting-edge tools\n"
        "💼 <b>Business</b> – Build smarter and scale faster\n"
        "💰 <b>Crypto</b> – Profit from tomorrow’s opportunities\n\n"
        "🔥 Choose your plan below and start asking questions that successful people ask!"
    )
    await message.answer(text, reply_markup=get_plan_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "🧭 <b>How to use AI Tutor Bot:</b>\n\n"
        "🧠 <b>/start</b> – Begin and choose your plan\n"
        "💬 <b>/questions</b> – Explore ready smart questions\n"
        "⚙️ <b>/upgrade</b> – Unlock Pro or Elite for full access\n"
        "📊 <b>/status</b> – View your plan and usage\n\n"
        "💡 You can also type your own question anytime!"
    )
    await message.answer(text)

@dp.message(Command("upgrade"))
async def cmd_upgrade(message: types.Message):
    text = (
        "🚀 <b>Upgrade Now!</b>\n\n"
        "⚡ <b>Pro:</b> Faster answers + 15 smart questions per category.\n"
        "💎 <b>Elite:</b> 25 premium questions per category + full power AI.\n\n"
        "💥 Don’t limit your growth — upgrade today and unlock your potential!"
    )
    await message.answer(text, reply_markup=get_upgrade_keyboard())

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    user = USERS.get(message.from_user.id, {"plan": "free", "used": 0})
    plan = user["plan"]
    used = user.get("used", 0)
    remaining = max(0, 5 - used)
    if plan == "free":
        text = (
            f"🆓 <b>Your Plan:</b> Free\n"
            f"❓ Questions used: {used}/5\n"
            "💬 You can still type your own questions.\n"
            "✨ Upgrade for faster and unlimited answers!"
        )
    else:
        renewal = user.get("renewal", "Next month")
        text = (
            f"💎 <b>Your Plan:</b> {plan.title()}\n"
            f"🔁 Renewal: {renewal}\n"
            "⚡ Enjoy unlimited smart questions & instant AI chat!"
        )
    await message.answer(text)

@dp.message(Command("questions"))
async def cmd_questions(message: types.Message):
    await message.answer("🧠 Choose your plan:", reply_markup=get_plan_keyboard())

# ====== Callback Handlers ======
@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    user = USERS.setdefault(user_id, {"plan": "free", "used": 0})

    if data.startswith("plan_"):
        plan = data.split("_")[1]
        if plan in ["free", "pro", "elite"]:
            await callback.message.edit_text(
                f"📚 <b>{plan.title()} Plan Selected!</b>\nChoose a category:",
                reply_markup=get_category_keyboard(plan)
            )
        return

    # Back buttons
    if data == "back_to_plans":
        await callback.message.edit_text("Choose your plan:", reply_markup=get_plan_keyboard())
        return
    if data.startswith("back_to_"):
        plan = data.split("_")[2]
        await callback.message.edit_text("Choose a category:", reply_markup=get_category_keyboard(plan))
        return

    # Category → Levels
    for plan in ["free", "pro", "elite"]:
        for cat in ["business", "ai", "crypto"]:
            if data == f"{plan}_{cat}":
                if plan != "free" and user["plan"] == "free":
                    await callback.message.edit_text(
                        "🔒 This section is locked. Upgrade to unlock premium content!",
                        reply_markup=get_upgrade_keyboard()
                    )
                    return
                await callback.message.edit_text(
                    f"📂 {cat.title()} – Choose Level:",
                    reply_markup=get_level_keyboard(plan, cat)
                )
                return

    # Levels → Questions
    for plan in ["free", "pro", "elite"]:
        for cat in ["business", "ai", "crypto"]:
            for level in ["starter", "profit"]:
                if data == f"{plan}_{cat}_{level}":
                    questions = QUESTIONS[cat][plan][level]  # ✅ fixed index order
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=q[:70], callback_data=f"ask_{q}")] for q in questions
                    ] + [[InlineKeyboardButton(text="⬅ Back", callback_data=f"{plan}_{cat}")]])
                    await callback.message.edit_text(
                        f"💬 {cat.title()} – {level.title()} Questions:",
                        reply_markup=keyboard
                    )
                    return

    # Ask AI
    if data.startswith("ask_"):
        question = data.replace("ask_", "")
        user = USERS.get(user_id)
        plan = user.get("plan", "free")
        if plan == "free":
            if user["used"] >= 5:
                await callback.message.answer(
                    "⚠️ You’ve reached your 5-question limit.\nUpgrade for unlimited access and faster answers!",
                    reply_markup=get_upgrade_keyboard())
                return
            USERS[user_id]["used"] += 1

        await callback.message.answer("🤖 Thinking...")
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": question}]
            )
            await callback.message.answer(response.choices[0].message.content)
        except Exception as e:
            await callback.message.answer(f"❌ Error: {e}")

# ===== User Messages =====
@dp.message()
async def handle_user_message(message: types.Message):
    text = message.text.strip()
    if not text:
        return
    await message.answer("🤖 Thinking...")
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": text}]
        )
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

# ===== Motivational Quotes Rotation =====
async def send_daily_quote():
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        quote = random.choice(MOTIVATIONAL_QUOTES)
        for user_id in USERS.keys():
            await bot.send_message(user_id, quote)

# ===== Health Check =====
async def handle_health(request):
    return web.Response(text="OK")

# ===== Main Setup =====
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_daily_quote())

def main():
    app = web.Application()
    app.router.add_get("/", handle_health)
    dp.startup.register(on_startup)
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/")
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()

