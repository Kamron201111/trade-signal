import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FREE_DAILY_LIMIT = 3
