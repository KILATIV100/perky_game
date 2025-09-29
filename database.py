import sqlite3
import logging
from config import DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()

    def _get_connection(self):
        """Створює з'єднання з базою даних."""
        return sqlite3.connect(self.db_path)

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
                logger.info("База даних успішно ініціалізована.")
        except sqlite3.Error as e:
            logger.error(f"Помилка при ініціалізації бази даних: {e}")

    def get_user_stats(self, user_id: int):
        """Отримує статистику користувача за його ID."""
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user_stats = cursor.fetchone()
                return dict(user_stats) if user_stats else None
        except sqlite3.Error as e:
            logger.error(f"Помилка отримання статистики для user {user_id}: {e}")
            return None

    def save_or_update_user(self, user_id: int, username: str, first_name: str):
        """Створює нового користувача або оновлює дані існуючого."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username,
                        first_name = excluded.first_name
                ''', (user_id, username, first_name))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Помилка збереження користувача {user_id}: {e}")

    def save_game_result(self, user_id: int, score: int, collected_beans: int):
        """Зберігає результат гри та оновлює загальну статистику користувача."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # 1. Записати результат поточної гри
                cursor.execute(
                    "INSERT INTO games (user_id, score, beans_collected) VALUES (?, ?, ?)",
                    (user_id, score, collected_beans)
                )
                # 2. Оновити загальну статистику користувача
                cursor.execute('''
                    UPDATE users SET
                        max_height = MAX(max_height, ?),
                        total_beans = total_beans + ?,
                        games_played = games_played + 1,
                        last_played = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (score, collected_beans, user_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Помилка збереження результату гри для user {user_id}: {e}")

    def get_leaderboard(self, limit: int = 10):
        """Отримує топ гравців за максимальною висотою."""
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT username, first_name, max_height FROM users
                    WHERE games_played > 0
                    ORDER BY max_height DESC
                    LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Помилка отримання рейтингу: {e}")
            return []

# Створюємо єдиний екземпляр класу для всього додатку
db = Database()

