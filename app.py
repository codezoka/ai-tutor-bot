import os
import json
import asyncio
from datetime import datetime, timedelta
from aiohttp import web

import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from openai import AsyncOpenAI
from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL
PORT = int(os.getenv("PORT", 8080))
APP_NAME = os.getenv("APP_NAME")
WEBHOOK_URL = f"https://{APP_NAME}.ondigitalocean.app/webhook"

# Payment URLs
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")


# ==========================================
# INITIALIZE BOT
# ==========================================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Fix DigitalOcean proxy issue for OpenAI
import httpx
from openai import AsyncOpenAI

transport = httpx.AsyncHTTPTransport(retries=3)
http_client = httpx.AsyncClient(transport=transport, follow_redirects=True)

openai_client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    http_client=http_client
)

db = None



# ==========================================
# LOAD PROMPTS + QUOTES
# ==========================================
with open("prompts.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

with open("motivational_quotes.json", "r", encoding="utf-8") as f:
    _qdata = json.load(f)

MOTIVATIONAL_QUOTES = _qdata.get("quotes", [])
if not MOTIVATIONAL_QUOTES:
    MOTIVATIONAL_QUOTES = [
        "Stay focused!",
        "Keep building!",
        "Your success starts today!",
    ]


# ==========================================
# AUTO-MIGRATION (CREATES TABLES IF MISSING)
# ==========================================
async def run_migrations():
    async with db.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                plan TEXT DEFAULT 'free',
                used INTEGER DEFAULT 0,
                renewal TEXT,
                tokens_used INTEGER DEFAULT 0
            );
        """)
        print("✅ PostgreSQL migration completed.")


# ==========================================
# DATABASE FUNCTIONS
# ==========================================
async def save_user(uid, username):
    async with db.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (id, username)
            VALUES ($1, $2)
            ON CONFLICT (id) DO NOTHING;
        """, uid, username)


async def get_user_row(uid):
    async with db.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", uid)
        return dict(row) if row else None


async def update_usage(uid):
    async with db.acquire() as conn:
        await conn.execute("UPDATE users SET used = used + 1 WHERE id=$1;", uid)


async def reset_usage(uid):
    async with db.acquire() as conn:
        await conn.execute("UPDATE users SET used = 0 WHERE id=$1;", uid)


async def update_plan(uid, plan, renewal):
    async with db.acquire() as conn:
        await conn.execute("""
            UPDATE users SET plan=$1, renewal=$2 WHERE id=$3;
        """, plan, renewal, uid)


async def log_tokens(uid, tokens):
    async with db.acquire() as conn:
        await conn.execute("""
            UPDATE users SET tokens_used = tokens_used + $1 WHERE id=$2;
        """, tokens, uid)


# ==========================================
# PLAN → MODEL LOGIC
# ==========================================
def model_for_plan(plan):
    if plan in ("pro", "elite"):
        return "gpt-4o"
    return "gpt-4o-mini"


# ==========================================
# KEYBOARDS
# ==========================================
def get_upgrade_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Pro — $9.99/mo", url=PRO_MONTHLY_URL)],
        [InlineKeyboardButton(text="⚡ Pro — $99/yr (Save 20%)", url=PRO_YEARLY_URL)],
        [InlineKeyboardButton(text="🚀 Elite — $19.99/mo", url=ELITE_MONTHLY_URL)],
        [InlineKeyboardButton(text="🚀 Elite — $199/yr (Save 20%)", url=ELITE_YEARLY_URL)],
        [InlineKeyboardButton(text="⬅ Back", callback_data="back_home")]
    ])


# ==========================================
# /START — AD APPROVED
# ==========================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await save_user(message.from_user.id, message.from_user.username or "Unknown")

    text = (
        "🤖 <b>Welcome to AI Tutor!</b>\n\n"
        "Learn smarter with AI insights in:\n"
        "• 💼 Business\n"
        "• 🤖 AI & Tech\n"
        "• 💰 Crypto\n\n"
        "✨ Try one of these free questions:\n"
        "• “Give me a simple business idea.”\n"
        "• “Explain AI like I'm 5.”\n"
        "• “What should beginners know about crypto?”\n\n"
        "Choose a category below 👇\n\n"
        "🔒 Privacy: Your data is never shared."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Business", callback_data="cat_business")],
        [InlineKeyboardButton(text="🤖 AI & Tech", callback_data="cat_ai")],
        [InlineKeyboardButton(text="💰 Crypto", callback_data="cat_crypto")],
        [InlineKeyboardButton(text="⚡ Upgrade Plans", callback_data="open_plans")]
    ])

    await message.answer(text, reply_markup=keyboard)


