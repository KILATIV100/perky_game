import os
from dotenv import load_dotenv

# Завантажуємо змінні з .env файлу (для локальної розробки)
load_dotenv()

# --- Ключові налаштування ---

# Токен вашого Telegram-бота. 
# Тепер він БЕРЕТЬСЯ ТІЛЬКИ зі змінних середовища.
BOT_TOKEN = os.getenv('BOT_TOKEN')

# URL, на якому працює ваш додаток.
WEBAPP_URL = os.getenv('WEBAPP_URL')

# Порт для запуску Uvicorn
PORT = int(os.getenv('PORT', 8000))

# --- Перевірка наявності змінних ---
# Якщо токен або URL не знайдено, програма не запуститься. Це безпечно.
if not BOT_TOKEN:
    raise ValueError("Не знайдено BOT_TOKEN. Додайте його в змінні середовища вашого сервера (напр. Railway).")
if not WEBAPP_URL:
    raise ValueError("Не знайдено WEBAPP_URL. Додайте його в змінні середовища.")


# --- Автоматичне очищення URL ---
# Базовий URL для вебхука (без /game)
BASE_WEBAPP_URL = WEBAPP_URL.rstrip('/').replace('/game', '')

# Повний URL для самої гри
GAME_URL = f"{BASE_WEBAPP_URL}/game"

# URL для встановлення вебхука
WEBHOOK_URL = f"{BASE_WEBAPP_URL}/{BOT_TOKEN}"

