import os
import json
import random
import asyncio
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.storage.memory import MemoryStorage
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# === ENVIRONMENT ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# === LOAD PROMPTS & QUOTES ===
with open("prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

with open("motivational_quotes.json", "r", encoding="utf-8") as f:
    QUOTES = json.load(f)["quotes"]

# === USER DATABASE (IN-MEMORY) ===
USERS = {}  # Example: {user_id: {"plan": "free", "questions_left": 5}}

# === HELPER: MAIN KEYBOARDS ===
def main_menu():
    buttons = [
        [InlineKeyboardButton("🆓 Free", callback_data="plan_free"),
         InlineKeyboardButton("💎 Pro", callback_data="plan_pro"),
         InlineKeyboardButton("🚀 Elite", callback_data="plan_elite")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def upgrade_menu():
    buttons = [
        [InlineKeyboardButton("💎 Pro – Monthly ($9.99)", url=PRO_MONTHLY_URL)],
        [InlineKeyboardButton("💎 Pro – Yearly ($99.99)", url=PRO_YEARLY_URL)],
        [InlineKeyboardButton("🚀 Elite – Monthly ($19.99)", url=ELITE_MONTHLY_URL)],
        [InlineKeyboardButton("🚀 Elite – Yearly ($199.99)", url=ELITE_YEARLY_URL)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_button(data):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("⬅️ Back", callback_data=data)]])
# === HELPER: REGISTER USER ===
def register_user(user_id):
    if user_id not in USERS:
        USERS[user_id] = {"plan": "free", "questions_left": 5, "last_motivation": None}

# === COMMAND: /start ===
@dp.message(commands=["start"])
async def start_command(message: types.Message):
    register_user(message.from_user.id)
    text = (
        "🤖 <b>Welcome to AI Tutor Pro Bot!</b>\n\n"
        "🧠 <i>Ask Smart. Think Smart.</i>\n\n"
        "Choose your plan to begin:\n"
        "🆓 <b>Free</b> — 5 smart questions total\n"
        "💎 <b>Pro</b> — 15 questions per category + faster AI\n"
        "🚀 <b>Elite</b> — 25 questions per category + full power AI\n\n"
        "💬 You can always type your own questions anytime for free!\n\n"
        "⏰ Daily Motivation arrives at 15:00 UTC — stay inspired!"
    )
    await message.answer(text, reply_markup=main_menu(), parse_mode=ParseMode.HTML)

# === COMMAND: /help ===
@dp.message(commands=["help"])
async def help_command(message: types.Message):
    text = (
        "💡 <b>How to use AI Tutor Pro Bot</b>\n\n"
        "1️⃣ /start — Choose your plan & explore categories\n"
        "2️⃣ /questions — Access smart pre-made questions\n"
        "3️⃣ /upgrade — Unlock more AI power\n"
        "4️⃣ /status — Check your plan & question usage\n\n"
        "💬 You can always type your own questions directly — anytime, for free."
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

# === COMMAND: /upgrade ===
@dp.message(commands=["upgrade"])
async def upgrade_command(message: types.Message):
    text = (
        "💳 <b>Upgrade your plan</b>\n\n"
        "💎 Pro Plan — 15 questions per category, faster AI.\n"
        "🚀 Elite Plan — 25 questions per category, full AI power.\n\n"
        "🔥 Yearly plans include <b>20% OFF</b>!\n"
        "Choose your upgrade option below 👇"
    )
    await message.answer(text, reply_markup=upgrade_menu(), parse_mode=ParseMode.HTML)

# === COMMAND: /status ===
@dp.message(commands=["status"])
async def status_command(message: types.Message):
    user = USERS.get(message.from_user.id)
    if not user:
        register_user(message.from_user.id)
        user = USERS[message.from_user.id]

    plan = user["plan"].capitalize()
    q_left = user["questions_left"]
    text = (
        f"📊 <b>Your Current Status</b>\n\n"
        f"💼 Plan: <b>{plan}</b>\n"
        f"❓ Questions Remaining: <b>{q_left}</b>\n\n"
        "💡 Upgrade for more power and faster replies!"
    )
    await message.answer(text, reply_markup=upgrade_menu(), parse_mode=ParseMode.HTML)

# === COMMAND: /questions ===
@dp.message(commands=["questions"])
async def questions_command(message: types.Message):
    buttons = [
        [InlineKeyboardButton("💼 Business", callback_data="cat_business")],
        [InlineKeyboardButton("🤖 AI", callback_data="cat_ai")],
        [InlineKeyboardButton("💰 Crypto", callback_data="cat_crypto")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
    ]
    await message.answer("📚 Choose your category:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
# === CATEGORY HANDLERS ===
@dp.callback_query(F.data.startswith("plan_"))
async def choose_plan(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    register_user(user_id)
    plan = callback.data.split("_")[1]
    USERS[user_id]["plan"] = plan
    USERS[user_id]["questions_left"] = 5 if plan == "free" else (15 if plan == "pro" else 25)

    buttons = [
        [InlineKeyboardButton("💼 Business", callback_data="cat_business")],
        [InlineKeyboardButton("🤖 AI", callback_data="cat_ai")],
        [InlineKeyboardButton("💰 Crypto", callback_data="cat_crypto")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
    ]

    await callback.message.edit_text(
        f"📚 You selected <b>{plan.capitalize()}</b> plan!\nChoose your category below 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("cat_"))
async def choose_category(callback: types.CallbackQuery):
    category = callback.data.split("_")[1]
    buttons = [
        [InlineKeyboardButton("🎯 Starter", callback_data=f"level_{category}_starter")],
        [InlineKeyboardButton("💼 Profit", callback_data=f"level_{category}_profit")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
    ]
    await callback.message.edit_text(
        f"📘 Choose your level for <b>{category.capitalize()}</b> 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("level_"))
async def show_questions(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    category, level = parts[1], parts[2]
    plan = USERS[callback.from_user.id]["plan"]
    q_limit = 5 if plan == "free" else (15 if plan == "pro" else 25)
    questions = PROMPTS.get(category, {}).get(level, [])[:q_limit]

    # If no questions or locked
    if not questions:
        await callback.message.edit_text(
            "🔒 This feature is locked. Upgrade to access more questions!",
            reply_markup=upgrade_menu(),
            parse_mode=ParseMode.HTML
        )
        return

    # Generate question buttons
    buttons = [[InlineKeyboardButton(q, callback_data=f"ask_{category}_{level}_{i}")]
               for i, q in enumerate(questions)]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"cat_{category}")])

    await callback.message.edit_text(
        f"💬 Choose a question from {level.capitalize()} {category.capitalize()} 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("ask_"))
async def ask_question(callback: types.CallbackQuery):
    user = USERS.get(callback.from_user.id)
    if not user:
        register_user(callback.from_user.id)
        user = USERS[callback.from_user.id]

    plan = user["plan"]
    if plan == "free" and user["questions_left"] <= 0:
        await callback.message.edit_text(
            "⚠️ You have reached your free limit. Please upgrade to continue!",
            reply_markup=upgrade_menu(),
            parse_mode=ParseMode.HTML
        )
        return

    parts = callback.data.split("_")
    category, level, index = parts[1], parts[2], int(parts[3])
    question = PROMPTS[category][level][index]

    await callback.message.edit_text(f"🤔 <b>You asked:</b> {question}\n\n🧠 Thinking...", parse_mode=ParseMode.HTML)

    try:
        model = "gpt-4o-mini" if plan == "free" else "gpt-4o"
        response = await openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": question}]
        )
        answer = response.choices[0].message.content
        user["questions_left"] -= 1
        await callback.message.edit_text(
            f"🤔 <b>Question:</b> {question}\n\n💡 <b>Answer:</b>\n{answer}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Error: {e}", parse_mode=ParseMode.HTML)

# === DAILY MOTIVATION SYSTEM ===
async def send_daily_motivation():
    while True:
        now = datetime.utcnow()
        target = datetime(now.year, now.month, now.day, 15, 0)
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        quote = random.choice(QUOTES)
        for user_id in USERS:
            try:
                await bot.send_message(user_id, f"🌟 Daily Motivation:\n\n{quote}")
            except:
                continue

# === CALLBACK: BACK TO MAIN ===
@dp.callback_query(F.data == "main_menu")
async def go_back_main(callback: types.CallbackQuery):
    await callback.message.edit_text("🏠 Back to main menu:", reply_markup=main_menu())

# === WEBHOOK SETUP ===
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_daily_motivation())

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


