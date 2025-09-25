# bot.py: Вся логіка Telegram-бота.
# Обробляє команди, кнопки та взаємодію з користувачем.

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from datetime import datetime

# Імпортуємо конфігурацію, базу даних та об'єкт бота
from config import BOT_TOKEN, WEBAPP_URL
from database import db

# Налаштування логування
logger = logging.getLogger(__name__)

class PerkyCoffeeBot:
    def __init__(self):
        self.application: Application = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /start."""
        user = update.effective_user
        # ВИПРАВЛЕННЯ: Зберігаємо дані користувача при старті
        db.save_user_info(user.id, user.username, user.first_name)
        
        welcome_message = f"""
🤖☕ Ласкаво просимо до **Perky Coffee Jump**!

Привіт, {user.first_name}! 👋

Це захоплива гра, де ти граєш за кавового робота, який намагається підстрибнути якомога вище, збираючи кавові зерна!

Обери дію нижче, щоб почати.
        """
        
        # ВИПРАВЛЕННЯ: Додано кнопку "Таблиця лідерів"
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/game"))],
            [InlineKeyboardButton("📊 Моя статистика", callback_data='stats')],
            [InlineKeyboardButton("🏆 Таблиця лідерів", callback_data='leaderboard')],
            [InlineKeyboardButton("❓ Допомога", callback_data='help')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник натискання кнопок."""
        query = update.callback_query
        await query.answer()
        
        actions = {
            'stats': self.show_stats,
            'leaderboard': self.show_leaderboard,
            'help': self.show_help,
            'main_menu': self.back_to_main_menu,
        }
        
        action = actions.get(query.data)
        if action:
            await action(query)

    async def show_stats(self, query):
        """Показує особисту статистику гравця."""
        user_id = query.from_user.id
        stats = db.get_user_stats(user_id)
        
        if not stats or stats.get('games_played', 0) == 0:
            stats_text = "📊 **Твоя статистика**\n\nТи ще не зіграв жодної гри. Час почати! 🚀"
        else:
            last_played_str = "нещодавно"
            if stats.get('last_played'):
                try:
                    # Конвертуємо час з UTC (як зберігає Railway) у локальний
                    dt_object = datetime.strptime(stats['last_played'], '%Y-%m-%d %H:%M:%S.%f') if '.' in stats['last_played'] else datetime.strptime(stats['last_played'], '%Y-%m-%d %H:%M:%S')
                    last_played_str = dt_object.strftime("%d.%m.%Y о %H:%M")
                except (ValueError, TypeError):
                    # Якщо формат інший або None, показуємо як є
                    last_played_str = str(stats['last_played']).split(" ")[0]


            stats_text = f"""
📊 **Твоя статистика**

🏆 **Рекорд висоти:** {stats.get('max_height', 0)} м
☕ **Всього зерен:** {stats.get('total_beans', 0)}
🎮 **Ігор зіграно:** {stats.get('games_played', 0)}
📅 **Остання гра:** {last_played_str}

Продовжуй грати, щоб стати найкращим!
            """
        
        keyboard = [[InlineKeyboardButton("↩️ Назад до меню", callback_data='main_menu')]]
        await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def show_leaderboard(self, query):
        """Показує глобальну таблицю лідерів."""
        leaderboard_data = db.get_leaderboard(10)
        
        if not leaderboard_data:
            leaderboard_text = "🏆 **Таблиця лідерів**\n\nПоки що ніхто не грав. Стань першим! 🚀"
        else:
            leaderboard_text = "🏆 **Топ-10 гравців:**\n\n"
            emojis = ["🥇", "🥈", "🥉"]
            for i, row in enumerate(leaderboard_data):
                # Unpack tuple or dictionary
                if isinstance(row, dict):
                    name, max_height, total_beans = row['display_name'], row['max_height'], row['total_beans']
                else:
                    name, max_height, total_beans = row
                
                place = emojis[i] if i < 3 else f"{i + 1}."
                leaderboard_text += f"{place} **{name}**\n      🏔️ {max_height} м  |  ☕️ {total_beans} зерен\n"
        
        keyboard = [[InlineKeyboardButton("↩️ Назад до меню", callback_data='main_menu')]]
        await query.edit_message_text(leaderboard_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def show_help(self, query):
        """Показує довідку по грі."""
        help_text = """
❓ **Допомога по грі**

**Мета:** Стрибай якомога вище, збирай кавові зерна ☕ і не падай!

**Керування:**
- **Кнопки:** Використовуй стрілки "←" та "→" внизу екрану.
- **Гіроскоп:** Нахиляй телефон, щоб рухати персонажа (можна увімкнути в налаштуваннях гри).

**Платформи:**
- **Коричневі:** Звичайні та безпечні.
- **Зелені:** Батути! Підкидають значно вище.
- **Крихкі:** Зникають після першого дотику!

Успіхів у стрибках! 🚀
        """
        keyboard = [[InlineKeyboardButton("↩️ Назад до меню", callback_data='main_menu')]]
        await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def back_to_main_menu(self, query):
        """Повертає користувача до головного меню."""
        user = query.from_user
        welcome_message = f"""
🤖☕ **Perky Coffee Jump**

Привіт, {user.first_name}! 👋 Обери дію нижче.
        """
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/game"))],
            [InlineKeyboardButton("📊 Моя статистика", callback_data='stats')],
            [InlineKeyboardButton("🏆 Таблиця лідерів", callback_data='leaderboard')],
            [InlineKeyboardButton("❓ Допомога", callback_data='help')]
        ]
        await query.edit_message_text(welcome_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# Створюємо єдиний екземпляр бота
perky_bot = PerkyCoffeeBot()

async def setup_bot():
    """Налаштовує та ініціалізує бота."""
    perky_bot.application = Application.builder().token(BOT_TOKEN).build()
    
    # Реєстрація обробників
    perky_bot.application.add_handler(CommandHandler("start", perky_bot.start))
    perky_bot.application.add_handler(CallbackQueryHandler(perky_bot.button_callback))
    
    # Встановлення вебхука
    # ВИПРАВЛЕННЯ: URL вебхука тепер вказує на правильний маршрут
    webhook_url = f"{WEBAPP_URL}/{BOT_TOKEN}"
    await perky_bot.application.bot.set_webhook(webhook_url)
    logger.info(f"Вебхук встановлено на: {webhook_url}")

