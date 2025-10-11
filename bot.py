import os, json, asyncio, nest_asyncio, logging, random
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Load .env variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# CryptoBot URLs
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Allow nested async (for Windows)
nest_asyncio.apply()

# Logging setup
logging.basicConfig(filename="bot.log", level=logging.INFO, format="%(asctime)s - %(message)s")
print("🤖 AI Tutor Pro Bot starting...")

# Free/Pro/Elite limits
QUESTION_LIMITS = {"free": 5, "pro": 10, "elite": 20}

# Example categories
CATEGORIES = ["AI", "Business", "Crypto", "Motivation"]

QUESTIONS = {
    "AI": [
        "How can AI improve productivity?",
        "What’s the difference between machine learning and AI?",
        "How can small businesses use AI effectively?",
        "What are the risks of using AI?",
        "What AI tools are shaping the future?"
    ],
    "Business": [
        "What’s the best way to scale a startup?",
        "How do successful founders handle failure?",
        "What makes a great business leader?",
        "How do you validate a new product idea?",
        "What’s the future of remote business?"
    ],
    "Crypto": [
        "Why does Bitcoin’s price fluctuate?",
        "What’s the safest way to invest in crypto?",
        "What role will crypto play in global finance?",
        "What’s the difference between blockchain and crypto?",
        "How can I earn passive income through crypto?"
    ],
    "Motivation": [
        "What daily habits separate successful people?",
        "How do I overcome fear of failure?",
        "What’s the link between mindset and success?",
        "How do I build long-term discipline?",
        "How can I stay consistent when motivation fades?"
    ]
}

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data[user.id] = {"plan": "free", "used": 0}

    welcome_text = (
        f"🔥 *Welcome to AI Tutor Pro!* 🔥\n\n"
        f"Ask smart — get smart answers.\n"
        f"Don’t waste time — learn what *really matters* in AI, Business & Crypto.\n\n"
        f"💎 Upgrade your knowledge. Build your future.\n\n"
        f"Choose a category below to start 👇"
    )

    buttons = [
        [InlineKeyboardButton("🤖 AI", callback_data="AI"),
         InlineKeyboardButton("💼 Business", callback_data="Business")],
        [InlineKeyboardButton("💰 Crypto", callback_data="Crypto"),
         InlineKeyboardButton("🔥 Motivation", callback_data="Motivation")],
        [InlineKeyboardButton("⭐ Upgrade to PRO", callback_data="upgrade_pro"),
         InlineKeyboardButton("💎 Go ELITE", callback_data="upgrade_elite")]
    ]

    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    if data in CATEGORIES:
        plan = user_data[user.id]["plan"]
        used = user_data[user.id]["used"]
        limit = QUESTION_LIMITS[plan]

        if used >= limit:
            await query.message.reply_text("⚠️ You’ve reached your question limit! Upgrade to continue 👇")
            await show_upgrade_options(query)
            return

        question = random.choice(QUESTIONS[data])
        user_data[user.id]["used"] += 1

        await query.message.reply_text(f"💬 *{data} Insight:* {question}", parse_mode="Markdown")
        response = ask_openai(question)
        await query.message.reply_text(f"🤖 {response}")

    elif data == "upgrade_pro":
        await query.message.reply_text(
            f"🌟 Unlock more power:\n\n"
            f"PRO → 10 questions/category\n\n"
            f"🔗 [Monthly Subscription]({PRO_MONTHLY_URL})\n"
            f"🔗 [Yearly Subscription]({PRO_YEARLY_URL})",
            parse_mode="Markdown", disable_web_page_preview=True)
    elif data == "upgrade_elite":
        await query.message.reply_text(
            f"💎 Go ELITE:\n\n"
            f"20 questions/category + VIP motivation\n\n"
            f"🔗 [Monthly Elite Plan]({ELITE_MONTHLY_URL})\n"
            f"🔗 [Yearly Elite Plan]({ELITE_YEARLY_URL})",
            parse_mode="Markdown", disable_web_page_preview=True)

def ask_openai(prompt):
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI Error: {e}")
        return "⚠️ Error fetching AI response."

async def daily_motivation(app):
    try:
        with open("motivation.json", "r", encoding="utf-8") as f:
            msgs = json.load(f)["messages"]
        message = random.choice(msgs)
        for user_id in user_data.keys():
            try:
                await app.bot.send_message(chat_id=user_id, text=f"🌞 Daily Motivation:\n\n{message}")
            except Exception as e:
                logging.warning(f"Couldn’t send message to {user_id}: {e}")
    except Exception as e:
        logging.error(f"Motivation system error: {e}")

async def scheduler(app):
    while True:
        now = datetime.utcnow()
        if now.hour == 15 and now.minute == 0:
            await daily_motivation(app)
        await asyncio.sleep(60)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    asyncio.create_task(scheduler(app))
    print("🤖 AI Tutor Pro is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

