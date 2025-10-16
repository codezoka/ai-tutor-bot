import json
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PRO_MONTHLY_URL = os.getenv("PRO_MONTHLY_URL")
PRO_YEARLY_URL = os.getenv("PRO_YEARLY_URL")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found in environment variables!")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Load prompts.json
PROMPTS_PATH = os.path.join(os.path.dirname(__file__), "prompts.json")
if not os.path.exists(PROMPTS_PATH):
    raise FileNotFoundError("❌ prompts.json file missing!")
with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
    prompts = json.load(f)

# Simple in-memory plan store
user_plans = {}

# =========================
#   START & HELP COMMANDS
# =========================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🆓 Free Plan", callback_data="plan_free"),
        InlineKeyboardButton("💼 Pro Plan", callback_data="plan_pro"),
        InlineKeyboardButton("💎 Elite Plan", callback_data="plan_elite")
    )

    text = (
        "👋 Welcome to <b>AI Tutor Pro Bot</b> — your intelligent mentor for mastering "
        "AI, Business, and Crypto.\n\n"
        "Choose your plan to begin 👇"
    )
    await message.answer(text, reply_markup=kb)


@dp.message_handler(commands=["help"])
async def help_command(message: types.Message):
    help_text = (
        "🧠 <b>How to use AI Tutor Pro Bot</b>\n\n"
        "• /start – Choose your plan and begin\n"
        "• /questions – Explore categories (AI, Business, Crypto)\n"
        "• /upgrade – Unlock higher levels (Pro & Elite)\n"
        "• /status – Check your usage and current plan\n\n"
        "💡 You can also type your own question anytime!"
    )
    await message.answer(help_text)


@dp.message_handler(commands=["status"])
async def status_command(message: types.Message):
    plan = user_plans.get(message.from_user.id, "Free")
    await message.answer(f"📊 Your current plan: <b>{plan}</b>")


# =========================
#   PLAN SELECTION
# =========================
@dp.callback_query_handler(lambda c: c.data.startswith("plan_"))
async def plan_select(call: types.CallbackQuery):
    plan = call.data.split("_")[1].capitalize()
    user_plans[call.from_user.id] = plan

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🤖 AI Path", callback_data=f"{plan}_ai"),
        InlineKeyboardButton("💼 Business Path", callback_data=f"{plan}_business"),
        InlineKeyboardButton("💰 Crypto Path", callback_data=f"{plan}_crypto"),
        InlineKeyboardButton("⬅️ Back", callback_data="main_menu")
    )

    try:
        await call.message.edit_text(f"✅ {plan} Plan Selected.\nChoose your path 👇", reply_markup=kb)
    except Exception:
        await call.message.answer(f"✅ {plan} Plan Selected.\nChoose your path 👇", reply_markup=kb)


# =========================
#   MAIN MENU
# =========================
@dp.callback_query_handler(lambda c: c.data == "main_menu")
async def main_menu(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🆓 Free Plan", callback_data="plan_free"),
        InlineKeyboardButton("💼 Pro Plan", callback_data="plan_pro"),
        InlineKeyboardButton("💎 Elite Plan", callback_data="plan_elite")
    )
    await call.message.answer("🔙 Back to main menu. Choose your plan:", reply_markup=kb)


# =========================
#   CATEGORY SELECTION
# =========================
@dp.callback_query_handler(lambda c: any(k in c.data for k in ["ai", "business", "crypto"]))
async def category_select(call: types.CallbackQuery):
    try:
        plan, category = call.data.split("_", 1)
    except ValueError:
        await call.message.answer("⚠️ Invalid selection. Please try again.")
        return

    if plan.lower() == "free":
        levels = ["starter", "profit"]
    else:
        levels = ["starter", "profit"]

    kb = InlineKeyboardMarkup(row_width=1)
    for level in levels:
        kb.add(InlineKeyboardButton(
            f"{'🧠' if level=='starter' else '💰'} {level.capitalize()}",
            callback_data=f"{plan}_{category}_{level}"
        ))
    kb.add(InlineKeyboardButton("⬅️ Back", callback_data=f"plan_{plan.lower()}"))

    intro = {
        "ai": "🤖 Welcome to the AI Path — let’s turn intelligence into freedom.",
        "business": "💼 Welcome to the Business Path — where systems create freedom and clarity builds wealth.",
        "crypto": "💰 Welcome to the Crypto Path — where knowledge meets opportunity."
    }[category]

    try:
        await call.message.edit_text(
            f"{intro}\n💡 Ask Smart. Think Smart.\nGuided by AI Tutor Pro Bot\n\nWhere would you like to begin?",
            reply_markup=kb
        )
    except Exception:
        await call.message.answer(
            f"{intro}\n💡 Ask Smart. Think Smart.\nGuided by AI Tutor Pro Bot\n\nWhere would you like to begin?",
            reply_markup=kb
        )


# =========================
#   SHOW QUESTIONS
# =========================
@dp.callback_query_handler(lambda c: any(k in c.data for k in ["starter", "profit"]))
async def show_questions(call: types.CallbackQuery):
    try:
        plan, category, level = call.data.split("_")
    except ValueError:
        await call.message.answer("⚠️ Something went wrong. Try again.")
        return

    questions = prompts.get(category, {}).get(level, [])
    if not questions:
        await call.message.answer("⚠️ No questions found for this section.")
        return

    # Handle Free plan limits
    if plan.lower() == "free" and level.lower() in ["pro", "elite"]:
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("💼 Upgrade to Pro", url=PRO_MONTHLY_URL or "https://your-upgrade-link.com"),
            InlineKeyboardButton("💎 Upgrade to Elite", url=PRO_YEARLY_URL or "https://your-upgrade-link.com")
        )
        await call.message.answer("🔒 This section is for Pro & Elite users. Unlock it below 👇", reply_markup=kb)
        return

    text = f"📘 <b>{category.capitalize()} – {level.capitalize()} Questions</b>\n\n"
    text += "\n".join(f"• {q}" for q in questions)
    await call.message.answer(text)


# =========================
#   CUSTOM USER QUESTIONS
# =========================
@dp.message_handler(lambda message: not message.text.startswith("/"))
async def handle_user_question(message: types.Message):
    user_input = message.text.strip()
    await message.answer("💭 Thinking...")

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are AI Tutor Pro Bot — an expert mentor for AI, business, and crypto."},
                {"role": "user", "content": user_input}
            ],
        )
        answer = response.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"⚠️ Something went wrong. Please try again.\n\nError: {str(e)}")


# =========================
#   MAIN LOOP
# =========================
if __name__ == "__main__":
    print("🤖 AI Tutor Pro Bot is running...")
    executor.start_polling(dp, skip_updates=True)

