import os
import json
import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import AsyncOpenAI
from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties

# ===== Load Environment Variables =====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 8080))
APP_NAME = os.getenv("APP_NAME")
WEBHOOK_URL = f"https://{APP_NAME}.ondigitalocean.app/webhook"

# Payment links
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")
ELITE_MONTHLY_URL = os.getenv("ELITE_MONTHLY_URL")
ELITE_YEARLY_URL = os.getenv("ELITE_YEARLY_URL")

# ===== Initialize Bot =====
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ===== Load Smart Questions =====
with open("prompts.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# ===== Load Motivational Quotes =====
with open("motivational_quotes.json", "r", encoding="utf-8") as f:
    MOTIVATIONAL_QUOTES = json.load(f)

# ===== Database Setup =====
DB_FILE = "users.db"
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    plan TEXT DEFAULT 'free',
    used INTEGER DEFAULT 0,
    renewal TEXT,
    tokens_used INTEGER DEFAULT 0
)
""")
conn.commit()

def save_user(user_id, username, plan="free"):
    cursor.execute("INSERT OR IGNORE INTO users (id, username, plan, used, tokens_used) VALUES (?, ?, ?, 0, 0)",
                   (user_id, username, plan))
    conn.commit()

def update_usage(user_id):
    cursor.execute("UPDATE users SET used = used + 1 WHERE id = ?", (user_id,))
    conn.commit()

def update_plan(user_id, plan, renewal=None):
    cursor.execute("UPDATE users SET plan = ?, renewal = ? WHERE id = ?", (plan, renewal, user_id))
    conn.commit()

def log_tokens(user_id, tokens):
    cursor.execute("UPDATE users SET tokens_used = tokens_used + ? WHERE id = ?", (tokens, user_id))
    conn.commit()

# ===== Simple In-Memory User Tracking =====
USERS = {}

# ===== Helper Keyboards =====
def get_plan_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Free", callback_data="plan_free")],
        [InlineKeyboardButton(text="⚡ Pro (Fast AI, Unlimited Access)", callback_data="plan_pro")],
        [InlineKeyboardButton(text="🚀 Elite (Full Power AI, Instant Results)", callback_data="plan_elite")]
    ])

def get_category_keyboard(plan):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Business", callback_data=f"{plan}_business")],
        [InlineKeyboardButton(text="🤖 AI", callback_data=f"{plan}_ai")],
        [InlineKeyboardButton(text="💰 Crypto", callback_data=f"{plan}_crypto")],
        [InlineKeyboardButton(text="⬅ Back", callback_data="back_to_plans")]
    ])

def get_level_keyboard(plan, category):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌱 Starter", callback_data=f"{plan}_{category}_starter")],
        [InlineKeyboardButton(text="💼 Profit", callback_data=f"{plan}_{category}_profit")],
        [InlineKeyboardButton(text="⬅ Back", callback_data=f"back_to_{plan}")]
    ])

def get_upgrade_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Pro — $9.99/mo", url=PRO_MONTHLY_URL)],
        [InlineKeyboardButton(text="⚡ Pro — $99.99/year (Save 20%)", url=PRO_YEARLY_URL)],
        [InlineKeyboardButton(text="🚀 Elite — $19.99/mo", url=ELITE_MONTHLY_URL)],
        [InlineKeyboardButton(text="🚀 Elite — $199.99/year (Save 20%)", url=ELITE_YEARLY_URL)],
        [InlineKeyboardButton(text="⬅ Back to Menu", callback_data="back_to_menu")]
    ])

# ===== Commands =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    USERS.setdefault(message.from_user.id, {"plan": "free", "used": 0})
    save_user(message.from_user.id, message.from_user.username or "Unknown")
    print(f"👤 New user started: {message.from_user.username} ({message.from_user.id})")

    text = (
        "🤖 <b>Welcome to AI Tutor Bot – Ask Like the 1%!</b>\n\n"
        "🚀 Ask like CEOs and top experts to get actionable, high-quality answers.\n"
        "💼 <b>Business</b> – Build smarter and scale faster\n"
        "🧠 <b>AI</b> – Master modern intelligence tools\n"
        "💰 <b>Crypto</b> – Spot and profit from emerging opportunities\n\n"
        "🔥 Choose your plan and start asking smarter questions below 👇"
    )
    await message.answer(text, reply_markup=get_plan_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "🧭 <b>How to use AI Tutor Bot:</b>\n\n"
        "💬 /start – Begin and choose your plan\n"
        "🧠 /questions – Explore smart questions by category\n"
        "⚙️ /upgrade – Unlock Pro or Elite for full access\n"
        "📊 /status – View your plan, usage, and renewal info\n\n"
        "💡 You can type your own question anytime!"
    )
    await message.answer(text)

@dp.message(Command("upgrade"))
async def cmd_upgrade(message: types.Message):
    text = (
        "🚀 <b>Upgrade Now!</b>\n\n"
        "⚡ <b>Pro:</b> Fast AI + 15 smart questions per category.\n"
        "💎 <b>Elite:</b> Full Power AI + 25 questions + instant replies.\n\n"
        "🔥 Successful people invest in their knowledge — upgrade now!"
    )
    await message.answer(text, reply_markup=get_upgrade_keyboard())

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    user = USERS.get(message.from_user.id, {"plan": "free", "used": 0})
    plan = user["plan"]
    used = user.get("used", 0)
    remaining = max(0, 5 - used)
    text = (
        f"📊 <b>Your Plan:</b> {plan.title()}\n"
        f"❓ Smart Questions Used: {used}/5\n"
        f"💡 You can type custom questions anytime.\n"
        f"✨ Upgrade for more, faster answers, and premium insights!"
    )
    await message.answer(text)

@dp.message(Command("questions"))
async def cmd_questions(message: types.Message):
    await message.answer("🧠 Choose your plan:", reply_markup=get_plan_keyboard())

# ====== Callback Handling (Improved Back Buttons & Full Question Text) ======
@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    user = USERS.setdefault(user_id, {"plan": "free", "used": 0})

    # ===== Plan Selection =====
    if data.startswith("plan_"):
        plan = data.split("_")[1]
        await callback.message.edit_text(
            f"📚 <b>{plan.title()} Plan Selected!</b>\nChoose a category:",
            reply_markup=get_category_keyboard(plan)
        )
        return

    # ===== Category → Level =====
    for plan in ["free", "pro", "elite"]:
        for cat in ["business", "ai", "crypto"]:
            if data == f"{plan}_{cat}":
                if plan != "free" and user["plan"] == "free":
                    await callback.message.edit_text(
                        "🔒 This section is locked. Upgrade to unlock premium content!",
                        reply_markup=get_upgrade_keyboard()
                    )
                    return
                await callback.message.edit_text(
                    f"📂 {cat.title()} – Choose Level:",
                    reply_markup=get_level_keyboard(plan, cat)
                )
                return

    # ===== Level → Questions =====
    for plan in ["free", "pro", "elite"]:
        for cat in ["business", "ai", "crypto"]:
            for level in ["starter", "profit"]:
                if data == f"{plan}_{cat}_{level}":
                    questions = QUESTIONS[cat][plan][level]
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=q if len(q) < 110 else q[:107] + "…", callback_data=f"ask_{q}")]
                        for q in questions
                    ] + [
                        [InlineKeyboardButton(text="⬅ Back to Levels", callback_data=f"{plan}_{cat}")],
                        [InlineKeyboardButton(text="🏠 Back to Plans", callback_data="back_to_plans")]
                    ])
                    await callback.message.edit_text(
                        f"💬 {cat.title()} – {level.title()} Questions:",
                        reply_markup=keyboard
                    )
                    return

    # ===== Back Navigation =====
    if data == "back_to_plans":
        await callback.message.edit_text(
            "🏠 Choose your plan:",
            reply_markup=get_plan_keyboard()
        )
        return

    # ===== Ask AI =====
    if data.startswith("ask_"):
        question = data.replace("ask_", "")
        plan = user.get("plan", "free")

        if plan == "free" and user["used"] >= 5:
            await callback.message.answer(
                "⚠️ You’ve reached your 5-question limit.\nUpgrade for unlimited smart insights!",
                reply_markup=get_upgrade_keyboard()
            )
            return

        user["used"] += 1
        update_usage(user_id)
        await callback.message.answer("🤖 Thinking...")

        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": question}]
            )
            tokens = response.usage.total_tokens if hasattr(response, "usage") else 0
            log_tokens(user_id, tokens)
            await callback.message.answer(response.choices[0].message.content)
        except Exception as e:
            await callback.message.answer(f"❌ Error: {e}")


# ===== Admin Dashboard with Export =====
ADMIN_ID = 5722976786  # Replace with your Telegram user ID

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ You are not authorized to view admin data.")
        return

    args = message.text.split()

    # === /admin users ===
    if len(args) > 1 and args[1] == "users":
        cursor.execute("SELECT username, plan, used, tokens_used, renewal FROM users ORDER BY used DESC LIMIT 30")
        rows = cursor.fetchall()
        if not rows:
            await message.answer("📭 No users found yet.")
            return

        text = "<b>📋 Active Users Report (Top 30)</b>\n\n"
        for i, (username, plan, used, tokens, renewal) in enumerate(rows, start=1):
            uname = username or "Unknown"
            renew = renewal or "—"
            text += f"{i}. @{uname}\n• Plan: {plan.title()} | Used: {used} | Tokens: {tokens}\n• Renewal: {renew}\n\n"
        
        await message.answer(text)
        return

    # === /admin export ===
    if len(args) > 1 and args[1] == "export":
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        if not rows:
            await message.answer("📭 No user data to export.")
            return

        import csv
        filename = "users_export.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "username", "plan", "used", "renewal", "tokens_used"])
            writer.writerows(rows)

        await message.answer_document(open(filename, "rb"), caption="📦 Exported full user database ✅")
        return

    # === Default /admin ===
    cursor.execute("""
        SELECT COUNT(*), SUM(used), SUM(tokens_used),
               SUM(plan='free'), SUM(plan='pro'), SUM(plan='elite')
        FROM users
    """)
    total_users, total_used, tokens, free_count, pro_count, elite_count = cursor.fetchone()

    text = (
        "📊 <b>AI Tutor Admin Dashboard</b>\n\n"
        f"👥 Users: <b>{total_users or 0}</b>\n"
        f"🆓 Free: <b>{free_count or 0}</b> | ⚡ Pro: <b>{pro_count or 0}</b> | 🚀 Elite: <b>{elite_count or 0}</b>\n"
        f"💬 Smart Questions Used: <b>{total_used or 0}</b>\n"
        f"🧠 Tokens Used: <b>{tokens or 0}</b>\n\n"
        f"🕓 Updated in real time ✅\n\n"
        f"📋 Type <code>/admin users</code> for user list\n"
        f"📤 Type <code>/admin export</code> to download full CSV"
    )
    await message.answer(text)


# ===== Motivational Quotes Rotation =====
async def send_daily_quote():
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        quote = random.choice(MOTIVATIONAL_QUOTES)
        for user_id in USERS.keys():
            await bot.send_message(user_id, quote)

# ===== Auto Webhook + Health Check =====
async def on_startup(app):
    try:
        await bot.set_webhook(WEBHOOK_URL)
        asyncio.create_task(send_daily_quote())
        print(f"✅ Webhook automatically set to: {WEBHOOK_URL}")
    except Exception as e:
        print(f"⚠️ Webhook setup failed: {e}")

async def on_shutdown(app):
    await bot.delete_webhook()
    print("🧹 Webhook removed")

async def handle_health(request):
    return web.Response(text="✅ AI Tutor Bot is Healthy", content_type="text/plain")

def main():
    app = web.Application()
    app.router.add_get("/", handle_health)

    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    # ✅ Register webhook correctly (no duplicate)
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")

    # Startup and shutdown hooks
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Properly link dispatcher to app
    setup_application(app, dp, bot=bot)

    print(f"🚀 Bot is now running with webhook: {WEBHOOK_URL}")
    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()



