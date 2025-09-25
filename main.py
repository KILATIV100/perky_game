# main.py: Головний файл для запуску FastAPI-додатку.
# Він ініціалізує додаток, підключає роутери та налаштовує запуск бота.

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging

# Змінено імпорт для уникнення можливих конфліктів імен
from api import router
from bot import setup_bot
from config import PORT

# Налаштування логування для виводу інформації в консоль.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Створення основного екземпляру FastAPI додатку.
app = FastAPI(title="Perky Coffee Jump WebApp")

@app.on_event("startup")
async def startup_event():
    """Виконується один раз при запуску сервера."""
    logging.info("Запуск налаштування Telegram-бота...")
    await setup_bot()
    logging.info("Налаштування бота завершено!")

# Підключення роутера з ендпоінтами з файлу api.py.
# Всі шляхи, визначені в router, будуть доступні в нашому додатку.
app.include_router(router)

# Монтування статичних файлів (CSS, JS).
# Це дозволить серверу віддавати файли з теки 'static' за шляхом '/static'.
# Наприклад, файл static/style.css буде доступний за URL /static/style.css.
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    # Ця частина виконується, тільки якщо файл запускається напряму (для локальної розробки).
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

