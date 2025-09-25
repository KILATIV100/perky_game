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
app.mount("/static", StaticFiles(directory="static"), name="static")


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
                INSERT OR IGNORE INTO users (user_id, username, first_name, max_height, total_beans, games_played)
                VALUES (?, ?, ?, 0, 0, 0)
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
    }
}

# Telegram Bot функції
class PerkyCoffeeBot:
    def __init__(self):
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка команди /start"""
        user = update.effective_user
        
        db.save_user(user.id, user.username, user.first_name)
        
        welcome_message = f"Привіт, {user.first_name}! 👋\n\nЛаскаво просимо до 🤖☕ **Perky Coffee Jump**!\n\nСтрибай, збирай зерна та став рекорди!"
        
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/static/index.html"))],
            [InlineKeyboardButton("📊 Статистика", callback_data='stats'), InlineKeyboardButton("🏆 Лідери", callback_data='leaderboard')],
            [InlineKeyboardButton("🛒 Магазин", callback_data='shop'), InlineKeyboardButton("❓ Допомога", callback_data='help')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка натискань кнопок"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'stats':
            await self.show_stats(query)
        elif query.data == 'leaderboard':
            await self.show_leaderboard(query)
        elif query.data == 'shop':
            await self.show_shop(query)
        elif query.data == 'help':
            await self.show_help(query)
        elif query.data == 'back_main':
            await self.back_to_main(query)
        elif query.data.startswith('buy_'):
            item_id = query.data.replace('buy_', '')
            await self.buy_item(query, item_id)
    
    async def show_stats(self, query):
        user_id = query.from_user.id
        stats = db.get_user_stats(user_id)
        
        if not stats or stats['games_played'] == 0:
            stats_text = "📊 **Твоя статистика**\n\nТи ще не грав. Час почати! 🚀"
        else:
            last_played = datetime.fromisoformat(stats['last_played']).strftime("%d.%m.%Y %H:%M") if stats['last_played'] else 'Ніколи'
            stats_text = (
                f"📊 **Твоя статистика**\n\n"
                f"🎮 Ігор зіграно: *{stats['games_played']}*\n"
                f"🏔️ Рекорд висоти: *{stats['max_height']} м*\n"
                f"☕ Усього зерен: *{stats['total_beans']}*\n"
                f"📅 Остання гра: *{last_played}*"
            )
        
        await query.edit_message_text(stats_text, reply_markup=self.get_back_keyboard('back_main'), parse_mode=ParseMode.MARKDOWN)

    async def show_leaderboard(self, query):
        leaderboard = db.get_leaderboard(10)
        leaderboard_text = "🏆 **Таблиця лідерів**\n\n"
        if not leaderboard:
            leaderboard_text += "Поки що немає рекордів. Стань першим!"
        else:
            for i, (username, first_name, max_height, total_beans) in enumerate(leaderboard, 1):
                name = first_name or username or "Гравець"
                emoji = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
                leaderboard_text += f"{emoji} *{name}* - {max_height} м\n"
        
        await query.edit_message_text(leaderboard_text, reply_markup=self.get_back_keyboard('back_main'), parse_mode=ParseMode.MARKDOWN)

    async def show_shop(self, query):
        shop_text = "🛒 **Магазин Perky Coffee**\n\nКупуй ексклюзивний мерч та підтримай розробку гри!"
        keyboard = [
            [InlineKeyboardButton(f"{item['name']} - {item['price']//100} грн", callback_data=f'buy_{item_id}')]
            for item_id, item in SHOP_ITEMS.items()
        ]
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data='back_main')])
        await query.edit_message_text(shop_text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def buy_item(self, query, item_id: str):
        item = SHOP_ITEMS.get(item_id)
        if not item:
            await query.answer("Товар не знайдено!", show_alert=True)
            return
            
        await query.edit_message_text(
            f"Ви обрали: *{item['name']}*\n\n{item['description']}\n\nЦіна: *{item['price']//100} грн*\n\n_(Функція оплати у розробці)_",
            reply_markup=self.get_back_keyboard('shop'),
            parse_mode=ParseMode.MARKDOWN
        )

    async def show_help(self, query):
        help_text = (
            "❓ **Допомога по грі**\n\n"
            "🎮 *Керування:*\nНатискай на екран або використовуй стрілки для переміщення.\n\n"
            "🎯 *Мета:*\nСтрибай якомога вище, збирай кавові зерна ☕ і не падай!\n\n"
            "Успіхів! 🚀"
        )
        await query.edit_message_text(help_text, reply_markup=self.get_back_keyboard('back_main'), parse_mode=ParseMode.MARKDOWN)

    async def back_to_main(self, query):
        user = query.from_user
        welcome_message = f"Привіт, {user.first_name}! 👋\n\nГотовий до нових рекордів у **Perky Coffee Jump**? 🤖☕"
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/static/index.html"))],
            [InlineKeyboardButton("📊 Статистика", callback_data='stats'), InlineKeyboardButton("🏆 Лідери", callback_data='leaderboard')],
            [InlineKeyboardButton("🛒 Магазин", callback_data='shop'), InlineKeyboardButton("❓ Допомога", callback_data='help')]
        ]
        await query.edit_message_text(welcome_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    def get_back_keyboard(self, callback_data: str):
        return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Назад", callback_data=callback_data)]])

perky_bot = PerkyCoffeeBot()

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<html><body><h1>Perky Coffee Jump Bot is running!</h1></body></html>"

@app.post("/save_stats")
async def save_game_stats_endpoint(stats: GameStats):
    try:
        db.save_game_result(stats.user_id, stats.score, stats.collected_beans)
        return {"success": True, "message": "Stats saved successfully"}
    except Exception as e:
        logger.error(f"Error saving game stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to save stats")

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, perky_bot.application.bot)
    await perky_bot.application.process_update(update)
    return {"status": "ok"}

async def setup_bot():
    perky_bot.application = Application.builder().token(BOT_TOKEN).build()
    perky_bot.application.add_handler(CommandHandler("start", perky_bot.start))
    perky_bot.application.add_handler(CallbackQueryHandler(perky_bot.button_callback))
    webhook_url = f"{WEBAPP_URL}/{BOT_TOKEN}"
    await perky_bot.application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

@app.on_event("startup")
async def startup_event():
    await setup_bot()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
