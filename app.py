import os
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ----------------------------
# ENVIRONMENT VARIABLES (SAFE)
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")

# Payment invoice IDs (from CryptoBot)
SMART_MONTHLY = "IVoOKgk2Ik7W"
GENIUS_MONTHLY = "IV20WdvjUVgB"
SMART_YEARLY = "IVBOLLq0SGII"
GENIUS_YEARLY = "IVt9617C1w6j"

WEBHOOK_URL = f"https://ai-tutor-bot-83opf.ondigitalocean.app/webhook"

# ----------------------------
# INITIALIZE BOT
# ----------------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ----------------------------
# FASTAPI for webhook
# ----------------------------
app = FastAPI()


# ----------------------------
# CONNECT TO POSTGRES
# ----------------------------
async def connect_db():
    return await asyncpg.connect(DATABASE_URL)


async def ensure_tables():
    conn = await connect_db()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            plan TEXT DEFAULT 'free',
            free_used INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            premium_until TIMESTAMP
        );
    """)
    await conn.close()


# ----------------------------
# MENU BUTTONS
# ----------------------------

def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Business", callback_data="cat_business")],
        [InlineKeyboardButton(text="🧠 AI & Tech", callback_data="cat_ai")],
        [InlineKeyboardButton(text="💰 Crypto", callback_data="cat_crypto")],
        [InlineKeyboardButton(text="⚡ Upgrade Premium", callback_data="upgrade")]
    ])
    return kb


def upgrade_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Smart Monthly — $9.99", callback_data="pay_smart_month")],
        [InlineKeyboardButton(text="⚡ Smart Yearly — $79.99", callback_data="pay_smart_year")],
        [InlineKeyboardButton(text="🚀 Genius Monthly — $19.99", callback_data="pay_genius_month")],
        [InlineKeyboardButton(text="🚀 Genius Yearly — $149.99", callback_data="pay_genius_year")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")]
    ])
    return kb


# ----------------------------
# HELPER FUNCTIONS
# ----------------------------

async def get_user(user_id):
    conn = await connect_db()
    user = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
    if not user:
        await conn.execute("INSERT INTO users (user_id) VALUES ($1)", user_id)
        user = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
    await conn.close()
    return user


async def increase_free_count(user_id):
    conn = await connect_db()
    await conn.execute("UPDATE users SET free_used = free_used + 1 WHERE user_id = $1", user_id)
    await conn.close()


async def set_plan(user_id, plan, days=30):
    conn = await connect_db()
    premium_until = datetime.utcnow() + timedelta(days=days)
    await conn.execute("UPDATE users SET plan=$1, premium_until=$2 WHERE user_id=$3",
                       plan, premium_until, user_id)
    await conn.close()


# ----------------------------
# BOT COMMANDS
# ----------------------------

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🤖 Welcome to AskSmartAI!\n\n"
        "Think smarter. Learn faster. Ask better questions.\n\n"
        "Choose a category or type your own question anytime.",
        reply_markup=main_menu()
    )


@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "👋 **How to Use AskSmartAI**\n\n"
        "• /start — Open the main menu\n"
        "• /questions — Smart categories\n"
        "• /upgrade — View premium plans\n"
        "• /status — Check your limits\n\n"
        "💡 You can ALWAYS type your own questions for free.\n"
        "Premium unlocks unlimited smart prompts."
    )


@dp.message(Command("status"))
async def status(message: types.Message):
    user = await get_user(message.from_user.id)

    if user["plan"] == "free":
        await message.answer(
            f"📊 **Your Status**\n\n"
            f"Smart Questions used: {user['free_used']}/5\n"
            f"Typed questions: Unlimited\n\n"
            f"🔥 Upgrade to unlock unlimited Smart Questions.",
            reply_markup=upgrade_menu()
        )
    else:
        await message.answer(
            f"🎉 You are on the **{user['plan'].capitalize()} Plan**!\n"
            f"Unlimited Smart Questions.\n"
            f"Premium active until: {user['premium_until']}"
        )


@dp.message(Command("questions"))
async def questions(message: types.Message):
    await message.answer(
        "Choose a category:",
        reply_markup=main_menu()
    )

# ----------------------------
# HANDLE CATEGORY BUTTONS
# ----------------------------

@dp.callback_query(F.data.startswith("cat_"))
async def category_handler(callback: types.CallbackQuery):
    user = await get_user(callback.from_user.id)

    # Only 5 free smart questions EVER
    if user["plan"] == "free" and user["free_used"] >= 5:
        await callback.message.answer(
            "⚠️ You’ve used all 5 free Smart Questions.\n\n"
            "Typed questions are always free.\n"
            "Upgrade to unlock unlimited Smart Questions.",
            reply_markup=upgrade_menu()
        )
        return

    # Count usage
    if user["plan"] == "free":
        await increase_free_count(callback.from_user.id)

    category = callback.data.replace("cat_", "").capitalize()
    await callback.message.answer(
        f"🧠 **{category} Smart Questions:**\n\n"
        "Type your question below 👇"
    )


# ----------------------------
# UPGRADE MENU
# ----------------------------

@dp.callback_query(F.data == "upgrade")
async def upgrade_handler(callback: types.CallbackQuery):
    await callback.message.answer(
        "🔥 **Upgrade Your Learning Power**\n\n"
        "Unlock unlimited Smart Questions and premium insights.",
        reply_markup=upgrade_menu()
    )


@dp.callback_query(F.data == "back_to_menu")
async def back_menu(callback: types.CallbackQuery):
    await callback.message.answer("Back to main menu:", reply_markup=main_menu())


# ----------------------------
# PAYMENT HANDLERS
# ----------------------------

async def send_invoice(callback, invoice_id):
    link = f"https://t.me/CryptoBot?start={invoice_id}"
    await callback.message.answer(
        "💳 Complete your payment:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Pay Now", url=link)]
        ])
    )


@dp.callback_query(F.data == "pay_smart_month")
async def pay1(callback: types.CallbackQuery):
    await send_invoice(callback, SMART_MONTHLY)


@dp.callback_query(F.data == "pay_genius_month")
async def pay2(callback: types.CallbackQuery):
    await send_invoice(callback, GENIUS_MONTHLY)


@dp.callback_query(F.data == "pay_smart_year")
async def pay3(callback: types.CallbackQuery):
    await send_invoice(callback, SMART_YEARLY)


@dp.callback_query(F.data == "pay_genius_year")
async def pay4(callback: types.CallbackQuery):
    await send_invoice(callback, GENIUS_YEARLY)


# ------------------------------------------------
# WEBHOOK HANDLER (Telegram → FastAPI → Bot)
# ------------------------------------------------
@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    await dp.feed_webhook_update(bot, update)
    return JSONResponse({"ok": True})


# ----------------------------
# FASTAPI ROOT
# ----------------------------
@app.get("/")
async def home():
    return {"status": "ok"}


# ----------------------------
# STARTUP
# ----------------------------
@app.on_event("startup")
async def on_startup():
    await ensure_tables()
    await bot.set_webhook(WEBHOOK_URL)

