from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal, User, RedemptionRequest
from sqlalchemy.orm import Session
import config


async def start_redemption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    db: Session = SessionLocal()

    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user and user.registration_complete:
            await query.edit_message_text(
                f"Ваш текущий баланс: {user.bonus_balance} баллов\n\n"
                "Введите количество баллов для списания:"
            )
            context.user_data['awaiting_redemption_amount'] = True
        else:
            await query.edit_message_text("Пожалуйста, завершите регистрацию.")

    finally:
        db.close()


async def handle_redemption_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if context.user_data.get('awaiting_redemption_amount'):
        try:
            amount = int(update.message.text)
            user_id = update.effective_user.id

            db: Session = SessionLocal()

            try:
                user = db.query(User).filter(User.telegram_id == user_id).first()
                if user and user.bonus_balance >= amount:
                    # Создаем запрос на списание
                    redemption_request = RedemptionRequest(
                        user_id=user.id,
                        amount=amount
                    )
                    db.add(redemption_request)
                    db.commit()

                    # Уведомляем администраторов
                    await notify_admins_about_redemption(context, user, redemption_request)

                    await update.message.reply_text(
                        f"Запрос на списание {amount} баллов отправлен администратору. "
                        f"Ожидайте подтверждения."
                    )
                else:
                    await update.message.reply_text("Недостаточно баллов на счете.")

            finally:
                db.close()

        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число.")

        context.user_data['awaiting_redemption_amount'] = False


async def notify_admins_about_redemption(context, user, redemption_request):
    message = f"🎁 Запрос на списание баллов!\n\n"
    message += f"Пользователь: {user.first_name} {user.last_name}\n"
    message += f"ID: {user.id}\n"
    message += f"Телефон: {user.phone}\n"
    message += f"Сумма: {redemption_request.amount} баллов\n"
    message += f"Текущий баланс: {user.bonus_balance}"

    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_redeem_confirm_{redemption_request.id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_redeem_reject_{redemption_request.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=message,
                reply_markup=reply_markup
            )
        except:
            pass


async def handle_admin_redemption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, request_id = query.data.split('_')[2], int(query.data.split('_')[3])

    db: Session = SessionLocal()

    try:
        redemption_request = db.query(RedemptionRequest).filter(RedemptionRequest.id == request_id).first()
        if redemption_request:
            user = db.query(User).filter(User.id == redemption_request.user_id).first()

            if action == 'confirm' and user.bonus_balance >= redemption_request.amount:
                user.bonus_balance -= redemption_request.amount
                redemption_request.status = 'approved'
                db.commit()

                # Уведомляем пользователя
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"С вашего счета списано {redemption_request.amount} бонусных баллов.\n"
                             f"Новый баланс: {user.bonus_balance}"
                    )
                except:
                    pass

                await query.edit_message_text(f"Списание подтверждено. Пользователь уведомлен.")
            else:
                redemption_request.status = 'rejected'
                db.commit()
                await query.edit_message_text("Списание отклонено.")

    finally:
        db.close()