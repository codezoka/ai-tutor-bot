import os
import json
import random
import asyncio
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from openai import AsyncOpenAI
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# 1️⃣ Load environment variables
# ─────────────────────────────────────────────
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://ai-tutor-bot-83opf.ondigitalocean.app/webhook")
PORT = int(os.getenv("PORT", 8080))

PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

# ─────────────────────────────────────────────
# 2️⃣ Initialize bot and clients
# ─────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ─────────────────────────────────────────────
# 3️⃣ Load data
# ─────────────────────────────────────────────
with open("prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

QUOTES = [
    "🚀 Success starts with the right question.",
    "💡 Smart questions lead to powerful answers.",
    "🔥 Every day is a new chance to grow smarter.",
    "🏆 Think big. Start small. Act now.",
    "📈 Your potential grows with every question you ask.",
    "✨ Knowledge is the new currency — invest in it.",
    "🤖 Let AI be your smartest business partner."
]

user_data = {}

def get_user(uid):
    if uid not in user_data:
        user_data[uid] = {"plan": "Free", "used": 0, "renewal": None}
    return user_data[uid]

# ─────────────────────────────────────────────
# 4️⃣ Helper functions
# ─────────────────────────────────────────────
def make_keyboard(buttons):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=b[0], callback_data=b[1])] for b in buttons]
    )

def get_upgrade_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("⚡ Pro Monthly $9.99", url=PRO_MONTHLY_URL),
            InlineKeyboardButton("⚡ Pro Yearly $99 (-20%)", url=PRO_YEARLY_URL),
        ],
        [
            InlineKeyboardButton("💎 Elite Monthly $19.99", url=ELITE_MONTHLY_URL),
            InlineKeyboardButton("💎 Elite Yearly $199 (-20%)", url=ELITE_YEARLY_URL),
        ],
        [InlineKeyboardButton("⬅ Back to Menu", callback_data="back_to_menu")]
    ])

# ─────────────────────────────────────────────
# 5️⃣ /start command
# ─────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        "🤖 *Welcome to AI Tutor Bot — Ask Smart, Think Smart!*\n\n"
        "💼 Unlock your potential through *Business*, *AI*, and *Crypto* paths.\n\n"
        "🆓 *Free Plan* — 5 Smart Questions Lifetime\n"
        "⚡ *Pro Plan* — 30 Smart Questions + Faster AI\n"
        "💎 *Elite Plan* — Unlimited Questions + Daily Insights\n\n"
        "💬 Choose a plan below to start your journey 👇"
    )
    buttons = [("🆓 Free", "plan_Free"), ("⚡ Pro", "plan_Pro"), ("💎 Elite", "plan_Elite")]
    await message.answer(text, reply_markup=make_keyboard(buttons), parse_mode="Markdown")

# ─────────────────────────────────────────────
# 6️⃣ /help command
# ─────────────────────────────────────────────
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "🧭 *How to use AI Tutor Bot:*\n\n"
        "💬 Type any question — AI will respond instantly!\n"
        "🧠 Or use our Smart Question categories:\n"
        "   - /start — Choose a plan\n"
        "   - /upgrade — Unlock Pro or Elite\n"
        "   - /status — Check your plan\n\n"
        "⚡ Pro & Elite users get *faster answers* and *exclusive content!*"
    )
    await message.answer(text, parse_mode="Markdown")

# ─────────────────────────────────────────────
# 7️⃣ /upgrade command
# ─────────────────────────────────────────────
@dp.message(Command("upgrade"))
async def cmd_upgrade(message: types.Message):
    text = (
        "💎 *Upgrade Your AI Tutor Experience*\n\n"
        "⚡ *Pro Plan* – $9.99/mo or $99/yr (20 % off)\n"
        "🚀 *Elite Plan* – $19.99/mo or $199/yr (20 % off)\n\n"
        "✨ Choose your plan below 👇"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_upgrade_keyboard())

# ─────────────────────────────────────────────
# 8️⃣ /status command
# ─────────────────────────────────────────────
@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    user = get_user(message.chat.id)
    plan, used, renewal = user["plan"], user["used"], user["renewal"] or "Not set"
    text = (
        f"📊 *Your Status:*\n\n"
        f"🏷 Plan: *{plan}*\n"
        f"💭 Questions Used: {used}\n"
        f"⏰ Renewal: {renewal}\n\n"
        "💡 Upgrade to Pro or Elite for more AI Power ⚡"
    )
    await message.answer(text, parse_mode="Markdown")

