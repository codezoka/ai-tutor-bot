import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found in environment variables!")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# -------------------------------
# Main Keyboards
# -------------------------------
def plan_keyboard():
    kb = [
        [InlineKeyboardButton(text="✅ Free Plan", callback_data="plan_free")],
        [InlineKeyboardButton(text="💼 Pro Plan", callback_data="plan_pro")],
        [InlineKeyboardButton(text="👑 Elite Plan", callback_data="plan_elite")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def path_keyboard():
    kb = [
        [InlineKeyboardButton(text="🤖 AI Path", callback_data="path_ai")],
        [InlineKeyboardButton(text="💼 Business Path", callback_data="path_business")],
        [InlineKeyboardButton(text="💰 Crypto Path", callback_data="path_crypto")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back_home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def category_keyboard():
    kb = [
        [InlineKeyboardButton(text="🧠 Starter", callback_data="category_starter")],
        [InlineKeyboardButton(text="💸 Profit", callback_data="category_profit")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back_path")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def upgrade_buttons():
    kb = [
        [InlineKeyboardButton(text="💼 Upgrade to Pro", callback_data="upgrade_pro")],
        [InlineKeyboardButton(text="👑 Upgrade to Elite", callback_data="upgrade_elite")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# -------------------------------
# START Command
# -------------------------------
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    text = (
        "👋 <b>Welcome to AI Tutor Pro Bot</b> — your intelligent mentor for mastering "
        "AI, Business, and Crypto.\n\n"
        "Here’s where your journey begins: choose your plan, unlock smarter systems, and build your future.\n\n"
        "💡 <i>Ask Smart. Think Smart.</i>"
    )
    await message.answer(text, reply_markup=plan_keyboard())


# -------------------------------
# HELP Command
# -------------------------------
@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    text = (
        "🧠 <b>How to use AI Tutor Pro Bot</b>\n\n"
        "• /start – Choose your plan and begin\n"
        "• /questions – Explore categories\n"
        "• /upgrade – Unlock higher levels\n"
        "• /status – Check your usage\n\n"
        "💬 You can also type your own questions anytime!"
    )
    await message.answer(text)


# -------------------------------
# PLAN Selection
# -------------------------------
@dp.callback_query(F.data.startswith("plan_"))
async def select_plan(callback: types.CallbackQuery):
    plan = callback.data.split("_")[1]
    user_plan = plan.lower()

    if user_plan == "free":
        await callback.message.edit_text(
            "✅ <b>Free Plan Selected.</b>\nChoose your path 👇",
            reply_markup=path_keyboard()
        )
    elif user_plan == "pro":
        await callback.message.edit_text(
            "💼 <b>Pro Plan Activated!</b>\nChoose your path 👇",
            reply_markup=path_keyboard()
        )
    elif user_plan == "elite":
        await callback.message.edit_text(
            "👑 <b>Elite Plan Activated!</b>\nChoose your path 👇",
            reply_markup=path_keyboard()
        )


# -------------------------------
# PATH Selection
# -------------------------------
@dp.callback_query(F.data.startswith("path_"))
async def path_select(callback: types.CallbackQuery):
    path = callback.data.split("_")[1]

    if path == "ai":
        intro = "🤖 Welcome to the <b>AI Path</b> — let’s turn intelligence into freedom."
    elif path == "business":
        intro = "💼 Welcome to the <b>Business Path</b> — where systems create clarity and wealth."
    elif path == "crypto":
        intro = "💰 Welcome to the <b>Crypto Path</b> — where strategy meets opportunity."
    else:
        intro = "❓ Unknown path."

    await callback.message.edit_text(
        f"{intro}\n\n💡 Ask Smart. Think Smart.\nGuided by AI Tutor Pro Bot\n\nWhere would you like to begin?",
        reply_markup=category_keyboard()
    )


# -------------------------------
# CATEGORY Selection
# -------------------------------
@dp.callback_query(F.data.startswith("category_"))
async def category_select(callback: types.CallbackQuery):
    category = callback.data.split("_")[1]
    plan_message = (
        "🧠 Here are your questions for the selected category (coming soon!)"
    )
    await callback.message.edit_text(plan_message, reply_markup=upgrade_buttons())


# -------------------------------
# Back Buttons
# -------------------------------
@dp.callback_query(F.data == "back_path")
async def back_to_paths(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Choose your path 👇", reply_markup=path_keyboard()
    )

@dp.callback_query(F.data == "back_home")
async def back_to_home(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🏠 Back to main menu. Choose your plan again 👇",
        reply_markup=plan_keyboard()
    )


# -------------------------------
# UPGRADE
# -------------------------------
@dp.message(Command("upgrade"))
async def upgrade_cmd(message: types.Message):
    await message.answer(
        "🚀 Unlock your full potential with Pro or Elite plans!",
        reply_markup=upgrade_buttons()
    )


# -------------------------------
# STATUS
# -------------------------------
@dp.message(Command("status"))
async def status_cmd(message: types.Message):
    await message.answer(
        "📊 <b>Status:</b>\nFree Plan active.\nUpgrade to Pro or Elite for more power!"
    )


# -------------------------------
# AI CHAT RESPONSE
# -------------------------------
@dp.message()
async def chat_with_ai(message: types.Message):
    user_text = message.text

    try:
        thinking_msg = await message.answer("💭 Thinking...")

        completion = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are AI Tutor Pro Bot, a helpful mentor."},
                {"role": "user", "content": user_text}
            ],
            max_tokens=250,
            temperature=0.8,
        )

        ai_response = completion.choices[0].message.content.strip()
        await thinking_msg.edit_text(ai_response)

    except Exception as e:
        print(f"❌ Error: {e}")
        await message.answer("⚠️ Something went wrong. Please try again.")


# -------------------------------
# Start the bot
# -------------------------------
async def main():
    print("🤖 AI Tutor Pro Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

