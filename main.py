import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional

import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
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

if not BOT_TOKEN:
    logger.error("BOT_TOKEN is not set!")
    exit(1)
if not WEBAPP_URL:
    logger.error("WEBAPP_URL is not set!")
    exit(1)

# FastAPI додаток
app = FastAPI(title="Perky Coffee Jump WebApp")

# Pydantic моделі для API
class GameStats(BaseModel):
    user_id: int
    score: int
    collected_beans: int
    achievements: Optional[str] = None

# База даних
def get_db_connection():
    conn = sqlite3.connect('perky_game.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                high_score INTEGER NOT NULL,
                total_beans INTEGER NOT NULL,
                games_played INTEGER NOT NULL,
                achievements TEXT
            )
        """)
        conn.commit()
    logger.info("Database initialized.")

# Глобальний клас для зберігання стану бота
class PerkyBot:
    def __init__(self):
        self.application: Optional[Application] = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /start"""
        user = update.effective_user
        welcome_message = (
            f"Привіт, {user.full_name}! 👋\n\n"
            "Я - **Perky Coffee Jump Bot**! 🤖☕\n\n"
            "Моя мета - допомогти тобі стрибати, збирати кавові зерна та бити рекорди!\n"
            "Готовий до гри? Просто натисни на кнопку нижче! 👇"
        )
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=WEBAPP_URL))],
            [
                InlineKeyboardButton("📊 Статистика", callback_data='stats'),
                InlineKeyboardButton("🏆 Таблиця лідерів", callback_data='leaderboard')
            ],
            [
                InlineKeyboardButton("🛒 Магазин", callback_data='shop'),
                InlineKeyboardButton("❓ Допомога", callback_data='help')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO stats (user_id, username, high_score, total_beans, games_played, achievements) VALUES (?, ?, 0, 0, 0, '{}')", (user.id, user.username))
            conn.commit()

        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"User {user.id} started the bot.")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник натискання кнопок"""
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()

        if query.data == 'stats':
            await self.show_stats(user_id, context)
        elif query.data == 'leaderboard':
            await self.show_leaderboard(context)
        elif query.data == 'shop':
            await self.show_shop(context)
        elif query.data == 'help':
            await self.show_help(context)

    async def show_stats(self, user_id, context):
        """Показує статистику користувача"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stats WHERE user_id = ?", (user_id,))
            user_stats = cursor.fetchone()

        if not user_stats:
            await context.bot.send_message(user_id, "Ваша статистика ще не була збережена. Спробуйте зіграти в гру!")
            return

        message = (
            f"📊 **Ваша статистика:**\n"
            f"🏆 Рекорд: **{user_stats['high_score']}** очок\n"
            f"☕ Зібрано зерен: **{user_stats['total_beans']}**\n"
            f"🕹️ Зіграно ігор: **{user_stats['games_played']}**\n"
        )
        await context.bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)

    async def show_leaderboard(self, context):
        """Показує таблицю лідерів"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, high_score FROM stats ORDER BY high_score DESC LIMIT 10")
            leaderboard_data = cursor.fetchall()
        
        message = "🏆 **Таблиця лідерів:**\n\n"
        for i, row in enumerate(leaderboard_data):
            message += f"**{i+1}.** {row['username']} - **{row['high_score']}** очок\n"
        
        await context.bot.send_message(context.effective_user.id, message, parse_mode=ParseMode.MARKDOWN)

    async def show_shop(self, context):
        """Показує магазин мерчу"""
        message = "🛒 **Магазин мерчу:**\n\n" \
                  "Тут ви можете придбати крутий мерч з Perky Coffee Jump!\n" \
                  "**(Функціонал у розробці)**"
        await context.bot.send_message(context.effective_user.id, message, parse_mode=ParseMode.MARKDOWN)

    async def show_help(self, context):
        """Показує інструкції з гри"""
        message = "❓ **Допомога:**\n\n" \
                  "У грі Perky Coffee Jump ваша мета - керувати кавовим роботом, щоб стрибати по платформах і збирати кавові зерна. Чим більше зерен - тим вищий ваш рахунок! Уникайте падіння!\n\n" \
                  "**Управління:**\n" \
                  "Натискайте на екран, щоб стрибати.\n\n" \
                  "**Підказка:** Чим довше утримуєте палець, тим вищий стрибок!"
        await context.bot.send_message(context.effective_user.id, message, parse_mode=ParseMode.MARKDOWN)

# Ініціалізація класу бота
perky_bot = PerkyBot()

# API endpoints
@app.get("/game", response_class=HTMLResponse)
async def get_game():
    """Подає HTML-файл гри"""
    try:
        with open("game.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Game file not found")

@app.post("/save_stats")
async def save_stats_endpoint(stats: GameStats):
    """Збереження статистики гри"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT high_score, total_beans, games_played FROM stats WHERE user_id = ?", (stats.user_id,))
            current_stats = cursor.fetchone()
            
            if current_stats:
                new_high_score = max(current_stats['high_score'], stats.score)
                new_total_beans = current_stats['total_beans'] + stats.collected_beans
                new_games_played = current_stats['games_played'] + 1
                
                cursor.execute("""
                    UPDATE stats
                    SET high_score = ?, total_beans = ?, games_played = ?
                    WHERE user_id = ?
                """, (new_high_score, new_total_beans, new_games_played, stats.user_id))
            else:
                cursor.execute("""
                    INSERT INTO stats (user_id, high_score, total_beans, games_played, achievements)
                    VALUES (?, ?, ?, ?, '{}')
                """, (stats.user_id, stats.score, stats.collected_beans, 1))

            conn.commit()
            logger.info(f"Stats saved for user {stats.user_id}: score={stats.score}, beans={stats.collected_beans}")
            return {"message": "Stats saved successfully"}
    except Exception as e:
        logger.error(f"Error saving stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to save stats")

