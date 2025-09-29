# kilativ100/perky_game/perky_game-main/models.py
# models.py: Pydantic моделі для валідації даних.

from pydantic import BaseModel
from typing import Optional

class GameStats(BaseModel):
    """
    Модель для даних, що надходять з гри після завершення раунду.
    """
    user_id: int  # ID користувача в Telegram
    # --- ДОДАНО НОВІ ПОЛЯ ДЛЯ ВАЛІДАЦІЇ ---
    username: Optional[str] = None # ДОДАНО
    first_name: Optional[str] = None # ДОДАНО
    # -------------------------------------
    score: int    # Фінальний рахунок (висота)
    collected_beans: int # Кількість зібраних зерен за раунд
