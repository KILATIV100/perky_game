import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import RetryAfter

# Імпортуємо конфігурацію та базу даних
from config import BOT_TOKEN, WEBAPP_URL
from database import db

# Налаштування логера
logger = logging.getLogger(__name__)

# --- ДАНІ МАГАЗИНУ ТА КОНТАКТИ ---
CONTACT_PHONE = "+380 (95) 394 19 00"
CAFE_MENU_URL = "https://menu.ps.me/ZK6-i-cBzeg" # <--- ВАЖЛИВО: Замініть на реальне посилання

COFFEE_ITEMS = [
    {"id": "coffee_1", "name": "Arabica Ethiopia Yirgacheffe", "price": "250 грн", "desc": "Вишуканий лот з квітковими нотами та яскравою кислотністю."},
    {"id": "coffee_2", "name": "Robusta India Cherry", "price": "180 грн", "desc": "Міцний та насичений, ідеальний для еспресо, з нотами шоколаду."},
]

MERCH_ITEMS = [
    {"id": "merch_1", "name": "Брендована чашка (350 мл)", "price": "199 грн", "desc": "Стильна керамічна чашка з логотипом Perky Robot."},
    {"id": "merch_2", "name": "Футболка 'Coffee Jumper'", "price": "450 грн", "desc": "Бавовняна футболка високої якості з принтом Perky Robot."},
]

class PerkyCoffeeBot:
    """
    Клас, що інкапсулює всю логіку Telegram-бота.
    """
    def __init__(self):
        self.application = None
        self.webhook_url = f"{WEBAPP_URL}/{BOT_TOKEN}"

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка команди /start."""
        user = update.effective_user
        db.save_or_update_user(user.id, user.username, user.first_name)
        
        welcome_message = (
            f"Привіт, {user.first_name}! 👋\n\n"
            "Я - <b>Perky Coffee Jump Bot</b>! 🤖☕\n\n"
            "Готовий до гри? Просто натисни на кнопку нижче! 👇"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎮 Почати гру", web_app=WebAppInfo(url=f"{WEBAPP_URL}/game"))],
            [
                InlineKeyboardButton("☕ Меню кав'ярні", url=CAFE_MENU_URL),
            ],
            [
                InlineKeyboardButton("🛒 Магазин", callback_data='shop'),
                InlineKeyboardButton("📊 Статистика", callback_data='stats'),
            ],
            [
                InlineKeyboardButton("🏆 Рейтинг", callback_data='leaderboard'),
                InlineKeyboardButton("❓ Правила", callback_data='help')
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
        elif action.startswith('shop_cat_'):
            category = action.split('_')[-1]
            await self.show_shop_category(query, category)
        elif action.startswith('shop_item_'):
            item_id = action.split('_', 2)[-1]
            await self.show_shop_item(query, item_id)

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
                f"🕹️ <b>Зіграно ігор:</b> {stats['games_played']}"
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
        """Показує головне меню магазину."""
        shop_text = "🛒 <b>Магазин Perky Coffee:</b>\n\nОберіть, що бажаєте придбати:"
        
        keyboard = [
            [
                InlineKeyboardButton("☕ Кава в зернах", callback_data='shop_cat_coffee'),
                InlineKeyboardButton("👕 Мерч та аксесуари", callback_data='shop_cat_merch')
            ],
            [InlineKeyboardButton("↩️ Назад", callback_data='back_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(shop_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def show_shop_category(self, query: Update, category: str):
        """Показує список товарів у вибраній категорії."""
        items = COFFEE_ITEMS if category == 'coffee' else MERCH_ITEMS
        title = "☕ Кава в зернах" if category == 'coffee' else "👕 Мерч та аксесуари"
        
        shop_text = f"<b>{title}:</b>\n\nОберіть позицію для детального опису:"
        
        keyboard = []
        for item in items:
            keyboard.append([InlineKeyboardButton(f"{item['name']} ({item['price']})", callback_data=f"shop_item_{item['id']}")])
            
        keyboard.append([InlineKeyboardButton("↩️ Назад до магазину", callback_data='shop')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(shop_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        
    async def show_shop_item(self, query: Update, item_id: str):
        """Показує детальний опис товару."""
        item = next((i for i in COFFEE_ITEMS + MERCH_ITEMS if i['id'] == item_id), None)
        
        if not item:
            await query.edit_message_text("Позицію не знайдено.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Назад до магазину", callback_data='shop')]]))
            return

        item_category = 'coffee' if item in COFFEE_ITEMS else 'merch'
        
        item_text = (
            f"<b>{item['name']}</b>\n\n"
            f"💰 <b>Ціна:</b> {item['price']}\n\n"
            f"📝 <b>Опис:</b> {item['desc']}\n\n"
            f"📞 Для замовлення, будь ласка, зателефонуйте: <b>{CONTACT_PHONE}</b>"
        )
        
        keyboard = [[InlineKeyboardButton("↩️ Назад до категорії", callback_data=f"shop_cat_{item_category}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(item_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


    async def show_help(self, query: Update):
        """Показує опис гри та правила отримання бонусів."""
        help_text = (
            "❓ <b>Правила та Бонуси:</b>\n\n"
            "Керуйте кавовим роботом, стрибайте по платформах і збирайте кавові зерна (☕) на шляху до найвищого рекорду.\n\n"
            "<b>🎯 Основні правила:</b>\n"
            "1. Стрибайте якомога вище, уникаючи падіння та ворогів.\n"
            "2. Використовуйте гіроскоп або екранні кнопки для керування.\n"
            "3. Складність зростає після 200м і 500м.\n\n"
            "🎁 <b>Як виграти бонуси:</b>\n"
            "Знижки та призи видаються за загальну кількість зібраних кавових зерен (☕) у грі:\n"
            "— Знижка 2%: від 100 зерен\n"
            "— Знижка 5%: від 200 зерен\n"
            "— Брендована чашка: від 5000 зерен\n\n"
            "Ваша поточна статистика доступна у вкладці 📊 Статистика."
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
                InlineKeyboardButton("☕ Меню кав'ярні", url=CAFE_MENU_URL),
            ],
            [
                InlineKeyboardButton("🛒 Магазин", callback_data='shop'),
                InlineKeyboardButton("📊 Статистика", callback_data='stats'),
            ],
            [
                InlineKeyboardButton("🏆 Рейтинг", callback_data='leaderboard'),
                InlineKeyboardButton("❓ Правила", callback_data='help')
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
