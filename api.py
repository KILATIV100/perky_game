# api.py: Логіка для API ендпоінтів.
# Тут знаходяться роути для отримання гри, збереження статистики тощо.

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from models import GameStats
from database import db

# Налаштування логера
logger = logging.getLogger(__name__)

# Створення роутера. Всі шляхи, визначені тут, будуть додані до основного додатку.
router = APIRouter()

# --- ІГРОВІ РОУТИ ---

@router.get("/game", response_class=FileResponse)
async def get_game_page():
    """Віддає головний HTML-файл гри."""
    return "static/index.html"

# --- РОУТИ ДЛЯ СТАТИСТИКИ ---

@router.post("/save_stats")
async def save_game_stats(stats: GameStats):
    """Зберігає ігрову статистику, отриману від WebApp."""
    try:
        db.save_game_result(stats.user_id, stats.score, stats.collected_beans)
        logger.info(f"Статистику для користувача {stats.user_id} збережено.")
        return {"success": True, "message": "Stats saved successfully"}
    except Exception as e:
        logger.error(f"Помилка збереження статистики: {e}")
        raise HTTPException(status_code=500, detail="Failed to save stats")

@router.get("/stats/{user_id}")
async def get_user_stats(user_id: int):
    """Отримує статистику конкретного користувача."""
    stats = db.get_user_stats(user_id)
    if stats:
        return stats
    raise HTTPException(status_code=404, detail="User not found")

@router.get("/leaderboard")
async def get_leaderboard():
    """Отримує таблицю лідерів."""
    leaderboard = db.get_leaderboard()
    return {"leaderboard": leaderboard}

