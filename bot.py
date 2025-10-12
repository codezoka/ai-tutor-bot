import os
import json
import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    CallbackContext, CallbackQueryHandler
)
from openai import OpenAI
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CRYPTOPAY_TOKEN = os.getenv("CRYPTOPAY_TOKEN", "N/A")

# === Initialize OpenAI Client (new SDK) ===
client = OpenAI()

# === Logging setup ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename="bot_log.txt",
)
logger = logging.getLogger(__name__)

# === Load prompt data ===
def load_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return {}

PROMPTS = load_json("prompts.json")
MOTIVATION = load_json("motivation.json").get("messages", [])

# === Helper functions ===
async def ai_response(prompt: str) -> str:
    """Send text to OpenAI and get a response"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are AI Tutor Pro, a concise, motivating expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.8,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "⚠️ Something went wrong with AI generation. Try again later."

# === Telegram command handlers ===
async def start(update: Update, context: CallbackContext):
    text = (
        "🤖 **Welcome to AI Tutor Pro!**\n\n"
        "🚀 *Ask smart. Learn fast. Build your future.*\n\n"
        "🧠 Free Plan: 5 daily smart prompts, unlimited typing.\n"
        "💼 Pro: $9.99/month — for entrepreneurs ready to scale.\n"
        "👑 Elite: $29.99/month — deep AI insights & mentoring.\n\n"
        "⚡ Use /questions or /upgrade to begin your journey!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🧭 *Commands:*\n"
        "/start — Welcome message\n"
        "/questions — Show smart prompts\n"
        "/upgrade — Subscription options\n"
        "/status — Check your current plan\n"
        "/motivate — Get a daily AI motivation boost 💡",
        parse_mode="Markdown"
    )

async def motivate(update: Update, context: CallbackContext):
    if MOTIVATION:
        import random
        message = random.choice(MOTIVATION)
        await update.message.reply_text(f"💬 *AI Insight:*\n_{message}_", parse_mode="Markdown")
    else:
        await update.message.reply_text("No motivation messages found.")

async def questions(update: Update, context: CallbackContext):
    text = (
        "💡 Choose a topic to explore:\n\n"
        "🏢 *Business*: /business\n"
        "💰 *Crypto*: /crypto\n"
        "🧠 *AI & Productivity*: /ai\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def ask_ai(update: Update, context: CallbackContext):
    """Handle any user-typed question"""
    user_input = update.message.text
    await update.message.reply_chat_action("typing")
    reply = await ai_response(user_input)
    await update.message.reply_text(reply)

async def upgrade(update: Update, context: CallbackContext):
    text = (
        "💳 *Upgrade Options:*\n"
        "Pro Plan — $9.99/month\n"
        "Elite Plan — $29.99/month\n\n"
        "⚡ Purchase via @CryptoBot:\n"
        "👉 [Pro Plan](https://t.me/CryptoBot?start=AAExxxxxxxxx)\n"
        "👉 [Elite Plan](https://t.me/CryptoBot?start=BBExxxxxxxxx)\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)

async def status(update: Update, context: CallbackContext):
    await update.message.reply_text("🟢 You’re currently on the *Free Plan*.\nUpgrade anytime with /upgrade.", parse_mode="Markdown")

# === Daily motivation job ===
async def daily_motivation_job(context: CallbackContext):
    chat_id = context.job.chat_id
    if MOTIVATION:
        import random
        message = random.choice(MOTIVATION)
        await context.bot.send_message(chat_id, f"🌞 *Daily AI Insight:*\n_{message}_", parse_mode="Markdown")

# === Schedule daily motivational messages ===
def schedule_jobs(application):
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(lambda: application.create_task(send_motivation_all(application)), "cron", hour=15, minute=0)
    scheduler.start()

async def send_motivation_all(application):
    """Send motivation to all users (expandable with DB tracking)."""
    logger.info("Daily motivation trigger executed.")

# === Main ===
async def main():
    print("🤖 AI Tutor Pro Bot starting...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("motivate", motivate))
    app.add_handler(CommandHandler("questions", questions))
    app.add_handler(CommandHandler("upgrade", upgrade))
    app.add_handler(CommandHandler("status", status))

    # Handle freeform AI chat
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_ai))

    # Scheduler
    schedule_jobs(app)

    print("✅ AI Tutor Pro is running...")
    await app.run_polling()

import asyncio

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())




