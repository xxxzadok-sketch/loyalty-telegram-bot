from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from database import Database
from config import ADMIN_IDS

# Состояния для списания баллов
REDEEM_AMOUNT = range(1)

db = Database()


async def start_redemption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = db.get_user_by_telegram_id(query.from_user.id)
    if not user:
        await query.edit_message_text("❌ Сначала зарегистрируйтесь с помощью /start")
        return ConversationHandler.END

    if user[5] <= 0:
        await query.edit_message_text("❌ У вас недостаточно баллов для списания.")
        return ConversationHandler.END

    context.user_data['redemption_user_id'] = user[0]
    context.user_data['redemption_user_data'] = user

    await query.edit_message_text(
        f"🔄 Списание баллов\n\n"
        f"💎 Доступно баллов: {user[5]}\n"
        f"💡 1 бонусный балл = 1 рубль\n\n"
        f"Введите количество баллов для списания:"
    )
    return REDEEM_AMOUNT


async def get_redemption_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        points = int(update.message.text.strip())
        user_data = context.user_data['redemption_user_data']

        if points <= 0:
            await update.message.reply_text("❌ Количество баллов должно быть положительным. Введите снова:")
            return REDEEM_AMOUNT

        if points > user_data[5]:
            await update.message.reply_text(
                f"❌ Недостаточно баллов. Доступно: {user_data[5]}\n"
                f"Введите другое количество:"
            )
            return REDEEM_AMOUNT

        # Создаем запрос на списание
        try:
            request_id = db.create_redemption_request(context.user_data['redemption_user_id'], points)

            # Уведомляем админов
            from main import application
            user = user_data

            for admin_id in ADMIN_IDS:
                try:
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_approve_{request_id}"),
                            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_{request_id}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    admin_message = f"""
🔄 ЗАПРОС НА СПИСАНИЕ БАЛЛОВ

👤 Пользователь: {user[2]} {user[3]}
🆔 ID: {user[0]}
📱 Телефон: {user[4]}
💎 Запрошено баллов: {points}
💰 Сумма: {points} руб.
📅 Запрос: #{request_id}
                    """

                    await application.bot.send_message(
                        admin_id,
                        admin_message,
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    print(f"Ошибка отправки админу {admin_id}: {e}")

            success_text = f"""
✅ Запрос на списание отправлен!

💎 Баллов к списанию: {points}
💰 Сумма: {points} руб.

⏳ Ожидайте подтверждения администратора.
Мы уведомим вас о результате.
            """

            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(success_text, reply_markup=reply_markup)

        except Exception as e:
            error_msg = "❌ Произошла ошибка при создании запроса. Попробуйте позже."
            if "Недостаточно баллов" in str(e):
                error_msg = "❌ Недостаточно баллов для списания."
            await update.message.reply_text(error_msg)

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректное число:")
        return REDEEM_AMOUNT


async def cancel_redemption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Списание баллов отменено.")
    context.user_data.clear()
    return ConversationHandler.END