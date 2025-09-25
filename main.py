# main.py: Головний файл для запуску FastAPI-додатку.
# Він ініціалізує додаток, підключає роутери та запускає налаштування бота.

import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from telegram import Update

from config import BOT_TOKEN
from api import router as api_router
from bot import setup_bot, perky_bot

# Налаштування логування для виводу інформації в консоль
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Створення основного екземпляру FastAPI
app = FastAPI(title="Perky Coffee Jump WebApp")

# --- WEBHOOK РОУТ ---
# Цей роут приймає оновлення від Telegram.
# Ми перенесли його сюди з api.py для надійності.
@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """Обробляє вхідні оновлення від Telegram."""
    try:
        data = await request.json()
        if perky_bot.application:
            update = Update.de_json(data, perky_bot.application.bot)
            await perky_bot.application.process_update(update)
            return {"status": "ok"}
        else:
            logger.warning("Отримано вебхук, але бот ще не ініціалізований.")
            return {"status": "bot not ready"}, 503
    except Exception as e:
        logger.error(f"Помилка обробки вебхука: {e}")
        return {"status": "error"}

# --- ПІДКЛЮЧЕННЯ ІНШИХ ЧАСТИН ДОДАТКУ ---

# Підключення роутера з api.py для обробки /game, /save_stats і т.д.
app.include_router(api_router)

# Вказуємо, що тека 'static' містить статичні файли (css, js, html).
# Це дозволить коректно завантажувати вашу гру.
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- ЗАПУСК ДОДАТКУ ---
@app.on_event("startup")
async def on_startup():
    """Виконується один раз при запуску сервера."""
    logger.info("Запуск налаштування Telegram-бота...")
    await setup_bot()
    logger.info("Налаштування бота завершено!")

