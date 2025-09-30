import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List

import sqlite3
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    WebAppInfo,
    LabeledPrice,
    KeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes, 
    MessageHandler, 
    filters,
    PreCheckoutQueryHandler
)
from telegram.constants import ParseMode
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
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
PAYMENT_TOKEN = os.getenv('PAYMENT_TOKEN')  # Telegram Payment Provider Token

# Конфігурація кав'ярні
CAFE_CONFIG = {
    "name": "Perky Coffee",
    "address": "вул. Сумська 12, Харків, Україна",
    "coordinates": {
        "latitude": 49.9935,
        "longitude": 36.2304
    },
    "phone": "+380123456789",
    "working_hours": "Пн-Нд: 08:00 - 22:00",
    "menu_url": "https://your-menu-link.com",  # Замініть на реальне посилання
    "instagram": "https://instagram.com/perkycoffee",
    "website": "https://perkycoffee.ua"
}

# Каталог товарів магазину
SHOP_ITEMS = {
    "merch": [
        {
            "id": "tshirt_black",
            "name": "🎽 Футболка Perky (чорна)",
            "description": "Якісна бавовняна футболка з логотипом Perky Coffee",
            "price": 45000,  # в копійках (450 грн)
            "currency": "UAH",
            "image_url": "https://via.placeholder.com/300x300.png?text=Perky+T-Shirt"
        },
        {
            "id": "mug",
            "name": "☕ Фірмова чашка",
            "description": "Керамічна чашка 350мл з роботом Perky",
            "price": 25000,
            "currency": "UAH",
            "image_url": "https://via.placeholder.com/300x300.png?text=Perky+Mug"
        },
        {
            "id": "hoodie",
            "name": "👕 Худі Perky",
            "description": "Тепле худі з капюшоном та кишенею-кенгуру",
            "price": 95000,
            "currency": "UAH",
            "image_url": "https://via.placeholder.com/300x300.png?text=Perky+Hoodie"
        },
        {
            "id": "cap",
            "name": "🧢 Кепка Perky",
            "description": "Стильна кепка з вишивкою",
            "price": 35000,
            "currency": "UAH",
            "image_url": "https://via.placeholder.com/300x300.png?text=Perky+Cap"
        },
        {
            "id": "stickers",
            "name": "🎨 Набір стікерів",
            "description": "10 крутих стікерів з роботом Perky",
            "price": 8000,
            "currency": "UAH",
            "image_url": "https://via.placeholder.com/300x300.png?text=Stickers"
        }
    ],
    "coffee": [
        {
            "id": "beans_250",
            "name": "☕ Кавові зерна 250г",
            "description": "Фірмова суміш Perky Blend - 100% арабіка",
            "price": 18000,
            "currency": "UAH",
            "image_url": "https://via.placeholder.com/300x300.png?text=Coffee+Beans"
        },
        {
            "id": "beans_1kg",
            "name": "☕ Кавові зерна 1кг",
            "description": "Економна упаковка фірмової суміші",
            "price": 65000,
            "currency": "UAH",
            "image_url": "https://via.placeholder.com/300x300.png?text=Coffee+1kg"
        },
        {
            "id": "subscription",
            "name": "📦 Кавова підписка (місяць)",
            "description": "Щотижнева доставка свіжообсмаженої кави",
            "price": 60000,
            "currency": "UAH",
            "image_url": "https://via.placeholder.com/300x300.png?text=Subscription"
        }
    ],
    "vouchers": [
        {
            "id": "voucher_100",
            "name": "🎁 Подарунковий сертифікат 100 грн",
            "description": "Електронний сертифікат на покупки в Perky Coffee",
            "price": 10000,
            "currency": "UAH",
            "image_url": "https://via.placeholder.com/300x300.png?text=Voucher+100"
        },
        {
            "id": "voucher_500",
            "name": "🎁 Подарунковий сертифікат 500 грн",
            "description": "Електронний сертифікат на покупки в Perky Coffee",
            "price": 50000,
            "currency": "UAH",
            "image_url": "https://via.placeholder.com/300x300.png?text=Voucher+500"
        }
    ]
}

