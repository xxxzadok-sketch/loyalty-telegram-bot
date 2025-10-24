from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import SessionLocal, User
from sqlalchemy.orm import Session
import config

REGISTRATION = range(1)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db: Session = SessionLocal()

    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()

        if user and user.registration_complete:
            # Пользователь уже зарегистрирован
            keyboard = [
                [InlineKeyboardButton("💰 Мой баланс", callback_data="balance")],
                [InlineKeyboardButton("🎯 Забронировать стол", callback_data="booking")],
                [InlineKeyboardButton("🎁 Списать баллы", callback_data="redeem_bonus")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"Добро пожаловать, {user.first_name}!",
                reply_markup=reply_markup
            )
        elif user and not user.registration_complete:
            # Пользователь в процессе регистрации
            await update.message.reply_text("Пожалуйста, завершите регистрацию.")
            await ask_registration_data(update, context)
        else:
            # Новый пользователь
            user = User(telegram_id=user_id)
            db.add(user)
            db.commit()

            context.user_data['registration_step'] = 0
            await update.message.reply_text(
                "Добро пожаловать! Для регистрации в системе лояльности нам нужны ваши данные."
            )
            await ask_registration_data(update, context)

    finally:
        db.close()


async def ask_registration_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    steps = ["Введите ваше имя:", "Введите вашу фамилию:", "Введите ваш номер телефона:"]
    current_step = context.user_data.get('registration_step', 0)

    if current_step < len(steps):
        await update.message.reply_text(steps[current_step])
        return REGISTRATION
    else:
        await show_registration_summary(update, context)
        return ConversationHandler.END


async def handle_registration_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_step = context.user_data.get('registration_step', 0)
    text = update.message.text

    if current_step == 0:
        context.user_data['first_name'] = text
    elif current_step == 1:
        context.user_data['last_name'] = text
    elif current_step == 2:
        context.user_data['phone'] = text

    context.user_data['registration_step'] = current_step + 1
    await ask_registration_data(update, context)


async def show_registration_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_registration"),
            InlineKeyboardButton("✏️ Исправить", callback_data="edit_registration")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    summary = f"Проверьте ваши данные:\n\n"
    summary += f"Имя: {context.user_data.get('first_name', '')}\n"
    summary += f"Фамилия: {context.user_data.get('last_name', '')}\n"
    summary += f"Телефон: {context.user_data.get('phone', '')}"

    await update.message.reply_text(summary, reply_markup=reply_markup)


async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    db: Session = SessionLocal()

    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.first_name = context.user_data.get('first_name')
            user.last_name = context.user_data.get('last_name')
            user.phone = context.user_data.get('phone')
            user.bonus_balance = 100  # Приветственные баллы
            user.registration_complete = True

            # Генерация ID (от 1 до 3000)
            max_id_user = db.query(User).filter(User.id.between(1, 3000)).order_by(User.id.desc()).first()
            new_id = 1 if not max_id_user else max_id_user.id + 1
            if new_id > 3000:
                # Найти свободный ID
                used_ids = {u.id for u in db.query(User.id).filter(User.id.between(1, 3000)).all()}
                new_id = next(i for i in range(1, 3001) if i not in used_ids)

            user.id = new_id
            db.commit()

            keyboard = [
                [InlineKeyboardButton("💰 Мой баланс", callback_data="balance")],
                [InlineKeyboardButton("🎯 Забронировать стол", callback_data="booking")],
                [InlineKeyboardButton("🎁 Списать баллы", callback_data="redeem_bonus")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"Благодарим за регистрацию! Вам начислено 100 бонусных баллов.\n"
                f"Ваш ID: {new_id}\n\n"
                f"Имя: {user.first_name}\n"
                f"Фамилия: {user.last_name}\n"
                f"Телефон: {user.phone}",
                reply_markup=reply_markup
            )

    finally:
        db.close()


async def edit_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data['registration_step'] = 0
    await query.edit_message_text("Давайте начнем регистрацию заново.")
    await ask_registration_data(update, context)

    async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех текстовых сообщений"""
        user_id = update.effective_user.id

        # Проверяем, ожидаем ли мы ввод данных для регистрации
        if context.user_data.get('registration_step') is not None:
            await handle_registration_data(update, context)
        # Проверяем, ожидаем ли мы ввод суммы для списания
        elif context.user_data.get('awaiting_redemption_amount'):
            await redemption_handlers.handle_redemption_confirmation(update, context)
        # Проверяем, ожидаем ли мы ввод данных для бронирования
        elif context.user_data.get('awaiting_booking_data'):
            await booking_handlers.handle_booking_data(update, context)
        else:
            await update.message.reply_text("Используйте кнопки меню для навигации.")


async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех текстовых сообщений"""
    user_id = update.effective_user.id

    # Проверяем, ожидаем ли мы ввод данных для регистрации
    if context.user_data.get('registration_step') is not None:
        await handle_registration_data(update, context)
    # Проверяем, ожидаем ли мы ввод суммы для списания
    elif context.user_data.get('awaiting_redemption_amount'):
        await redemption_handlers.handle_redemption_confirmation(update, context)
    # Проверяем, ожидаем ли мы ввод данных для бронирования
    elif context.user_data.get('awaiting_booking_data'):
        await booking_handlers.handle_booking_data(update, context)
    else:
        await update.message.reply_text("Используйте кнопки меню для навигации.")