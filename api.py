from fastapi import APIRouter, HTTPException
import logging

from database import db
from models import GameStats

# Налаштування логера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Створення роутера
router = APIRouter()

@router.post("/save_stats")
# kilativ100/perky_game/perky_game-main/api.py (фрагмент)

from fastapi import APIRouter, HTTPException
# ...
from models import GameStats, SkinAction # ДОДАМО SkinAction після створення в models.py

# ... (існуючі ендпоінти /save_stats, /stats/{user_id}, /leaderboard без змін)

@router.get("/skins/{user_id}")
async def get_skins_endpoint(user_id: int):
    """Ендпоінт для отримання всіх скінів та їх статусу для користувача."""
    try:
        skins = db.get_all_skins(user_id)
        return {"success": True, "skins": skins}
    except Exception as e:
        logger.error(f"Помилка отримання скінів для user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутрішня помилка сервера при отриманні скінів.")

@router.post("/skin_action")
async def skin_action_endpoint(action: SkinAction):
    """Ендпоінт для купівлі або активації скіна."""
    if action.action_type == 'buy':
        result = db.buy_skin(action.user_id, action.skin_id)
    elif action.action_type == 'activate':
        result = db.activate_skin(action.user_id, action.skin_id)
    else:
        raise HTTPException(status_code=400, detail="Невідомий тип дії.")
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
        
    return result



async def save_stats_endpoint(stats: GameStats):
    """Ендпоінт для збереження статистики гри."""
    try:
        # Спочатку переконуємось, що користувач існує, або створюємо/оновлюємо його
        db.save_or_update_user(stats.user_id, stats.username, stats.first_name)
        
        # Зберігаємо результат гри
        db.save_game_result(
            user_id=stats.user_id,
            score=stats.score,
            collected_beans=stats.collected_beans
        )
        
        # Повертаємо оновлену статистику, щоб гра могла її відобразити
        updated_stats = db.get_user_stats(stats.user_id)
        
        return {"success": True, "message": "Статистику успішно збережено", "stats": updated_stats}
    except Exception as e:
        logger.error(f"Помилка збереження статистики для user {stats.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутрішня помилка сервера при збереженні статистики.")

@router.get("/stats/{user_id}")
async def get_user_stats_endpoint(user_id: int):
    """Ендпоінт для отримання статистики користувача."""
    try:
        stats = db.get_user_stats(user_id)
        if stats:
            return {"success": True, "stats": stats}
        else:
            # Якщо користувача ще немає в базі, повертаємо нульову статистику
            return {"success": True, "stats": {
                "user_id": user_id, "max_height": 0, "total_beans": 0, "games_played": 0
            }}
    except Exception as e:
        logger.error(f"Помилка отримання статистики для user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутрішня помилка сервера при отриманні статистики.")

@router.get("/leaderboard")
async def get_leaderboard_endpoint():
    """Ендпоінт для отримання таблиці лідерів."""
    try:
        leaderboard = db.get_leaderboard()
        return {"success": True, "leaderboard": leaderboard}
    except Exception as e:
        logger.error(f"Помилка отримання рейтингу: {e}")
        raise HTTPException(status_code=500, detail="Внутрішня помилка сервера при отриманні рейтингу.")