if not BOT_TOKEN:
    logger.error("BOT_TOKEN is not set!")
    exit(1)
if not WEBAPP_URL:
    logger.error("WEBAPP_URL is not set!")
    exit(1)

# FastAPI додаток
app = FastAPI(title="Perky Coffee Jump WebApp")

# Pydantic моделі
class GameStats(BaseModel):
    user_id: int
    score: int
    height: int
    collected_beans: int
    mode: str
    achievements: Optional[str] = None

class UserProgress(BaseModel):
    user_id: int
    level: int
    experience: int
    coins: int
    powerups: str
    character: str

# База даних
def get_db_connection():
    conn = sqlite3.connect('perky_game.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Таблиця статистики гри
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_stats (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                best_height INTEGER DEFAULT 0,
                best_coffee INTEGER DEFAULT 0,
                total_coffee INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                achievements TEXT DEFAULT '{}'
            )
        """)
        
        # Таблиця прогресу користувача
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER PRIMARY KEY,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                powerups TEXT DEFAULT '{}',
                character TEXT DEFAULT '{"skin":"default","jumpEffect":"default"}',
                friends TEXT DEFAULT '[]',
                last_daily_reward DATE
            )
        """)
        
        # Таблиця замовлень
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                item_id TEXT,
                item_name TEXT,
                amount INTEGER,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                telegram_payment_id TEXT
            )
        """)
        
        conn.commit()
    logger.info("Database initialized.")

# Глобальний клас бота
class PerkyBot:
    def __init__(self):
        self.application: Optional[Application] = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Головне меню бота"""
        user = update.effective_user
        
        # Реєструємо користувача
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO game_stats 
                (user_id, username, best_height, best_coffee, total_coffee, games_played) 
                VALUES (?, ?, 0, 0, 0, 0)
            """, (user.id, user.username or user.first_name))
            
            cursor.execute("""
                INSERT OR IGNORE INTO user_progress 
                (user_id) VALUES (?)
            """, (user.id,))
            
            conn.commit()

        welcome_message = (
            f"🤖☕ *Вітаю в Perky Coffee Jump!*\n\n"
            f"Привіт, {user.first_name}! Я твій помічник у світі кави та ігор!\n\n"
            f"*Що я вмію:*\n"
            f"🎮 Запускати гру Perky Coffee Jump\n"
            f"🛍️ Показувати магазин мерчу та кави\n"
            f"📍 Допомагати знайти нашу кав'ярню\n"
            f"📊 Відстежувати твою статистику\n"
            f"🎁 Давати бонуси та знижки\n\n"
            f"Обирай дію в меню нижче! 👇"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎮 Грати", web_app=WebAppInfo(url=WEBAPP_URL))],
            [
                InlineKeyboardButton("🛍️ Магазин", callback_data='shop_main'),
                InlineKeyboardButton("📋 Меню кав'ярні", url=CAFE_CONFIG["menu_url"])
            ],
            [
                InlineKeyboardButton("📍 Як нас знайти", callback_data='location'),
                InlineKeyboardButton("📊 Моя статистика", callback_data='stats')
            ],
            [
                InlineKeyboardButton("🏆 Рейтинг", callback_data='leaderboard'),
                InlineKeyboardButton("🎁 Бонуси", callback_data='bonuses')
            ],
            [InlineKeyboardButton("ℹ️ Про нас", callback_data='about')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                welcome_message, 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.callback_query.message.edit_text(
                welcome_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник кнопок"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        # Роутинг по callback_data
        if data == 'back_main':
            await self.start(update, context)
        elif data == 'stats':
            await self.show_stats(query, context)
        elif data == 'leaderboard':
            await self.show_leaderboard(query, context)
        elif data == 'bonuses':
            await self.show_bonuses(query, context)
        elif data == 'location':
            await self.show_location(query, context)
        elif data == 'about':
            await self.show_about(query, context)
        elif data == 'shop_main':
            await self.show_shop_menu(query, context)
        elif data.startswith('shop_category_'):
            category = data.replace('shop_category_', '')
            await self.show_shop_category(query, context, category)
        elif data.startswith('buy_'):
            item_id = data.replace('buy_', '')
            await self.initiate_purchase(query, context, item_id)

    async def show_stats(self, query, context):
        """Показати статистику користувача"""
        user_id = query.from_user.id
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gs.*, up.level, up.experience, up.coins 
                FROM game_stats gs
                LEFT JOIN user_progress up ON gs.user_id = up.user_id
                WHERE gs.user_id = ?
            """, (user_id,))
            stats = cursor.fetchone()
        
        if not stats:
            await query.message.edit_text("Статистика не знайдена. Спочатку зіграйте в гру!")
            return
        
        message = (
            f"📊 *Твоя статистика*\n\n"
            f"⚡ Рівень: *{stats['level']}*\n"
            f"💫 Досвід: *{stats['experience']}* XP\n"
            f"🪙 Монет: *{stats['coins']}*\n\n"
            f"🎮 *Ігрові досягнення:*\n"
            f"🏆 Рекорд висоти: *{stats['best_height']}м*\n"
            f"☕ Найбільше зерен: *{stats['best_coffee']}*\n"
            f"📦 Всього зібрано: *{stats['total_coffee']}* зерен\n"
            f"🕹️ Ігор зіграно: *{stats['games_played']}*\n\n"
            f"Продовжуй грати, щоб покращити результати! 🚀"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_main')]]
        
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def show_leaderboard(self, query, context):
        """Таблиця лідерів"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, best_height, best_coffee 
                FROM game_stats 
                ORDER BY best_height DESC 
                LIMIT 10
            """)
            leaders = cursor.fetchall()
        
        message = "🏆 *Топ-10 гравців*\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        for i, leader in enumerate(leaders):
            medal = medals[i] if i < 3 else f"{i+1}."
            message += f"{medal} *{leader['username']}*\n"
            message += f"   📏 {leader['best_height']}м  |  ☕ {leader['best_coffee']} зерен\n\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_main')]]
        
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def show_bonuses(self, query, context):
        """Показати бонуси та знижки"""
        user_id = query.from_user.id
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT total_coffee, last_daily_reward 
                FROM user_progress up
                JOIN game_stats gs ON up.user_id = gs.user_id
                WHERE up.user_id = ?
            """, (user_id,))
            user_data = cursor.fetchone()
        
        total_beans = user_data['total_coffee'] if user_data else 0
        
        # Визначаємо доступні бонуси
        bonuses = []
        if total_beans >= 50:
            bonuses.append("✅ *2% знижка* на всі напої")
        if total_beans >= 100:
            bonuses.append("✅ *5% знижка* на всі напої")
        if total_beans >= 500:
            bonuses.append("✅ *Безкоштовна чашка* при покупці кави")
        if total_beans >= 1000:
            bonuses.append("✅ *10% знижка* на весь асортимент")
        
        message = (
            f"🎁 *Система бонусів*\n\n"
            f"☕ Зібрано зерен: *{total_beans}*\n\n"
        )
        
        if bonuses:
            message += "*Твої активні бонуси:*\n" + "\n".join(bonuses) + "\n\n"
        else:
            message += "Поки що немає активних бонусів.\nГрай і збирай зерна! 🎮\n\n"
        
        message += (
            "*Як отримати бонуси:*\n"
            "• 50 зерен → 2% знижка\n"
            "• 100 зерен → 5% знижка\n"
            "• 500 зерен → безкоштовна чашка\n"
            "• 1000 зерен → 10% знижка\n\n"
            "Покажи це повідомлення бариста для активації! 📱"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_main')]]
        
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def show_location(self, query, context):
        """Показати локацію кав'ярні"""
        message = (
            f"📍 *{CAFE_CONFIG['name']}*\n\n"
            f"📫 Адреса: {CAFE_CONFIG['address']}\n"
            f"📞 Телефон: {CAFE_CONFIG['phone']}\n"
            f"🕐 Години роботи: {CAFE_CONFIG['working_hours']}\n\n"
            f"🌐 [Наш сайт]({CAFE_CONFIG['website']})\n"
            f"📸 [Instagram]({CAFE_CONFIG['instagram']})\n\n"
            f"Надішлю локацію на карті нижче! 📍"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_main')]]
        
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        
        # Надсилаємо локацію
        await context.bot.send_location(
            chat_id=query.message.chat_id,
            latitude=CAFE_CONFIG['coordinates']['latitude'],
            longitude=CAFE_CONFIG['coordinates']['longitude']
        )

    async def show_about(self, query, context):
        """Про Perky Coffee"""
        message = (
            f"☕ *Про Perky Coffee*\n\n"
            f"Ми - команда кавоманів, яка поєднує любов до якісної кави "
            f"з інноваційними технологіями! 🚀\n\n"
            f"*Наша місія:*\n"
            f"Зробити кожну чашку кави особливою, а кожен візит - "
            f"незабутньою пригодою! 🎮☕\n\n"
            f"*Що ми пропонуємо:*\n"
            f"• Свіжообсмажена кава\n"
            f"• Унікальні напої від барист\n"
            f"• Затишна атмосфера\n"
            f"• Ігрова зона та еспорт\n"
            f"• Крутий мерч\n\n"
            f"Приходь і переконайся сам! 😊"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_main')]]
        
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def show_shop_menu(self, query, context):
        """Головне меню магазину"""
        message = (
            f"🛍️ *Інтернет-магазин Perky Coffee*\n\n"
            f"Обирай категорію товарів:\n\n"
            f"👕 Мерч - футболки, худі, кепки\n"
            f"☕ Кава - зерна та підписки\n"
            f"🎁 Сертифікати - подарунки для друзів"
        )
        
        keyboard = [
            [InlineKeyboardButton("👕 Мерч", callback_data='shop_category_merch')],
            [InlineKeyboardButton("☕ Кава", callback_data='shop_category_coffee')],
            [InlineKeyboardButton("🎁 Сертифікати", callback_data='shop_category_vouchers')],
            [InlineKeyboardButton("◀️ Назад", callback_data='back_main')]
        ]
        
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def show_shop_category(self, query, context, category: str):
        """Показати товари категорії"""
        items = SHOP_ITEMS.get(category, [])
        
        category_names = {
            'merch': '👕 Мерч',
            'coffee': '☕ Кава',
            'vouchers': '🎁 Сертифікати'
        }
        
        for item in items:
            price_uah = item['price'] / 100
            message = (
                f"*{item['name']}*\n\n"
                f"{item['description']}\n\n"
                f"💰 Ціна: *{price_uah:.0f} грн*"
            )
            
            keyboard = [
                [InlineKeyboardButton("🛒 Купити", callback_data=f"buy_{item['id']}")],
                [InlineKeyboardButton("◀️ Назад до категорій", callback_data='shop_main')]
            ]
            
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=item['image_url'],
                caption=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )

    async def initiate_purchase(self, query, context, item_id: str):
        """Почати процес оплати"""
        # Знаходимо товар
        item = None
        for category in SHOP_ITEMS.values():
            for product in category:
                if product['id'] == item_id:
                    item = product
                    break
        
        if not item:
            await query.answer("Товар не знайдено!", show_alert=True)
            return
        
        if not PAYMENT_TOKEN:
            await query.answer(
                "⚠️ Оплата тимчасово недоступна. "
                "Зв'яжіться з нами для оформлення замовлення!",
                show_alert=True
            )
            return
        
        # Створюємо інвойс
        title = item['name']
        description = item['description']
        payload = f"order_{item_id}_{query.from_user.id}"
        currency = item['currency']
        prices = [LabeledPrice(label=item['name'], amount=item['price'])]
        
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=PAYMENT_TOKEN,
            currency=currency,
            prices=prices,
            photo_url=item['image_url'],
            need_name=True,
            need_phone_number=True,
            need_shipping_address=True
        )

    async def precheckout_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Підтвердження перед оплатою"""
        query = update.pre_checkout_query
        await query.answer(ok=True)

    async def successful_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Успішна оплата"""
        payment = update.message.successful_payment
        user = update.effective_user
        
        # Зберігаємо замовлення
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders 
                (user_id, username, item_id, item_name, amount, status, telegram_payment_id)
                VALUES (?, ?, ?, ?, ?, 'paid', ?)
            """, (
                user.id,
                user.username or user.first_name,
                payment.invoice_payload.split('_')[1],
                payment.invoice_payload,
                payment.total_amount,
                payment.telegram_payment_charge_id
            ))
            conn.commit()
        
        message = (
            f"✅ *Оплата успішна!*\n\n"
            f"Дякуємо за покупку! Ми зв'яжемося з вами найближчим часом "
            f"для уточнення деталей доставки.\n\n"
            f"Номер замовлення: `{payment.telegram_payment_charge_id}`\n\n"
            f"З питань звертайтеся: {CAFE_CONFIG['phone']}"
        )
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        
        # Нараховуємо бонусні монети
        bonus_coins = payment.total_amount // 10000  # 1 монета за кожні 100 грн
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_progress 
                SET coins = coins + ?
                WHERE user_id = ?
            """, (bonus_coins, user.id))
            conn.commit()

