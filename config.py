# config.py: Всі налаштування та константи проєкту.

import os
from dotenv import load_dotenv

load_dotenv() # Завантажує змінні з .env файлу

# Telegram Bot
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_DEFAULT_TOKEN_HERE')

# Web Application
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://your-app-name.up.railway.app')
PORT = int(os.getenv('PORT', 8000))

# Database
DB_PATH = "perky_jump.db"

# Shop Items (ціна в копійках)
SHOP_ITEMS = {
    'coffee_cup': {
        'name': '☕ Кавова чашка Perky',
        'description': 'Стильна керамічна чашка з логотипом.',
        'price': 25000,
        'currency': 'UAH'
    },
    'tshirt': {
        'name': '👕 Футболка Perky',
        'description': 'Комфортна бавовняна футболка з дизайном гри.',
        'price': 45000,
        'currency': 'UAH'
    }
}

