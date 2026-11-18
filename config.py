import os
from pathlib import Path

from dotenv import load_dotenv

# Корневая директория проекта
BASE_DIR = Path(__file__).resolve().parent

# Загружаем переменные из .env
load_dotenv(BASE_DIR / ".env")

# Токен Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")

CHAT_ID = int(os.getenv("CHAT_ID", "0"))

if CHAT_ID == 0:
    raise ValueError("CHAT_ID не найден. Проверь файл .env")

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден. Проверь файл .env"
    )

# Часовой пояс
TZ = os.getenv("TZ", "Europe/Vilnius")

# Время автоматических отчётов
WEEKLY_REPORT_TIME = os.getenv(
    "WEEKLY_REPORT_TIME",
    "20:00"
)

MONTH_RESULT_TIME = os.getenv(
    "MONTH_RESULT_TIME",
    "00:05"
)

# Путь к базе данных
DATABASE_PATH = BASE_DIR / "data" / "bot.db"