@app.get("/stats/{user_id}")
async def get_user_stats(user_id: int):
    """Отримання статистики користувача"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT high_score, total_beans, games_played FROM stats WHERE user_id = ?", (user_id,))
            user_stats = cursor.fetchone()
            if user_stats:
                return dict(user_stats)
            else:
                raise HTTPException(status_code=404, detail="User stats not found")
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user stats")

@app.get("/leaderboard")
async def get_leaderboard_endpoint():
    """Отримання таблиці лідерів"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, high_score FROM stats ORDER BY high_score DESC LIMIT 10")
            leaderboard = [dict(row) for row in cursor.fetchall()]
        return {"leaderboard": leaderboard}
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to get leaderboard")

# Змінений вебхук-ендпоінт для коректної роботи з Application
@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """Webhook для Telegram бота"""
    try:
        # Важливо: перевірка, чи Application вже ініціалізовано
        if not perky_bot.application:
            logger.warning("Webhook received, but bot not initialized yet. Returning 503.")
            return {"status": "bot not initialized yet"}, 503
        
        json_data = await request.json()
        update = Update.de_json(json_data, perky_bot.application.bot)
        
        # Обробка оновлення через Application
        async with perky_bot.application:
            await perky_bot.application.process_update(update)

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error"}

async def setup_bot():
    """Налаштування Telegram бота"""
    try:
        perky_bot.application = Application.builder().token(BOT_TOKEN).build()
        
        # Додати обробники
        perky_bot.application.add_handler(CommandHandler("start", perky_bot.start))
        perky_bot.application.add_handler(CallbackQueryHandler(perky_bot.button_callback))
        perky_bot.application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, perky_bot.web_app_data))
        
        # Налаштувати webhook
        webhook_url = f"{WEBAPP_URL}/{BOT_TOKEN}"
        await perky_bot.application.bot.set_webhook(webhook_url)
        
        logger.info(f"Webhook set to: {webhook_url}")
    except Exception as e:
        logger.error(f"Error during bot setup: {e}")
        raise

# Додаємо обробку даних з WebApp
async def web_app_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка даних, надісланих з WebApp"""
    data = json.loads(update.effective_message.web_app_data.data)
    user_id = update.effective_user.id
    score = data.get('score', 0)
    
    # Збереження даних у базу
    # У цьому прикладі я використаю твій ендпоінт,
    # але можна було б зберегти напряму в БД
    stats = GameStats(user_id=user_id, score=score, collected_beans=0)
    await save_stats_endpoint(stats)
    
    message = f"🎉 Гра завершена! Ваш рахунок: **{score}** очок."
    await context.bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Received game data from user {user_id}: score={score}")

# Додаємо цей метод до класу PerkyBot
PerkyBot.web_app_data = web_app_data

# Запуск бота і вебхука під час старту FastAPI
@app.on_event("startup")
async def startup_event():
    """Виконується при запуску FastAPI"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Starting Perky Coffee Jump Bot...")
    await setup_bot()
    logger.info("Bot setup completed!")
    
# Запуск FastAPI сервера (для локального тестування)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
