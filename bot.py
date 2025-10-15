import os
import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from openai import OpenAI
from dotenv import load_dotenv

# === Load .env variables ===
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# === Payment Links ===
PRO_MONTHLY_URL = "https://t.me/send?start=IVdixIeFSP3W"
PRO_YEARLY_URL = "https://t.me/send?start=IVRnAnXOWzRM"
ELITE_MONTHLY_URL = "https://t.me/send?start=IVfwy1t6hcu9"
ELITE_YEARLY_URL = "https://t.me/send?start=IVxMW0UNvl7d"

# === Setup Logging ===
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === OpenAI client ===
client = OpenAI(api_key=OPENAI_KEY)
user_data = {}

# === Motivation Messages ===
MOTIVATIONAL_QUOTES = [
    "🌟 Success begins with the decision to try.",
    "🔥 Don’t watch the clock — do what it does: keep going.",
    "💡 Consistency beats intensity — small steps daily!",
    "🚀 You are one smart move away from your next breakthrough."
]

# === Telegram Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    text = (
        f"🤖 Welcome to AI Tutor Pro, {user}!\n\n"
        "Ask smarter. Think sharper. Grow unstoppable.\n\n"
        "💬 You can ask *your own questions* anytime or explore expert topics below.\n\n"
        "Choose your plan to begin:"
    )
    keyboard = [
        [InlineKeyboardButton("🆓 Free", callback_data="free")],
        [InlineKeyboardButton("⚡ Pro", callback_data="pro")],
        [InlineKeyboardButton("🔥 Elite", callback_data="elite")]
    ]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📘 *How to Use AI Tutor Pro*\n\n"
        "💬 Ask *any question* directly in chat — AI will respond instantly.\n"
        "📚 Tap *Questions* to explore AI, Business, and Crypto topics.\n\n"
        f"🚀 Want unlimited questions? [Upgrade to Pro]({PRO_MONTHLY_URL}) or [Elite]({ELITE_MONTHLY_URL})."
    )
    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    plan = user_data.get(user_id, {}).get("plan", "Free")
    remaining = user_data.get(user_id, {}).get("remaining", 5)
    text = (
        f"📊 *Your Plan:* {plan}\n"
        f"💡 *Questions left:* {remaining}\n\n"
        f"Upgrade anytime:\n👉 [Upgrade Here]({PRO_MONTHLY_URL})"
    )
    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚡ Pro – $9.99", url=PRO_MONTHLY_URL)],
        [InlineKeyboardButton("🔥 Elite – $29.99", url=ELITE_MONTHLY_URL)]
    ]
    await update.message.reply_text("💎 Choose your plan:", reply_markup=InlineKeyboardMarkup(keyboard))

async def questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💼 Business", callback_data="cat_business")],
        [InlineKeyboardButton("💰 Crypto", callback_data="cat_crypto")],
        [InlineKeyboardButton("🤖 AI", callback_data="cat_ai")]
    ]
    await update.message.reply_text("📚 Choose your category:", reply_markup=InlineKeyboardMarkup(keyboard))

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    topics = {
        "cat_business": [
            "What are the fundamentals of building a profitable business?",
            "How can small businesses use AI for growth?",
            "What’s the most effective marketing strategy in 2025?"
        ],
        "cat_crypto": [
            "What is blockchain and why is it important?",
            "How can beginners start investing in crypto safely?",
            "What’s the future of DeFi?"
        ],
        "cat_ai": [
            "What are neural networks and how do they work?",
            "How can AI improve productivity?",
            "What are the top AI tools in 2025?"
        ]
    }

    category = query.data
    if category not in topics:
        return

    text = f"📘 *{category.split('_')[1].capitalize()} Questions:*\n\n"
    for i, q in enumerate(topics[category], 1):
        text += f"{i}. {q}\n"
    await query.edit_message_text(text=text, parse_mode="Markdown")

async def chat_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text

    if user_id not in user_data:
        user_data[user_id] = {"plan": "Free", "remaining": 5}

    plan = user_data[user_id]["plan"]
    remaining = user_data[user_id]["remaining"]

    if plan == "Free" and remaining <= 0:
        await update.message.reply_text(
            "⚠️ You’ve reached your daily limit.\nUpgrade for unlimited access:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ Pro – $9.99", url=PRO_MONTHLY_URL)],
                [InlineKeyboardButton("🔥 Elite – $29.99", url=ELITE_MONTHLY_URL)]
            ])
        )
        return

    user_data[user_id]["remaining"] -= 1

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": message}]
    )

    ai_reply = response.choices[0].message.content.strip()
    await update.message.reply_text(ai_reply)

# === Motivation ===
async def send_daily_motivation(app):
    for user_id in user_data.keys():
        quote = MOTIVATIONAL_QUOTES[datetime.now().day % len(MOTIVATIONAL_QUOTES)]
        try:
            await app.bot.send_message(chat_id=user_id, text=f"🌅 Daily Motivation:\n\n{quote}")
        except Exception:
            continue

# === Main Bot Runner ===
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("upgrade", upgrade))
    app.add_handler(CommandHandler("questions", questions))
    app.add_handler(CallbackQueryHandler(category_callback, pattern="^cat_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_with_ai))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_motivation, "cron", hour=9, args=[app])
    scheduler.start()

    logger.info("✅ Bot connected successfully! Running 24/7 on DigitalOcean Worker.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())



