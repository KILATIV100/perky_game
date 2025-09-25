# bot.py: Вся логіка, пов'язана з Telegram-ботом.

from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes, Application, CommandHandler, CallbackQueryHandler
from telegram.constants import ParseMode
import config
from database import Database

class PerkyCoffeeBot:
    """Клас, що інкапсулює логіку Telegram-бота."""
    def __init__(self, database: Database):
        self.db = database
        self.application: Application = None

    async def setup(self):
        """Ініціалізація додатка бота."""
        self.application = Application.builder().token(config.BOT_TOKEN).build()

    async def set_webhook(self):
        """Встановлення вебхука для бота."""
        webhook_url = f"{config.WEBAPP_URL}/{config.BOT_TOKEN}"
        await self.application.bot.set_webhook(webhook_url)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /start."""
        user = update.effective_user
        self.db.save_user(user.id, user.username, user.first_name)

        welcome_message = f"Привіт, {user.first_name}! 👋\n\nЛаскаво просимо до 🤖☕ **Perky Coffee Jump**!\n\nСтрибай, збирай зерна та став рекорди!"
        await update.message.reply_text(welcome_message, reply_markup=self._main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник натискань на inline-кнопки."""
        query = update.callback_query
        await query.answer()

        action_map = {
            'stats': self.show_stats,
            'leaderboard': self.show_leaderboard,
            'shop': self.show_shop,
            'help': self.show_help,
            'back_main': self.back_to_main
        }

        if query.data in action_map:
            await action_map[query.data](query)
        elif query.data.startswith('buy_'):
            item_id = query.data.replace('buy_', '')
            await self.buy_item(query, item_id)

    async def show_stats(self, query):
        """Показує статистику гравця."""
        user_id = query.from_user.id
        stats = self.db.get_user_stats(user_id)

        if not stats or stats['games_played'] == 0:
            stats_text = "📊 **Твоя статистика**\n\nТи ще не грав. Час почати! 🚀"
        else:
            last_played_str = datetime.fromisoformat(stats['last_played']).strftime("%d.%m.%Y %H:%M") if stats['last_played'] else 'Ніколи'
            stats_text = (
                f"📊 **Твоя статистика**\n\n"
                f"🎮 Ігор зіграно: *{stats['games_played']}*\n"
                f"🏔️ Рекорд висоти: *{stats['max_height']} м*\n"
                f"☕ Усього зерен: *{stats['total_beans']}*\n"
                f"📅 Остання гра: *{last_played_str}*"
            )
        await query.edit_message_text(stats_text, reply_markup=self._back_keyboard('back_main'), parse_mode=ParseMode.MARKDOWN)

    async def show_leaderboard(self, query):
        """Показує таблицю лідерів."""
        leaderboard = self.db.get_leaderboard(10)
        leaderboard_text = "🏆 **Таблиця лідерів**\n\n"
        if not leaderboard:
            leaderboard_text += "Поки що немає рекордів. Стань першим!"
        else:
            for i, (username, first_name, max_height, total_beans) in enumerate(leaderboard, 1):
                name = first_name or username or "Гравець"
                emoji = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
                leaderboard_text += f"{emoji} *{name}* - {max_height} м\n"
        await query.edit_message_text(leaderboard_text, reply_markup=self._back_keyboard('back_main'), parse_mode=ParseMode.MARKDOWN)

    async def show_shop(self, query):
        """Показує магазин."""
        shop_text = "🛒 **Магазин Perky Coffee**\n\nКупуй ексклюзивний мерч та підтримай розробку гри!"
        keyboard_buttons = [
            [InlineKeyboardButton(f"{item['name']} - {item['price']//100} грн", callback_data=f'buy_{item_id}')]
            for item_id, item in config.SHOP_ITEMS.items()
        ]
        keyboard_buttons.append([InlineKeyboardButton("↩️ Назад", callback_data='back_main')])
        await query.edit_message_text(shop_text, reply_markup=InlineKeyboardMarkup(keyboard_buttons))

    async def buy_item(self, query, item_id: str):
        """Обробляє покупку товару."""
        item = config.SHOP_ITEMS.get(item_id)
        if not item:
            await query.answer("Товар не знайдено!", show_alert=True)
            return
        await query.edit_message_text(
            f"Ви обрали: *{item['name']}*\n\n{item['description']}\n\nЦіна: *{item['price']//100} грн*\n\n_(Функція оплати у розробці)_",
            reply_markup=self._back_keyboard('shop'), parse_mode=ParseMode.MARKDOWN
        )

    async def show_help(self, query):
        """Показує довідку по грі."""
        help_text = (
            "❓ **Допомога по грі**\n\n"
            "🎮 *Керування:*\nНатискай на екран або використовуй стрілки для переміщення.\n\n"
            "🎯 *Мета:*\nСтрибай якомога вище, збирай кавові зерна ☕ і не падай!\n\n"
            "Успіхів! 🚀"
        )
        await query.edit_message_text(help_text, reply_markup=self._back_keyboard('back_main'), parse_mode=ParseMode.MARKDOWN)

    async def back_to_main(self, query):
        """Повертає користувача в головне меню."""
        user = query.from_user
        welcome_message = f"Привіт, {user.first_name}! 👋\n\nГотовий до нових рекордів у **Perky Coffee Jump**? 🤖☕"
        await query.edit_message_text(welcome_message, reply_markup=self._main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)

    def _main_menu_keyboard(self):
        """Генерує клавіатуру головного меню."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/static/index.html"))],
            [InlineKeyboardButton("📊 Статистика", callback_data='stats'), InlineKeyboardButton("🏆 Лідери", callback_data='leaderboard')],
            [InlineKeyboardButton("🛒 Магазин", callback_data='shop'), InlineKeyboardButton("❓ Допомога", callback_data='help')]
        ])

    def _back_keyboard(self, callback_data: str):
        """Генерує клавіатуру з кнопкою "Назад"."""
        return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Назад", callback_data=callback_data)]])

def setup_bot_handlers(bot_instance: PerkyCoffeeBot):
    """Реєструє обробники команд для бота."""
    application = bot_instance.application
    application.add_handler(CommandHandler("start", bot_instance.start))
    application.add_handler(CallbackQueryHandler(bot_instance.button_callback))

