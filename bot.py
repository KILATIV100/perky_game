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
CONTACT_PHONE = "+380 (95) 394 19 00" # <--- ОНОВЛЕНО
CAFE_MENU_URL = "https://menu.ps.me/ZK6-i-cBzeg" # <--- ОНОВЛЕНО

COFFEE_ITEMS = [ # <--- ОНОВЛЕНО
    {
        "id": "coffee_1", 
        "name": "ZAVARI Santos Blend (100% арабіка)", 
        "price": "340 грн (200 г) / 1450 грн (1 кг)", 
        "desc": "Кава, що підкорює з першого ковтка! 🌟 **М’яка бразильська арабіка** з горіховим солодким ароматом. Післясмак чорного шоколаду та фруктові нотки. Ідеальний варіант для підзарядження.\n\n*Обсмаження: Середнє | Кислотність: Низька | Тіло: Насичене*"
    },
    {
        "id": "coffee_2", 
        "name": "Brazil Alfenas Dulce (100% арабіка)", 
        "price": "340 грн (200 г)", 
        "desc": "Неймовірна м'якість та багатство смаку. Солодкуватий аромат **молочного шоколаду та підсмаженого фундука** 🌰🍫. Ніжна солодкість карамелі з нотками какао. Кава для справжніх гурманів."
    },
    {
        "id": "coffee_3", 
        "name": "ETHIOPIA YIRGACHEFFE GRADE 1 (100% арабіка)", 
        "price": "380 грн (200 г)", 
        "desc": "Для любителів ніжної кави з **фруктовими акцентами**. Яскравий аромат жасмину та медової дині. Легкий смак з нотами цитрусу, чорниць, полуниць 🍓🍋, та післясмаком вишні і карамелі."
    },
    {
        "id": "coffee_4", 
        "name": "Italy Blend (100% арабіка)", 
        "price": "340 грн (200 г) / 1450 грн (1 кг)", 
        "desc": "Класичний італійський бленд. Аромат обсмаженого зерна, карамелі та горіхів. Гармонійний баланс гіркоти і солодкості з легкими нотами **шоколаду та цитрусової свіжості** 🍫🍊. Ідеальна для будь-якого часу доби."
    },
    {
        "id": "coffee_5", 
        "name": "GOURMETTO (80% арабіка / 20% робуста)", 
        "price": "300 грн (200 г)", 
        "desc": "Кава, яка дарує справжній смаковий експірієнс. Гармонійне поєднання **шоколаду, карамелі та сухофруктів** з легкою пікантною гірчинкою. Глибокий, тривалий післясмак і делікатна кислинка. 🍇🍬"
    },
]

MERCH_ITEMS = [ # <--- ОНОВЛЕНО
    {
        "id": "merch_1", 
        "name": "Еко чашка з бамбука 'PerkUP'", 
        "price": "200 грн", 
        "desc": "Стильна багаторазова еко-чашка з бамбукового волокна. Зменшуйте відходи та насолоджуйтесь кавою на ходу! Об'єм: 350 мл."
    },
    {
        "id": "merch_2", 
        "name": "Футболка 'Coffee Jumper'", 
        "price": "350 грн", 
        "desc": "Бавовняна футболка високої якості з унікальним принтом **Perky Robot**! Ідеально підходить для фанатів гри та поціновувачів комфорту."
    },
    {
        "id": "merch_3", 
        "name": "Худі 'Coffee Jumper'", 
        "price": "1000 грн", 
        "desc": "Тепле та затишне худі з капюшоном. Стильний мінімалістичний дизайн із логотипом гри. Ідеально для холодних днів з гарячою кавою."
    },
    {
        "id": "merch_4", 
        "name": "Подарунковий набір 'PerkUP'", 
        "price": "2000 грн", 
        "desc": "Ідеальний подарунок для кавомана! Включає: 200 г кави на вибір, брендовану еко-чашку та міні-пакування крафтового шоколаду. **Справжнє свято смаку**!"
    },
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
        db.save_or_update_user(user.id, user.username, user.first_name) # <--- ВИПРАВЛЕНО
        
        welcome_message = (
            f"Привіт, {user.first_name}! 👋\n\n"
            "Я - <b>Perky Coffee Jump Bot</b>! 🤖☕\n\n"
            "Готовий до гри? Просто натисни на кнопку нижче! 👇"
        )
        
        keyboard = [ # <--- ОНОВЛЕНО
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
        # ОНОВЛЕНА ЛОГІКА ДЛЯ КАТЕГОРІЙ МАГАЗИНУ - ЯВНА ПЕРЕВІРКА
        elif action == 'shop_cat_coffee':
            await self.show_shop_category(query, 'coffee')
        elif action == 'shop_cat_merch':
            await self.show_shop_category(query, 'merch')
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
        help_text = ( # <--- ОНОВЛЕНО
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
