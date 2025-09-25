# models.py: Pydantic моделі для валідації даних.
# Описує, яку структуру даних очікує отримати API.

from pydantic import BaseModel
from typing import Optional

class GameStats(BaseModel):
    """
    Модель для даних, що надходять з гри після завершення раунду.
    Pydantic автоматично перевіряє, що всі поля мають правильний тип.
    """
    user_id: int  # ID користувача в Telegram
    score: int    # Фінальний рахунок (висота)
    collected_beans: int # Кількість зібраних зерен за раунд
