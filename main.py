import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional

import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, PreCheckoutQueryHandler, ShippingQueryHandler
from telegram.constants import ParseMode
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Змінні середовища
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL')
PORT = int(os.getenv('PORT', 8000))

# FastAPI додаток
app = FastAPI(title="Perky Coffee Jump WebApp")

# Pydantic моделі для API
class GameStats(BaseModel):
    user_id: int
    score: int
    collected_beans: int

class UserStats(BaseModel):
    user_id: int
    username: Optional[str] = None
    max_height: int = 0
    total_beans: int = 0
    games_played: int = 0
    last_played: Optional[str] = None

# База даних
class Database:
    def __init__(self, db_path: str = "perky_jump.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Ініціалізація бази даних"""
        with sqlite3.connect(self.db_path) as conn:
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
            
            # Таблиця замовлень
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    product_name TEXT,
                    price INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Отримати статистику користувача"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, max_height, total_beans, games_played, last_played
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'user_id': result[0],
                    'username': result[1],
                    'max_height': result[2],
                    'total_beans': result[3],
                    'games_played': result[4],
                    'last_played': result[5]
                }
            return None
    
    def save_user(self, user_id: int, username: str = None, first_name: str = None):
        """Зберегти або оновити користувача"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
            ''', (user_id, username, first_name))
            conn.commit()
    
    def save_game_result(self, user_id: int, score: int, beans_collected: int):
        """Зберегти результат гри"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Додати запис про гру
            cursor.execute('''
                INSERT INTO games (user_id, score, beans_collected)
                VALUES (?, ?, ?)
            ''', (user_id, score, beans_collected))
            
            # Оновити статистику користувача
            cursor.execute('''
                UPDATE users SET 
                    max_height = MAX(max_height, ?),
                    total_beans = total_beans + ?,
                    games_played = games_played + 1,
                    last_played = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (score, beans_collected, user_id))
            
            conn.commit()
    
    def get_leaderboard(self, limit: int = 10) -> list:
        """Отримати таблицю лідерів"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username, first_name, max_height, total_beans
                FROM users 
                WHERE games_played > 0
                ORDER BY max_height DESC
                LIMIT ?
            ''', (limit,))
            
            return cursor.fetchall()

# Ініціалізація бази даних
db = Database()

# Товари в магазині
SHOP_ITEMS = {
    'coffee_cup': {
        'name': '☕ Кавова чашка Perky',
        'description': 'Стильна керамічна чашка з логотипом Perky Coffee Jump',
        'price': 25000,  # в копійках (250 грн)
        'currency': 'UAH',
        'photo': 'https://example.com/coffee_cup.jpg'
    },
    'tshirt': {
        'name': '👕 Футболка Perky',
        'description': 'Комфортна бавовняна футболка з унікальним дизайном гри',
        'price': 45000,  # 450 грн
        'currency': 'UAH',
        'photo': 'https://example.com/tshirt.jpg'
    },
    'travel_mug': {
        'name': '🥤 Термокружка Perky',
        'description': 'Подорожня термокружка для справжніх кавоманів',
        'price': 35000,  # 350 грн
        'currency': 'UAH',
        'photo': 'https://example.com/travel_mug.jpg'
    },
    'coffee_beans': {
        'name': '🍵 Кава Perky Blend',
        'description': 'Ексклюзивна суміш кавових зерен від Perky Coffee',
        'price': 30000,  # 300 грн
        'currency': 'UAH',
        'photo': 'https://example.com/coffee_beans.jpg'
    }
}

# Telegram Bot функції
class PerkyCoffeeBot:
    def __init__(self):
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка команди /start"""
        user = update.effective_user
        
        # Зберегти користувача в БД
        db.save_user(user.id, user.username, user.first_name)
        
        welcome_message = f"""
🤖☕ Ласкаво просимо до Perky Coffee Jump!

Привіт, {user.first_name}! 👋

Це захоплююча платформер-гра, де ти граєш за кавового робота, який намагається підстрибнути якомога вище, збираючи кавові зерна!

🎮 Як грати:
• Стрибай з платформи на платформу
• Збирай кавові зерна ☕
• Намагайся досягти максимальної висоти!

