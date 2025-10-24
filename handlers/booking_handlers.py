from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal, User, Booking
from sqlalchemy.orm import Session


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data['booking_step'] = 0
    await query.edit_message_text(
        "🎯 Бронирование стола\n\n"
        "Пожалуйста, введите данные в следующем формате:\n"
        "Дата (ДД.ММ.ГГГГ) Время (ЧЧ:ММ) Количество гостей\n\n"
        "Например: 25.12.2024 19:30 4"
    )


async def handle_booking_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    db: Session = SessionLocal()

    try:
        user = db.query(User).filter(User.telegram_id == user_id, User.registration_complete == True).first()
        if not user:
            await update.message.reply_text("Пожалуйста, завершите регистрацию через /start")
            return

        # Парсим введенные данные
        try:
            parts = text.split()
            if len(parts) != 3:
                raise ValueError

            date_str, time_str, guests_str = parts
            guests = int(guests_str)

            # Создаем бронирование
            booking = Booking(
                user_id=user.id,
                date=date_str,
                time=time_str,
                guests=guests
            )
            db.add(booking)
            db.commit()

            # Уведомляем администратора
            await notify_admin_about_booking(context, user, booking)

            await update.message.reply_text(
                f"✅ Бронирование принято!\n\n"
                f"Дата: {date_str}\n"
                f"Время: {time_str}\n"
                f"Гости: {guests} чел.\n\n"
                f"Мы свяжемся с вами для подтверждения."
            )

        except ValueError:
            await update.message.reply_text(
                "Неверный формат. Пожалуйста, введите данные в формате:\n"
                "Дата Время Количество_гостей\n\n"
                "Например: 25.12.2024 19:30 4"
            )

    finally:
        db.close()


async def notify_admin_about_booking(context, user, booking):
    message = f"🎯 Новое бронирование!\n\n"
    message += f"Пользователь: {user.first_name} {user.last_name}\n"
    message += f"ID: {user.id}\n"
    message += f"Телефон: {user.phone}\n"
    message += f"Дата: {booking.date}\n"
    message += f"Время: {booking.time}\n"
    message += f"Гости: {booking.guests} чел."

    # Отправляем всем администраторам
    from config import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message)
        except:
            pass