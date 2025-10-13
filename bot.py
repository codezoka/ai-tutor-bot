import os
import logging
import random
import json
import asyncio
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import nest_asyncio

nest_asyncio.apply()

# ======================
# ✅ CONFIGURATION
# ======================
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PRO_MONTHLY_URL = "https://t.me/send?start=IVdixIeFSP3W"
PRO_YEARLY_URL = "https://t.me/send?start=IVRnAnXOWzRM"
ELITE_MONTHLY_URL = "https://t.me/send?start=IVfwy1t6hcu9"
ELITE_YEARLY_URL = "https://t.me/send?start=IVxMW0UNvl7d"

# ======================
# ✅ LOGGING
# ======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ======================
# ✅ USER STORAGE
# ======================
users = {}

FREE_LIMIT = 5
PRO_LIMIT = 10
ELITE_LIMIT = 20

# ======================
# ✅ FLASK KEEP ALIVE
# ======================
app = Flask('ai_tutor_pro')

@app.route('/')
def home():
    return "AI Tutor Pro is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask).start()

# ======================
# ✅ MOTIVATION SYSTEM
# ======================
def load_motivations():
    try:
        with open("motivation.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return ["Stay curious and learn every day!", "Smart questions lead to smart answers."]

motivations = load_motivations()

async def send_daily_motivation(app):
    while True:
        now = datetime.utcnow()
        target = datetime(now.year, now.month, now.day, 14, 0)  # 9AM EST = 14 UTC
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        for user_id in users:
            msg = random.choice(motivations)
            try:
                await app.bot.send_message(chat_id=user_id, text=f"💡 *Daily Boost:*\n{msg}", parse_mode="Markdown")
            except:
                continue

# ======================
# ✅ BOT COMMANDS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users[user.id] = {"plan": "Free", "used": 0}

    welcome_text = (
        f"🤖 *Welcome to AI Tutor Pro!*\n\n"
        "Ask smart. Learn fast. Grow unstoppable.\n\n"
        "✨ Here, every question is a step toward mastery — in Business, Crypto, or AI.\n\n"
        "Start free or upgrade for deeper insights and pro-level tools.\n\n"
        "🔥 *Ask Smart. Think Smart. Succeed.*"
    )

    buttons = [
        [InlineKeyboardButton("❓ Questions", callback_data="questions")],
        [InlineKeyboardButton("💎 Upgrade", callback_data="upgrade")],
        [InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]

    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🧠 *How to use AI Tutor Pro:*\n\n"
        "• Tap *❓ Questions* to choose a category (AI, Business, or Crypto).\n"
        "• You can always *type your own questions* — no limits!\n"
        "• Free plan: 5 guided questions per topic.\n"
        "• Pro & Elite plans unlock more power and smart insights.\n\n"
        "Ready to level up your learning? 🚀"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ======================
# ✅ QUESTIONS
# ======================
questions = {
    "AI": [
        "What is AI and how is it transforming industries?",
        "How can I use AI to increase productivity?",
        "What are the key ethical challenges in AI?",
        "How do neural networks actually learn?",
        "How can AI help me automate my business?"
    ],
    "Business": [
        "What are the fundamentals of building a profitable business?",
        "How can small businesses use AI for growth?",
        "What is the most effective marketing strategy in 2025?",
        "How can I turn an idea into a startup?",
        "What are the biggest business mistakes to avoid?"
    ],
    "Crypto": [
        "What is blockchain and why does it matter?",
        "How can I start investing in crypto safely?",
        "What are the best long-term crypto strategies?",
        "How is AI changing crypto trading?",
        "What trends are shaping the crypto market in 2025?"
    ]
}

async def questions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan_buttons = [
        [InlineKeyboardButton("🆓 Free", callback_data="free")],
        [InlineKeyboardButton("💼 Pro", callback_data="pro")],
        [InlineKeyboardButton("👑 Elite", callback_data="elite")]
    ]
    await update.callback_query.message.reply_text("Choose your plan:", reply_markup=InlineKeyboardMarkup(plan_buttons))

async def topic_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query.data
    context.user_data["plan"] = query
    topics = [
        [InlineKeyboardButton("🤖 AI", callback_data="AI")],
        [InlineKeyboardButton("💼 Business", callback_data="Business")],
        [InlineKeyboardButton("₿ Crypto", callback_data="Crypto")]
    ]
    await update.callback_query.message.reply_text("Choose a topic:", reply_markup=InlineKeyboardMarkup(topics))

async def show_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = update.callback_query.data
    q_list = questions[topic]
    q_text = "\n\n".join([f"{i+1}. {q}" for i, q in enumerate(q_list[:5])])
    await update.callback_query.message.reply_text(f"📚 *{topic} Questions:*\n\n{q_text}", parse_mode="Markdown")

# ======================
# ✅ UPGRADE SYSTEM
# ======================
async def upgrade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("💼 Upgrade to PRO", callback_data="pro_upgrade")],
        [InlineKeyboardButton("👑 Upgrade to ELITE", callback_data="elite_upgrade")]
    ]
    await update.callback_query.message.reply_text("Choose your plan to upgrade:", reply_markup=InlineKeyboardMarkup(buttons))

