# models.py: Моделі даних для валідації запитів до API.

from pydantic import BaseModel

class GameStats(BaseModel):
    """Модель для даних, що надходять з гри після її завершення."""
    user_id: int
    score: int
    collected_beans: int

