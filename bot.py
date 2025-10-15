import os
import logging
import asyncio
import nest_asyncio
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
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
    ContextTypes,
    filters,
)
from openai import OpenAI
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PRO_MONTHLY_URL = "https://t.me/send?start=IVdixIeFSP3W"
PRO_YEARLY_URL = "https://t.me/send?start=IVRnAnXOWzRM"
ELITE_MONTHLY_URL = "https://t.me/send?start=IVfwy1t6hcu9"
ELITE_YEARLY_URL = "https://t.me/send?start=IVxMW0UNvl7d"

# === Logging ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# === Flask app (keeps DigitalOcean app alive 24/7) ===
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "AI Tutor Pro is running 24/7 🚀"

# === AI setup ===
client = OpenAI(api_key=OPENAI_API_KEY)

# === Question Data ===
QUESTIONS = {
    "Business": [
        "What are the fundamentals of building a profitable business?",
        "How can small businesses use AI for growth?",
        "What is the most effective marketing strategy in 2025?",
        "How can I turn an idea into a startup?",
        "What are the biggest business mistakes to avoid?"
    ],
    "Crypto": [
        "How does blockchain ensure security?",
        "What are the most promising crypto projects in 2025?",
        "How can AI improve cryptocurrency trading?",
        "What causes crypto price volatility?",
        "What are the future trends in DeFi?"
    ],
    "AI": [
        "How does machine learning differ from deep learning?",
        "What are the ethical implications of AI in business?",
        "How can I integrate AI into my company?",
        "What is prompt engineering and why is it important?",
        "How will AI change jobs by 2030?"
    ]
}

# === Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🆓 Free", callback_data="plan_free")],
        [InlineKeyboardButton("💼 Pro", callback_data="plan_pro")],
        [InlineKeyboardButton("🔥 Elite", callback_data="plan_elite")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🤖 <b>Welcome to AI Tutor Pro, Z!</b>\n\n"
        "Ask smarter. Think sharper. Every question gets you closer to success.\n\n"
        "🚀 Use AI to grow your <b>business</b>, master <b>crypto</b>, and unlock your <b>potential</b>.\n\n"
        "💬 You can ask your <b>own questions anytime</b> — or explore expert questions below.\n\n"
        "🧭 Choose your plan to begin:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📘 <b>How to Use AI Tutor Pro</b>\n\n"
        "💬 Ask <b>any question</b> directly in the chat — AI will respond instantly.\n"
        "🌱 Or tap <a href='https://t.me/ai_tutor_pro_bot?start=questions'>Questions</a> "
        "to explore smart prompts in AI, Business, and Crypto.\n\n"
        "🚀 Ready for more? <a href='https://t.me/ai_tutor_pro_bot?start=upgrade'>Upgrade to Pro</a> "
        "or <a href='https://t.me/ai_tutor_pro_bot?start=upgrade'>Elite</a> for advanced insights."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📊 <b>Your Plan:</b> Free\n"
        "💡 <b>Questions left:</b> 3\n\n"
        "Upgrade anytime for more insights:\n"
        "👉 <a href='https://t.me/ai_tutor_pro_bot?start=upgrade'>Upgrade Here</a>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# === Plan Handlers ===
async def plan_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "plan_free":
        await show_categories(query)
    elif choice in ["plan_pro", "plan_elite"]:
        await upgrade_countdown(query, choice)

# === Show categories ===
async def show_categories(query):
    keyboard = [
        [InlineKeyboardButton("💼 Business", callback_data="cat_business")],
        [InlineKeyboardButton("💰 Crypto", callback_data="cat_crypto")],
        [InlineKeyboardButton("🤖 AI", callback_data="cat_ai")],
    ]
    await query.message.reply_text("📚 <b>Choose your category:</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

# === Category Clicks ===
async def category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mapping = {
        "cat_business": "Business",
        "cat_crypto": "Crypto",
        "cat_ai": "AI"
    }

    cat = mapping.get(query.data)
    if not cat:
        return

    # Sub-plan menu for Free / Pro / Elite
    keyboard = [
        [InlineKeyboardButton("🆓 Free", callback_data=f"show_free_{cat}")],
        [InlineKeyboardButton("💼 Pro", callback_data=f"show_pro_{cat}")],
        [InlineKeyboardButton("🔥 Elite", callback_data=f"show_elite_{cat}")]
    ]
    await query.message.reply_text(f"📖 <b>{cat}:</b> Choose your plan:", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

# === Show Free Questions ===
async def show_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    plan = data[1]
    cat = data[2]

    if plan == "free":
        qs = QUESTIONS[cat]
        buttons = [[InlineKeyboardButton(q, callback_data=f"q_{cat}_{i}")] for i, q in enumerate(qs)]
        await query.message.reply_text(
            f"📚 <b>{cat} Questions:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await upgrade_countdown(query, plan)

# === Handle Question Clicks ===
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, cat, idx = query.data.split("_")
    q_text = QUESTIONS[cat][int(idx)]
    await query.message.reply_text(f"💬 {q_text}")
    await ai_response(update, context, q_text)

# === Countdown for Upgrade ===
async def upgrade_countdown(query, plan):
    links = {
        "pro": (PRO_MONTHLY_URL, PRO_YEARLY_URL),
        "elite": (ELITE_MONTHLY_URL, ELITE_YEARLY_URL),
    }
    month_url, year_url = links.get(plan, ("#", "#"))

    msg = await query.message.reply_text("⏳ Special offer ends in 10 seconds!")
    for i in range(10, 0, -1):
        await asyncio.sleep(1)
        try:
            await msg.edit_text(f"⏳ Special offer ends in {i} seconds!")
        except:
            break

    text = (
        f"🔥 Unlock <b>{plan.capitalize()} Plan</b> access now:\n\n"
        f"💼 <a href='{month_url}'>Monthly</a>\n"
        f"🏆 <a href='{year_url}'>Yearly (Save 20%)</a>"
    )
    await query.message.reply_text(text, parse_mode=ParseMode.HTML)

# === AI response for any typed question ===
async def ai_response(update: Update, context: ContextTypes.DEFAULT_TYPE, custom_text=None):
    user_input = custom_text or update.message.text
    if not user_input:
        return

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_input}]
        )
        answer = completion.choices[0].message.content
        if update.message:
            await update.message.reply_text(answer)
        else:
            await update.callback_query.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text("⚠️ AI is currently busy. Try again later.")
        logging.error(e)

# === Scheduler for daily motivation (optional) ===
def send_motivation():
    logging.info("Motivation message scheduled at 9:00 AM (US time)")

scheduler = BackgroundScheduler()
scheduler.start()

# === Main ===
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(plan_choice, pattern="^plan_"))
    app.add_handler(CallbackQueryHandler(category_choice, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(show_questions, pattern="^show_"))
    app.add_handler(CallbackQueryHandler(handle_question, pattern="^q_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_response))

    print("✅ Bot connected successfully!")
    await app.run_polling()

# === Run Bot + Flask (DigitalOcean-ready) ===
if __name__ == "__main__":
    nest_asyncio.apply()
    import threading

    # Run the Telegram bot in a separate thread
    def run_telegram():
        asyncio.run(main())

    threading.Thread(target=run_telegram).start()

    # Run Flask on the main thread
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


