import os
import json
import asyncio
from datetime import datetime
from aiohttp import web

import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

from openai import AsyncOpenAI
import httpx
from dotenv import load_dotenv


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", 8080))
APP_NAME = os.getenv("APP_NAME")
WEBHOOK_URL = f"https://{APP_NAME}.ondigitalocean.app/webhook"

PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")


# ==========================================
# INITIALIZE BOT
# ==========================================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Fix DigitalOcean proxy issue for OpenAI
transport = httpx.AsyncHTTPTransport(retries=3)
http_client = httpx.AsyncClient(transport=transport, follow_redirects=True)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

db = None


# ==========================================
# LOAD PROMPTS
# ==========================================
with open("prompts.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)


# ==========================================
# MIGRATIONS
# ==========================================
async def run_migrations():
    async with db.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                plan TEXT DEFAULT 'free',
                used INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0
            );
        """)
        print("✅ PostgreSQL migration completed.")


# ==========================================
# DB FUNCTIONS
# ==========================================
async def save_user(uid, username):
    async with db.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (id, username)
            VALUES ($1, $2)
            ON CONFLICT (id) DO NOTHING;
        """, uid, username)


async def get_user(uid):
    async with db.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", uid)
        return dict(row) if row else None


async def increment_usage(uid):
    async with db.acquire() as conn:
        await conn.execute("UPDATE users SET used = used + 1 WHERE id=$1;", uid)


# ==========================================
# MODEL SELECTION
# ==========================================
def model_for_plan(plan):
    return "gpt-4o" if plan in ("pro", "elite") else "gpt-4o-mini"


# ==========================================
# KEYBOARDS
# ==========================================
def upgrade_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Pro — $9.99/mo", url=PRO_MONTHLY_URL)],
        [InlineKeyboardButton(text="⚡ Pro — $99/yr (Save 20%)", url=PRO_YEARLY_URL)],
        [InlineKeyboardButton(text="🚀 Elite — $19.99/mo", url=ELITE_MONTHLY_URL)],
        [InlineKeyboardButton(text="🚀 Elite — $199/yr (Save 20%)", url=ELITE_YEARLY_URL)],
        [InlineKeyboardButton(text="⬅ Back", callback_data="back_home")]
    ])


# ==========================================
# START COMMAND
# ==========================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await save_user(message.from_user.id, message.from_user.username)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Business", callback_data="cat_business")],
        [InlineKeyboardButton(text="🤖 AI & Tech", callback_data="cat_ai")],
        [InlineKeyboardButton(text="💰 Crypto", callback_data="cat_crypto")],
        [InlineKeyboardButton(text="⚡ Upgrade Plans", callback_data="open_plans")]
    ])

    await message.answer(
        "🤖 <b>Welcome to AI Tutor!</b>\nChoose a category.",
        reply_markup=kb
    )


# ==========================================
# CALLBACK HANDLER
# ==========================================
@dp.callback_query()
async def cb_handler(cb: types.CallbackQuery):
    uid = cb.from_user.id
    data = cb.data

    user = await get_user(uid)
    plan = user.get("plan", "free")
    used = user.get("used", 0)

    # CATEGORY SELECTION
    if data.startswith("cat_"):
        cat = data.split("_")[1]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌱 Starter", callback_data=f"lvl|{cat}|starter")],
            [InlineKeyboardButton(text="💼 Profit", callback_data=f"lvl|{cat}|profit")],
            [InlineKeyboardButton(text="⬅ Back", callback_data="back_home")]
        ])
        await cb.message.edit_text(f"📘 <b>{cat.title()} Questions</b>\nChoose level:", reply_markup=kb)
        return

    # LEVEL
    if data.startswith("lvl|"):
        _, cat, level = data.split("|")

        # Profit locked
        if plan == "free" and level == "profit":
            await cb.message.edit_text(
                "🔒 Profit level is for Pro/Elite only.",
                reply_markup=upgrade_keyboard()
            )
            return

        # Starter but limit reached
        if plan == "free" and level == "starter" and used >= 5:
            await cb.message.edit_text(
                "🔒 You reached your free category limit (5).\n"
                "You can still type your own questions anytime 😊",
                reply_markup=upgrade_keyboard()
            )
            return

        # Show questions
        questions = QUESTIONS[cat][plan][level]
        kb = []
        for i, q in enumerate(questions):
            kb.append([InlineKeyboardButton(text=q[:40], callback_data=f"ask|{cat}|{level}|{i}")])
        kb.append([InlineKeyboardButton(text="⬅ Back", callback_data=f"cat_{cat}")])

        await cb.message.edit_text(f"🧠 {cat.title()} – {level.title()} Questions:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return

    # ASK QUESTION
    if data.startswith("ask|"):
        _, cat, level, idx = data.split("|")
        idx = int(idx)

        user = await get_user(uid)
        plan = user["plan"]
        used = user["used"]

        # Limit reached
        if plan == "free" and used >= 5:
            await cb.message.answer(
                "🔒 You reached your free category limit.\n"
                "You can still type your own questions anytime 😊",
                reply_markup=upgrade_keyboard()
            )
            return

        # Count only category questions
        await increment_usage(uid)

        question = QUESTIONS[cat][plan][level][idx]
        msg = await cb.message.answer("🤖 Thinking…")

        reply = ""
        stream = await openai_client.chat.completions.create(
            model=model_for_plan(plan),
            messages=[{"role": "user", "content": question}],
            stream=True
        )

        async for event in stream:
            if hasattr(event, "choices") and event.choices:
                delta = event.choices[0].delta
                if delta and getattr(delta, "content", None):
                    reply += delta.content
                    if len(reply) % 30 == 0:
                        await bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id, text=reply)

        await bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id, text=reply)
        return

    # BACK HOME
    if data == "back_home":
        await cmd_start(cb.message)
        return

    # OPEN PLANS
    if data == "open_plans":
        await cb.message.edit_text("✨ Upgrade Plans", reply_markup=upgrade_keyboard())
        return


# ==========================================
# FREE TEXT CHAT — ALWAYS ALLOWED
# ==========================================
@dp.message()
async def free_chat(message: types.Message):
    uid = message.from_user.id
    text = message.text

    await save_user(uid, message.from_user.username)
    user = await get_user(uid)
    plan = user["plan"]

    msg = await message.answer("🤖 Thinking…")

    reply = ""
    stream = await openai_client.chat.completions.create(
        model=model_for_plan(plan),
        messages=[{"role": "user", "content": text}],
        stream=True
    )

    async for event in stream:
        if hasattr(event, "choices") and event.choices:
            delta = event.choices[0].delta
            if delta and getattr(delta, "content", None):
                reply += delta.content
                if len(reply) % 30 == 0:
                    await bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id, text=reply)

    await bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id, text=reply)


# ==========================================
# WEBHOOK & SERVER
# ==========================================
async def on_startup(app):
    global db
    db = await asyncpg.create_pool(DATABASE_URL)
    print("🔌 Connected to PostgreSQL.")

    await run_migrations()

    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook set →", WEBHOOK_URL)


async def on_shutdown(app):
    await bot.delete_webhook()
    print("Webhook removed.")


async def health(request):
    return web.Response(text="OK")


def main():
    app = web.Application()
    app.router.add_get("/", health)

    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()