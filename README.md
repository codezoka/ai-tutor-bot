# 🤖 AI Tutor Pro Bot

AI Tutor Pro Bot helps users learn, grow, and profit in **Crypto**, **AI**, and **Business** — powered by GPT intelligence.  
Built for Telegram, hosted on DigitalOcean with Flask webhook integration.

---

## 🚀 Features

- 💬 **Chat freely** with AI at any time  
- 🧭 Smart question explorer: `/questions`  
  - Free (10 total)
  - Pro (30 total)
  - Elite (50 total)
- 🏦 Built-in CryptoBot payments:
  - Pro Monthly / Yearly
  - Elite Monthly / Yearly (with 20% countdown discount)
- 🧠 **Personalized learning:** Starter & Profit levels in each category
- 💎 Upgrade system with `/upgrade`
- 📊 Status overview `/status`
- 🔔 Daily motivational quotes
- ⚡ Powered by GPT-4o for premium users and GPT-4o-mini for free users
- 🌐 Hosted on DigitalOcean (Flask webhook)

---

## ⚙️ Environment Setup

Create a `.env` file in your project root:

```bash
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
OPENAI_API_KEY=YOUR_OPENAI_KEY

PRO_MONTHLY_URL=https://t.me/send?start=IVdixIeFSP3W
PRO_YEARLY_URL=https://t.me/send?start=IVRnAnXOWzRM
ELITE_MONTHLY_URL=https://t.me/send?start=IVfwy1t6hcu9
ELITE_YEARLY_URL=https://t.me/send?start=IVxMW0UNvl7d
