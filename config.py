"""
⚙️ Bot Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trading_bot.db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # Railway/Render uchun

# Premium narxlar (admin panel orqali o'zgartiriladi)
DEFAULT_PRICES = {
    "weekly": 5.0,
    "monthly": 15.0,
    "quarterly": 35.0,
}

# Bepul limitlar
FREE_DAILY_LIMIT = 3

# To'lov rekvizitlari (admin panel orqali o'zgartiriladi)
DEFAULT_PAYMENT = {
    "card": "8600 XXXX XXXX XXXX",
    "name": "Karta egasi",
    "note": "To'lov izohiga Telegram username yozing"
}
