import sqlite3
import logging
try:
    from config import DB_PATH
except ImportError:
    # Припускаємо стандартний шлях для локальної розробки
    DB_PATH = 'perky_jump.db'

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
                # Таблиця користувачів (ОНОВЛЕНО: Додано active_skin_id)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        max_height INTEGER DEFAULT 0,
                        total_beans INTEGER DEFAULT 0,
                        games_played INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_played TIMESTAMP,
                        active_skin_id INTEGER DEFAULT 1 -- Додано поле для активного скіна (Default = ID 1)
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
                        PRIMARY KEY (user_id, skin_id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (skin_id) REFERENCES skins (id)
                    )
                ''')
                
                # Заповнення скінами, якщо таблиця пуста
                cursor.execute("SELECT COUNT(*) FROM skins")
                if cursor.fetchone()[0] == 0:
                    self._populate_initial_skins(cursor)

                # Додати дефолтний скін кожному користувачу
                self._ensure_default_skin_for_all_users(cursor)

                conn.commit()
                logger.info("База даних успішно ініціалізована.")
        except sqlite3.Error as e:
            logger.error(f"Помилка при ініціалізації бази даних: {e}")

    def _populate_initial_skins(self, cursor):
        """Заповнює таблицю скінів початковими даними, використовуючи 12 скінів."""
        
        # Перший скін - Default Robot
        skins_data = [
            ("Default Robot", 0, True, "default_robot.svg"), 
        ]

        # Додаємо 11 додаткових скінів (skin_1.svg до skin_11.svg)
        # Ціни поступово зростають для стимуляції накопичення зерен
        base_price = 400
        for i in range(1, 12):
            price = base_price + (i * 150) # Ціни від 550 до 2050
            name = f"Skin #{i}"
            svg_file = f"skin_{i}.svg"
            skins_data.append((name, price, False, svg_file))
        
        cursor.executemany(
            "INSERT INTO skins (name, price, is_default, svg_data) VALUES (?, ?, ?, ?)",
            skins_data
        )
        logger.info("Початкові 12 скінів додано.")

    def _ensure_default_skin_for_all_users(self, cursor):
        """Гарантує, що кожен користувач має default скін у user_skins."""
        cursor.execute("""
            INSERT OR IGNORE INTO user_skins (user_id, skin_id)
            SELECT user_id, (SELECT id FROM skins WHERE is_default = TRUE LIMIT 1)
            FROM users
        """)

    def get_user_stats(self, user_id: int):
        """Отримує статистику користувача за його ID (ОНОВЛЕНО: включає активний скін)."""
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        u.*, 
                        s.svg_data AS active_skin
                    FROM users u
                    JOIN skins s ON u.active_skin_id = s.id
                    WHERE u.user_id = ?
                """, (user_id,))
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
                self._ensure_default_skin_for_all_users(cursor) # Додати дефолтний скін при створенні/оновленні
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

    # --- НОВІ МЕТОДИ ДЛЯ СКІНІВ ---

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
                        s.id = u.active_skin_id AS is_active
                    FROM skins s
                    LEFT JOIN user_skins us ON s.id = us.skin_id AND us.user_id = ?
                    JOIN users u ON u.user_id = ?
                    ORDER BY s.id
                """, (user_id, user_id))
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
                cursor.execute("SELECT price, is_default FROM skins WHERE id = ?", (skin_id,))
                skin = cursor.fetchone()
                if not skin:
                    return {"success": False, "message": "Скін не знайдено."}
                price, is_default = skin
                
                if is_default:
                    return {"success": False, "message": "Дефолтний скін не можна купувати."}
                
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
                cursor.execute("INSERT INTO user_skins (user_id, skin_id) VALUES (?, ?)", (user_id, skin_id))
                
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
                
                # 1. Перевірка, чи належить скін користувачу або чи це дефолтний скін
                cursor.execute("""
                    SELECT 
                        s.is_default,
                        us.skin_id
                    FROM skins s
                    LEFT JOIN user_skins us ON s.id = us.skin_id AND us.user_id = ?
                    WHERE s.id = ?
                """, (user_id, skin_id))
                
                result = cursor.fetchone()
                if not result:
                     return {"success": False, "message": "Скін не існує."}
                
                is_default, is_owned_id = result
                
                if not is_default and is_owned_id is None:
                     return {"success": False, "message": "Скін не належить вам."}

                # 2. Активувати обраний скін
                cursor.execute("UPDATE users SET active_skin_id = ? WHERE user_id = ?", (skin_id, user_id))
                
                conn.commit()
                
                # Оновлюємо та повертаємо активний скін для JS
                updated_stats = self.get_user_stats(user_id)
                return {"success": True, "message": "Скін успішно активовано!", "active_skin": updated_stats['active_skin']}
        except sqlite3.Error as e:
            logger.error(f"Помилка активації скіна {skin_id} для user {user_id}: {e}")
            return {"success": False, "message": f"Помилка БД: {e}"}

# Створюємо єдиний екземпляр класу для всього додатку
db = Database()