# ─────────────────────────────────────────────
# 9️⃣ Handle plan selection
# ─────────────────────────────────────────────
@dp.callback_query(F.data.startswith("plan_"))
async def select_plan(callback: types.CallbackQuery):
    plan = callback.data.split("_")[1]
    user = get_user(callback.from_user.id)
    user["plan"] = plan
    text = f"🎉 You’re now on the *{plan}* plan! Choose a category to start 👇"
    buttons = [("🤖 AI", "cat_ai"), ("💼 Business", "cat_business"), ("💰 Crypto", "cat_crypto")]
    await callback.message.edit_text(text, reply_markup=make_keyboard(buttons), parse_mode="Markdown")
    await callback.answer()

# ─────────────────────────────────────────────
# 🔟 Handle category selection
# ─────────────────────────────────────────────
@dp.callback_query(F.data.startswith("cat_"))
async def select_category(callback: types.CallbackQuery):
    category = callback.data.split("_")[1]
    levels = [("🌱 Starter", f"level_{category}_starter"), ("🚀 Profit", f"level_{category}_profit")]
    await callback.message.edit_text(
        f"📘 Choose your level in *{category.capitalize()}* category:",
        reply_markup=make_keyboard(levels + [("⬅ Back", "back_to_menu")]),
        parse_mode="Markdown"
    )
    await callback.answer()

# ─────────────────────────────────────────────
# 1️⃣1️⃣ Handle level selection → show questions
# ─────────────────────────────────────────────
@dp.callback_query(F.data.startswith("level_"))
async def select_level(callback: types.CallbackQuery):
    _, category, level = callback.data.split("_")
    questions = PROMPTS.get(category, {}).get(level, [])
    if not questions:
        await callback.message.answer("⚠️ No questions found for this section.")
        return

    keyboard = [
        [InlineKeyboardButton(q[:45], callback_data=f"q_{category}_{level}_{i}")]
        for i, q in enumerate(questions)
    ]
    keyboard.append([InlineKeyboardButton("⬅ Back", callback_data=f"cat_{category}")])
    await callback.message.edit_text(
        f"🧠 *{category.capitalize()} – {level} Questions:*\nChoose one below 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )
    await callback.answer()

# ─────────────────────────────────────────────
# 1️⃣2️⃣ Handle question → get AI response
# ─────────────────────────────────────────────
@dp.callback_query(F.data.startswith("q_"))
async def handle_question(callback: types.CallbackQuery):
    _, category, level, idx = callback.data.split("_")
    idx = int(idx)
    question = PROMPTS[category][level][idx]
    user = get_user(callback.from_user.id)

    if user["plan"] == "Free" and user["used"] >= 5:
        await callback.message.answer("🔒 Free plan limit reached. 💳 /upgrade to unlock more!")
        return

    user["used"] += 1
    await callback.message.answer(f"🤔 *You asked:* {question}", parse_mode="Markdown")
    await callback.message.answer("💭 Thinking...")

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question}]
        )
        ai_answer = response.choices[0].message.content
        await callback.message.answer(f"💬 *AI Answer:*\n{ai_answer}", parse_mode="Markdown")
    except Exception as e:
        await callback.message.answer(f"⚠️ AI Error: {e}")

# ─────────────────────────────────────────────
# 1️⃣3️⃣ Daily Motivation
# ─────────────────────────────────────────────
async def send_daily_quotes():
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        quote = random.choice(QUOTES)
        for uid in user_data.keys():
            try:
                await bot.send_message(uid, f"🌟 *Daily Motivation*\n\n{quote}", parse_mode="Markdown")
            except:
                pass

# ─────────────────────────────────────────────
# 1️⃣4️⃣ Webhook + Health Check (/)
# ─────────────────────────────────────────────
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_daily_quotes())
    print("✅ Webhook set and daily quotes task started.")

async def on_shutdown(app):
    await bot.delete_webhook()
    print("🧹 Webhook deleted on shutdown.")

def main():
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="✅ AI Tutor Bot is Healthy"))
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()

