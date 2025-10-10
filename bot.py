import os
import asyncio
import logging
import nest_asyncio
nest_asyncio.apply()
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import random

# -------------------------------
# Load Environment Variables
# -------------------------------
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")

PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

# -------------------------------
# Logging Setup
# -------------------------------
logging.basicConfig(
    filename="bot_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -------------------------------
# Global Data
# -------------------------------
FREE_LIMIT = 5
PRO_LIMIT = 10
ELITE_LIMIT = 20

user_data = {}  # Track user questions
motivation_messages = [
    "💭 *Success begins with the right question.* Keep learning, keep winning.",
    "🚀 *AI doesn’t replace people—it upgrades them.* Use it wisely.",
    "💡 *Small steps daily create massive success.* You’ve got this!",
    "🏆 *You don’t need to be lucky—you need to be consistent.*",
    "🤖 *Smart minds ask smarter questions.* Keep growing!"
]

categories = {
    "AI": [
        "How can I use AI to make money online?",
        "What’s the best AI tool to start automating tasks?",
        "How can I train my own AI model?",
        "How is AI changing small businesses?",
        "What are the biggest AI mistakes to avoid?"
    ],
    "Business": [
        "How do I find a profitable niche?",
        "What’s the best way to build a brand fast?",
        "How can I automate my business with AI?",
        "How can I get my first 100 customers?",
        "What’s the secret to scaling a business in 2025?"
    ],
    "Crypto": [
        "How can I start investing in crypto safely?",
        "What’s the best way to identify early crypto gems?",
        "How can AI help me analyze crypto markets?",
        "What are the biggest crypto trends of 2025?",
        "How do I protect my assets during volatility?"
    ]
}

# -------------------------------
# Helper Functions
# -------------------------------
def get_plan_limit(user_id):
    """Return the user’s plan limit"""
    return user_data.get(user_id, {}).get("limit", FREE_LIMIT)

def get_plan_name(user_id):
    """Return the user’s plan name"""
    return user_data.get(user_id, {}).get("plan", "Free")

def record_question(user_id):
    """Track how many free questions user asked"""
    user = user_data.setdefault(user_id, {"count": 0, "plan": "Free", "limit": FREE_LIMIT})
    user["count"] += 1

def can_ask_question(user_id):
    """Check if user can still ask questions"""
    user = user_data.setdefault(user_id, {"count": 0, "plan": "Free", "limit": FREE_LIMIT})
    return user["count"] < user["limit"]

def reset_monthly_limits():
    """Reset question limits monthly for all users"""
    for user in user_data.values():
        if user["plan"] == "Pro":
            user["limit"] = PRO_LIMIT
        elif user["plan"] == "Elite":
            user["limit"] = ELITE_LIMIT
        else:
            user["limit"] = FREE_LIMIT
        user["count"] = 0
    logger.info("Monthly limits reset for all users")

async def send_daily_motivation(app):
    """Send daily motivation to all users"""
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        for user_id in user_data.keys():
            message = random.choice(motivation_messages)
            try:
                await app.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Could not send motivation to {user_id}: {e}")

# -------------------------------
# Commands
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"count": 0, "plan": "Free", "limit": FREE_LIMIT}

    welcome_message = (
        "🎓 *Welcome to AI Tutor Pro!*\n\n"
        "This bot helps you master AI, Business, and Crypto by asking smarter questions.\n\n"
        "💡 *Free Plan:* 5 questions per category.\n"
        "🚀 *Pro:* 10 per category + daily motivation.\n"
        "👑 *Elite:* 20 per category + exclusive questions.\n\n"
        "Start learning now by choosing a category below 👇"
    )

    keyboard = [
        [InlineKeyboardButton("🤖 AI", callback_data="AI")],
        [InlineKeyboardButton("💼 Business", callback_data="Business")],
        [InlineKeyboardButton("₿ Crypto", callback_data="Crypto")],
        [InlineKeyboardButton("🌟 Upgrade to Pro", callback_data="upgrade_pro")],
        [InlineKeyboardButton("👑 Upgrade to Elite", callback_data="upgrade_elite")]
    ]
    await update.message.reply_text(welcome_message, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    logger.info(f"User {user_id} started bot.")

async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not can_ask_question(user_id):
        await query.edit_message_text(
            "⚠️ You’ve reached your daily question limit.\nUpgrade to unlock more questions!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌟 Upgrade to Pro", callback_data="upgrade_pro")],
                [InlineKeyboardButton("👑 Upgrade to Elite", callback_data="upgrade_elite")]
            ])
        )
        return

    record_question(user_id)
    category = query.data
    question = random.choice(categories[category])

    await query.edit_message_text(f"🧠 *{category} Insight:*\n\n_{question}_", parse_mode="Markdown")
    logger.info(f"{user_id} asked {category} question: {question}")

async def upgrade_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "upgrade_pro":
        keyboard = [
            [InlineKeyboardButton("💸 Monthly", url=PRO_MONTHLY_URL)],
            [InlineKeyboardButton("💰 Yearly", url=PRO_YEARLY_URL)]
        ]
        await query.edit_message_text("🚀 *Upgrade to Pro Plan* — get 10 questions per category!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        keyboard = [
            [InlineKeyboardButton("💸 Monthly", url=ELITE_MONTHLY_URL)],
            [InlineKeyboardButton("💰 Yearly", url=ELITE_YEARLY_URL)]
        ]
        await query.edit_message_text("👑 *Upgrade to Elite Plan* — full power, 20 questions per category!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# -------------------------------
# Main
# -------------------------------
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(category_handler, pattern="^(AI|Business|Crypto)$"))
    app.add_handler(CallbackQueryHandler(upgrade_handler, pattern="^(upgrade_pro|upgrade_elite)$"))

    asyncio.create_task(send_daily_motivation(app))
    logger.info("🤖 AI Tutor Pro Bot is running...")

    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

