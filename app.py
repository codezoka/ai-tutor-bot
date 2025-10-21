import os
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from openai import AsyncOpenAI
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# === CryptoBot Payment Links ===
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

# Initialize API clients
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# === User Database (in-memory for now) ===
users = {}

# === Helper: load prompts ===
with open("prompts.json", "r", encoding="utf-8") as f:
    prompts = json.load(f)

# === Helper: Create upgrade keyboard ===
def get_upgrade_keyboard():
    keyboard = [
        [InlineKeyboardButton("💎 Pro Monthly – $9.99", url=PRO_MONTHLY_URL)],
        [InlineKeyboardButton("💎 Pro Yearly – $99.99 (20% OFF)", url=PRO_YEARLY_URL)],
        [InlineKeyboardButton("🚀 Elite Monthly – $19.99", url=ELITE_MONTHLY_URL)],
        [InlineKeyboardButton("🚀 Elite Yearly – $199.99 (20% OFF)", url=ELITE_YEARLY_URL)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# === Helper: Create motivational message ===
def get_daily_motivation():
    quotes = [
        "💡 Every question you ask is a step toward success.",
        "🚀 Smart thinking turns small ideas into big wins!",
        "🔥 Great minds ask, learn, and act.",
        "💬 Don’t wait for opportunity — create it.",
        "🎯 Focus on progress, not perfection.",
    ]
    return quotes[datetime.utcnow().day % len(quotes)]

# === Helper: Initialize user ===
def init_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "plan": "free",
            "remaining_questions": 5,
            "renewal": (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d"),
        }

# === START Command ===
@dp.message(commands=["start"])
async def start_command(message: types.Message):
    init_user(message.from_user.id)
    text = (
        "🤖 *Welcome to AI Tutor Pro Bot!*\n\n"
        "💡 Ask Smart. Think Smart.\n"
        "✨ Let’s turn *intelligence into freedom*.\n\n"
        "Choose your path to unlock full AI power 👇"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🆓 Free Plan", callback_data="plan_free")],
        [InlineKeyboardButton("💎 Pro Plan", callback_data="plan_pro")],
        [InlineKeyboardButton("🚀 Elite Plan", callback_data="plan_elite")]
    ])
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

# === HELP Command ===
@dp.message(commands=["help"])
async def help_command(message: types.Message):
    text = (
        "💬 *How to use AI Tutor Pro Bot*\n\n"
        "• `/start` – Begin your journey and choose your plan.\n"
        "• `/questions` – Explore Smart Questions in AI, Business, or Crypto.\n"
        "• `/upgrade` – Unlock faster responses and premium insights.\n"
        "• `/status` – View your plan, renewal date, and remaining questions.\n\n"
        "🧠 You can *always* type your own question to chat directly with AI!"
    )
    await message.answer(text, parse_mode="Markdown")

# === STATUS Command ===
@dp.message(commands=["status"])
async def status_command(message: types.Message):
    init_user(message.from_user.id)
    user = users[message.from_user.id]
    plan = user["plan"].capitalize()
    remain = user["remaining_questions"]
    renewal = user["renewal"]
    motivation = get_daily_motivation()

    text = (
        f"📊 *Your Current Plan:* {plan}\n"
        f"💭 *Remaining Questions:* {remain}\n"
        f"📅 *Renewal Date:* {renewal}\n\n"
        f"{motivation}\n\n"
        "⬆️ [Upgrade here for more power!](https://t.me/send?start=IVdixIeFSP3W)"
    )
    await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

# === Placeholder for payment verification ===
def verify_payment(user_id, plan_name):
    """
    🔒 Placeholder for payment confirmation.
    In future: connect CryptoBot API here to confirm actual payment.
    """
    # Currently simulates check based on user's stored plan
    return users.get(user_id, {}).get("plan") == plan_name
# === PLAN HANDLERS ===
@dp.callback_query(lambda c: c.data.startswith("plan_"))
async def handle_plan(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    init_user(user_id)
    plan = callback.data.split("_")[1]
    users[user_id]["selected_plan"] = plan

    if plan == "free":
        await callback.message.edit_text(
            "🆓 You’re on the *Free Plan* — 5 Smart Questions total.\n"
            "💭 You can always type your own questions too!\n\n"
            "Choose your category 👇",
            parse_mode="Markdown",
            reply_markup=get_category_keyboard(plan)
        )
    elif plan in ["pro", "elite"]:
        if verify_payment(user_id, plan):
            await callback.message.edit_text(
                f"✅ Welcome back, *{plan.capitalize()} Member!* 💎\n\n"
                "Choose your category 👇",
                parse_mode="Markdown",
                reply_markup=get_category_keyboard(plan)
            )
        else:
            await callback.message.edit_text(
                f"🔒 You haven’t unlocked *{plan.capitalize()} Plan* yet.\n"
                "Click below to upgrade and access all Smart Questions 👇",
                parse_mode="Markdown",
                reply_markup=get_upgrade_keyboard()
            )

# === CATEGORY KEYBOARD ===
def get_category_keyboard(plan):
    buttons = [
        [InlineKeyboardButton("🤖 AI", callback_data=f"cat_{plan}_ai")],
        [InlineKeyboardButton("💼 Business", callback_data=f"cat_{plan}_business")],
        [InlineKeyboardButton("💰 Crypto", callback_data=f"cat_{plan}_crypto")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_plans")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# === CATEGORY HANDLER ===
@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def handle_category(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    plan, category = parts[1], parts[2]
    keyboard = [
        [InlineKeyboardButton("📘 Starter", callback_data=f"lvl_{plan}_{category}_starter")],
        [InlineKeyboardButton("💼 Profit", callback_data=f"lvl_{plan}_{category}_profit")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"back_to_plans")]
    ]
    await callback.message.edit_text(
        f"📚 *{category.capitalize()}* — choose your learning level:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

# === LEVEL HANDLER ===
@dp.callback_query(lambda c: c.data.startswith("lvl_"))
async def handle_level(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    plan, category, level = parts[1], parts[2], parts[3]
    user_id = callback.from_user.id
    user = users[user_id]

    # Restrict unpaid access
    if plan != user["plan"]:
        await callback.message.edit_text(
            "🔒 This section is locked.\nUpgrade to unlock all Smart Questions 👇",
            parse_mode="Markdown",
            reply_markup=get_upgrade_keyboard()
        )
        return

    # Load questions
    try:
        qlist = prompts[plan][category][level]
    except KeyError:
        await callback.message.edit_text("❌ Questions not found for this category.")
        return

    # Show clickable questions
    keyboard = []
    for idx, q in enumerate(qlist, start=1):
        keyboard.append([InlineKeyboardButton(f"{idx}. {q[:40]}", callback_data=f"q_{plan}_{category}_{level}_{idx}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=f"cat_{plan}_{category}")])

    await callback.message.edit_text(
        f"💡 Choose a Smart Question from {category.capitalize()} ({level.capitalize()}) 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

# === QUESTION HANDLER ===
@dp.callback_query(lambda c: c.data.startswith("q_"))
async def handle_question(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    plan, category, level, q_index = parts[1], parts[2], parts[3], int(parts[4])
    user_id = callback.from_user.id
    user = users[user_id]

    # Restrict usage if limit reached
    if user["remaining_questions"] <= 0 and plan == "free":
        await callback.message.edit_text(
            "⚠️ You’ve reached your Free Plan question limit.\n"
            "Upgrade for unlimited Smart Questions 🚀",
            parse_mode="Markdown",
            reply_markup=get_upgrade_keyboard()
        )
        return

    question = prompts[plan][category][level][q_index - 1]
    await callback.message.edit_text(f"🤔 *{question}*\n\nThinking...", parse_mode="Markdown")

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini" if plan == "free" else "gpt-4o",
            messages=[{"role": "user", "content": question}],
        )
        ai_answer = response.choices[0].message.content
        await callback.message.answer(f"💬 {ai_answer}")

        if plan == "free":
            user["remaining_questions"] -= 1
    except Exception as e:
        await callback.message.answer(f"❌ Error: {e}")

# === BACK HANDLERS ===
@dp.callback_query(lambda c: c.data == "back_to_plans")
async def back_to_plans(callback: types.CallbackQuery):
    text = (
        "🤖 *Choose your plan again:*\n"
        "🆓 Free • 💎 Pro • 🚀 Elite\n\n"
        "Pick the one that fits your goals 👇"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🆓 Free Plan", callback_data="plan_free")],
        [InlineKeyboardButton("💎 Pro Plan", callback_data="plan_pro")],
        [InlineKeyboardButton("🚀 Elite Plan", callback_data="plan_elite")]
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
# === UPGRADE Command ===
@dp.message(commands=["upgrade"])
async def upgrade_command(message: types.Message):
    text = (
        "💎 *Upgrade Your Plan*\n\n"
        "🚀 Unlock faster AI responses, deeper insights & unlimited Smart Questions!\n\n"
        "• *Pro Plan* – $9.99/mo or $99.99/yr (20% OFF)\n"
        "• *Elite Plan* – $19.99/mo or $199.99/yr (20% OFF)\n\n"
        "After payment, you’ll automatically unlock your premium access.\n\n"
        "👇 Choose your plan to upgrade now:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_upgrade_keyboard())

# === DAILY MOTIVATIONAL QUOTE SENDER (15:00 UTC) ===
async def send_daily_quotes():
    while True:
        now = datetime.utcnow()
        # Schedule for 15:00 UTC daily
        target = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        wait = (target - now).total_seconds()
        await asyncio.sleep(wait)

        quote = get_daily_motivation()
        for user_id in users.keys():
            try:
                await bot.send_message(user_id, f"🌟 *Daily Motivation:*\n\n{quote}", parse_mode="Markdown")
            except Exception:
                continue

# === AIOHTTP WEBHOOK SETUP ===
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_daily_quotes())

async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()


