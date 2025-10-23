import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from database import Database
from config import ADMIN_IDS

logger = logging.getLogger(__name__)
db = Database()

# Состояния для регистрации
FIRST_NAME, LAST_NAME, PHONE, CONFIRM = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing_user = db.get_user_by_telegram_id(user.id)

    if existing_user:
        await show_main_menu(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "👋 Добро пожаловать! Давайте зарегистрируем вас в нашей системе лояльности.\n"
            "📝 Пожалуйста, введите ваше имя:"
        )
        return FIRST_NAME


async def get_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['first_name'] = update.message.text.strip()
    if not context.user_data['first_name']:
        await update.message.reply_text("❌ Имя не может быть пустым. Пожалуйста, введите ваше имя:")
        return FIRST_NAME

    await update.message.reply_text("📝 Теперь введите вашу фамилию:")
    return LAST_NAME


async def get_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['last_name'] = update.message.text.strip()
    if not context.user_data['last_name']:
        await update.message.reply_text("❌ Фамилия не может быть пустой. Пожалуйста, введите вашу фамилию:")
        return LAST_NAME

    await update.message.reply_text("📱 Теперь введите ваш номер телефона:")
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text.strip()
    if not context.user_data['phone']:
        await update.message.reply_text("❌ Телефон не может быть пустым. Пожалуйста, введите ваш номер телефона:")
        return PHONE

    # Показываем данные для подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Всё верно", callback_data="confirm_yes")],
        [InlineKeyboardButton("✏️ Исправить данные", callback_data="confirm_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user_data = context.user_data
    confirmation_text = f"""
📋 Проверьте ваши данные:

👤 Имя: {user_data['first_name']}
📖 Фамилия: {user_data['last_name']}
📱 Телефон: {user_data['phone']}

Всё верно?
    """

    await update.message.reply_text(confirmation_text, reply_markup=reply_markup)
    return CONFIRM


async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_yes":
        user_data = context.user_data

        try:
            user_id = db.create_user(
                query.from_user.id,
                user_data['first_name'],
                user_data['last_name'],
                user_data['phone']
            )

            welcome_text = f"""
🎉 Благодарим за регистрацию!

✅ Вам начислено 100 бонусных баллов!
📋 Ваши данные:
   👤 Имя: {user_data['first_name']}
   📖 Фамилия: {user_data['last_name']}
   📱 Телефон: {user_data['phone']}
   🆔 Ваш ID: {user_id}

💎 Теперь вы можете пользоваться всеми возможностями нашего бота!
            """

            await query.edit_message_text(welcome_text)
            await show_main_menu_from_query(query, context)

        except Exception as e:
            error_message = "❌ Произошла ошибка при регистрации. Пожалуйста, попробуйте позже."
            if "уже зарегистрирован" in str(e):
                error_message = "❌ Вы уже зарегистрированы в системе!"
            elif "лимит пользователей" in str(e):
                error_message = "❌ Достигнут лимит регистраций. Пожалуйста, обратитесь к администратору."

            await query.edit_message_text(error_message)

        context.user_data.clear()
        return ConversationHandler.END

    else:
        await query.edit_message_text("📝 Пожалуйста, введите ваше имя:")
        return FIRST_NAME


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 Мой баланс", callback_data="balance")],
        [InlineKeyboardButton("🎫 Забронировать стол", callback_data="book_table")],
        [InlineKeyboardButton("🔄 Списать баллы", callback_data="redeem_points")],
        [InlineKeyboardButton("📊 История операций", callback_data="history")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🏠 Главное меню:\nВыберите действие:",
        reply_markup=reply_markup
    )


async def show_main_menu_from_query(query, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 Мой баланс", callback_data="balance")],
        [InlineKeyboardButton("🎫 Забронировать стол", callback_data="book_table")],
        [InlineKeyboardButton("🔄 Списать баллы", callback_data="redeem_points")],
        [InlineKeyboardButton("📊 История операций", callback_data="history")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "🏠 Главное меню:\nВыберите действие:",
        reply_markup=reply_markup
    )


async def user_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = db.get_user_by_telegram_id(query.from_user.id)
    if not user:
        await query.edit_message_text("❌ Пользователь не найден. Используйте /start для регистрации.")
        return

    if query.data == "balance":
        await show_balance(query, user)
    elif query.data == "history":
        await show_history(query, user)
    elif query.data == "main_menu":
        await show_main_menu_from_query(query, context)


async def show_balance(query, user):
    balance_text = f"""
💎 Ваш баланс:

🆔 Ваш ID: {user[0]}
👤 Имя: {user[2]} {user[3]}
📱 Телефон: {user[4]}
⭐ Бонусные баллы: {user[5]}

💡 1 бонусный балл = 1 рубль
    """

    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(balance_text, reply_markup=reply_markup)


async def show_history(query, user):
    transactions = db.get_user_transactions(user[0])

    if not transactions:
        history_text = "📊 История операций пуста"
    else:
        history_text = "📊 Последние операции:\n\n"
        for trans in transactions:
            points, desc, timestamp = trans
            sign = "+" if points > 0 else ""
            date_str = timestamp.split()[0]
            history_text += f"📅 {date_str} - {sign}{points} баллов\n   {desc}\n\n"

    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(history_text, reply_markup=reply_markup)


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Регистрация отменена.")
    context.user_data.clear()
    return ConversationHandler.END