# bot.py: Вся логіка, що стосується Telegram-бота.
# Включає обробники команд, кнопок та налаштування вебхука.

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

from config import BOT_TOKEN, WEBAPP_URL, SHOP_ITEMS
from database import db

# Налаштування логера
logger = logging.getLogger(__name__)

class PerkyCoffeeBot:
    def __init__(self):
        # application буде ініціалізовано в setup_bot
        self.application: Application | None = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка команди /start"""
        user = update.effective_user
        db.save_user(user.id, user.username, user.first_name)
        
        welcome_message = f"Привіт, {user.first_name}! 👋\n\nЯ - Perky Coffee Jump Bot! 🤖☕\n\nГотовий до гри? Просто натисни на кнопку нижче! 👇"
        
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/game"))],
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
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

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

    async def show_stats(self, query: Update):
        """Показує статистику користувача."""
        user_id = query.from_user.id
        stats = db.get_user_stats(user_id)
        
        if not stats or stats.get('games_played', 0) == 0:
            stats_text = "📊 Ваша статистика порожня. Час зіграти першу гру!"
        else:
            stats_text = (
                f"📊 **Ваша статистика:**\n"
                f"🏆 Рекорд: **{stats['max_height']}** м\n"
                f"☕ Зібрано зерен: **{stats['total_beans']}**\n"
                f"🕹️ Зіграно ігор: **{stats['games_played']}**"
            )
        
        keyboard = [
            [InlineKeyboardButton("🏆 Таблиця лідерів", callback_data='leaderboard')],
            [InlineKeyboardButton("↩️ Назад", callback_data='back_main')]
        ]
        await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def show_leaderboard(self, query: Update):
        """Показує таблицю лідерів."""
        leaderboard = db.get_leaderboard()
        
        if not leaderboard:
            leaderboard_text = "🏆 Таблиця лідерів порожня. Будьте першим!"
        else:
            leaderboard_text = "🏆 **Топ-10 гравців:**\n\n"
            for i, (username, first_name, max_height, _) in enumerate(leaderboard, 1):
                name = first_name or username or "Анонім"
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{emoji} {name} - **{max_height}** м\n"

        keyboard = [[InlineKeyboardButton("↩️ Назад до статистики", callback_data='stats')]]
        await query.edit_message_text(leaderboard_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        
    async def show_shop(self, query: Update):
        """Показує магазин."""
        shop_text = "🛒 **Магазин мерчу**\n\nОберіть товар:"
        keyboard = []
        for item_id, item in SHOP_ITEMS.items():
            price_grn = item['price'] // 100
            keyboard.append([InlineKeyboardButton(f"{item['name']} - {price_grn} грн", callback_data=f'buy_{item_id}')])
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data='back_main')])
        await query.edit_message_text(shop_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def show_help(self, query: Update):
        """Показує допомогу."""
        help_text = "❓ **Допомога**\n\nСтрибайте якомога вище, збирайте зерна та не падайте!"
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_main')]]
        await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def back_to_main(self, query: Update):
        """Повертає користувача до головного меню."""
        user = query.from_user
        welcome_message = f"Привіт, {user.first_name}! 👋\n\nГотовий до гри? Просто натисни на кнопку нижче! 👇"
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/game"))],
            [
                InlineKeyboardButton("📊 Статистика", callback_data='stats'),
                InlineKeyboardButton("🏆 Таблиця лідерів", callback_data='leaderboard')
            ],
            [
                InlineKeyboardButton("🛒 Магазин", callback_data='shop'),
                InlineKeyboardButton("❓ Допомога", callback_data='help')
            ]
        ]
        await query.edit_message_text(welcome_message, reply_markup=InlineKeyboardMarkup(keyboard))

# Створюємо єдиний екземпляр класу бота, який будемо використовувати у всьому додатку.
perky_bot = PerkyCoffeeBot()

async def setup_bot():
    """
    Ініціалізує та налаштовує екземпляр Telegram-бота.
    Ця функція створює об'єкт Application, додає до нього обробники
    команд та встановлює вебхук, щоб Telegram міг надсилати оновлення.
    """
    # Ініціалізація Application з токеном
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Додавання обробників
    application.add_handler(CommandHandler("start", perky_bot.start))
    application.add_handler(CallbackQueryHandler(perky_bot.button_callback))

    # Зберігаємо application в екземплярі нашого бота для доступу з інших частин коду
    perky_bot.application = application

    # Встановлення вебхука
    webhook_url = f"{WEBAPP_URL}/{BOT_TOKEN}"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Вебхук встановлено на: {webhook_url}")

