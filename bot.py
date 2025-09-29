import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import RetryAfter

# Імпортуємо конфігурацію та базу даних
from config import BOT_TOKEN, WEBAPP_URL, WEBHOOK_URL # ОНОВЛЕНО: Додано WEBHOOK_URL
from database import db

# Налаштування логера
logger = logging.getLogger(__name__)

class PerkyCoffeeBot:
    """
    Клас, що інкапсулює всю логіку Telegram-бота.
    """
    def __init__(self):
        self.application = None
        # ВИПРАВЛЕНО: Використовуємо коректний WEBHOOK_URL
        self.webhook_url = WEBHOOK_URL 

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка команди /start."""
        user = update.effective_user
        db.save_user(user.id, user.username, user.first_name)
        
        welcome_message = (
            f"Привіт, {user.first_name}! 👋\n\n"
            "Я - <b>Perky Coffee Jump Bot</b>! 🤖☕\n\n"
            "Готовий до гри? Просто натисни на кнопку нижче! 👇"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/game"))],
            [
                InlineKeyboardButton("📊 Статистика", callback_data='stats'),
                InlineKeyboardButton("🏆 Рейтинг", callback_data='leaderboard')
            ],
            [
                InlineKeyboardButton("🛒 Магазин", callback_data='shop'),
                InlineKeyboardButton("❓ Допомога", callback_data='help')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_html(welcome_message, reply_markup=reply_markup)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка натискань на кнопки."""
        query = update.callback_query
        await query.answer()

        action = query.data
        if action == 'stats':
            await self.show_stats(query)
        elif action == 'leaderboard':
            await self.show_leaderboard(query)
        elif action == 'shop':
            await self.show_shop(query)
        elif action == 'help':
            await self.show_help(query)
        elif action == 'back_main':
            await self.back_to_main(query)

    async def show_stats(self, query: Update):
        """Показує статистику користувача."""
        user_id = query.from_user.id
        stats = db.get_user_stats(user_id)
        
        if not stats or stats['games_played'] == 0:
            stats_text = "📊 <b>Ваша статистика:</b>\n\nВи ще не зіграли жодної гри. Час почати!"
        else:
            stats_text = (
                f"📊 <b>Ваша статистика:</b>\n\n"
                f"🏆 <b>Рекорд висоти:</b> {stats['max_height']} м\n"
                f"☕ <b>Всього зерен:</b> {stats['total_beans']}\n"
                f"🕹️ <b>Зіграно ігор:</b> {stats['games_played']} \n"
                f"🤖 <b>Активний скін:</b> {stats.get('active_skin', 'default')}"
            )

        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(stats_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def show_leaderboard(self, query: Update):
        """Показує таблицю лідерів."""
        leaderboard = db.get_leaderboard()
        
        if not leaderboard:
            leaderboard_text = "🏆 <b>Таблиця лідерів:</b>\n\nПоки що порожньо. Станьте першим!"
        else:
            leaderboard_text = "🏆 <b>Топ-10 гравців:</b>\n\n"
            emojis = ["🥇", "🥈", "🥉"]
            for i, user in enumerate(leaderboard):
                name = user.get('username') or user.get('first_name') or "Гравець"
                max_height = user.get('max_height', 0)
                emoji = emojis[i] if i < 3 else f"<b>{i+1}.</b>"
                leaderboard_text += f"{emoji} {name} - {max_height} м\n"

        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(leaderboard_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        
    async def show_shop(self, query: Update):
        """Показує магазин."""
        shop_text = "🛒 <b>Магазин мерчу:</b>\n\nТут ви можете придбати нові скіни за зібрані кавові зерна!"
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(shop_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def show_help(self, query: Update):
        """Показує допомогу."""
        help_text = (
            "❓ <b>Допомога:</b>\n\n"
            "Керуйте кавовим роботом, стрибайте по платформах і збирайте кавові зерна. "
            "Чим вище ви стрибнете, тим кращим буде ваш рекорд!"
        )
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(help_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def back_to_main(self, query: Update):
        """Повертає користувача в головне меню."""
        user = query.from_user
        welcome_message = (
            f"Привіт, {user.first_name}! 👋\n\n"
            "Я - <b>Perky Coffee Jump Bot</b>! 🤖☕\n\n"
            "Готовий до гри? Просто натисни на кнопку нижче! 👇"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/game"))],
            [
                InlineKeyboardButton("📊 Статистика", callback_data='stats'),
                InlineKeyboardButton("🏆 Рейтинг", callback_data='leaderboard')
            ],
            [
                InlineKeyboardButton("🛒 Магазин", callback_data='shop'),
                InlineKeyboardButton("❓ Допомога", callback_data='help')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(welcome_message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

# Створюємо єдиний екземпляр бота
perky_bot = PerkyCoffeeBot()

async def setup_bot_handlers():
    """Створює та налаштовує додаток бота."""
    logger.info("Ініціалізація додатку Telegram-бота...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Реєструємо обробники
    application.add_handler(CommandHandler("start", perky_bot.start))
    application.add_handler(CallbackQueryHandler(perky_bot.button_callback))
    
    perky_bot.application = application
    logger.info("Обробники команд додано.")