Обери дію нижче:
        """
        
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/game"))],
            [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
            [InlineKeyboardButton("🛒 Магазин", callback_data='shop')],
            [InlineKeyboardButton("❓ Допомога", callback_data='help')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка натискань кнопок"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'stats':
            await self.show_stats(query)
        elif query.data == 'shop':
            await self.show_shop(query)
        elif query.data == 'help':
            await self.show_help(query)
        elif query.data == 'leaderboard':
            await self.show_leaderboard(query)
        elif query.data == 'back_main':
            await self.back_to_main(query)
        elif query.data.startswith('buy_'):
            item_id = query.data.replace('buy_', '')
            await self.buy_item(query, item_id)
    
    async def show_stats(self, query):
        """Показати статистику користувача"""
        user_id = query.from_user.id
        stats = db.get_user_stats(user_id)
        
        if not stats or stats['games_played'] == 0:
            stats_text = """
📊 Твоя статистика

🎮 Ігор зіграно: 0
🏔️ Максимальна висота: 0 м
☕ Зібрано зерен: 0
📅 Остання гра: Ще не грав

Час почати свою першу гру! 🚀
            """
        else:
            last_played = stats['last_played']
            if last_played:
                last_played = datetime.fromisoformat(last_played).strftime("%d.%m.%Y %H:%M")
            
            stats_text = f"""
📊 Твоя статистика

🎮 Ігор зіграно: {stats['games_played']}
🏔️ Максимальна висота: {stats['max_height']} м
☕ Зібрано зерен: {stats['total_beans']}
📅 Остання гра: {last_played or 'Невідомо'}

Продовжуй грати та покращуй свої рекорди! 🏆
            """
        
        keyboard = [
            [InlineKeyboardButton("🏆 Таблиця лідерів", callback_data='leaderboard')],
            [InlineKeyboardButton("↩️ Назад", callback_data='back_main')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            stats_text,
            reply_markup=reply_markup
        )
    
    async def show_leaderboard(self, query):
        """Показати таблицю лідерів"""
        leaderboard = db.get_leaderboard(10)
        
        if not leaderboard:
            leaderboard_text = """
🏆 Таблиця лідерів

Поки що немає записів.
Стань першим! 🚀
            """
        else:
            leaderboard_text = "🏆 Топ-10 гравців:\n\n"
            
            for i, (username, first_name, max_height, total_beans) in enumerate(leaderboard, 1):
                name = username or first_name or "Невідомий"
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{emoji} {name}\n🏔️ {max_height} м | ☕ {total_beans} зерен\n\n"
        
        keyboard = [
            [InlineKeyboardButton("↩️ Назад до статистики", callback_data='stats')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            leaderboard_text,
            reply_markup=reply_markup
        )
    
    async def show_shop(self, query):
        """Показати магазин"""
        shop_text = """
🛒 Магазин Perky Coffee

Купуй ексклюзивний мерч та кавові товари!
Всі покупки підтримують розвиток гри ❤️
        """
        
        keyboard = []
        for item_id, item in SHOP_ITEMS.items():
            price_grn = item['price'] // 100
            keyboard.append([
                InlineKeyboardButton(
                    f"{item['name']} - {price_grn} грн", 
                    callback_data=f'buy_{item_id}'
                )
            ])
        
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data='back_main')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            shop_text,
            reply_markup=reply_markup
        )
    
    async def buy_item(self, query, item_id: str):
        """Купити товар"""
        if item_id not in SHOP_ITEMS:
            await query.answer("Товар не знайдено!")
            return
        
        item = SHOP_ITEMS[item_id]
        
        # Тут буде інтеграція з Telegram Payments
        # Поки що показуємо інформацію про товар
        item_text = f"""
{item['name']}

{item['description']}

