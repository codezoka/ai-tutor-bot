import os
import json
import asyncio
import logging
import random
from datetime import time

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from openai import OpenAI
from dotenv import load_dotenv

# --- Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

PRO_MONTHLY = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY = os.getenv("ELITE_YEARLY_URL")

# --- Question Bank ---
QUESTIONS = {
    "free": {
        "AI": [
            "What is Artificial Intelligence?",
            "How can AI improve everyday life?",
            "What are the main challenges of AI ethics?",
            "How do neural networks learn?",
            "What industries benefit most from AI?"
        ],
        "Business": [
            "What makes a business idea successful?",
            "How can entrepreneurs leverage AI tools?",
            "What are key steps in building a strong brand?",
            "How to attract investors effectively?",
            "What strategies boost productivity?"
        ],
        "Crypto": [
            "What is blockchain technology?",
            "How does Bitcoin differ from Ethereum?",
            "What are smart contracts used for?",
            "How do I safely invest in crypto?",
            "What role will crypto play in the future economy?"
        ],
    },
    "pro": {
        "AI": [f"Pro AI Q{i}" for i in range(1, 11)],
        "Business": [f"Pro Business Q{i}" for i in range(1, 11)],
        "Crypto": [f"Pro Crypto Q{i}" for i in range(1, 11)],
    },
    "elite": {
        "AI": [f"Elite AI Q{i}" for i in range(1, 21)],
        "Business": [f"Elite Business Q{i}" for i in range(1, 21)],
        "Crypto": [f"Elite Crypto Q{i}" for i in range(1, 21)],
    },
}

USER_PLANS = {}
FREE_LIMIT = 5

# --- Helper Functions ---
def get_plan(user_id):
    return USER_PLANS.get(user_id, "free")

def reduce_free_limit(user_id):
    if "free_uses" not in USER_PLANS:
        USER_PLANS["free_uses"] = {}
    USER_PLANS["free_uses"][user_id] = USER_PLANS["free_uses"].get(user_id, FREE_LIMIT) - 1

def remaining_free(user_id):
    return USER_PLANS.get("free_uses", {}).get(user_id, FREE_LIMIT)

async def ask_ai(question: str) -> str:
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question}],
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(e)
        return "⚠️ There was an issue with AI response."

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *Welcome to AI Tutor Pro!*\n\n"
        "Ask smarter. Learn faster. Build success.\n"
        "You can freely chat with AI anytime or explore our question sections.\n\n"
        "💎 Upgrade to unlock advanced insights and exclusive lessons.\n\n"
        "👇 Choose your level below:"
    )
    keyboard = [
        [InlineKeyboardButton("🧠 Free", callback_data="menu_free")],
        [InlineKeyboardButton("🚀 Pro", url=PRO_MONTHLY)],
        [InlineKeyboardButton("👑 Elite", url=ELITE_MONTHLY)],
    ]
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🧭 *How to use AI Tutor Pro*\n\n"
        "💬 Type any question directly — AI will respond instantly.\n"
        "🎯 Or explore category questions from the *Questions* menu.\n"
        "🚀 Upgrade to unlock deeper insights:\n"
        f"[Upgrade to Pro]({PRO_MONTHLY}) | [Upgrade to Elite]({ELITE_MONTHLY})"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💼 Business", callback_data="cat_Business")],
        [InlineKeyboardButton("💰 Crypto", callback_data="cat_Crypto")],
        [InlineKeyboardButton("🤖 AI", callback_data="cat_AI")],
    ]
    await update.message.reply_text("📚 Choose a category:", reply_markup=InlineKeyboardMarkup(keyboard))

async def category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, cat = query.data.split("_")
    plan = get_plan(query.from_user.id)

    if plan == "free" and remaining_free(query.from_user.id) <= 0:
        await query.edit_message_text(
            "⚠️ You’ve reached your free question limit.\nUpgrade to continue learning:\n"
            f"[Pro Plan]({PRO_MONTHLY}) | [Elite Plan]({ELITE_MONTHLY})",
            parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
        )
        return

    questions = QUESTIONS[plan][cat]
    buttons = [
        [InlineKeyboardButton(q, callback_data=f"ask_{cat}_{i}")]
        for i, q in enumerate(questions[:5])
    ]
    await query.edit_message_text(f"📖 *{cat} Questions* — Choose one:", parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(buttons))

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, cat, idx = query.data.split("_")
    plan = get_plan(query.from_user.id)

    question = QUESTIONS[plan][cat][int(idx)]
    if plan == "free":
        reduce_free_limit(query.from_user.id)
    await query.edit_message_text(f"💭 *{question}*", parse_mode=ParseMode.MARKDOWN)
    response = await ask_ai(question)
    await query.message.reply_text(f"✨ {response}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    plan = get_plan(user_id)
    remaining = remaining_free(user_id)
    text = (
        f"📊 *Your Status*\n\n"
        f"👤 Plan: *{plan.capitalize()}*\n"
        f"🧮 Remaining Free Questions: {remaining}\n\n"
        f"🚀 [Upgrade to Pro]({PRO_MONTHLY}) | [Upgrade to Elite]({ELITE_MONTHLY})"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    response = await ask_ai(user_text)
    await update.message.reply_text(response)

async def send_daily_motivation(context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("motivation.json", "r", encoding="utf-8") as f:
            quotes = json.load(f)
        quote = random.choice(quotes)
        for user_id in USER_PLANS.keys():
            try:
                await context.bot.send_message(chat_id=user_id, text=f"🌅 *Daily Motivation:*\n\n{quote}",
                                               parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {e}")
    except Exception as e:
        logger.error(f"Motivation error: {e}")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("questions", menu))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(category, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(ask, pattern="^ask_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    job_queue = app.job_queue
    job_queue.run_daily(send_daily_motivation, time=time(9, 0, 0))

    logger.info("🤖 AI Tutor Pro running 24/7 on DigitalOcean Worker...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

