import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from telegram import Update

# Імпортуємо роутер, конфігурацію та логіку бота
from api import router as api_router
from config import BOT_TOKEN
from bot import perky_bot, setup_bot_handlers

# Налаштування логера
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Функція, що виконується при старті та зупинці додатку.
    Ідеальне місце для ініціалізації бота.
    """
    logger.info("Запуск додатка...")
    # Ініціалізуємо додаток бота та всі його обробники
    await setup_bot_handlers()
    # Встановлюємо вебхук
    await perky_bot.application.bot.set_webhook(
        url=perky_bot.webhook_url,
        allowed_updates=["message", "callback_query"]
    )
    logger.info(f"Вебхук встановлено на: {perky_bot.webhook_url}")
    yield
    # Цей код виконається при зупинці сервера
    logger.info("Зупинка додатка...")
    await perky_bot.application.bot.delete_webhook()
    logger.info("Вебхук видалено.")

# Створюємо FastAPI додаток з налаштованим життєвим циклом
app = FastAPI(lifespan=lifespan, title="Perky Coffee Jump")

# Підключаємо роути для гри (/game, /save_stats, etc.)
app.include_router(api_router)

@app.get("/", include_in_schema=False)
async def root_redirect():
    """Перенаправляє користувачів з кореневого URL на сторінку гри."""
    return RedirectResponse(url="/game")

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """
    Основний вебхук для отримання оновлень від Telegram.
    """
    try:
        # Перевіряємо, чи бот ініціалізований
        if not perky_bot.application:
            logger.error("Спроба обробити вебхук до ініціалізації бота.")
            raise HTTPException(status_code=500, detail="Бот не ініціалізований")
            
        # Декодуємо запит та створюємо об'єкт Update
        json_data = await request.json()
        update = Update.de_json(json_data, perky_bot.application.bot)
        
        # Передаємо оновлення для обробки
        await perky_bot.application.process_update(update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Помилка обробки вебхука: {e}")
        # Повертаємо успішний статус, щоб Telegram не намагався повторно надіслати запит
        return {"status": "error handled"}

