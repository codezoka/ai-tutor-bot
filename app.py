import os
import json
import asyncio
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.storage.memory import MemoryStorage
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 🧠 Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://ai-tutor-bot-83opf.ondigitalocean.app/webhook")

# 🧩 Initialize clients
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# 🧰 Load Prompts & Quotes
def load_json_file(filename, fallback):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return fallback

PROMPTS = load_json_file("prompts.json", {})
QUOTES = load_json_file("motivational_quotes.json", {
    "quotes": ["Dream big, work smart, and stay humble."]
})["quotes"]

# 🧍 User state (in-memory)
USERS = {}

# 💬 Start command
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    USERS[user_id] = USERS.get(user_id, {"plan": "free", "used": 0})
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Free Plan", callback_data="plan_free")],
        [InlineKeyboardButton(text="⚡ Pro Plan", callback_data="plan_pro")],
        [InlineKeyboardButton(text="💎 Elite Plan", callback_data="plan_elite")]
    ])
    await message.answer(
        "🤖 <b>Welcome to AI Tutor Bot</b>\n\n"
        "🚀 Learn, grow, and succeed with smart questions and AI-powered insights.\n"
        "💡 Choose your plan to start asking smart questions today!",
        reply_markup=kb,
        parse_mode="HTML"
    )

# 🆘 Help command
@dp.message(F.text == "/help")
async def cmd_help(message: Message):
    await message.answer(
        "📚 <b>How to use AI Tutor Bot</b>\n\n"
        "🟢 <b>/start</b> – Choose your plan (Free, Pro, Elite)\n"
        "💬 <b>/questions</b> – Access smart questions by category\n"
        "💳 <b>/upgrade</b> – Upgrade your plan with CryptoBot\n"
        "📊 <b>/status</b> – View your current plan and usage\n\n"
        "✨ You can also ask your own question anytime!",
        parse_mode="HTML"
    )
# 💳 Upgrade command
@dp.message(F.text == "/upgrade")
async def cmd_upgrade(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ Pro Monthly – $9.99", url="https://t.me/send?start=IVdixIeFSP3W")
        ],
        [
            InlineKeyboardButton(text="⚡ Pro Yearly – $99.99 (Save 20%)", url="https://t.me/send?start=IVRnAnXOWzRM")
        ],
        [
            InlineKeyboardButton(text="💎 Elite Monthly – $19.99", url="https://t.me/send?start=IVfwy1t6hcu9")
        ],
        [
            InlineKeyboardButton(text="💎 Elite Yearly – $199.99 (Save 20%)", url="https://t.me/send?start=IVxMW0UNvl7d")
        ]
    ])
    await message.answer(
        "💳 <b>Upgrade your plan today!</b>\n\n"
        "🚀 <b>Pro:</b> Faster AI + 15 Smart Questions per category.\n"
        "💎 <b>Elite:</b> Full Power AI + 25 Smart Questions per category.\n\n"
        "Select your payment option below 👇",
        reply_markup=kb,
        parse_mode="HTML"
    )

# 📊 Status command
@dp.message(F.text == "/status")
async def cmd_status(message: Message):
    user = USERS.get(message.from_user.id, {"plan": "free", "used": 0})
    plan = user["plan"].capitalize()
    used = user["used"]
    await message.answer(
        f"📊 <b>Your Plan:</b> {plan}\n"
        f"💬 <b>Questions Used:</b> {used}/5\n"
        "⏰ Free users can upgrade anytime for faster, unlimited access.",
        parse_mode="HTML"
    )

# 🧭 Choose plan buttons
@dp.callback_query(F.data.startswith("plan_"))
async def cb_choose_plan(callback: CallbackQuery):
    user_id = callback.from_user.id
    plan = callback.data.split("_")[1]
    USERS[user_id]["plan"] = plan

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 AI", callback_data=f"cat_ai_{plan}")],
        [InlineKeyboardButton(text="💼 Business", callback_data=f"cat_business_{plan}")],
        [InlineKeyboardButton(text="🪙 Crypto", callback_data=f"cat_crypto_{plan}")],
        [InlineKeyboardButton(text="⬅ Back", callback_data="back_start")]
    ])

    await callback.message.edit_text(
        f"📂 You selected the <b>{plan.capitalize()}</b> plan.\n"
        f"Now choose your category 👇",
        reply_markup=kb,
        parse_mode="HTML"
    )

