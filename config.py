import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_NAME = os.getenv("DB_NAME", "Services.db")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    exit(" Ошибка: BOT_TOKEN не найден в файле .env")
