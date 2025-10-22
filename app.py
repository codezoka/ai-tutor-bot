import os, json, random, asyncio
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.storage.memory import MemoryStorage
from openai import AsyncOpenAI
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# 1️⃣  Environment & Setup
# ─────────────────────────────────────────────
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://ai-tutor-bot-83opf.ondigitalocean.app/webhook")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ─────────────────────────────────────────────
# 2️⃣  Data loading
# ─────────────────────────────────────────────
with open("prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)
with open("motivational_quotes.json", "r", encoding="utf-8") as f:
    QUOTES = json.load(f)

# ─────────────────────────────────────────────
# 3️⃣  Utility
# ─────────────────────────────────────────────
user_data = {}  # stores user plan & usage

def get_user(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {"plan": "Free", "used": 0, "renewal": None}
    return user_data[chat_id]

# ─────────────────────────────────────────────
# 4️⃣  Keyboards
# ─────────────────────────────────────────────
def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧭 Questions", callback_data="menu_questions")],
        [InlineKeyboardButton(text="💳 Upgrade Plan", callback_data="menu_upgrade")],
        [InlineKeyboardButton(text="📊 Status", callback_data="menu_status")],
        [InlineKeyboardButton(text="❓ Help", callback_data="menu_help")]
    ])
    return kb

def plans_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("🆓 Free", callback_data="plan_Free"),
            InlineKeyboardButton("⚡ Pro", callback_data="plan_Pro"),
            InlineKeyboardButton("💎 Elite", callback_data="plan_Elite")
        ]
    ])

# ─────────────────────────────────────────────
# 5️⃣  /start  — Premium Welcome + Plan Choice
# ─────────────────────────────────────────────
@dp.message(commands=["start"])
async def start_handler(message: types.Message):
    user = get_user(message.chat.id)
    welcome = (
        "🤖 *Welcome to AI Tutor Bot — Ask Smart, Think Smart!*\n\n"
        "💡 Here you’ll get expert-crafted smart questions for "
        "*Business*, *AI*, and *Crypto* — each tuned to make you think like a CEO.\n\n"
        "🎯 Type anything to chat with AI anytime — or choose your plan below to unlock more!\n\n"
        "🆓 Free = 5 questions  |  ⚡ Pro = Faster + 30 Qs  |  💎 Elite = Full Power AI (+ daily insights)"
    )
    await message.answer(welcome, reply_markup=plans_keyboard(), parse_mode="Markdown")

# ─────────────────────────────────────────────
# 6️⃣  /help — Clickable + Emoji-rich
# ─────────────────────────────────────────────
@dp.message(commands=["help"])
async def help_handler(message: types.Message):
    help_text = (
        "💬 *How to use AI Tutor Bot*\n\n"
        "🧠 `/start` – Choose your plan and get started\n"
        "📚 `/questions` – Browse categories & smart questions\n"
        "💳 `/upgrade` – See plans & upgrade to Pro or Elite\n"
        "📊 `/status` – Check your plan & remaining uses\n\n"
        "💭 You can also type your own question anytime!"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("🏁 Start", callback_data="menu_start"),
            InlineKeyboardButton("💬 Questions", callback_data="menu_questions")
        ],
        [
            InlineKeyboardButton("💳 Upgrade", callback_data="menu_upgrade"),
            InlineKeyboardButton("📊 Status", callback_data="menu_status")
        ]
    ])
    await message.answer(help_text, reply_markup=kb, parse_mode="Markdown")

# ─────────────────────────────────────────────
# 7️⃣  Plan-selection logic
# ─────────────────────────────────────────────
@dp.callback_query(F.data.startswith("plan_"))
async def plan_selected(callback: types.CallbackQuery):
    plan = callback.data.split("_")[1]
    user = get_user(callback.from_user.id)
    if plan == "Free":
        user["plan"] = "Free"
        await callback.message.edit_text(
            "🆓 You’re on the *Free* plan.\n\nChoose a category below:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("🤖 AI", callback_data="cat_AI")],
                [InlineKeyboardButton("💼 Business", callback_data="cat_Business")],
                [InlineKeyboardButton("₿ Crypto", callback_data="cat_Crypto")],
                [InlineKeyboardButton("⬅ Back", callback_data="menu_start")]
            ]),
            parse_mode="Markdown"
        )
    else:
        # Placeholder check until payment logic
        await callback.message.edit_text(
            f"🔒 The *{plan}* plan is locked.\n\n"
            "💳 Upgrade now to unlock faster AI and more smart questions!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("⚡ Upgrade to Pro $9.99", url=os.getenv("PRO_MONTHLY_URL"))],
                [InlineKeyboardButton("💎 Go Elite $19.99", url=os.getenv("ELITE_MONTHLY_URL"))],
                [InlineKeyboardButton("⬅ Back", callback_data="menu_start")]
            ])
        )