# Ініціалізація бота
perky_bot = PerkyBot()

# FastAPI endpoints
app.mount("/game", StaticFiles(directory="static", html=True), name="static")

@app.post("/save_game_stats")
async def save_game_stats(stats: GameStats):
    """Зберегти статистику гри"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Оновлюємо game_stats
            cursor.execute("""
                INSERT INTO game_stats (user_id, best_height, best_coffee, total_coffee, games_played)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    best_height = MAX(best_height, ?),
                    best_coffee = MAX(best_coffee, ?),
                    total_coffee = total_coffee + ?,
                    games_played = games_played + 1
            """, (stats.user_id, stats.height, stats.collected_beans, 
                  stats.collected_beans, stats.height, stats.collected_beans, 
                  stats.collected_beans))
            
            conn.commit()
            
        return {"status": "success", "message": "Stats saved"}
    except Exception as e:
        logger.error(f"Error saving game stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save_progress")
async def save_user_progress(progress: UserProgress):
    """Зберегти прогрес користувача"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_progress (user_id, level, experience, coins, powerups, character)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    level = ?,
                    experience = ?,
                    coins = ?,
                    powerups = ?,
                    character = ?
            """, (progress.user_id, progress.level, progress.experience, 
                  progress.coins, progress.powerups, progress.character,
                  progress.level, progress.experience, progress.coins,
                  progress.powerups, progress.character))
            conn.commit()
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_progress/{user_id}")
async def get_user_progress(user_id: int):
    """Отримати прогрес користувача"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM user_progress WHERE user_id = ?
            """, (user_id,))
            progress = cursor.fetchone()
            
            if progress:
                return dict(progress)
            else:
                return {
                    "level": 1,
                    "experience": 0,
                    "coins": 0,
                    "powerups": "{}",
                    "character": '{"skin":"default","jumpEffect":"default"}'
                }
    except Exception as e:
        logger.error(f"Error getting progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """Telegram webhook"""
    try:
        if not perky_bot.application:
            return {"status": "bot not ready"}, 503
        
        json_data = await request.json()
        update = Update.de_json(json_data, perky_bot.application.bot)
        
        async with perky_bot.application:
            await perky_bot.application.process_update(update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

async def setup_bot():
    """Налаштування бота"""
    try:
        perky_bot.application = Application.builder().token(BOT_TOKEN).build()
        
        # Хендлери
        perky_bot.application.add_handler(CommandHandler("start", perky_bot.start))
        perky_bot.application.add_handler(CallbackQueryHandler(perky_bot.button_callback))
        perky_bot.application.add_handler(PreCheckoutQueryHandler(perky_bot.precheckout_callback))
        perky_bot.application.add_handler(
            MessageHandler(filters.SUCCESSFUL_PAYMENT, perky_bot.successful_payment_callback)
        )
        
        # Встановлюємо webhook
        webhook_url = f"{WEBAPP_URL.replace('/game', '')}/{BOT_TOKEN}"
        await perky_bot.application.bot.set_webhook(webhook_url)
        
        logger.info(f"Bot ready! Webhook: {webhook_url}")
    except Exception as e:
        logger.error(f"Bot setup error: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Запуск"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Starting bot...")
    await setup_bot()
    logger.info("Ready!")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
