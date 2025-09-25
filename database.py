# database.py: Управління базою даних SQLite.
# Цей файл містить клас для роботи з БД та створює єдиний екземпляр
# цього класу для використання у всьому додатку.

import sqlite3
import logging
from typing import Dict, Optional, List, Tuple

from config import DB_PATH

# Налаштування логера
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    def _get_connection(self):
        """Створює та повертає з'єднання з базою даних."""
        conn = sqlite3.connect(self.db_path)
        # Дозволяє звертатися до колонок за їхніми іменами
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Ініціалізує таблиці в базі даних, якщо їх не існує."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Таблиця користувачів
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
                # Таблиця ігор
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS games (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        score INTEGER,
                        beans_collected INTEGER,
                        played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                conn.commit()
            logger.info("Базу даних успішно ініціалізовано.")
        except sqlite3.Error as e:
            logger.error(f"Помилка при ініціалізації БД: {e}")

    def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Отримує статистику конкретного користувача."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except sqlite3.Error as e:
            logger.error(f"Помилка отримання статистики для user_id {user_id}: {e}")
            return None

    def save_user(self, user_id: int, username: str, first_name: str):
        """Зберігає нового користувача або оновлює існуючого."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # INSERT OR IGNORE не буде нічого робити, якщо користувач вже існує
                cursor.execute(
                    "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                    (user_id, username, first_name)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Помилка збереження користувача {user_id}: {e}")

    def save_game_result(self, user_id: int, score: int, beans_collected: int):
        """Зберігає результат гри та оновлює загальну статистику користувача."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Запис результату гри
                cursor.execute(
                    "INSERT INTO games (user_id, score, beans_collected) VALUES (?, ?, ?)",
                    (user_id, score, beans_collected)
                )
                # Оновлення статистики користувача
                cursor.execute("""
                    UPDATE users SET 
                        max_height = MAX(max_height, ?),
                        total_beans = total_beans + ?,
                        games_played = games_played + 1,
                        last_played = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (score, beans_collected, user_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Помилка збереження результату гри для {user_id}: {e}")

    def get_leaderboard(self, limit: int = 10) -> List[Tuple]:
        """Повертає топ гравців за максимальним рекордом."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, first_name, max_height, total_beans
                    FROM users 
                    WHERE games_played > 0
                    ORDER BY max_height DESC
                    LIMIT ?
                """, (limit,))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Помилка отримання таблиці лідерів: {e}")
            return []

# Створюємо єдиний екземпляр класу для роботи з базою даних у всьому додатку.
# Саме цей об'єкт `db` буде імпортуватися в інших файлах (bot.py, api.py).
db = Database()

