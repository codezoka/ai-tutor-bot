import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from openai import AsyncOpenAI

# === Load Environment Variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# === User Data ===
users = {}

def init_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "plan": "free",
            "remaining_questions": 5,
            "selected_plan": None,
            "last_reset": datetime.utcnow(),
        }

# === Load Prompts ===
try:
    with open("prompts.json", "r", encoding="utf-8") as f:
        prompts = json.load(f)
except Exception as e:
    print("Error loading prompts:", e)
    prompts = {}

# === Upgrade Links (CryptoBot URLs) ===
PAYMENT_LINKS = {
    "pro_monthly": "https://t.me/send?start=IVdixIeFSP3W",
    "pro_yearly": "https://t.me/send?start=IVRnAnXOWzRM",
    "elite_monthly": "https://t.me/send?start=IVfwy1t6hcu9",
    "elite_yearly": "https://t.me/send?start=IVxMW0UNvl7d"
}

# === Upgrade Keyboard ===
def get_upgrade_keyboard():
    buttons = [
        [
            InlineKeyboardButton("⚡ Pro Monthly – $9.99", url=PAYMENT_LINKS["pro_monthly"]),
            InlineKeyboardButton("⚡ Pro Yearly – $99.99", url=PAYMENT_LINKS["pro_yearly"]),
        ],
        [
            InlineKeyboardButton("🚀 Elite Monthly – $19.99", url=PAYMENT_LINKS["elite_monthly"]),
            InlineKeyboardButton("🚀 Elite Yearly – $199.99", url=PAYMENT_LINKS["elite_yearly"]),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_plans")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# === Payment Verification Stub ===
def verify_payment(user_id, plan):
    # Placeholder: Replace this with real payment verification later
    # You can call CryptoBot API here in the future
    return False

# === Motivation Quotes ===
MOTIVATION_QUOTES = [
    "Dream big. Start small. Act now. 💪",
    "Every CEO was once a beginner. Keep moving. 🚀",
    "Discipline beats motivation — daily actions build freedom. 🔥",
    "Your ideas can change your life. Ask smart questions. 💡",
    "Freedom starts with clarity and bold action. 💎",
]

def get_daily_motivation():
    return random.choice(MOTIVATION_QUOTES)

# === Start Command ===
@dp.message(Command("start"))
async def start(message: types.Message):
    init_user(message.from_user.id)
    text = (
        "🤖 *AI Tutor Bot – Ask Smart, Think Smart*\n\n"
        "Welcome! I’m your personal AI tutor helping you ask smarter questions in *Business*, *AI*, and *Crypto*.\n\n"
        "✨ Free Plan – 5 smart questions total\n"
        "⚡ Pro Plan – +30 questions & faster AI\n"
        "🚀 Elite Plan – +50 questions & priority support\n\n"
        "Ready to grow your mind and business? Choose your plan below 👇"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🆓 Free Plan", callback_data="plan_free")],
        [InlineKeyboardButton("⚡ Pro Plan", callback_data="plan_pro")],
        [InlineKeyboardButton("🚀 Elite Plan", callback_data="plan_elite")]
    ])
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

# === Help Command ===
@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    text = (
        "ℹ️ *How to use the AI Tutor Bot:*\n\n"
        "• `/start` – Begin or reset the menu\n"
        "• `/questions` – Explore smart questions by category\n"
        "• `/upgrade` – Unlock Pro or Elite plans\n"
        "• `/status` – View your plan, remaining questions, and renewal\n\n"
        "💬 You can also just type your own question anytime!"
    )
    await message.answer(text, parse_mode="Markdown")

# === Status Command ===
@dp.message(Command("status"))
async def status_cmd(message: types.Message):
    user = users.get(message.from_user.id)
    if not user:
        await message.answer("Please use /start first.")
        return

    plan = user["plan"].capitalize()
    remaining = user["remaining_questions"]
    renewal = user["last_reset"] + timedelta(days=30)
    await message.answer(
        f"💼 *Your Plan:* {plan}\n"
        f"💬 *Remaining Questions:* {remaining}\n"
        f"📅 *Next Renewal:* {renewal.strftime('%d %b %Y')}",
        parse_mode="Markdown"
    )
# === PLAN SELECTION CALLBACK ===
@dp.callback_query(lambda c: c.data.startswith("plan_"))
async def plan_selected(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    init_user(user_id)
    plan = callback.data.split("_")[1]
    user = users[user_id]

    if plan == "free":
        user["plan"] = "free"
        user["remaining_questions"] = 5
        await callback.message.answer(
            "🆓 *You're on the Free Plan!*\nLet's turn intelligence into freedom.\n"
            "Type /questions to begin or tap a category below 👇",
            parse_mode="Markdown",
        )
        await show_categories(callback.message)

    elif plan == "pro":
        if verify_payment(user_id, "pro"):
            user["plan"] = "pro"
            user["remaining_questions"] = 30
            await callback.message.answer(
                "⚡ *Pro Plan activated!* Enjoy faster AI and +30 questions 🚀",
                parse_mode="Markdown",
            )
            await show_categories(callback.message)
        else:
            await callback.message.answer(
                "🔒 This is locked. Please [upgrade to Pro here](https://t.me/send?start=IVdixIeFSP3W)",
                parse_mode="Markdown",
            )

    elif plan == "elite":
        if verify_payment(user_id, "elite"):
            user["plan"] = "elite"
            user["remaining_questions"] = 50
            await callback.message.answer(
                "🚀 *Elite Plan activated!* Fastest AI & priority support enabled 💎",
                parse_mode="Markdown",
            )
            await show_categories(callback.message)
        else:
            await callback.message.answer(
                "🔒 Elite is locked. Please [upgrade to Elite here](https://t.me/send?start=IVfwy1t6hcu9)",
                parse_mode="Markdown",
            )

    await callback.answer()


# === SHOW CATEGORIES (BUSINESS / AI / CRYPTO) ===
async def show_categories(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("💼 Business", callback_data="cat_business"),
                InlineKeyboardButton("🤖 AI", callback_data="cat_ai"),
                InlineKeyboardButton("💰 Crypto", callback_data="cat_crypto"),
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_plans")],
        ]
    )
    await message.answer("📚 Choose a category below:", reply_markup=keyboard)


# === CATEGORY HANDLER → LEVEL CHOICE ===
@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def category_selected(callback: types.CallbackQuery):
    category = callback.data.split("_")[1]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("🌱 Starter", callback_data=f"level_{category}_starter"),
                InlineKeyboardButton("💼 Profit", callback_data=f"level_{category}_profit"),
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_categories")],
        ]
    )
    await callback.message.answer(
        f"📘 *{category.capitalize()} – Choose your level 👇*", parse_mode="Markdown", reply_markup=keyboard
    )
    await callback.answer()


