import os
import json
import random
import asyncio
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from openai import AsyncOpenAI
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

# === Initialize clients ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_KEY)

# === File paths ===
PROMPTS_FILE = "prompts.json"
USERS_FILE = "users.json"

# === Load prompts ===
with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

# === Helper functions ===
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_user(user_id):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {
            "plan": "free",
            "used_questions": 0,
            "last_reset": str(datetime.utcnow().date())
        }
        save_users(users)
    return users[str(user_id)]

def update_user(user_id, key, value):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {}
    users[str(user_id)][key] = value
    save_users(users)

# === AI model selector ===
def get_model(plan):
    if plan == "pro":
        return "gpt-4-turbo"
    elif plan == "elite":
        return "gpt-4o"
    return "gpt-4o-mini"

# === UI keyboards ===
def plans_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Free", callback_data="plan_free"),
         InlineKeyboardButton(text="⚡ Pro", callback_data="plan_pro"),
         InlineKeyboardButton(text="💎 Elite", callback_data="plan_elite")]
    ])
    return kb

def categories_keyboard(plan):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Business", callback_data=f"{plan}_business")],
        [InlineKeyboardButton(text="🤖 AI", callback_data=f"{plan}_ai")],
        [InlineKeyboardButton(text="💰 Crypto", callback_data=f"{plan}_crypto")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_plans")]
    ])
    return kb

def level_keyboard(plan, category):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Starter", callback_data=f"{plan}_{category}_starter")],
        [InlineKeyboardButton(text="🚀 Profit", callback_data=f"{plan}_{category}_profit")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"back_{plan}_categories")]
    ])
    return kb

def questions_keyboard(plan, category, level):
    questions = PROMPTS[category][plan][level]
    kb = []
    for q in questions:
        kb.append([InlineKeyboardButton(text=q[:60], callback_data=f"q_{plan}_{category}_{level}_{questions.index(q)}")])
    kb.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"back_{plan}_{category}_levels")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def upgrade_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Pro $9.99/mo", url=PRO_MONTHLY_URL)],
        [InlineKeyboardButton(text="⚡ Pro $99.99/yr (20% off)", url=PRO_YEARLY_URL)],
        [InlineKeyboardButton(text="💎 Elite $19.99/mo", url=ELITE_MONTHLY_URL)],
        [InlineKeyboardButton(text="💎 Elite $199.99/yr (20% off)", url=ELITE_YEARLY_URL)]
    ])

# === Message handlers ===
@dp.message(commands=["start"])
async def start_cmd(message: types.Message):
    text = (
        "🤖 <b>AI Tutor Bot — Ask Smart. Think Smart.</b>\n\n"
        "Learn to think like a CEO and innovator.\n\n"
        "🟢 Free plan → Try 5 Smart Questions across AI, Business and Crypto.\n"
        "⚡ Pro & Elite → Unlock more Smart Questions and get <b>faster AI responses</b>.\n\n"
        "You can always type your own questions freely below.\n\n"
        "👇 Choose your plan to begin:"
    )
    await message.answer(text, reply_markup=plans_keyboard(), parse_mode="HTML")

@dp.message(commands=["help"])
async def help_cmd(message: types.Message):
    text = (
        "💡 <b>How to use AI Tutor Bot</b>\n\n"
        "1️⃣ /start — Choose your plan and explore Smart Questions.\n"
        "2️⃣ You can type any question anytime to chat freely with AI.\n"
        "3️⃣ /status — See your plan and remaining Smart Questions.\n"
        "4️⃣ /upgrade — Unlock Pro or Elite for more Smart Questions and faster AI.\n\n"
        "🧠 Ask Smart. Think Smart. Grow daily."
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(commands=["upgrade"])
async def upgrade_cmd(message: types.Message):
    text = (
        "💎 <b>Upgrade Your Experience</b>\n\n"
        "⚡ Pro Plan → 30 Smart Questions per category (15 Starter + 15 Profit) with Faster AI.\n"
        "💎 Elite Plan → 50 Smart Questions per category (25 Starter + 25 Profit) with Full Power AI.\n\n"
        "Yearly plans include <b>20% off</b> and Full Power AI speed.\n\n"
        "👇 Choose your plan:"
    )
    await message.answer(text, reply_markup=upgrade_keyboard(), parse_mode="HTML")

@dp.message(commands=["status"])
async def status_cmd(message: types.Message):
    user = get_user(message.from_user.id)
    remaining = max(0, 5 - user["used_questions"]) if user["plan"] == "free" else "Unlimited until renewal"
    text = (
        f"📊 <b>Your Status</b>\n\n"
        f"👤 Plan: <b>{user['plan'].capitalize()}</b>\n"
        f"💬 Smart Questions left: <b>{remaining}</b>\n"
        f"⏰ Renewal: <b>{user.get('renewal', 'Lifetime Free')}</b>\n\n"
        "Upgrade for more Smart Questions and faster AI responses!"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message()
async def chat_ai(message: types.Message):
    user = get_user(message.from_user.id)
    model = get_model(user["plan"])
    try:
        response = await openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": message.text}],
        )
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

# === Callback handlers ===
@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    data = call.data
    user = get_user(call.from_user.id)

    if data == "back_to_plans":
        await call.message.edit_text("👇 Choose your plan:", reply_markup=plans_keyboard())
        return

    if data.startswith("plan_"):
        plan = data.split("_")[1]
        update_user(call.from_user.id, "plan_choice", plan)
        await call.message.edit_text("📂 Choose a category:", reply_markup=categories_keyboard(plan))
        return

    if data.startswith("back_") and "categories" in data:
        plan = data.split("_")[1]
        await call.message.edit_text("📂 Choose a category:", reply_markup=categories_keyboard(plan))
        return

    if data.startswith(("free_", "pro_", "elite_")) and data.count("_") == 1:
        plan, category = data.split("_")
        await call.message.edit_text("📘 Choose a level:", reply_markup=level_keyboard(plan, category))
        return

    if data.startswith(("free_", "pro_", "elite_")) and data.count("_") == 2:
        plan, category, level = data.split("_")
        await call.message.edit_text("🧠 Choose a Smart Question:", reply_markup=questions_keyboard(plan, category, level))
        return

    if data.startswith("q_"):
        _, plan, category, level, q_index = data.split("_")
        q_index = int(q_index)
        question = PROMPTS[category][plan][level][q_index]
        if user["plan"] == "free" and user["used_questions"] >= 5:
            await call.message.answer("🔒 You’ve reached your free Smart Question limit. Upgrade to unlock full access!", reply_markup=upgrade_keyboard())
            return
        await call.message.answer(f"🤔 <b>{question}</b>", parse_mode="HTML")
        model = get_model(user["plan"])
        try:
            response = await openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": question}],
            )
            await call.message.answer(response.choices[0].message.content)
            if user["plan"] == "free":
                update_user(call.from_user.id, "used_questions", user["used_questions"] + 1)
        except Exception as e:
            await call.message.answer(f"❌ Error: {e}")
        return

# === Daily motivation ===
async def send_motivations():
    quotes = [
        "💡 Small steps create big wins — take one today.",
        "🚀 Knowledge without action is just potential — act now.",
        "💭 Every click you make is a step toward freedom.",
        "⚡ Winners don’t wait — they start.",
        "🔥 Discipline beats motivation every day — do it now."
    ]
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        users = load_users()
        for uid in users:
            try:
                await bot.send_message(uid, random.choice(quotes) + "\n\n🤖 @ai_tutor_pro_bot")
            except:
                pass

# === Webhook setup ===
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_motivations())

async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()

