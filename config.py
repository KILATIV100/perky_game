# config.py: Конфігураційні змінні.
# Містить усі налаштування, токени та константи для проєкту.

import os
import logging
from dotenv import load_dotenv

# Завантажуємо змінні з файлу .env (для локальної розробки)
load_dotenv()

# Налаштування логування
logger = logging.getLogger(__name__)

# --- Основні налаштування ---

# Токен вашого Telegram-бота. Береться зі змінних середовища.
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Публічна URL-адреса вашого додатку на Railway.
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000")

# Порт, на якому буде працювати сервер. Railway надає його автоматично.
PORT = int(os.getenv("PORT", 8000))

# --- Валідація змінних ---
# Перевіряємо, чи задано токен, інакше виводимо помилку.
if not BOT_TOKEN:
    logger.error("Помилка: не знайдено змінну середовища BOT_TOKEN!")
    # У реальному застосунку тут можна було б завершити роботу
    # raise ValueError("Необхідно встановити BOT_TOKEN")

# --- Очищення та підготовка URL ---
# Гарантуємо, що WEBAPP_URL не містить зайвих слешів у кінці.
# Це важливо для коректної побудови посилань.
BASE_WEBAPP_URL = WEBAPP_URL.rstrip('/').replace('/game', '')

# --- Налаштування бази даних ---
DATABASE_NAME = "perky_jump.db"

