# models.py: Pydantic моделі для валідації даних.
# Описує, яку структуру даних очікує отримати API.

from pydantic import BaseModel, Field
from typing import Optional

class GameStats(BaseModel):
    """
    Модель для даних, що надходять з гри після завершення раунду.
    Pydantic автоматично перевіряє, що всі поля мають правильний тип.
    """
    user_id: int  # ID користувача в Telegram
    username: Optional[str] = None
    first_name: Optional[str] = None
    score: int    # Фінальний рахунок (висота)
    collected_beans: int # Кількість зібраних зерен за раунд

class SkinAction(BaseModel):
    """
    Модель для валідації дій з скінами (купівля/активація).
    """
    user_id: int
    skin_id: int
    action_type: str = Field(..., pattern="^(buy|activate)$") # Дозволяє лише 'buy' або 'activate'
