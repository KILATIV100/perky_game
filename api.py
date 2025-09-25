# api.py: Логіка для API ендпоінтів.
# Відповідає за обробку запитів від гри (збереження статистики, отримання рейтингів).

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import logging

# Імпортуємо Pydantic-модель та об'єкт бази даних
from models import GameStats
from database import db

# Налаштування логування
logger = logging.getLogger(__name__)

# Створюємо роутер для API
router = APIRouter()

@router.get("/game", response_class=FileResponse)
async def get_game_page():
    """
    Головний ендпоінт для гри.
    Віддає користувачу файл index.html, який запускає гру.
    """
    return "static/index.html"

@router.post("/save_stats")
async def save_stats(stats: GameStats):
    """
    Зберігає статистику гри, отриману від клієнта.
    """
    try:
        db.save_game_result(
            user_id=stats.user_id,
            score=stats.score,
            beans_collected=stats.collected_beans
        )
        return {"success": True, "message": "Статистику успішно збережено"}
    except Exception as e:
        logger.error(f"Помилка збереження статистики для user {stats.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Не вдалося зберегти статистику")

@router.get("/stats/{user_id}")
async def get_stats(user_id: int):
    """
    Повертає статистику конкретного гравця за його ID.
    """
    user_stats = db.get_user_stats(user_id)
    if not user_stats:
        raise HTTPException(status_code=404, detail="Статистика для гравця не знайдена")
    return user_stats

@router.get("/leaderboard")
async def get_leaderboard():
    """
    Повертає глобальну таблицю лідерів.
    """
    leaderboard_data = db.get_leaderboard()
    # Конвертуємо дані з бази в більш зручний формат JSON
    leaderboard = [
        {"name": row[0], "max_height": row[1], "total_beans": row[2]}
        for row in leaderboard_data
    ]
    return {"leaderboard": leaderboard}
