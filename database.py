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
                # ... (таблиці users та games без змін)
                
                # --- ДОДАНО: Таблиця доступних скінів ---
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS skins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        price INTEGER DEFAULT 100,
                        is_default BOOLEAN DEFAULT FALSE,
                        svg_data TEXT
                    )
                ''')
                
                # --- ДОДАНО: Таблиця куплених скінів користувачів ---
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_skins (
                        user_id INTEGER,
                        skin_id INTEGER,
                        is_active BOOLEAN DEFAULT FALSE,
                        PRIMARY KEY (user_id, skin_id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (skin_id) REFERENCES skins (id)
                    )
                ''')
                conn.commit()
                
                # ДОДАНО: Ініціалізація скінів (запуск тільки якщо таблиця пуста)
                cursor.execute("SELECT COUNT(*) FROM skins")
                if cursor.fetchone()[0] == 0:
                    self._populate_initial_skins(cursor)
                    conn.commit()
                    
                logger.info("База даних успішно ініціалізована.")
        except sqlite3.Error as e:
            logger.error(f"Помилка при ініціалізації бази даних: {e}")

    def _populate_initial_skins(self, cursor):
        """Заповнює таблицю скінів початковими даними."""
        skins_data = [
            # ID 1: Дефолтний скін, безкоштовний
            ("Default Robot", 0, True, "default"), 
            # ID 2: Приклад платного скіна
            ("Red Hot", 500, False, "red_hot"), 
            # ID 3: Ще один приклад
            ("Blue Ice", 1000, False, "blue_ice"), 
        ]
        # Примітка: SVG_DATA - тут тимчасовий рядок для позначення, на ділі тут має бути SVG-код
        cursor.executemany(
            "INSERT INTO skins (name, price, is_default, svg_data) VALUES (?, ?, ?, ?)",
            skins_data
        )

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

     def get_all_skins(self, user_id: int):
        """Отримує всі скіни, позначаючи, які куплені та активні для користувача."""
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT 
                        s.id, s.name, s.price, s.is_default, s.svg_data,
                        us.skin_id IS NOT NULL AS is_owned,
                        us.is_active
                    FROM skins s
                    LEFT JOIN user_skins us ON s.id = us.skin_id AND us.user_id = ?
                    ORDER BY s.id
                """, (user_id,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Помилка отримання скінів для user {user_id}: {e}")
            return []

    def buy_skin(self, user_id: int, skin_id: int):
        """Логіка купівлі скіна."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Перевірка, чи скін існує і яка його ціна
                cursor.execute("SELECT price FROM skins WHERE id = ?", (skin_id,))
                skin = cursor.fetchone()
                if not skin:
                    return {"success": False, "message": "Скін не знайдено."}
                price = skin[0]
                
                # 2. Перевірка балансу користувача
                cursor.execute("SELECT total_beans FROM users WHERE user_id = ?", (user_id,))
                user_beans = cursor.fetchone()[0]
                
                if user_beans < price:
                    return {"success": False, "message": "Недостатньо кавових зерен."}

                # 3. Перевірка, чи вже куплено
                cursor.execute("SELECT * FROM user_skins WHERE user_id = ? AND skin_id = ?", (user_id, skin_id))
                if cursor.fetchone():
                    return {"success": False, "message": "Скін вже куплено."}
                
                # 4. Проведення транзакції
                cursor.execute("UPDATE users SET total_beans = total_beans - ? WHERE user_id = ?", (price, user_id))
                cursor.execute("INSERT INTO user_skins (user_id, skin_id, is_active) VALUES (?, ?, FALSE)", (user_id, skin_id))
                
                conn.commit()
                return {"success": True, "message": "Скін успішно придбано!"}
        except sqlite3.Error as e:
            logger.error(f"Помилка купівлі скіна {skin_id} для user {user_id}: {e}")
            return {"success": False, "message": f"Помилка БД: {e}"}

    def activate_skin(self, user_id: int, skin_id: int):
        """Активує обраний скін."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Перевірка, чи належить скін користувачу (або це дефолтний)
                cursor.execute("""
                    SELECT 
                        (SELECT is_default FROM skins WHERE id = ?) AS is_default_skin,
                        (SELECT skin_id FROM user_skins WHERE user_id = ? AND skin_id = ?) AS is_owned
                """, (skin_id, user_id, skin_id))
                
                result = cursor.fetchone()
                if not result or (result[0] == 0 and result[1] is None):
                     return {"success": False, "message": "Скін не належить вам або не існує."}

                # 2. Деактивувати всі поточні скіни
                cursor.execute("UPDATE user_skins SET is_active = FALSE WHERE user_id = ?", (user_id,))
                
                # 3. Активувати обраний скін (якщо це не дефолтний)
                if result[0] == 0: # Якщо не дефолтний
                    cursor.execute("UPDATE user_skins SET is_active = TRUE WHERE user_id = ? AND skin_id = ?", (user_id, skin_id))
                
                conn.commit()
                return {"success": True, "message": "Скін успішно активовано!"}
        except sqlite3.Error as e:
            logger.error(f"Помилка активації скіна {skin_id} для user {user_id}: {e}")
            return {"success": False, "message": f"Помилка БД: {e}"}

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