# ─────────────────────────────────────────────
# 8️⃣  Category Selection
# ─────────────────────────────────────────────
@dp.callback_query(F.data.startswith("cat_"))
async def category_selected(callback: types.CallbackQuery):
    category = callback.data.split("_")[1]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🎯 Starter", callback_data=f"level_{category}_Starter")],
        [InlineKeyboardButton("🚀 Profit", callback_data=f"level_{category}_Profit")],
        [InlineKeyboardButton("⬅ Back to Plans", callback_data="menu_start")]
    ])
    await callback.message.edit_text(
        f"📘 Choose your level in *{category}* category:",
        reply_markup=keyboard, parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
# 9️⃣  Level Selection → Smart Questions
# ─────────────────────────────────────────────
@dp.callback_query(F.data.startswith("level_"))
async def level_selected(callback: types.CallbackQuery):
    _, category, level = callback.data.split("_")
    questions = PROMPTS.get(category, {}).get(level, [])
    if not questions:
        await callback.message.edit_text("⚠️ No questions found for this section.")
        return

    keyboard = []
    for q in questions:
        keyboard.append([InlineKeyboardButton(q[:45], callback_data=f"q_{category}_{level}_{questions.index(q)}")])
    keyboard.append([InlineKeyboardButton("⬅ Back", callback_data=f"cat_{category}")])

    await callback.message.edit_text(
        f"🧠 *{category} – {level} Questions:*\nChoose a smart question below 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
# 🔟 When user clicks a question → AI Answer
# ─────────────────────────────────────────────
@dp.callback_query(F.data.startswith("q_"))
async def question_selected(callback: types.CallbackQuery):
    _, category, level, idx = callback.data.split("_")
    idx = int(idx)
    question = PROMPTS[category][level][idx]
    user = get_user(callback.from_user.id)

    # Check limit for Free users
    if user["plan"] == "Free" and user["used"] >= 5:
        await callback.message.answer("🔒 You’ve used all 5 Free smart questions.\nType your own question or 💳 /upgrade to unlock more!")
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
        await callback.message.answer(f"❌ Error: {e}")
# ─────────────────────────────────────────────
# 1️⃣1️⃣  /upgrade — Payment Plans
# ─────────────────────────────────────────────
@dp.message(commands=["upgrade"])
async def upgrade_handler(message: types.Message):
    text = (
        "💳 *Upgrade your AI Tutor Plan*\n\n"
        "⚡ Pro Plan – $9.99 / month (30 Smart Questions + Faster AI)\n"
        "💎 Elite Plan – $19.99 / month (Full Power AI + Unlimited Questions + Daily Insights)\n\n"
        "🎁 20 % off on yearly plans! ✨"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("⚡ Pro Monthly $9.99", url=os.getenv("PRO_MONTHLY_URL")),
            InlineKeyboardButton("⚡ Pro Yearly $99 (-20 %)", url=os.getenv("PRO_YEARLY_URL")),
        ],
        [
            InlineKeyboardButton("💎 Elite Monthly $19.99", url=os.getenv("ELITE_MONTHLY_URL")),
            InlineKeyboardButton("💎 Elite Yearly $199 (-20 %)", url=os.getenv("ELITE_YEARLY_URL")),
        ],
        [InlineKeyboardButton("⬅ Back to Menu", callback_data="menu_start")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# ─────────────────────────────────────────────
# 1️⃣2️⃣  /status — User Plan & Usage
# ─────────────────────────────────────────────
@dp.message(commands=["status"])
async def status_handler(message: types.Message):
    user = get_user(message.chat.id)
    plan = user["plan"]
    used = user["used"]
    renewal = user["renewal"] or "Not set"
    text = (
        f"📊 *Your Status:*\n\n"
        f"🏷 Plan: *{plan}*\n"
        f"💭 Questions Used: {used}\n"
        f"⏰ Renewal Date: {renewal}\n\n"
        "Upgrade to Pro or Elite for more AI Power ⚡"
    )
    await message.answer(text, parse_mode="Markdown")

# ─────────────────────────────────────────────
# 1️⃣3️⃣  Scheduled Daily Motivational Message (15:00 UTC)
# ─────────────────────────────────────────────
async def send_daily_quotes():
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        quote = random.choice(QUOTES)
        for uid in list(user_data.keys()):
            try:
                await bot.send_message(
                    uid,
                    f"💬 *Daily Inspiration:*\n_{quote}_\n\n"
                    "✨ Keep learning smart – upgrade for full AI power!",
                    parse_mode="Markdown"
                )
            except Exception:
                continue

# ─────────────────────────────────────────────
# 1️⃣4️⃣  Webhook & Health Check for DigitalOcean
# ─────────────────────────────────────────────
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_daily_quotes())
    print("🚀 Bot started & webhook set!")

async def on_shutdown(app):
    await bot.delete_webhook()
    print("🛑 Bot stopped.")

def main():
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="✅ AI Tutor Bot is Healthy"))
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()