# === LEVEL → SHOW SMART QUESTIONS ===
@dp.callback_query(lambda c: c.data.startswith("level_"))
async def level_selected(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = users.get(user_id)
    if not user:
        await callback.message.answer("Please start the bot with /start first.")
        return

    _, category, level = callback.data.split("_")
    plan = user["plan"]

    try:
        question_list = prompts[plan][category][level]
    except KeyError:
        await callback.message.answer(f"⚠️ Error loading prompts for {plan}.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(q, callback_data=f"q_{category}_{level}_{i}")]
            for i, q in enumerate(question_list)
        ]
        + [[InlineKeyboardButton("⬅️ Back", callback_data=f"back_to_{category}")]]
    )
    await callback.message.answer("🧠 Choose a smart question below:", reply_markup=keyboard)
    await callback.answer()


# === HANDLE CLICKED QUESTION ===
@dp.callback_query(lambda c: c.data.startswith("q_"))
async def handle_question(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = users[user_id]
    _, category, level, idx = callback.data.split("_")
    idx = int(idx)

    question = prompts[user["plan"]][category][level][idx]
    if user["remaining_questions"] <= 0:
        await callback.message.answer("🚫 No remaining questions. Please upgrade your plan.")
        return

    user["remaining_questions"] -= 1
    await callback.message.answer(f"🤖 Thinking about:\n*{question}*", parse_mode="Markdown")

    try:
        completion = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI Tutor Bot that gives insightful answers."},
                {"role": "user", "content": question},
            ],
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        answer = f"⚠️ AI error: {e}"

    await callback.message.answer(answer)
    await callback.answer()


# === BACK NAVIGATION ===
@dp.callback_query(lambda c: c.data == "back_to_plans")
async def back_to_plans(callback: types.CallbackQuery):
    await start(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_categories")
async def back_to_categories(callback: types.CallbackQuery):
    await show_categories(callback.message)
    await callback.answer()
# === /UPGRADE COMMAND ===
@dp.message(Command("upgrade"))
async def upgrade_cmd(message: types.Message):
    text = (
        "💎 *Upgrade Your AI Tutor Experience*\n\n"
        "⚡ *Pro Plan* – $9.99/mo or $99.99/yr (20 % off)\n"
        "→ Faster AI responses + 30 smart questions\n\n"
        "🚀 *Elite Plan* – $19.99/mo or $199.99/yr (20 % off)\n"
        "→ Fastest AI + 50 smart questions + priority support\n\n"
        "Choose your plan below 👇"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_upgrade_keyboard())


# === DAILY MOTIVATIONAL QUOTES ===
async def send_daily_motivation():
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        wait = (target - now).total_seconds()
        await asyncio.sleep(wait)

        quote = get_daily_motivation()
        for uid in users.keys():
            try:
                await bot.send_message(uid, f"🌟 *Daily Motivation*\n\n{quote}", parse_mode="Markdown")
            except Exception:
                pass


# === WEBHOOK SETUP ===
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_daily_motivation())
    print("✅ Webhook set and daily task started")


async def on_shutdown(app):
    await bot.delete_webhook()
    print("🧹 Webhook removed")


# === MAIN ENTRY POINT ===
def main():
    app = web.Application()
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    setup_application(app, dp, bot=bot)

    # Add this health check route
    app.router.add_get("/", lambda request: web.json_response({"status": "ok"}))

    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

