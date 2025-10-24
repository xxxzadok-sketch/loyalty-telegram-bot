from telegram import Update
from telegram.ext import ContextTypes
from database import SessionLocal, User
from sqlalchemy.orm import Session


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db: Session = SessionLocal()

    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user and user.registration_complete:
            await update.message.reply_text(f"Ваш баланс: {user.bonus_balance} бонусных баллов")
        else:
            await update.message.reply_text("Пожалуйста, завершите регистрацию через /start")
    finally:
        db.close()