# ==========================================
# CALLBACK HANDLER (CATEGORY → LEVEL → AI)
# ==========================================
@dp.callback_query()
async def callbacks(cb: types.CallbackQuery):
    data = cb.data
    uid = cb.from_user.id
    row = await get_user_row(uid)

    if not row:
        await save_user(uid, cb.from_user.username or "Unknown")
        row = await get_user_row(uid)

    plan = row["plan"]

    # CATEGORY
    if data.startswith("cat_"):
        cat = data.split("_")[1]
        await cb.message.edit_text(
            f"📘 <b>{cat.title()} Questions</b>\nChoose a level:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌱 Starter", callback_data=f"lvl|{cat}|starter")],
                [InlineKeyboardButton(text="💼 Profit", callback_data=f"lvl|{cat}|profit")],
                [InlineKeyboardButton(text="⬅ Back", callback_data="back_home")]
            ])
        )
        return

    # LEVEL
    if data.startswith("lvl|"):
        _, cat, level = data.split("|")

        if plan == "free" and level == "profit":
            await cb.message.edit_text(
                "🔒 Profit level is for Pro & Elite.\n"
                "Starter level is free.\n\n"
                "Upgrade whenever you're ready ✨",
                reply_markup=get_upgrade_keyboard()
            )
            return

        qs = QUESTIONS[cat][plan][level]

        buttons = [
            [InlineKeyboardButton(text=q[:45], callback_data=f"ask|{cat}|{level}|{i}")]
            for i, q in enumerate(qs)
        ]
        buttons.append([InlineKeyboardButton(text="⬅ Back", callback_data=f"cat_{cat}")])

        await cb.message.edit_text(
            f"🧠 {cat.title()} – {level.title()} Questions:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        return

    # ASK AI
    if data.startswith("ask|"):
        _, cat, level, idx = data.split("|")
        idx = int(idx)

        qs = QUESTIONS[cat][plan][level]
        question = qs[idx]

        used = row["used"]

        if plan == "free" and used >= 5:
            await cb.message.answer(
                "⚠️ Free limit reached.\nUpgrade for unlimited access.",
                reply_markup=get_upgrade_keyboard()
            )
            return

        await update_usage(uid)

        msg = await cb.message.answer("🤖 Thinking...")

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
                        await bot.edit_message_text(
                            chat_id=msg.chat.id,
                            message_id=msg.message_id,
                            text=reply
                        )

        await bot.edit_message_text(
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            text=reply
        )
        return

    # BACK HOME
    if data == "back_home":
        await cmd_start(cb.message)
        return

    # OPEN PLANS
    if data == "open_plans":
        await cb.message.edit_text(
            "✨ <b>Upgrade Plans</b>\nChoose your plan:",
            reply_markup=get_upgrade_keyboard()
        )
        return


# ==========================================
# FREE TEXT CHAT
# ==========================================
@dp.message()
async def free_chat(message: types.Message):
    uid = message.from_user.id
    text = message.text

    await save_user(uid, message.from_user.username or "Unknown")
    row = await get_user_row(uid)

    plan = row["plan"]
    used = row["used"]

    if plan == "free" and used >= 5:
        await message.answer(
            "🔒 You reached your free limit.\n"
            "Upgrade for unlimited access 🙂",
            reply_markup=get_upgrade_keyboard()
        )
        return

    await update_usage(uid)

    msg = await message.answer("🤖 Thinking...")

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
                    await bot.edit_message_text(
                        chat_id=msg.chat.id,
                        message_id=msg.message_id,
                        text=reply
                    )

    await bot.edit_message_text(
        chat_id=msg.chat.id,
        message_id=msg.message_id,
        text=reply
    )


# ==========================================
# ADMIN COMMANDS (KEPT)
# ==========================================
ADMIN_ID = 5722976786  # keep your admin

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Not authorized.")
        return

    args = message.text.split()

    if len(args) == 1:
        await message.answer(
            "📊 <b>Admin Panel</b>\n\n"
            "Commands:\n"
            "/admin users\n"
            "/admin find <id or username>\n"
            "/admin export\n"
            "/admin broadcast <msg>"
        )
        return

    cmd = args[1].lower()

    # ADMIN USERS
    if cmd == "users":
        async with db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT username, plan, used, tokens_used, renewal
                FROM users ORDER BY used DESC LIMIT 30;
            """)

        if not rows:
            await message.answer("📭 No users found.")
            return

        txt = "<b>📋 Users (Top 30)</b>\n\n"
        for i, r in enumerate(rows, 1):
            txt += (
                f"{i}. @{r['username']}\n"
                f"• Plan: {r['plan']} | Used: {r['used']} | Tokens: {r['tokens_used']}\n"
                f"• Renewal: {r['renewal']}\n\n"
            )

        await message.answer(txt)
        return

    # ADMIN FIND
    if cmd == "find" and len(args) >= 3:
        key = args[2].lstrip("@")

        async with db.acquire() as conn:
            if key.isdigit():
                row = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", int(key))
            else:
                row = await conn.fetchrow("SELECT * FROM users WHERE username=$1;", key)

        if not row:
            await message.answer("❌ User not found.")
            return

        row = dict(row)
        txt = (
            f"👤 <b>User:</b> @{row['username']} (ID: {row['id']})\n"
            f"Plan: {row['plan']}\n"
            f"Used: {row['used']}\n"
            f"Tokens: {row['tokens_used']}\n"
            f"Renewal: {row['renewal']}"
        )
        await message.answer(txt)
        return

    # ADMIN EXPORT
    if cmd == "export":
        async with db.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users;")

        if not rows:
            await message.answer("📭 No user data.")
            return

        import csv
        filename = "users_export.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "username", "plan", "used", "renewal", "tokens_used"])
            for r in rows:
                writer.writerow([r["id"], r["username"], r["plan"], r["used"], r["renewal"], r["tokens_used"]])

        await message.answer_document(open(filename, "rb"))
        return

    # ADMIN BROADCAST
    if cmd == "broadcast":
        if len(args) < 3:
            await message.answer("Usage: /admin broadcast <message>")
            return

        msg_text = " ".join(args[2:])

        async with db.acquire() as conn:
            rows = await conn.fetch("SELECT id FROM users;")

        count = 0
        for r in rows:
            try:
                await bot.send_message(r["id"], msg_text)
                count += 1
            except:
                pass

        await message.answer(f"📣 Message sent to {count} users.")
        return


# ==========================================
# WEBHOOK SETUP
# ==========================================
async def on_startup(app):
    global db
    db = await asyncpg.create_pool(DATABASE_URL)

    print("🔌 Connected to PostgreSQL.")

    await run_migrations()

    try:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"Webhook set → {WEBHOOK_URL}")
    except Exception as e:
        print("Webhook error:", e)


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