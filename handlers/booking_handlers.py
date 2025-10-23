from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from database import Database

# Состояния для бронирования
BOOK_DATE, BOOK_TIME, BOOK_GUESTS, BOOK_CONFIRM = range(4)

db = Database()


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = db.get_user_by_telegram_id(query.from_user.id)
    if not user:
        await query.edit_message_text("❌ Сначала зарегистрируйтесь с помощью /start")
        return ConversationHandler.END

    context.user_data['booking_user_id'] = user[0]
    await query.edit_message_text(
        "🎫 Бронирование стола\n\n"
        "Пожалуйста, введите дату бронирования (в формате ДД.ММ.ГГГГ):\n"
        "Например: 25.12.2024"
    )
    return BOOK_DATE


async def get_booking_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = update.message.text.strip()

    # Простая валидация даты
    if len(date) != 10 or date[2] != '.' or date[5] != '.':
        await update.message.reply_text("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ:\nНапример: 25.12.2024")
        return BOOK_DATE

    context.user_data['booking_date'] = date
    await update.message.reply_text(
        "⏰ Теперь введите время бронирования (в формате ЧЧ:ММ):\n"
        "Например: 19:30"
    )
    return BOOK_TIME


async def get_booking_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time = update.message.text.strip()

    # Простая валидация времени
    if len(time) != 5 or time[2] != ':':
        await update.message.reply_text("❌ Неверный формат времени. Используйте ЧЧ:ММ:\nНапример: 19:30")
        return BOOK_TIME

    context.user_data['booking_time'] = time
    await update.message.reply_text("👥 Введите количество гостей:")
    return BOOK_GUESTS


async def get_booking_guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        guests = int(update.message.text.strip())

        if guests <= 0 or guests > 20:
            await update.message.reply_text("❌ Количество гостей должно быть от 1 до 20. Введите корректное число:")
            return BOOK_GUESTS

        context.user_data['booking_guests'] = guests

        # Показываем подтверждение
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить бронирование", callback_data="booking_confirm")],
            [InlineKeyboardButton("✏️ Изменить данные", callback_data="booking_edit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        booking_text = f"""
📋 Проверьте данные бронирования:

📅 Дата: {context.user_data['booking_date']}
⏰ Время: {context.user_data['booking_time']}
👥 Гости: {guests} человек

Всё верно?
        """

        await update.message.reply_text(booking_text, reply_markup=reply_markup)
        return BOOK_CONFIRM

    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректное число гостей:")
        return BOOK_GUESTS


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "booking_confirm":
        user_id = context.user_data['booking_user_id']
        date = context.user_data['booking_date']
        time = context.user_data['booking_time']
        guests = context.user_data['booking_guests']

        try:
            booking_id = db.create_booking(user_id, date, time, guests)

            booking_text = f"""
✅ Бронирование подтверждено!

🎫 Номер брони: #{booking_id}
📅 Дата: {date}
⏰ Время: {time}
👥 Гости: {guests} человек

🎉 Ждем вас в нашем заведении!
💎 Не забудьте предъявить ваш ID: {user_id}
            """

            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(booking_text, reply_markup=reply_markup)

        except Exception as e:
            await query.edit_message_text("❌ Произошла ошибка при бронировании. Пожалуйста, попробуйте позже.")

        context.user_data.clear()
        return ConversationHandler.END

    else:
        await query.edit_message_text("🎫 Введите дату бронирования (ДД.ММ.ГГГГ):")
        return BOOK_DATE


async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Бронирование отменено.")
    context.user_data.clear()
    return ConversationHandler.END