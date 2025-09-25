# config.py: Конфігураційні змінні (токен, URL, налаштування).
# Тут зберігаються всі налаштування, щоб їх було легко змінювати.

import os
from dotenv import load_dotenv

# Завантажує змінні з файлу .env для локальної розробки.
# На сервері ці змінні будуть братися з налаштувань хостингу.
load_dotenv()

# --- ОСНОВНІ НАЛАШТУВАННЯ ---

# Токен вашого Telegram-бота.
BOT_TOKEN = os.getenv('BOT_TOKEN', '8352289810:AAGP6zB_zMd9UMra1vxc-fgMv2m-hr8piG4')

# URL вашого веб-додатку, де він розміщений.
WEBAPP_URL_RAW = os.getenv('WEBAPP_URL', 'https://perky.up.railway.app')

# !!! ВИПРАВЛЕННЯ: Автоматично очищуємо URL від зайвих '/game' або слешів.
# Це гарантує, що вебхук буде встановлено на правильну кореневу адресу,
# навіть якщо в налаштуваннях на сервері буде помилка.
WEBAPP_URL = WEBAPP_URL_RAW.removesuffix('/game').removesuffix('/')

# Порт, на якому буде працювати Uvicorn.
PORT = int(os.getenv('PORT', 8000))

# Шлях до файлу бази даних.
DB_PATH = "perky_jump.db"


# --- НАЛАШТУВАННЯ МАГАЗИНУ ---
SHOP_ITEMS = {
    'coffee_cup': {
        'name': '☕ Кавова чашка Perky',
        'description': 'Стильна керамічна чашка з логотипом Perky Coffee Jump',
        'price': 25000,  # в копійках (250 грн)
    },
    'tshirt': {
        'name': '👕 Футболка Perky',
        'description': 'Комфортна бавовняна футболка з унікальним дизайном гри',
        'price': 45000,  # 450 грн
    },
}

