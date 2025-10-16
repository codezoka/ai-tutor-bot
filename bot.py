import json
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
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
dp = Dispatcher()
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
@dp.message(Command("start"))
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Free Plan", callback_data="plan_free")],
        [InlineKeyboardButton(text="💼 Pro Plan", callback_data="plan_pro")],
        [InlineKeyboardButton(text="💎 Elite Plan", callback_data="plan_elite")]
    ])
    text = (
        "👋 Welcome to <b>AI Tutor Pro Bot</b> — your intelligent mentor for mastering "
        "AI, Business, and Crypto.\n\n"
        "Choose your plan to begin 👇"
    )
    await message.answer(text, reply_markup=kb)


@dp.message(Command("help"))
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


@dp.message(Command("status"))
async def status_command(message: types.Message):
    plan = user_plans.get(message.from_user.id, "Free")
    await message.answer(f"📊 Your current plan: <b>{plan}</b>")


# =========================
#   PLAN SELECTION
# =========================
@dp.callback_query(lambda c: c.data.startswith("plan_"))
async def plan_select(callback: types.CallbackQuery):
    plan = callback.data.split("_")[1].capitalize()
    user_plans[callback.from_user.id] = plan

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 AI Path", callback_data=f"{plan}_ai")],
        [InlineKeyboardButton(text="💼 Business Path", callback_data=f"{plan}_business")],
        [InlineKeyboardButton(text="💰 Crypto Path", callback_data=f"{plan}_crypto")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="main_menu")]
    ])

    try:
        await callback.message.edit_text(f"✅ {plan} Plan Selected.\nChoose your path 👇", reply_markup=kb)
    except Exception:
        await callback.message.answer(f"✅ {plan} Plan Selected.\nChoose your path 👇", reply_markup=kb)
    await callback.answer()


# =========================
#   MAIN MENU
# =========================
@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Free Plan", callback_data="plan_free")],
        [InlineKeyboardButton(text="💼 Pro Plan", callback_data="plan_pro")],
        [InlineKeyboardButton(text="💎 Elite Plan", callback_data="plan_elite")]
    ])
    await callback.message.answer("🔙 Back to main menu. Choose your plan:", reply_markup=kb)
    await callback.answer()


# =========================
#   CATEGORY SELECTION
# =========================
@dp.callback_query(lambda c: any(k in c.data for k in ["ai", "business", "crypto"]))
async def category_select(callback: types.CallbackQuery):
    try:
        plan, category = callback.data.split("_", 1)
    except ValueError:
        await callback.message.answer("⚠️ Invalid selection. Please try again.")
        return

    levels = ["starter", "profit"]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Starter", callback_data=f"{plan}_{category}_starter")],
        [InlineKeyboardButton(text="💰 Profit", callback_data=f"{plan}_{category}_profit")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"plan_{plan.lower()}")]
    ])

    intro = {
        "ai": "🤖 Welcome to the AI Path — let’s turn intelligence into freedom.",
        "business": "💼 Welcome to the Business Path — where systems create freedom and clarity builds wealth.",
        "crypto": "💰 Welcome to the Crypto Path — where knowledge meets opportunity."
    }[category]

    try:
        await callback.message.edit_text(
            f"{intro}\n💡 Ask Smart. Think Smart.\nGuided by AI Tutor Pro Bot\n\nWhere would you like to begin?",
            reply_markup=kb
        )
    except Exception:
        await callback.message.answer(
            f"{intro}\n💡 Ask Smart. Think Smart.\nGuided by AI Tutor Pro Bot\n\nWhere would you like to begin?",
            reply_markup=kb
        )
    await callback.answer()


# =========================
#   SHOW QUESTIONS
# =========================
@dp.callback_query(lambda c: any(k in c.data for k in ["starter", "profit"]))
async def show_questions(callback: types.CallbackQuery):
    try:
        plan, category, level = callback.data.split("_")
    except ValueError:
        await callback.message.answer("⚠️ Something went wrong. Try again.")
        return

    questions = prompts.get(category, {}).get(level, [])
    if not questions:
        await callback.message.answer("⚠️ No questions found for this section.")
        return

    # Free plan restrictions
    if plan.lower() == "free" and level.lower() in ["pro", "elite"]:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💼 Upgrade to Pro", url=PRO_MONTHLY_URL or "https://your-upgrade-link.com")],
            [InlineKeyboardButton(text="💎 Upgrade to Elite", url=PRO_YEARLY_URL or "https://your-upgrade-link.com")]
        ])
        await callback.message.answer("🔒 This section is for Pro & Elite users. Unlock it below 👇", reply_markup=kb)
        return

    text = f"📘 <b>{category.capitalize()} – {level.capitalize()} Questions</b>\n\n"
    text += "\n".join(f"• {q}" for q in questions)
    await callback.message.answer(text)
    await callback.answer()


# =========================
#   CUSTOM USER QUESTIONS
# =========================
@dp.message()
async def handle_user_question(message: types.Message):
    if message.text.startswith("/"):
        return

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
#   RUN BOT
# =========================
async def main():
    print("🤖 AI Tutor Pro Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

