# database.py: Управління базою даних SQLite.
# Відповідає за створення таблиць, збереження та отримання даних гравців.

import sqlite3
import logging
from typing import Dict, List, Tuple

# Налаштування логування
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "/data/perky_jump.db"):
        """
        Ініціалізація бази даних.
        ВИПРАВЛЕННЯ: Шлях змінено на /data/ для постійного зберігання на Railway.
        """
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Створює з'єднання з базою даних."""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Ініціалізація таблиць у базі даних, якщо вони не існують."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Таблиця користувачів для зберігання основної статистики
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        max_height INTEGER DEFAULT 0,
                        total_beans INTEGER DEFAULT 0,
                        games_played INTEGER DEFAULT 0,
                        last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблиця для зберігання кожної окремої гри
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
                logger.info("База даних успішно ініціалізована.")
        except Exception as e:
            logger.error(f"Помилка при ініціалізації бази даних: {e}")

    def get_user_stats(self, user_id: int) -> Dict:
        """Отримати повну статистику користувача за його ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, max_height, total_beans, games_played, last_played
                    FROM users WHERE user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'user_id': result[0],
                        'username': result[1],
                        'first_name': result[2],
                        'max_height': result[3],
                        'total_beans': result[4],
                        'games_played': result[5],
                        'last_played': result[6]
                    }
        except Exception as e:
            logger.error(f"Помилка при отриманні статистики для user_id {user_id}: {e}")
        return None

    def save_user_info(self, user_id: int, username: str, first_name: str):
        """Зберігає або оновлює інформацію про користувача (id, username, first_name)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username,
                        first_name = excluded.first_name;
                ''', (user_id, username, first_name))
                conn.commit()
        except Exception as e:
            logger.error(f"Помилка при збереженні користувача {user_id}: {e}")

    def save_game_result(self, user_id: int, score: int, beans_collected: int):
        """Зберігає результат однієї гри та оновлює загальну статистику користувача."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Вставляємо запис про нову гру
                cursor.execute('''
                    INSERT INTO games (user_id, score, beans_collected)
                    VALUES (?, ?, ?)
                ''', (user_id, score, beans_collected))
                
                # Оновлюємо сумарну статистику користувача
                cursor.execute('''
                    UPDATE users SET 
                        max_height = MAX(max_height, ?),
                        total_beans = total_beans + ?,
                        games_played = games_played + 1,
                        last_played = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (score, beans_collected, user_id))
                
                conn.commit()
                logger.info(f"Результати гри для user_id {user_id} збережено: висота={score}, зерна={beans_collected}")
        except Exception as e:
            logger.error(f"Помилка при збереженні результатів гри для user_id {user_id}: {e}")

    def get_leaderboard(self, limit: int = 10) -> List[Tuple]:
        """Отримує глобальну таблицю лідерів на основі максимальної висоти."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # ВИПРАВЛЕННЯ: Використовуємо COALESCE для відображення імені або юзернейму
                cursor.execute('''
                    SELECT 
                        COALESCE(first_name, username, 'Гравець ' || user_id) as display_name,
                        max_height,
                        total_beans
                    FROM users 
                    WHERE games_played > 0
                    ORDER BY max_height DESC
                    LIMIT ?
                ''', (limit,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Помилка при отриманні таблиці лідерів: {e}")
        return []

# Створення єдиного екземпляру класу для всього додатку
db = Database()

