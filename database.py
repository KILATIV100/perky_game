# database.py: Управління всіма операціями з базою даних SQLite.

import sqlite3
from typing import Dict, List, Tuple, Optional

class Database:
    """Клас для роботи з базою даних SQLite."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Створює та повертає з'єднання з БД."""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Ініціалізує структуру бази даних (таблиці)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    max_height INTEGER DEFAULT 0,
                    total_beans INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_played TIMESTAMP
                )
            ''')
            conn.commit()
    
    def save_user(self, user_id: int, username: Optional[str] = None, first_name: Optional[str] = None):
        """Зберігає нового користувача або ігнорує, якщо він вже існує."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
            conn.commit()
    
    def save_game_result(self, user_id: int, score: int, beans_collected: int):
        """Оновлює статистику користувача після завершення гри."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET 
                    max_height = MAX(max_height, ?),
                    total_beans = total_beans + ?,
                    games_played = games_played + 1,
                    last_played = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (score, beans_collected, user_id))
            conn.commit()

    def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Отримує статистику конкретного користувача."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_leaderboard(self, limit: int = 10) -> List[Tuple]:
        """Повертає топ гравців за максимальною висотою."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username, first_name, max_height
                FROM users 
                WHERE games_played > 0
                ORDER BY max_height DESC
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()

