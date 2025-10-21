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

# ───────────────────────────────
# Load environment variables
# ───────────────────────────────
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://ai-tutor-bot-83opf.ondigitalocean.app/webhook")

PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

MOTIVATION_HOUR = int(os.getenv("MOTIVATION_HOUR", 15))

# ───────────────────────────────
# Initialize clients
# ───────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ───────────────────────────────
# Load prompts
# ───────────────────────────────
with open("prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

# ───────────────────────────────
# User storage & motivation quotes
# ───────────────────────────────
user_data = {}

QUOTES = [
    "🚀 Success starts with the right question.",
    "💡 Smart questions lead to powerful answers.",
    "🔥 Every day is a new chance to grow smarter.",
    "🏆 Think big. Start small. Act now.",
    "📈 Your potential grows with every question you ask.",
    "✨ Knowledge is the new currency — invest in it.",
    "🤖 Let AI be your smartest business partner."
]

# ───────────────────────────────
# Helper functions
# ───────────────────────────────
def keyboard(buttons):
    """Build InlineKeyboardMarkup from list of tuples"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=d) for t, d in buttons]
    ])

# ───────────────────────────────
# Health check (DigitalOcean probe)
# ───────────────────────────────
async def handle_root(request):
    return web.Response(text="✅ AI Tutor Bot alive and healthy!", status=200)
# ───────────────────────────────
# /start command
# ───────────────────────────────
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    text = (
        "🤖 **AI Tutor Bot – Ask Smart, Think Smart!**\n\n"
        "Welcome! I’m your personal AI tutor helping you ask **smarter questions** in **Business**, **AI**, and **Crypto**.\n\n"
        "✨ Free Plan – 5 smart questions total\n"
        "⚡ Pro Plan – +30 smart questions & faster AI\n"
        "🚀 Elite Plan – +50 questions & priority support\n\n"
        "Ready? Choose your plan below 👇"
    )
    buttons = [
        (f"🆓 Free Plan", "plan_free"),
        (f"⚡ Pro Plan", "plan_pro"),
        (f"🚀 Elite Plan", "plan_elite")
    ]
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard(buttons))


# ───────────────────────────────
# /help command
# ───────────────────────────────
@dp.message(F.text == "/help")
async def cmd_help(message: types.Message):
    await message.answer(
        "ℹ️ Use the commands below:\n\n"
        "• /start – Begin or reset menu\n"
        "• /questions – Ask smart questions by topic\n"
        "• /upgrade – View Pro and Elite plans\n"
        "• /status – See your remaining AI questions\n\n"
        "Or just type your own question to chat with AI 🤖"
    )


# ───────────────────────────────
# /status command
# ───────────────────────────────
@dp.message(F.text == "/status")
async def cmd_status(message: types.Message):
    user_id = str(message.from_user.id)
    remaining = user_data.get(user_id, {}).get("remaining", 5)
    plan = user_data.get(user_id, {}).get("plan", "Free")
    await message.answer(f"👤 Your plan: *{plan}*\n💬 Remaining questions: {remaining}", parse_mode="Markdown")


# ───────────────────────────────
# /upgrade command
# ───────────────────────────────
@dp.message(F.text == "/upgrade")
async def cmd_upgrade(message: types.Message):
    text = (
        "💎 **Upgrade Your AI Tutor Experience**\n\n"
        "⚡ *Pro Plan* – $9.99 / month or $99.99 / year (20 % off)\n"
        "   – Faster AI responses + 30 smart questions\n\n"
        "🚀 *Elite Plan* – $19.99 / month or $199.99 / year (20 % off)\n"
        "   – Fastest AI + 50 smart questions + priority support\n\n"
        "Choose your plan below 👇"
    )
    buttons = [
        (f"⚡ Pro Monthly – $9.99", "pay_pro_month"),
        (f"⚡ Pro Yearly – $99.99", "pay_pro_year"),
        (f"🚀 Elite Monthly – $19.99", "pay_elite_month"),
        (f"🚀 Elite Yearly – $199.99", "pay_elite_year"),
        (f"⬅️ Back", "back_start")
    ]
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard(buttons))


# ───────────────────────────────
# /questions command
# ───────────────────────────────
@dp.message(F.text == "/questions")
async def cmd_questions(message: types.Message):
    text = "📚 Choose a category below:"
    buttons = [
        ("💼 Business", "cat_business"),
        ("🤖 AI", "cat_ai"),
        ("💰 Crypto", "cat_crypto"),
        ("⬅️ Back", "back_start")
    ]
    await message.answer(text, reply_markup=keyboard(buttons))


# ───────────────────────────────
# Category handlers
# ───────────────────────────────
@dp.callback_query(F.data.startswith("cat_"))
async def category_selected(callback: types.CallbackQuery):
    cat = callback.data.split("_")[1]
    intro = PROMPTS[cat]["intro"]
    buttons = [
        ("🌱 Starter", f"lvl_{cat}_starter"),
        ("💼 Profit", f"lvl_{cat}_profit"),
        ("⬅️ Back", "back_questions")
    ]
    await callback.message.answer(intro, parse_mode="Markdown", reply_markup=keyboard(buttons))
    await callback.answer()


# ───────────────────────────────
# Level handlers (load questions)
# ───────────────────────────────
@dp.callback_query(F.data.startswith("lvl_"))
async def level_selected(callback: types.CallbackQuery):
    _, cat, level = callback.data.split("_")
    plan = user_data.get(str(callback.from_user.id), {}).get("plan", "free")
    try:
        prompts = PROMPTS[cat][plan][level]
    except KeyError:
        await callback.message.answer("⚠️ Error loading prompts. Try another category or check your plan.")
        await callback.answer()
        return

    q = random.choice(prompts)
    await callback.message.answer(f"🧠 {q}\n\nType your answer or ask your own question below 👇")
    await callback.answer()
# ───────────────────────────────
# Handle direct AI questions
# ───────────────────────────────
@dp.message()
async def handle_question(message: types.Message):
    user_id = str(message.from_user.id)
    user_info = user_data.get(user_id, {"plan": "free", "remaining": 5})

    if user_info["remaining"] <= 0:
        await message.answer(
            "⚠️ You’ve reached your question limit. Use /upgrade to unlock more smart questions 🔓"
        )
        return

    await message.answer("🤖 *Thinking...*", parse_mode="Markdown")

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are AI Tutor Bot – an expert AI assistant for business, AI, and crypto advice. Respond clearly, use emojis, and format text with markdown."},
                {"role": "user", "content": message.text},
            ],
            temperature=0.7,
            max_tokens=400,
        )
        answer = response.choices[0].message.content.strip()
        await message.answer(answer, parse_mode="Markdown")

        # Reduce remaining count
        user_info["remaining"] -= 1
        user_data[user_id] = user_info

    except Exception as e:
        await message.answer("❌ Sorry, there was an error processing your question.")
        print("AI Error:", e)


# ───────────────────────────────
# Plan selection (free, pro, elite)
# ───────────────────────────────
@dp.callback_query(F.data.startswith("plan_"))
async def plan_selected(callback: types.CallbackQuery):
    plan = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)

    if plan == "free":
        user_data[user_id] = {"plan": "free", "remaining": 5}
        await callback.message.answer("🆓 You’re now on the *Free Plan*! Type /questions to start learning.", parse_mode="Markdown")
    elif plan == "pro":
        user_data[user_id] = {"plan": "pro", "remaining": 35}
        await callback.message.answer("⚡ Pro Plan activated! Enjoy faster AI and +30 questions 🚀", parse_mode="Markdown")
    elif plan == "elite":
        user_data[user_id] = {"plan": "elite", "remaining": 55}
        await callback.message.answer("🚀 Elite Plan unlocked! 50 smart questions + priority support 💎", parse_mode="Markdown")

    await callback.answer()


# ───────────────────────────────
# Payment link callbacks
# ───────────────────────────────
@dp.callback_query(F.data.startswith("pay_"))
async def payment_links(callback: types.CallbackQuery):
    links = {
        "pay_pro_month": PRO_MONTHLY_URL,
        "pay_pro_year": PRO_YEARLY_URL,
        "pay_elite_month": ELITE_MONTHLY_URL,
        "pay_elite_year": ELITE_YEARLY_URL
    }
    url = links.get(callback.data)
    if url:
        await callback.message.answer(f"💳 [Click here to complete payment]({url})", parse_mode="Markdown")
    await callback.answer()


# ───────────────────────────────
# Back button handlers
# ───────────────────────────────
@dp.callback_query(F.data == "back_start")
async def back_start(callback: types.CallbackQuery):
    await cmd_start(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "back_questions")
async def back_questions(callback: types.CallbackQuery):
    await cmd_questions(callback.message)
    await callback.answer()


# ───────────────────────────────
# Daily motivation (15:00 UTC)
# ───────────────────────────────
async def send_daily_motivation():
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=MOTIVATION_HOUR, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        wait_time = (target - now).total_seconds()
        await asyncio.sleep(wait_time)
        for user_id in user_data.keys():
            try:
                await bot.send_message(user_id, random.choice(QUOTES))
            except:
                continue


# ───────────────────────────────
# Webhook setup & main entry
# ───────────────────────────────
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_daily_motivation())
    print("🚀 Webhook set and bot started successfully!")

async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    app = web.Application()
    app.router.add_get("/", handle_root)

    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))


if __name__ == "__main__":
    main()


