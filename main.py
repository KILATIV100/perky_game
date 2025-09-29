import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, FileResponse # <-- ДОДАНО FileResponse
from fastapi.staticfiles import StaticFiles
from telegram import Update
from telegram.error import RetryAfter
import time

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
    """
    logger.info("Запуск додатка...")
    await setup_bot_handlers()

    try:
        await perky_bot.application.bot.set_webhook(
            url=perky_bot.webhook_url,
            allowed_updates=["message", "callback_query"]
        )
        logger.info(f"Вебхук встановлено на: {perky_bot.webhook_url}")
    except RetryAfter as e:
        logger.warning(f"Telegram flood control: чекаємо {e.retry_after} секунд. Вебхук, ймовірно, вже встановлено іншим процесом.")
        time.sleep(e.retry_after)
    except Exception as e:
        logger.error(f"Критична помилка при встановленні вебхука: {e}")

    yield

    logger.info("Зупинка додатка...")
    try:
        await perky_bot.application.bot.delete_webhook()
        logger.info("Вебхук видалено.")
    except Exception as e:
        logger.error(f"Помилка при видаленні вебхука: {e}")

# Створюємо FastAPI додаток
app = FastAPI(lifespan=lifespan, title="Perky Coffee Jump")

# ВАЖЛИВО: Монтуємо теку "static" для роздачі CSS та JS файлів
app.mount("/static", StaticFiles(directory="static"), name="static")

# Підключаємо роути для гри (/game, /save_stats, etc.)
app.include_router(api_router)

# --- ВИПРАВЛЕННЯ 404: ДОДАНО МАРШРУТ ДЛЯ ОБСЛУГОВУВАННЯ ГРИ ---
@app.get("/game", include_in_schema=False)
async def get_game_html():
    """Обслуговує HTML-файл гри, коли користувач переходить за шляхом /game."""
    return FileResponse("static/index.html")
# ---------------------------------------------

@app.get("/", include_in_schema=False)
async def root_redirect():
    """Перенаправляє з кореневого URL на сторінку гри."""
    return RedirectResponse(url="/game")

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """
    Основний вебхук для отримання оновлень від Telegram.
    """
    try:
        if not perky_bot.application:
            logger.error("Спроба обробити вебхук до ініціалізації бота.")
            raise HTTPException(status_code=503, detail="Бот ще не готовий, спробуйте за мить")

        json_data = await request.json()
        update = Update.de_json(json_data, perky_bot.application.bot)

        # Використовуємо асинхронний менеджер контексту для обробки
        async with perky_bot.application:
            await perky_bot.application.process_update(update)

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Помилка обробки вебхука: {e}")
        return {"status": "error handled"}
