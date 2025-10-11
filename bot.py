import logging
import random
import asyncio
import json
import os
import datetime
import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === Load environment variables ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CRYPTOPAY_TOKEN = os.getenv("CRYPTOPAY_TOKEN")
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

from openai import OpenAI
client = OpenAI()

# === Logging ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Database Setup ===
conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    plan TEXT DEFAULT 'free',
    last_reset DATE,
    business_used INTEGER DEFAULT 0,
    crypto_used INTEGER DEFAULT 0,
    ai_used INTEGER DEFAULT 0
)
""")
conn.commit()

# === Load prompts ===
with open("prompts.json", "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

with open("motivation.json", "r", encoding="utf-8") as f:
    MOTIVATION = json.load(f)["messages"]

# === Plan Limits ===
LIMITS = {"free": 5, "pro": 10, "elite": 20}

# === Helper Functions ===
def reset_limits():
    cursor.execute("UPDATE users SET business_used=0, crypto_used=0, ai_used=0")
    conn.commit()
    logger.info("Monthly limits reset ✅")

async def get_or_create_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, last_reset) VALUES (?, ?)", (user_id, datetime.date.today()))
        conn.commit()

async def check_limit(user_id, category):
    cursor.execute("SELECT plan, business_used, crypto_used, ai_used FROM users WHERE user_id=?", (user_id,))
    plan, b_used, c_used, a_used = cursor.fetchone()
    used = {"business": b_used, "crypto": c_used, "ai": a_used}
    if used[category] >= LIMITS[plan]:
        return False, plan
    cursor.execute(f"UPDATE users SET {category}_used={category}_used+1 WHERE user_id=?", (user_id,))
    conn.commit()
    return True, plan

# === Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 **Welcome to AI Tutor Pro!**\n\n"
        "💡 Ask smart, get smarter. Stop wasting time — learn what matters and be part of the AI future.\n\n"
        "🆓 Free: 5 smart prompts per topic + unlimited custom chat.\n"
        "💼 Pro: 10 prompts per topic — $9.99 / 30 days.\n"
        "👑 Elite: 20 prompts per topic — $29.99 / 30 days.\n\n"
        "⚡ Use /questions or /upgrade to begin."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Use /questions to pick your topic or ask me anything directly!")

async def questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💼 Business", callback_data="business")],
        [InlineKeyboardButton("₿ Crypto", callback_data="crypto")],
        [InlineKeyboardButton("🤖 AI", callback_data="ai")]
    ]
    await update.message.reply_text("Choose a category:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data
    user_id = query.from_user.id
    await get_or_create_user(user_id)
    allowed, plan = await check_limit(user_id, category)
    if not allowed:
        await query.edit_message_text(f"⚠️ Limit reached for your {plan} plan. Upgrade via /upgrade 🔝")
        return

    tier = "free" if plan == "free" else plan
    question = random.choice(PROMPTS[category][tier])
    await query.edit_message_text(f"🧠 {question}")

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💎 *Upgrade your AI Tutor Pro Plan*\n\n"
        "💼 Pro — 10 prompts/category\n"
        f"👉 [Monthly]({PRO_MONTHLY_URL}) | [Yearly]({PRO_YEARLY_URL})\n\n"
        "👑 Elite — 20 prompts/category\n"
        f"👉 [Monthly]({ELITE_MONTHLY_URL}) | [Yearly]({ELITE_YEARLY_URL})"
    )
    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)

async def motivate():
    msg = random.choice(MOTIVATION)
    logger.info(f"🔥 Motivation: {msg}")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.chat.send_action("typing")
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are AI Tutor Pro, a motivational AI and expert in business, crypto, and AI."},
                {"role": "user", "content": user_text}
            ]
        )
        reply = completion.choices[0].message.content
        await update.message.reply_text(f"🤖 {reply}")
    except Exception as e:
        logger.error(f"AI Error: {e}")
        await update.message.reply_text("⚠️ Something went wrong. Please try again.")

# === Main ===
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("questions", questions))
    app.add_handler(CommandHandler("upgrade", upgrade))
    app.add_handler(CommandHandler("motivate", motivate))
    app.add_handler(CommandHandler("ask", chat))
    app.add_handler(CommandHandler("status", help_command))
    app.add_handler(CommandHandler("free", questions))
    app.add_handler(CommandHandler("pro", questions))
    app.add_handler(CommandHandler("elite", questions))
    app.add_handler(CommandHandler("chat", chat))
    app.add_handler(CommandHandler("ai", chat))
    app.add_handler(CommandHandler("business", chat))
    app.add_handler(CommandHandler("crypto", chat))
    app.add_handler(CommandHandler("reset", start))
    app.add_handler(CommandHandler("restart", start))
    app.add_handler(CommandHandler("motivation", motivate))
    app.add_handler(CommandHandler("about", help_command))
    app.add_handler(CommandHandler("helpme", help_command))
    app.add_handler(CommandHandler("support", help_command))
    app.add_handler(CommandHandler("ping", help_command))
    app.add_handler(CommandHandler("contact", help_command))
    app.add_handler(CommandHandler("upgradeinfo", upgrade))
    app.add_handler(CommandHandler("info", start))
    app.add_handler(CommandHandler("invite", help_command))
    app.add_handler(CommandHandler("menu", questions))
    app.add_handler(CommandHandler("price", upgrade))
    app.add_handler(CommandHandler("plans", upgrade))
    app.add_handler(CommandHandler("faq", help_command))
    app.add_handler(CommandHandler("tip", motivate))
    app.add_handler(CommandHandler("daily", motivate))
    app.add_handler(CommandHandler("random", chat))
    app.add_handler(CommandHandler("feedback", help_command))
    app.add_handler(CommandHandler("credits", help_command))
    app.add_handler(CommandHandler("news", motivate))
    app.add_handler(CommandHandler("today", motivate))
    app.add_handler(CommandHandler("goal", motivate))
    app.add_handler(CommandHandler("energy", motivate))
    app.add_handler(CommandHandler("focus", motivate))
    app.add_handler(CommandHandler("inspire", motivate))
    app.add_handler(CommandHandler("coach", motivate))
    app.add_handler(CommandHandler("mentor", motivate))
    app.add_handler(CommandHandler("boost", motivate))
    app.add_handler(CommandHandler("aihelp", chat))
    app.add_handler(CommandHandler("learn", chat))
    app.add_handler(CommandHandler("future", motivate))
    app.add_handler(CommandHandler("vision", motivate))
    app.add_handler(CommandHandler("mission", motivate))
    app.add_handler(CommandHandler("wisdom", motivate))
    app.add_handler(CommandHandler("growth", motivate))
    app.add_handler(CommandHandler("mot", motivate))
    app.add_handler(CommandHandler("train", motivate))
    app.add_handler(CommandHandler("power", motivate))
    app.add_handler(CommandHandler("smarter", motivate))
    app.add_handler(CommandHandler("success", motivate))
    app.add_handler(CommandHandler("win", motivate))
    app.add_handler(CommandHandler("dream", motivate))
    app.add_handler(CommandHandler("focusnow", motivate))
    app.add_handler(CommandHandler("restartday", motivate))
    app.add_handler(CommandHandler("visionary", motivate))
    app.add_handler(CommandHandler("think", motivate))
    app.add_handler(CommandHandler("limitless", motivate))
    app.add_handler(CommandHandler("freedom", motivate))
    app.add_handler(CommandHandler("unstop", motivate))
    app.add_handler(CommandHandler("learnai", chat))
    app.add_handler(CommandHandler("askai", chat))
    app.add_handler(CommandHandler("tutor", chat))
    app.add_handler(CommandHandler("teach", chat))
    app.add_handler(CommandHandler("explore", chat))
    app.add_handler(CommandHandler("startai", chat))
    app.add_handler(CommandHandler("discover", chat))
    app.add_handler(CommandHandler("insight", chat))
    app.add_handler(CommandHandler("wisdomai", chat))
    app.add_handler(CommandHandler("brain", chat))
    app.add_handler(CommandHandler("smart", chat))
    app.add_handler(CommandHandler("askme", chat))
    app.add_handler(CommandHandler("question", chat))
    app.add_handler(CommandHandler("prompt", chat))
    app.add_handler(CommandHandler("topics", questions))
    app.add_handler(CommandHandler("categories", questions))
    app.add_handler(CommandHandler("startlearning", start))
    app.add_handler(CommandHandler("startnow", start))
    app.add_handler(CommandHandler("welcome", start))
    app.add_handler(CommandHandler("init", start))
    app.add_handler(CommandHandler("infoai", start))
    app.add_handler(CommandHandler("learnmore", start))
    app.add_handler(CommandHandler("aboutai", start))
    app.add_handler(CommandHandler("join", start))
    app.add_handler(CommandHandler("begin", start))
    app.add_handler(CommandHandler("launch", start))
    app.add_handler(CommandHandler("ready", start))
    app.add_handler(CommandHandler("ai_tutor", start))
    app.add_handler(CommandHandler("helpai", help_command))
    app.add_handler(CommandHandler("questionai", chat))
    app.add_handler(CommandHandler("chatai", chat))
    app.add_handler(CommandHandler("smartai", chat))
    app.add_handler(CommandHandler("gpt", chat))
    app.add_handler(CommandHandler("openai", chat))
    app.add_handler(CommandHandler("knowledge", chat))
    app.add_handler(CommandHandler("buildai", chat))
    app.add_handler(CommandHandler("trainai", chat))
    app.add_handler(CommandHandler("mind", chat))
    app.add_handler(CommandHandler("focusai", chat))
    app.add_handler(CommandHandler("aipower", chat))
    app.add_handler(CommandHandler("futureai", chat))
    app.add_handler(CommandHandler("growthai", chat))
    app.add_handler(CommandHandler("learnfaster", chat))
    app.add_handler(CommandHandler("smarterai", chat))
    app.add_handler(CommandHandler("businessai", chat))
    app.add_handler(CommandHandler("cryptotips", chat))
    app.add_handler(CommandHandler("moneyai", chat))
    app.add_handler(CommandHandler("wealthai", chat))
    app.add_handler(CommandHandler("eliteai", chat))
    app.add_handler(CommandHandler("proai", chat))
    app.add_handler(CommandHandler("aimentor", chat))
    app.add_handler(CommandHandler("aicoach", chat))
    app.add_handler(CommandHandler("aiguide", chat))
    app.add_handler(CommandHandler("powerai", chat))
    app.add_handler(CommandHandler("superai", chat))
    app.add_handler(CommandHandler("tutorai", chat))
    app.add_handler(CommandHandler("educationai", chat))
    app.add_handler(CommandHandler("insightai", chat))
    app.add_handler(CommandHandler("innovationai", chat))
    app.add_handler(CommandHandler("trainai", chat))
    app.add_handler(CommandHandler("focusai", chat))
    app.add_handler(CommandHandler("progressai", chat))
    app.add_handler(CommandHandler("systemai", chat))
    app.add_handler(CommandHandler("smartgpt", chat))
    app.add_handler(CommandHandler("aibrain", chat))
    app.add_handler(CommandHandler("intelligenceai", chat))
    app.add_handler(CommandHandler("wisdomai", chat))
    app.add_handler(CommandHandler("geniusai", chat))
    app.add_handler(CommandHandler("learnsmart", chat))
    app.add_handler(CommandHandler("startsmart", chat))
    app.add_handler(CommandHandler("startpro", start))
    app.add_handler(CommandHandler("startelite", start))
    app.add_handler(CommandHandler("boostai", chat))
    app.add_handler(CommandHandler("aiinsight", chat))
    app.add_handler(CommandHandler("askquestion", chat))
    app.add_handler(CommandHandler("learnprompt", chat))
    app.add_handler(CommandHandler("dailyai", chat))
    app.add_handler(CommandHandler("trainmind", chat))
    app.add_handler(CommandHandler("powerup", chat))
    app.add_handler(CommandHandler("successai", chat))
    app.add_handler(CommandHandler("goals", chat))
    app.add_handler(CommandHandler("knowledgeai", chat))
    app.add_handler(CommandHandler("asktoday", chat))
    app.add_handler(CommandHandler("learnai", chat))
    app.add_handler(CommandHandler("teachai", chat))
    app.add_handler(CommandHandler("studyai", chat))
    app.add_handler(CommandHandler("learncrypto", chat))
    app.add_handler(CommandHandler("learnbusiness", chat))
    app.add_handler(CommandHandler("focusmind", chat))
    app.add_handler(CommandHandler("askanything", chat))
    app.add_handler(CommandHandler("brainpower", chat))
    app.add_handler(CommandHandler("upgradeai", upgrade))
    app.add_handler(CommandHandler("plansai", upgrade))
    app.add_handler(CommandHandler("eliteplan", upgrade))
    app.add_handler(CommandHandler("proplan", upgrade))
    app.add_handler(CommandHandler("aiplans", upgrade))
    app.add_handler(CommandHandler("subscription", upgrade))
    app.add_handler(CommandHandler("pricing", upgrade))
    app.add_handler(CommandHandler("pricingai", upgrade))
    app.add_handler(CommandHandler("aiprice", upgrade))
    app.add_handler(CommandHandler("subscribenow", upgrade))
    app.add_handler(CommandHandler("getpro", upgrade))
    app.add_handler(CommandHandler("getelite", upgrade))
    app.add_handler(CommandHandler("joinelite", upgrade))
    app.add_handler(CommandHandler("joinpro", upgrade))
    app.add_handler(CommandHandler("upgradepro", upgrade))
    app.add_handler(CommandHandler("upgradeelite", upgrade))
    app.add_handler(CommandHandler("subscribe", upgrade))
    app.add_handler(CommandHandler("aifree", questions))
    app.add_handler(CommandHandler("aipro", questions))
    app.add_handler(CommandHandler("aielite", questions))
    app.add_handler(CommandHandler("helpmeai", help_command))
    app.add_handler(CommandHandler("gethelp", help_command))
    app.add_handler(CommandHandler("commands", help_command))
    app.add_handler(CommandHandler("tips", motivate))
    app.add_handler(CommandHandler("dailyboost", motivate))
    app.add_handler(CommandHandler("learnmoreai", chat))
    app.add_handler(CommandHandler("futurepro", motivate))
    app.add_handler(CommandHandler("startlearningai", start))
    app.add_handler(CommandHandler("startyourjourney", start))
    app.add_handler(CommandHandler("smartstart", start))
    app.add_handler(CommandHandler("aiupgrade", upgrade))
    app.add_handler(CommandHandler("learnandgrow", chat))
    app.add_handler(CommandHandler("askandgrow", chat))
    app.add_handler(CommandHandler("businessgrowth", chat))
    app.add_handler(CommandHandler("cryptoinsight", chat))
    app.add_handler(CommandHandler("learning", chat))
    app.add_handler(CommandHandler("motivation", motivate))
    app.add_handler(CommandHandler("motivate", motivate))
    app.add_handler(CommandHandler("growthmindset", motivate))
    app.add_handler(CommandHandler("selfimprove", motivate))
    app.add_handler(CommandHandler("focusmore", motivate))
    app.add_handler(CommandHandler("hustle", motivate))
    app.add_handler(CommandHandler("learnandearn", motivate))
    app.add_handler(CommandHandler("worksmart", motivate))
    app.add_handler(CommandHandler("buildfuture", motivate))
    app.add_handler(CommandHandler("thinksmart", motivate))
    app.add_handler(CommandHandler("sharpmind", motivate))
    app.add_handler(CommandHandler("aiboss", motivate))
    app.add_handler(CommandHandler("entrepreneur", motivate))
    app.add_handler(CommandHandler("startjourney", start))
    app.add_handler(CommandHandler("boostmind", motivate))
    app.add_handler(CommandHandler("challenge", motivate))
    app.add_handler(CommandHandler("grow", motivate))
    app.add_handler(CommandHandler("aiinsight", chat))
    app.add_handler(CommandHandler("smarterai", chat))
    app.add_handler(CommandHandler("startai", chat))
    app.add_handler(CommandHandler("freeai", questions))
    app.add_handler(CommandHandler("askpro", chat))
    app.add_handler(CommandHandler("elitemind", chat))
    app.add_handler(CommandHandler("smartermind", chat))
    app.add_handler(CommandHandler("aiquestions", chat))
    app.add_handler(CommandHandler("aichat", chat))



