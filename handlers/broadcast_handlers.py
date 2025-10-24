from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal, User
from sqlalchemy.orm import Session
import config


async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if user_id not in config.ADMIN_IDS:
        await query.edit_message_text("У вас нет доступа к этой функции.")
        return

    context.user_data['awaiting_broadcast'] = True
    await query.edit_message_text(
        "Отправьте сообщение для рассылки (текст, фото или видео):"
    )


async def handle_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in config.ADMIN_IDS or not context.user_data.get('awaiting_broadcast'):
        return

    db: Session = SessionLocal()

    try:
        users = db.query(User).filter(User.registration_complete == True).all()
        sent_count = 0

        for user in users:
            try:
                if update.message.text:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=update.message.text
                    )
                elif update.message.photo:
                    await context.bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=update.message.photo[-1].file_id,
                        caption=update.message.caption
                    )
                elif update.message.video:
                    await context.bot.send_video(
                        chat_id=user.telegram_id,
                        video=update.message.video.file_id,
                        caption=update.message.caption
                    )
                sent_count += 1
            except:
                continue  # Пользователь заблокировал бота

        await update.message.reply_text(f"Рассылка завершена. Сообщение отправлено {sent_count} пользователям.")

    finally:
        db.close()
        context.user_data['awaiting_broadcast'] = False