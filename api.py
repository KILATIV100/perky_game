# api.py: Визначає ендпоінти для взаємодії з грою.

import logging
from fastapi import APIRouter, HTTPException
from database import Database
from models import GameStats
import config

logger = logging.getLogger(__name__)
router = APIRouter()
db = Database(config.DB_PATH)

@router.post("/save_stats", status_code=201)
async def save_game_stats_endpoint(stats: GameStats):
    """API ендпоінт для збереження ігрової статистики."""
    try:
        db.save_game_result(stats.user_id, stats.score, stats.collected_beans)
        return {"success": True, "message": "Stats saved successfully"}
    except Exception as e:
        logger.error(f"Помилка при збереженні статистики: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while saving stats")

