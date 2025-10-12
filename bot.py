import os
import asyncio
import logging
import nest_asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from openai import OpenAI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import random
import json

# ---------------- CONFIG ---------------- #
load_dotenv()
nest_asyncio.apply()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
logging.basicConfig(level=logging.INFO)

# ------------- MOTIVATION SYSTEM -------- #
def load_motivations():
    try:
        with open("motivations.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return ["✨ Stay curious!", "🚀 Keep learning, keep growing!", "💡 Every day is a chance to improve!"]

motivations = load_motivations()

async def send_daily_motivation(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    message = random.choice(motivations)
    await context.bot.send_message(chat_id=chat_id, text=message)

# ------------- COMMANDS ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 **Welcome to AI Tutor Pro!**\n\n"
        "Ask smart, learn fast, and shape your future with AI. 💡\n"
        "Stay focused, learn what matters, and move forward 🚀\n\n"
        "**Plans:**\n"
        "💬 Free: 5 prompts/day\n"
        "⚡ Pro: $9.99 → 30 days\n"
        "👑 Elite: $29.99 → 30 days\n\n"
        "Use /questions or /upgrade to start learning!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 Available commands:\n"
        "/start - Welcome message\n"
        "/help - Show help\n"
        "/questions - Practice AI questions\n"
        "/upgrade - Upgrade your plan\n"
        "/motivate - Get a motivational quote\n"
    )

async def motivate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quote = random.choice(motivations)
    await update.message.reply_text(quote)

async def questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = [
        "💭 What’s one new AI concept you learned today?",
        "🤖 How would you explain machine learning to a 10-year-old?",
        "⚡ What real-world problem could you solve using AI?",
        "💡 What’s your goal in learning AI this month?"
    ]
    await update.message.reply_text(random.choice(questions))

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚡ Upgrade to Pro - $9.99", callback_data="pro")],
        [InlineKeyboardButton("👑 Upgrade to Elite - $29.99", callback_data="elite")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose your plan:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    await update.message.chat.send_action(action="typing")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI tutor who explains clearly and concisely."},
                {"role": "user", "content": user_input}
            ]
        )
        reply = response.choices[0].message.content.strip()
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"AI Error: {e}")
        await update.message.reply_text("⚠️ Sorry, I couldn’t process that. Please try again.")

# ------------- MAIN LOOP ---------------- #
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("motivate", motivate))
    app.add_handler(CommandHandler("questions", questions))
    app.add_handler(CommandHandler("upgrade", upgrade))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Daily motivational job
    scheduler = AsyncIOScheduler()
    scheduler.start()

    logging.info("🤖 AI Tutor Pro bot is starting...")
    await app.run_polling()

# ------------- SAFE ASYNC ENTRY ------------- #
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()



