from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from database import Database
from config import ADMIN_IDS

# Состояния для рассылки
BROADCAST_MESSAGE, BROADCAST_CONFIRM = range(2)

db = Database()

def get_bot():
    from main import application
    return application

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("❌ Доступ запрещен")
        return ConversationHandler.END

    await query.edit_message_text(
        "📢 Рассылка сообщения\n\n"
        "Отправьте сообщение для рассылки (текст, фото или видео):"
    )
    return BROADCAST_MESSAGE


async def get_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем сообщение для рассылки
    context.user_data['broadcast_message'] = {
        'text': update.message.text if update.message.text else update.message.caption,
        'photo': update.message.photo[-1].file_id if update.message.photo else None,
        'video': update.message.video.file_id if update.message.video else None
    }

    users = db.get_all_users()
    context.user_data['broadcast_users_count'] = len(users)

    confirm_text = f"""
📢 Подтверждение рассылки:

👥 Получателей: {len(users)} пользователей
📝 Сообщение: {context.user_data['broadcast_message']['text'][:100]}...

✅ Начать рассылку?
    """

    keyboard = [
        [InlineKeyboardButton("✅ Начать рассылку", callback_data="broadcast_confirm")],
        [InlineKeyboardButton("❌ Отменить", callback_data="broadcast_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(confirm_text, reply_markup=reply_markup)
    return BROADCAST_CONFIRM


async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "broadcast_confirm":
        users = db.get_all_users()
        broadcast_data = context.user_data['broadcast_message']
        sent_count = 0
        failed_count = 0

        # Отправляем сообщение о начале рассылки
        await query.edit_message_text(f"📢 Начата рассылка...\n\n👥 Отправка для {len(users)} пользователей")

        bot_app = get_bot()

        # Рассылаем сообщение
        for user in users:
            try:
                if broadcast_data['photo']:
                    await bot_app.bot.send_photo(
                        chat_id=user[1],
                        photo=broadcast_data['photo'],
                        caption=broadcast_data['text']
                    )
                elif broadcast_data['video']:
                    await bot_app.bot.send_video(
                        chat_id=user[1],
                        video=broadcast_data['video'],
                        caption=broadcast_data['text']
                    )
                else:
                    await bot_app.bot.send_message(
                        chat_id=user[1],
                        text=broadcast_data['text']
                    )
                sent_count += 1
            except Exception as e:
                print(f"Ошибка отправки пользователю {user[0]}: {e}")
                failed_count += 1

        # Отчет о рассылке
        report_text = f"""
📢 Рассылка завершена:

✅ Успешно отправлено: {sent_count}
❌ Не удалось отправить: {failed_count}
👥 Всего пользователей: {len(users)}
        """

        await query.message.reply_text(report_text)

    else:
        await query.edit_message_text("❌ Рассылка отменена")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Рассылка отменена.")
    context.user_data.clear()
    return ConversationHandler.END