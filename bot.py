import os
import logging
import random
import asyncio
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from openai import OpenAI
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Setup logging
logging.basicConfig(filename="bot.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# Tokens
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# CryptoBot links
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

# AI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Flask keep-alive app
app = Flask(__name__)

@app.route('/')
def home():
    return "AI Tutor Pro is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

# User storage
user_data = {}

# Daily motivation messages
MOTIVATION_QUOTES = [
    "💡 *Ask smart. Think smarter.* Every question builds your future.",
    "🚀 *Consistency beats talent.* One smart question a day keeps failure away.",
    "💰 *Learn AI, earn success.* Knowledge compounds faster than crypto.",
    "🔥 *Winners ask better questions.* Use AI wisely — it’s your mentor 24/7.",
    "🎯 *Focus on progress, not perfection.* The right question moves you forward."
]

# Categories & questions
QUESTIONS = {
    "Business": [
        "What is the smartest way to start a profitable business today?",
        "How can AI help me find new customers?",
        "What are high-demand niches with low competition?",
        "How can I automate parts of my business using AI tools?",
        "How do I make my brand stand out online?"
    ],
    "Crypto": [
        "What are the safest ways to invest in crypto long-term?",
        "How do I use AI to predict crypto trends?",
        "What are the best strategies for passive income in crypto?",
        "How can I analyze new crypto projects effectively?",
        "What is the role of blockchain in future AI systems?"
    ],
    "AI": [
        "How can I use AI to increase my income?",
        "What are the best AI tools for entrepreneurs?",
        "How do I start learning AI for business?",
        "What is the easiest way to use ChatGPT to grow online?",
        "How can I make money with AI automations?"
    ]
}

# Subscription tiers
PLANS = {
    "Free": {"limit": 5},
    "Pro": {"limit": 10},
    "Elite": {"limit": 20}
}

# Helper functions
def get_user_plan(user_id):
    return user_data.get(user_id, {"plan": "Free", "used": 0})

def set_user_plan(user_id, plan):
    user_data[user_id] = {"plan": plan, "used": 0}

def remaining_questions(user_id):
    data = get_user_plan(user_id)
    return PLANS[data["plan"]]["limit"] - data["used"]

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {"plan": "Free", "used": 0}

    welcome = (
        f"🤖 *Welcome to AI Tutor Pro, {user.first_name or 'Learner'}!*\n\n"
        "Ask smarter. Think sharper. Every question gets you closer to success.\n\n"
        "🧭 Use AI to grow your *business*, master *crypto*, and unlock your *potential*.\n\n"
        "💬 You can ask *your own questions anytime* — or explore expert questions below.\n\n"
        "⬇️ Choose your plan to begin:"
    )

    buttons = [
        [InlineKeyboardButton("🆓 Free", callback_data="plan_Free")],
        [InlineKeyboardButton("💼 Pro", callback_data="plan_Pro")],
        [InlineKeyboardButton("👑 Elite", callback_data="plan_Elite")]
    ]
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📘 *How to Use AI Tutor Pro*\n\n"
        "💬 Ask *any question* directly in the chat — AI will respond instantly.\n\n"
        "🧩 Or tap *Questions* to explore smart prompts in AI, Business, and Crypto.\n\n"
        "🚀 Ready for more? [Upgrade to Pro or Elite](https://t.me/ai_tutor_pro_bot) to unlock advanced insights."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", disable_web_page_preview=True)

async def show_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("💼 Business", callback_data="cat_Business")],
        [InlineKeyboardButton("💰 Crypto", callback_data="cat_Crypto")],
        [InlineKeyboardButton("🤖 AI", callback_data="cat_AI")]
    ]
    await update.message.reply_text("📚 Choose your category:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.split("_")[1]
    q_list = QUESTIONS[category]
    buttons = [[InlineKeyboardButton(q, callback_data=f"ask_{category}_{i}")] for i, q in enumerate(q_list)]
    await query.edit_message_text(f"✨ *{category}* questions:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, category, index = query.data.split("_")
    question = QUESTIONS[category][int(index)]
    user_id = query.from_user.id
    data = get_user_plan(user_id)
    plan = data["plan"]

    if data["used"] >= PLANS[plan]["limit"]:
        await query.edit_message_text(
            "⚠️ You've reached your question limit.\n\nUpgrade now to unlock more AI answers.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💼 Upgrade to Pro", url=f"t.me/{PRO_MONTHLY_URL}")],
                [InlineKeyboardButton("👑 Upgrade to Elite", url=f"t.me/{ELITE_MONTHLY_URL}")]
            ])
        )
        return

    user_data[user_id]["used"] += 1

    await query.edit_message_text(f"💭 *{question}*\n\n⌛ Thinking...", parse_mode="Markdown")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}]
    )
    answer = response.choices[0].message.content
    await query.edit_message_text(f"💭 *{question}*\n\n🧠 {answer}", parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": text}]
    )
    answer = response.choices[0].message.content
    await update.message.reply_text(f"🧠 {answer}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_user_plan(user_id)
    left = remaining_questions(user_id)
    await update.message.reply_text(
        f"📊 *Your Plan:* {data['plan']}\n"
        f"💡 *Questions left:* {left}\n\n"
        "Upgrade anytime for more insights:\n👉 [Upgrade Here](https://t.me/ai_tutor_pro_bot)",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def send_daily_motivation(app):
    while True:
        now = datetime.utcnow()
        target = datetime(now.year, now.month, now.day, 14, 0)  # 9 AM EST
        wait = (target - now).total_seconds()
        if wait < 0:
            wait += 86400
        await asyncio.sleep(wait)
        quote = random.choice(MOTIVATION_QUOTES)
        for user_id in user_data:
            try:
                await app.bot.send_message(chat_id=user_id, text=quote, parse_mode="Markdown")
            except Exception:
                continue

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("questions", show_questions))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(handle_category, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(handle_question, pattern="^ask_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    asyncio.create_task(send_daily_motivation(app))
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass


