import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import RetryAfter

# Імпортуємо конфігурацію та базу даних
from config import BOT_TOKEN, GAME_URL, WEBHOOK_URL
from database import db

# Налаштування логера
logger = logging.getLogger(__name__)

class PerkyCoffeeBot:
    """Клас, що інкапсулює всю логіку Telegram-бота."""
    
    def __init__(self):
        # Ініціалізуємо основні компоненти як None
        self.application: Application = None
        self.webhook_url: str = WEBHOOK_URL

    async def initialize(self):
        """Створює екземпляр Application та налаштовує його."""
        logger.info("Ініціалізація додатку Telegram-бота...")
        self.application = Application.builder().token(BOT_TOKEN).build()

        # Додаємо обробники команд та кнопок
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        logger.info("Обробники команд додано.")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /start."""
        user = update.effective_user
        logger.info(f"Користувач {user.id} ({user.username}) запустив бота.")
        
        # Зберігаємо користувача в БД
        db.save_user(user.id, user.username, user.first_name)
        
        welcome_message = f"""
🤖☕ **Ласкаво просимо до Perky Coffee Jump!**

Привіт, {user.first_name}! 👋

Це захоплююча гра, де ти граєш за кавового робота Perky, стрибаючи все вище і вище, збираючи кавові зерна!

Обери дію в меню нижче, щоб почати.
        """
        
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=GAME_URL))],
            [InlineKeyboardButton("📊 Моя статистика", callback_data='stats')],
            [InlineKeyboardButton("🏆 Таблиця лідерів", callback_data='leaderboard')],
            [InlineKeyboardButton("🛒 Магазин", callback_data='shop')],
            [InlineKeyboardButton("❓ Допомога", callback_data='help')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник натискань на inline-кнопки."""
        query = update.callback_query
        await query.answer()
        
        action = query.data
        user_id = query.from_user.id
        
        logger.info(f"Користувач {user_id} натиснув кнопку: {action}")

        if action == 'stats':
            await self.show_stats(query)
        elif action == 'leaderboard':
            await self.show_leaderboard(query)
        elif action == 'shop':
            await self.show_shop(query)
        elif action == 'help':
            await self.show_help(query)
        elif action == 'back_main':
            await self.back_to_main_menu(query)

    async def show_stats(self, query: Update):
        """Показує особисту статистику гравця."""
        user_stats = db.get_user_stats(query.from_user.id)
        
        if not user_stats or user_stats['games_played'] == 0:
            stats_text = "📊 **Твоя статистика**\n\nТи ще не зіграв жодної гри. Час це виправити!"
        else:
            stats_text = f"""
📊 **Твоя статистика**

🏆 **Найкращий результат:** {user_stats['high_score']} м
☕️ **Зібрано зерен (всього):** {user_stats['total_beans']}
🎮 **Зіграно ігор:** {user_stats['games_played']}
        """
        
        keyboard = [
            [InlineKeyboardButton("🏆 Загальний рейтинг", callback_data='leaderboard')],
            [InlineKeyboardButton("↩️ Назад", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def show_leaderboard(self, query: Update):
        """Показує таблицю лідерів."""
        leaderboard_data = db.get_leaderboard(10)
        
        if not leaderboard_data:
            leaderboard_text = "🏆 **Таблиця лідерів**\n\nПоки що ніхто не грав. Стань першим!"
        else:
            leaderboard_text = "🏆 **Топ-10 гравців:**\n\n"
            medals = ["🥇", "🥈", "🥉"]
            for i, user in enumerate(leaderboard_data):
                place = medals[i] if i < 3 else f"{i + 1}."
                username = user['username'] or "Гравець"
                leaderboard_text += f"{place} {username} - **{user['high_score']} м**\n"
        
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_main')]]
        
        await query.edit_message_text(
            leaderboard_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def show_shop(self, query: Update):
        """Показує інформацію про магазин."""
        shop_text = """
🛒 **Магазин Perky**

Тут скоро з'явиться можливість купувати унікальні скіни для робота Perky та інші бонуси за зібрані кавові зерна!

Слідкуйте за оновленнями! ✨
        """
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_main')]]
        await query.edit_message_text(
            shop_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def show_help(self, query: Update):
        """Показує довідкову інформацію."""
        help_text = """
❓ **Допомога**

**Мета гри:** Стрибай якомога вище, збирай кавові зерна ☕️ і не падай!

**Керування:**
- **Кнопки:** Використовуй стрілки на екрані.
- **Гіроскоп:** Нахиляй телефон, щоб керувати роботом (можна увімкнути в налаштуваннях гри).

**Типи платформ:**
- **Коричнева:** Звичайна.
- **Зелена:** Батут, підкидає вище.
- **Сіра:** Ламається після першого стрибка.

Успіхів у грі! 🚀
        """
        keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data='back_main')]]
        await query.edit_message_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def back_to_main_menu(self, query: Update):
        """Повертає користувача в головне меню."""
        user = query.from_user
        main_menu_text = f"🤖☕ **Perky Coffee Jump**\n\nПривіт, {user.first_name}! Чим займемося?"
        
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=GAME_URL))],
            [InlineKeyboardButton("📊 Моя статистика", callback_data='stats')],
            [InlineKeyboardButton("🏆 Таблиця лідерів", callback_data='leaderboard')],
            [InlineKeyboardButton("🛒 Магазин", callback_data='shop')],
            [InlineKeyboardButton("❓ Допомога", callback_data='help')]
        ]
        
        await query.edit_message_text(
            main_menu_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

# Створюємо єдиний екземпляр класу для всього додатку
perky_bot = PerkyCoffeeBot()

async def setup_bot_handlers():
    """
    Ініціалізує додаток бота та налаштовує обробники.
    Ця функція тепер викликається один раз при старті сервера.
    """
    await perky_bot.initialize()
