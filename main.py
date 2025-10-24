from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
import config
from handlers import user_handlers, admin_handlers, booking_handlers, broadcast_handlers, redemption_handlers
from database import init_db
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def main():
    # Инициализация базы данных
    init_db()

    # Создание приложения
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Регистрация обработчиков пользователя
    application.add_handler(CommandHandler("start", user_handlers.start))
    application.add_handler(CommandHandler("balance", user_handlers.balance))

    # Обработчики регистрации
    application.add_handler(CallbackQueryHandler(user_handlers.handle_registration, pattern="^confirm_registration$"))
    application.add_handler(CallbackQueryHandler(user_handlers.edit_registration, pattern="^edit_registration$"))

    # Обработчики бронирования
    application.add_handler(CallbackQueryHandler(booking_handlers.start_booking, pattern="^booking$"))

    # Обработчики списания баллов
    application.add_handler(CallbackQueryHandler(redemption_handlers.start_redemption, pattern="^redeem_bonus$"))
    application.add_handler(CallbackQueryHandler(redemption_handlers.handle_admin_redemption, pattern="^admin_redeem_"))

    # Обработчики администратора
    application.add_handler(CommandHandler("admin", admin_handlers.admin_panel))
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_action, pattern="^admin_"))

    # Обработчики рассылки
    application.add_handler(CallbackQueryHandler(broadcast_handlers.start_broadcast, pattern="^broadcast$"))

    # Обработка текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_handlers.handle_all_messages))

    # Запуск бота
    print("Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    main()