# 🧩 Category handler
@dp.callback_query(F.data.startswith("cat_"))
async def cb_category(callback: CallbackQuery):
    _, category, plan = callback.data.split("_")

    # For free plan — limit usage
    if plan == "free" and USERS[callback.from_user.id]["used"] >= 5:
        await callback.message.edit_text(
            "🚫 You’ve reached your 5 free smart questions.\n"
            "Upgrade to unlock more 👉 /upgrade"
        )
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Starter", callback_data=f"level_{category}_{plan}_starter")],
        [InlineKeyboardButton(text="🚀 Profit", callback_data=f"level_{category}_{plan}_profit")],
        [InlineKeyboardButton(text="⬅ Back", callback_data="back_plans")]
    ])

    await callback.message.edit_text(
        f"📘 Choose your focus level for {category.capitalize()} 👇",
        reply_markup=kb
    )

# 🎯 Level (starter/profit)
@dp.callback_query(F.data.startswith("level_"))
async def cb_level(callback: CallbackQuery):
    _, category, plan, level = callback.data.split("_")
    questions = PROMPTS.get(category, {}).get(plan, {}).get(level, [])

    if not questions:
        await callback.message.edit_text("⚠️ No questions found for this section.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=q[:50], callback_data=f"ask_{category}_{plan}_{level}_{i}")]
        for i, q in enumerate(questions)
    ] + [[InlineKeyboardButton(text="⬅ Back", callback_data=f"cat_{category}_{plan}")]])

    await callback.message.edit_text(
        f"🧠 {category.capitalize()} – {level.capitalize()} Smart Questions 👇",
        reply_markup=kb
    )

# 💬 Ask AI when clicking a question
@dp.callback_query(F.data.startswith("ask_"))
async def cb_ask(callback: CallbackQuery):
    _, category, plan, level, index = callback.data.split("_")
    index = int(index)
    questions = PROMPTS.get(category, {}).get(plan, {}).get(level, [])
    question = questions[index]

    user_id = callback.from_user.id
    user = USERS.get(user_id, {"plan": "free", "used": 0})

    if user["plan"] == "free":
        if user["used"] >= 5:
            await callback.message.edit_text("🚫 Free limit reached. Upgrade 👉 /upgrade")
            return
        user["used"] += 1
        USERS[user_id] = user

    await callback.message.answer("🤖 Thinking...")
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question}],
        )
        answer = response.choices[0].message.content
        await callback.message.answer(f"🧠 <b>Q:</b> {question}\n\n💬 <b>A:</b> {answer}", parse_mode="HTML")
    except Exception as e:
        await callback.message.answer(f"❌ Error: {str(e)}")
# 🌞 Daily motivational message (15:00 UTC)
async def send_daily_quotes():
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        wait_time = (target - now).total_seconds()
        await asyncio.sleep(wait_time)

        for user_id in USERS.keys():
            quote = QUOTES[(now.day + now.month) % len(QUOTES)]
            try:
                await bot.send_message(
                    user_id,
                    f"💡 <b>Daily Motivation:</b>\n\n{quote}\n\n🚀 Keep learning and growing!",
                    parse_mode="HTML"
                )
            except:
                continue

# 🩺 Health check route
async def health_check(request):
    return web.Response(text="OK", content_type="text/plain")

# 🚀 Webhook startup/shutdown handlers
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook set to {WEBHOOK_URL}")

    # Start daily quote task
    app['daily_task'] = asyncio.create_task(send_daily_quotes())

async def on_shutdown(app):
    await bot.delete_webhook()
    app['daily_task'].cancel()
    print("🛑 Webhook removed, bot shutting down.")

# 🌐 Webhook app setup
def main():
    app = web.Application()
    dp.include_router(dp)

    app.router.add_get("/", health_check)  # ✅ Health check for DigitalOcean
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    setup_application(app, dp, bot=bot)

    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()

