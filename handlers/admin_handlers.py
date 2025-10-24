from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal, User
from sqlalchemy.orm import Session
import config


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return

    keyboard = [
        [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("💰 Начислить баллы", callback_data="admin_add_bonus")],
        [InlineKeyboardButton("📤 Рассылка", callback_data="broadcast")],
        [InlineKeyboardButton("🎁 Запросы на списание", callback_data="admin_redemption_requests")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Панель администратора:", reply_markup=reply_markup)


async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "admin_users":
        await show_users_list(query, context)
    elif action == "admin_add_bonus":
        await ask_user_for_bonus(query, context)


async def show_users_list(query, context):
    db: Session = SessionLocal()

    try:
        users = db.query(User).filter(User.registration_complete == True).all()

        if not users:
            await query.edit_message_text("Нет зарегистрированных пользователей.")
            return

        message = "Список пользователей:\n\n"
        for user in users[:10]:  # Показываем первых 10
            message += f"ID: {user.id} | {user.first_name} {user.last_name} | Баланс: {user.bonus_balance}\n"

        if len(users) > 10:
            message += f"\n... и еще {len(users) - 10} пользователей"

        await query.edit_message_text(message)

    finally:
        db.close()


async def ask_user_for_bonus(query, context):
    context.user_data['admin_action'] = 'add_bonus'
    await query.edit_message_text("Введите ID пользователя и сумму через пробел (например: 123 1000):")


async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in config.ADMIN_IDS:
        return

    text = update.message.text

    if context.user_data.get('admin_action') == 'add_bonus':
        await process_bonus_addition(update, context, text)


async def process_bonus_addition(update, context, text):
    try:
        user_id_str, amount_str = text.split()
        user_id = int(user_id_str)
        amount = int(amount_str)

        db: Session = SessionLocal()

        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                bonus_amount = int(amount * 0.05)  # 5% от суммы
                user.bonus_balance += bonus_amount
                db.commit()

                # Уведомляем пользователя
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"Вам начислено {bonus_amount} бонусных баллов за посещение!\n"
                             f"Текущий баланс: {user.bonus_balance}"
                    )
                except:
                    pass  # Пользователь заблокировал бота

                await update.message.reply_text(
                    f"Пользователю {user.first_name} {user.last_name} начислено {bonus_amount} баллов.\n"
                    f"Новый баланс: {user.bonus_balance}"
                )
            else:
                await update.message.reply_text("Пользователь не найден.")

        finally:
            db.close()

    except ValueError:
        await update.message.reply_text("Неверный формат. Введите ID и сумму через пробел (например: 123 1000)")