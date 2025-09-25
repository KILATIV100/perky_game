import sqlite3
import os
import logging

# Налаштування логера
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "/data/perky_jump.db"):
        """
        Використовуємо шлях /data/, який буде підключено як постійне сховище на Railway.
        """
        self.db_path = db_path
        # Перевіряємо та створюємо директорію, якщо її немає
        db_dir = os.path.dirname(self.db_path)
        try:
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
                logger.info(f"Створено директорію для бази даних: {db_dir}")
        except OSError as e:
            logger.error(f"Не вдалося створити директорію для БД: {e}")

        self.init_database()

    def init_database(self):
        """Ініціалізація або підключення до бази даних."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Таблиця користувачів
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        high_score INTEGER DEFAULT 0,
                        total_beans INTEGER DEFAULT 0,
                        games_played INTEGER DEFAULT 0,
                        best_coffee_per_game INTEGER DEFAULT 0,
                        purchased_skins TEXT DEFAULT '["default"]',
                        current_skin TEXT DEFAULT 'default',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_played TIMESTAMP
                    )
                ''')
                conn.commit()
                logger.info(f"База даних успішно ініціалізована за шляхом: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Помилка при ініціалізації бази даних: {e}")

    def get_user_stats(self, user_id: int) -> dict:
        """Отримати статистику користувача."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user = cursor.fetchone()
                return dict(user) if user else None
        except sqlite3.Error as e:
            logger.error(f"Помилка отримання статистики для user_id {user_id}: {e}")
            return None

    def save_user(self, user_id: int, username: str, first_name: str):
        """Зберегти або оновити інформацію про користувача."""
        try:
            with sqlite3.connect(self.db_path) as conn:
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
            
    def save_game_result(self, user_id: int, username: str, score: int, collected_beans: int):
        """Зберегти результат гри та оновити статистику."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Оновлюємо або вставляємо користувача
                self.save_user(user_id, username, username)

                # Отримуємо поточні рекорди
                cursor.execute("SELECT high_score, best_coffee_per_game FROM users WHERE user_id = ?", (user_id,))
                current_records = cursor.fetchone()
                current_high_score = current_records[0] if current_records else 0
                current_best_coffee = current_records[1] if current_records else 0

                new_high_score = max(current_high_score, score)
                new_best_coffee = max(current_best_coffee, collected_beans)

                # Оновлюємо статистику
                cursor.execute('''
                    UPDATE users SET
                        high_score = ?,
                        total_beans = total_beans + ?,
                        games_played = games_played + 1,
                        best_coffee_per_game = ?,
                        last_played = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (new_high_score, collected_beans, new_best_coffee, user_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Помилка збереження результатів гри для {user_id}: {e}")

    def get_leaderboard(self, limit: int = 10) -> list:
        """Отримати таблицю лідерів."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT username, high_score FROM users
                    WHERE games_played > 0 ORDER BY high_score DESC LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Помилка отримання таблиці лідерів: {e}")
            return []
            
    def save_skin_settings(self, user_id: int, purchased_skins: str, current_skin: str):
        """Зберегти налаштування скінів."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET
                        purchased_skins = ?,
                        current_skin = ?
                    WHERE user_id = ?
                ''', (purchased_skins, current_skin, user_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Помилка збереження скінів для {user_id}: {e}")

# Створюємо єдиний екземпляр класу для всього додатку
db = Database()