async def upgrade_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == "pro_upgrade":
        buttons = [
            [InlineKeyboardButton("💳 Monthly - $9.99", url=PRO_MONTHLY_URL)],
            [InlineKeyboardButton("🔥 Yearly - $99.99 (20% OFF for 30s!)", url=PRO_YEARLY_URL)]
        ]
        await update.callback_query.message.reply_text("Choose your PRO plan:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "elite_upgrade":
        buttons = [
            [InlineKeyboardButton("💳 Monthly - $19.99", url=ELITE_MONTHLY_URL)],
            [InlineKeyboardButton("🔥 Yearly - $199.99 (20% OFF for 30s!)", url=ELITE_YEARLY_URL)]
        ]
        await update.callback_query.message.reply_text("Choose your ELITE plan:", reply_markup=InlineKeyboardMarkup(buttons))

# ======================
# ✅ STATUS
# ======================
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = users.get(update.effective_user.id, {"plan": "Free", "used": 0})
    plan = user["plan"]
    used = user["used"]
    remaining = max(0, FREE_LIMIT - used) if plan == "Free" else "Unlimited"
    await update.message.reply_text(
        f"📊 *Your Plan:* {plan}\n"
        f"💬 *Questions Left:* {remaining}\n\n"
        f"Upgrade anytime for more power 🚀",
        parse_mode="Markdown"
    )

# ======================
# ✅ AI RESPONSE HANDLER
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    user = users.setdefault(user_id, {"plan": "Free", "used": 0})
    if user["plan"] == "Free" and user["used"] >= FREE_LIMIT:
        await update.message.reply_text("⚠️ You’ve reached your Free limit. Upgrade to Pro or Elite to continue!")
        return

    user["used"] += 1
    await update.message.reply_text(f"💡 AI Response:\n{text} — that’s a smart question! Keep learning! 🚀")

# ======================
# ✅ MAIN
# ======================
async def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(questions_menu, pattern="^questions$"))
    application.add_handler(CallbackQueryHandler(topic_menu, pattern="^(free|pro|elite)$"))
    application.add_handler(CallbackQueryHandler(show_questions, pattern="^(AI|Business|Crypto)$"))
    application.add_handler(CallbackQueryHandler(upgrade_menu, pattern="^upgrade$"))
    application.add_handler(CallbackQueryHandler(upgrade_options, pattern="^(pro_upgrade|elite_upgrade)$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    asyncio.create_task(send_daily_motivation(application))
    logging.info("🤖 AI Tutor Pro Bot is now running 24/7 on DigitalOcean...")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())



