# main.py: Головний файл для запуску FastAPI-додатку.
# Відповідає за ініціалізацію, запуск сервера та підключення роутерів.

import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from telegram import Update
import uvicorn

# Імпортуємо компоненти з інших файлів
from config import BOT_TOKEN, PORT
from api import router as api_router
from bot import perky_bot, setup_bot

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Створюємо екземпляр FastAPI
app = FastAPI(title="Perky Coffee Jump")

# Підключаємо роутер з api.py для обробки ігрових запитів
app.include_router(api_router)

# Монтуємо теку "static" для роздачі HTML, CSS, JS
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """
    Основний вебхук для отримання оновлень від Telegram.
    """
    try:
        # Перевіряємо, чи бот ініціалізований
        if not perky_bot.application:
            logger.warning("Отримано вебхук, але бот ще не ініціалізований.")
            return {"status": "bot not initialized"}, 503
        
        data = await request.json()
        update = Update.de_json(data, perky_bot.application.bot)
        await perky_bot.application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Помилка обробки вебхука: {e}")
        return {"status": "error"}

@app.on_event("startup")
async def on_startup():
    """
    Функція, яка виконується один раз при запуску сервера.
    Ідеальне місце для налаштування бота.
    """
    logger.info("Запуск налаштування Telegram-бота...")
    await setup_bot()
    logger.info("Налаштування бота завершено!")

if __name__ == "__main__":
    # Цей блок виконується, якщо файл запускається напряму
    # (для локальної розробки)
    uvicorn.run(app, host="0.0.0.0", port=PORT)