💰 Ціна: {item['price'] // 100} грн

🔜 Оплата буде додана незабаром!
Ми працюємо над інтеграцією платіжної системи.
        """
        
        keyboard = [
            [InlineKeyboardButton("↩️ Назад до магазину", callback_data='shop')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            item_text,
            reply_markup=reply_markup
        )
    
    async def show_help(self, query):
        """Показати допомогу"""
        help_text = """
❓ Як грати в Perky Coffee Jump

🎮 Керування:
• На мобільному: торкайся екрану для стрибків
• На комп'ютері: використовуй клавіші стрілок або WASD

🎯 Мета гри:
• Стрибай якомога вище
• Збирай кавові зерна ☕
• Не падай вниз!

🏆 Очки:
• Висота = очки
• Кожне зерно додає до статистики
• Встановлюй нові рекорди!

💡 Поради:
• Ретельно розраховуй стрибки
• Збирай всі зерна на шляху
• Тренуйся для покращення результатів

Удачі в грі! 🚀
        """
        
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data='back_main')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text,
            reply_markup=reply_markup
        )
    
    async def back_to_main(self, query):
        """Повернутися до головного меню"""
        user = query.from_user
        
        welcome_message = f"""
🤖☕ Ласкаво просимо до Perky Coffee Jump!

Привіт, {user.first_name}! 👋

Це захоплююча платформер-гра, де ти граєш за кавового робота, який намагається підстрибнути якомога вище, збираючи кавові зерна!

Обери дію нижче:
        """
        
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/game"))],
            [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
            [InlineKeyboardButton("🛒 Магазин", callback_data='shop')],
            [InlineKeyboardButton("❓ Допомога", callback_data='help')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_message,
            reply_markup=reply_markup
        )

# Ініціалізація бота
perky_bot = PerkyCoffeeBot()

# FastAPI роути
@app.get("/game", response_class=HTMLResponse)
async def get_game():
    """Повертає HTML гру"""
    # Ваш HTML код гри тут - я збережу його як є, але з мінімальними змінами
    html_content = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖☕ Perky Coffee Jump</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            overflow: hidden;
            height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            user-select: none;
            -webkit-user-select: none;
            -webkit-touch-callout: none;
        }

        .game-container {
            position: relative;
            width: 100%;
            max-width: 400px;
            height: 100vh;
            background: linear-gradient(180deg, #87CEEB 0%, #98FB98 100%);
            border-radius: 0;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            touch-action: none;
        }

        canvas {
            display: block;
            width: 100%;
            height: 100%;
        }

        .ui-panel {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            color: #fff;
            font-weight: bold;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        }

        .ui-panel .item {
            display: flex;
            align-items: center;
        }

        .ui-panel .icon {
            margin-right: 5px;
            font-size: 1.5em;
        }

        .end-game-screen {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.7);
            color: #fff;
            padding: 20px 40px;
            border-radius: 15px;
            text-align: center;
            display: none;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 100;
        }
        
        .end-game-screen h2 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .end-game-screen p {
            font-size: 1.2em;
            margin-bottom: 20px;
        }

        .end-game-screen button {
            background: #fff;
            color: #4b0082;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
        }
        .end-game-screen button:hover {
            background: #e0e0e0;
        }
        .buttons-container {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .achievement-notification {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.8);
            color: #fff;
            padding: 10px 20px;
            border-radius: 10px;
            text-align: center;
            opacity: 0;
            transition: opacity 0.5s ease-in-out;
            pointer-events: none;
            z-index: 200;
        }
    </style>
</head>
<body>
    <div class="game-container">
        <canvas id="gameCanvas"></canvas>
        <div class="ui-panel">
            <div class="item">
                <span class="icon">📏 Висота:</span>
                <span id="scoreDisplay">0 м</span>
            </div>
            <div class="item">
                <span class="icon">☕</span>
                <span id="beansDisplay">0</span>
            </div>
        </div>
        <div class="end-game-screen" id="endGameScreen">
            <h2 id="finalScore">Гра завершена!</h2>
            <p id="highScore">Новий рекорд: 0 м</p>
            <p id="totalBeans">Зібрано зерен: 0</p>
            <div class="buttons-container">
                <button id="restartButton">Спробувати ще раз</button>
                <button id="mainMenuButton">Головне меню</button>
            </div>
        </div>
    </div>
    <div class="achievement-notification" id="achievementNotification"></div>

    <script>
        // Ініціалізація Telegram WebApp
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
        
        // Game variables
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreDisplay = document.getElementById('scoreDisplay');
        const beansDisplay = document.getElementById('beansDisplay');
        const endGameScreen = document.getElementById('endGameScreen');
        const finalScoreDisplay = document.getElementById('finalScore');
        const highScoreDisplay = document.getElementById('highScore');
        const totalBeansDisplay = document.getElementById('totalBeans');
        const restartButton = document.getElementById('restartButton');
        const mainMenuButton = document.getElementById('mainMenuButton');
        const achievementNotification = document.getElementById('achievementNotification');

        let player;
        let platforms;
        let gameScore;
        let beans;
        let lastPlatformY;
        let isGameOver;
        let keys = {};
        let touchStart = null;
        let touchEnd = null;
        let maxJumpHeight = 150;
        let beanSpawnRate = 0.5;
        let playerWidth = 40;
        let playerHeight = 40;
        let platformWidth = 80;
        let platformHeight = 10;
        let gameDifficulty = 1;
        let vibrationEnabled = true;

        let gameStats = {
            highScore: 0,
            totalBeans: 0
        };

        // Player class
        class Player {
            constructor(x, y) {
                this.x = x;
                this.y = y;
                this.width = playerWidth;
                this.height = playerHeight;
                this.dy = 0;
                this.onGround = false;
                this.isJumping = false;
            }

            draw() {
                // Намалювати кавового робота
                ctx.fillStyle = '#8B4513';
                ctx.fillRect(this.x, this.y, this.width, this.height);
                
                // Очі робота
                ctx.fillStyle = '#FFD700';
                ctx.fillRect(this.x + 8, this.y + 8, 8, 8);
                ctx.fillRect(this.x + 24, this.y + 8, 8, 8);
                
                // Посмішка
                ctx.fillStyle = '#FFD700';
                ctx.fillRect(this.x + 12, this.y + 24, 16, 4);
            }

            update() {
                this.y += this.dy;

                if (!this.onGround) {
                    this.dy += 0.5; // Gravity
                }

                if (this.y + this.height > canvas.height) {
                    this.y = canvas.height - this.height;
                    this.onGround = true;
                    this.isJumping = false;
                    this.dy = 0;
                }
            }

            jump() {
                if (this.onGround) {
                    this.dy = -15;
                    this.onGround = false;
                    this.isJumping = true;
                    vibrate([50]);
                }
            }
        }

        // Platform class
        class Platform {
            constructor(x, y) {
                this.x = x;
                this.y = y;
                this.width = platformWidth;
                this.height = platformHeight;
            }

            draw() {
                ctx.fillStyle = '#A0522D';
                ctx.fillRect(this.x, this.y, this.width, this.height);
                
                // Додати текстуру платформи
                ctx.fillStyle = '#8B4513';
                ctx.fillRect(this.x + 2, this.y + 2, this.width - 4, this.height - 4);
            }
        }

        // Bean class
        class Bean {
            constructor(x, y) {
                this.x = x;
                this.y = y;
                this.size = 10;
                this.collected = false;
            }

            draw() {
                if (!this.collected) {
                    // Кавове зерно
                    ctx.fillStyle = '#4B0082';
                    ctx.beginPath();
                    ctx.ellipse(this.x, this.y, this.size, this.size * 0.8, 0, 0, Math.PI * 2);
                    ctx.fill();
                    
                    // Блик на зерні
                    ctx.fillStyle = '#8A2BE2';
                    ctx.beginPath();
                    ctx.ellipse(this.x - 3, this.y - 3, this.size * 0.3, this.size * 0.2, 0, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
        }

        // Initialize game
        function init() {
            resizeCanvas();
            player = new Player(canvas.width / 2 - playerWidth / 2, canvas.height - playerHeight);
            platforms = [];
            beans = [];
            gameScore = 0;
            lastPlatformY = canvas.height - 100;
            isGameOver = false;

            // Generate initial platforms
            for (let i = 0; i < 10; i++) {
                let x = Math.random() * (canvas.width - platformWidth);
                let y = lastPlatformY - i * 80;
                platforms.push(new Platform(x, y));
                
                // Spawn beans
                if (Math.random() < beanSpawnRate) {
                    beans.push(new Bean(x + platformWidth / 2, y - 20));
                }
            }
            
            loadStats();
        }

        function resizeCanvas() {
            const container = document.querySelector('.game-container');
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
        }

        // Handle game over
        function gameOver() {
            isGameOver = true;
            endGameScreen.style.display = 'flex';
            
            const finalScore = Math.floor(gameScore / 10);
            finalScoreDisplay.textContent = `Ти пролетів: ${finalScore} м`;
            totalBeansDisplay.textContent = `Зібрано зерен: ${gameStats.totalBeans}`;
            
            if (finalScore > gameStats.highScore) {
                gameStats.highScore = finalScore;
                highScoreDisplay.textContent = `Новий рекорд: ${gameStats.highScore} м`;
                highScoreDisplay.style.color = 'gold';
                showAchievementNotification('🏅 Новий рекорд!');
                vibrate([200, 100, 200]);
            } else {
                highScoreDisplay.textContent = `Рекорд: ${gameStats.highScore} м`;
                highScoreDisplay.style.color = '#fff';
            }

            // Зберегти статистику на сервері
            saveGameStats(finalScore, gameStats.totalBeans);
            saveStats();
        }

        // Game loop
        function update() {
            if (isGameOver) return;

            player.update();

            // Check for collision with platforms
            platforms.forEach(platform => {
                if (player.dy > 0 && 
                    player.x + player.width > platform.x &&
                    player.x < platform.x + platform.width &&
                    player.y + player.height > platform.y &&
                    player.y + player.height < platform.y + platform.height + 10) {
                    
                    player.y = platform.y - player.height;
                    player.onGround = true;
                    player.isJumping = false;
                    player.dy = 0;
                }
            });

            // Handle player input
            if (keys['ArrowUp'] || keys['w'] || keys[' '] || (touchEnd && touchEnd.y < touchStart.y - 20)) {
                player.jump();
                touchStart = null;
                touchEnd = null;
            } else if (keys['ArrowLeft'] || keys['a']) {
                player.x -= 5;
            } else if (keys['ArrowRight'] || keys['d']) {
                player.x += 5;
            }

            // Keep player within canvas bounds
            if (player.x < 0) player.x = 0;
            if (player.x + player.width > canvas.width) player.x = canvas.width - player.width;

            // Update platforms and generate new ones
            if (player.dy < 0) {
                platforms.forEach(platform => {
                    platform.y -= player.dy;
                });
                beans.forEach(bean => {
                    bean.y -= player.dy;
                });
                gameScore += Math.abs(player.dy);
            }
            
            platforms = platforms.filter(platform => platform.y < canvas.height);
            beans = beans.filter(bean => bean.y < canvas.height);
            
            while (platforms.length < 10) {
                let x = Math.random() * (canvas.width - platformWidth);
                let y = platforms[platforms.length - 1].y - 80;
                platforms.push(new Platform(x, y));
                
                // Spawn beans
                if (Math.random() < beanSpawnRate) {
                    beans.push(new Bean(x + platformWidth / 2, y - 20));
                }
            }

            // Check for bean collection
            beans.forEach((bean, index) => {
                if (!bean.collected &&
                    player.x < bean.x + bean.size &&
                    player.x + player.width > bean.x - bean.size &&
                    player.y < bean.y + bean.size &&
                    player.y + player.height > bean.y - bean.size) {
                    
                    bean.collected = true;
                    gameStats.totalBeans++;
                    beans.splice(index, 1);
                    vibrate([30]);
                    
                    // Achievement notifications
                    if (gameStats.totalBeans % 10 === 0) {
                        showAchievementNotification(`☕ ${gameStats.totalBeans} зерен зібрано!`);
                    }
                }
            });

            // Update UI
            scoreDisplay.textContent = Math.floor(gameScore / 10) + ' м';
            beansDisplay.textContent = gameStats.totalBeans;

            // Check if player falls off the bottom
            if (player.y > canvas.height) {
                gameOver();
            }
        }

        // Draw everything
        function draw() {
            // Clear canvas with gradient background
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, '#87CEEB');
            gradient.addColorStop(1, '#98FB98');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Draw clouds
            drawClouds();
            
            platforms.forEach(platform => platform.draw());
            beans.forEach(bean => bean.draw());
            player.draw();
        }

        function drawClouds() {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            
            // Static clouds for background
            const cloudY = (gameScore / 20) % canvas.height;
            
            // Cloud 1
            ctx.beginPath();
            ctx.arc(50, cloudY, 20, 0, Math.PI * 2);
            ctx.arc(70, cloudY, 25, 0, Math.PI * 2);
            ctx.arc(90, cloudY, 20, 0, Math.PI * 2);
            ctx.fill();
            
            // Cloud 2
            ctx.beginPath();
            ctx.arc(canvas.width - 80, cloudY + 100, 18, 0, Math.PI * 2);
            ctx.arc(canvas.width - 65, cloudY + 100, 22, 0, Math.PI * 2);
            ctx.arc(canvas.width - 50, cloudY + 100, 18, 0, Math.PI * 2);
            ctx.fill();
        }

        function gameLoop() {
            update();
            draw();
            requestAnimationFrame(gameLoop);
        }

        // Event listeners
        window.addEventListener('keydown', (e) => {
            keys[e.key] = true;
            e.preventDefault();
        });

        window.addEventListener('keyup', (e) => {
            keys[e.key] = false;
        });

        canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const rect = canvas.getBoundingClientRect();
            touchStart = { 
                x: touch.clientX - rect.left, 
                y: touch.clientY - rect.top 
            };
        });

        canvas.addEventListener('touchend', (e) => {
            e.preventDefault();
            const touch = e.changedTouches[0];
            const rect = canvas.getBoundingClientRect();
            touchEnd = { 
                x: touch.clientX - rect.left, 
                y: touch.clientY - rect.top 
            };
        });

        canvas.addEventListener('click', (e) => {
            e.preventDefault();
            player.jump();
        });

        // Buttons
        restartButton.addEventListener('click', () => {
            endGameScreen.style.display = 'none';
            init();
        });

        mainMenuButton.addEventListener('click', () => {
            window.Telegram.WebApp.close();
        });

        // Utility functions
        function saveStats() {
            localStorage.setItem('perkyCoffeeStats', JSON.stringify(gameStats));
        }

        function loadStats() {
            const savedStats = localStorage.getItem('perkyCoffeeStats');
            if (savedStats) {
                const parsed = JSON.parse(savedStats);
                gameStats.highScore = parsed.highScore || 0;
                // Don't load totalBeans from localStorage as it's managed by server
            }
        }

        function showAchievementNotification(message) {
            achievementNotification.textContent = message;
            achievementNotification.style.opacity = 1;
            setTimeout(() => {
                achievementNotification.style.opacity = 0;
            }, 3000);
        }

        function vibrate(pattern) {
            if (vibrationEnabled && navigator.vibrate) {
                navigator.vibrate(pattern);
            }
        }

        /**
         * Збереження статистики гри на сервері
         */
        function saveGameStats(score, collected_beans) {
            if (!window.Telegram.WebApp.initDataUnsafe || !window.Telegram.WebApp.initDataUnsafe.user) {
                console.error('Telegram WebApp user data not available');
                return;
            }
            
            const user_id = window.Telegram.WebApp.initDataUnsafe.user.id;
            
            fetch('/save_stats', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: user_id,
                    score: Math.floor(score),
                    collected_beans: collected_beans
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Stats saved successfully:', data);
            })
            .catch(error => {
                console.error('Error saving stats:', error);
            });
        }

        // Resize handler
        window.addEventListener('resize', () => {
            resizeCanvas();
        });

        // Initialize and start game
        init();
        gameLoop();
    </script>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)

@app.post("/save_stats")
async def save_game_stats(stats: GameStats):
    """API endpoint для збереження статистики гри"""
    try:
        db.save_game_result(stats.user_id, stats.score, stats.collected_beans)
        return {"success": True, "message": "Stats saved successfully"}
    except Exception as e:
        logger.error(f"Error saving game stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to save stats")

@app.get("/stats/{user_id}")
async def get_user_stats(user_id: int):
    """API endpoint для отримання статистики користувача"""
    try:
        stats = db.get_user_stats(user_id)
        if stats:
            return stats
        else:
            return {"error": "User not found"}
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stats")

@app.get("/leaderboard")
async def get_leaderboard():
    """API endpoint для отримання таблиці лідерів"""
    try:
        leaderboard = db.get_leaderboard()
        return {"leaderboard": leaderboard}
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to get leaderboard")

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """Webhook для Telegram бота"""
    try:
        json_data = await request.json()
        update = Update.de_json(json_data, perky_bot.application.bot)
        await perky_bot.application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error"}

async def setup_bot():
    """Налаштування Telegram бота"""
    perky_bot.application = Application.builder().token(BOT_TOKEN).build()
    
    # Додати обробники
    perky_bot.application.add_handler(CommandHandler("start", perky_bot.start))
    perky_bot.application.add_handler(CallbackQueryHandler(perky_bot.button_callback))
    
    # Налаштувати webhook
    webhook_url = f"{WEBAPP_URL}/{BOT_TOKEN}"
    await perky_bot.application.bot.set_webhook(webhook_url)
    
    logger.info(f"Webhook set to: {webhook_url}")

@app.on_event("startup")
async def startup_event():
    """Подія запуску сервера"""
    logger.info("Starting Perky Coffee Jump Bot...")
    await setup_bot()
    logger.info("Bot setup completed!")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
