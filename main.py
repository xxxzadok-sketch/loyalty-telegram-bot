from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import config
from handlers import user_handlers, admin_handlers, booking_handlers, broadcast_handlers, redemption_handlers
from database import init_db


def main():
    # Инициализация базы данных
    init_db()

    # Создание приложения
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Регистрация обработчиков пользователя
    application.add_handler(CommandHandler("start", user_handlers.start))
    application.add_handler(CallbackQueryHandler(user_handlers.handle_registration, pattern="^confirm_registration$"))
    application.add_handler(CallbackQueryHandler(user_handlers.edit_registration, pattern="^edit_registration$"))

    # Регистрация обработчиков бронирования
    application.add_handler(CallbackQueryHandler(booking_handlers.start_booking, pattern="^booking$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, booking_handlers.handle_booking_data))

    # Регистрация обработчиков списания баллов
    application.add_handler(CallbackQueryHandler(redemption_handlers.start_redemption, pattern="^redeem_bonus$"))
    application.add_handler(
        CallbackQueryHandler(redemption_handlers.handle_redemption_confirmation, pattern="^redeem_confirm_"))
    application.add_handler(CallbackQueryHandler(redemption_handlers.handle_admin_redemption, pattern="^admin_redeem_"))

    # Регистрация обработчиков администратора
    application.add_handler(CommandHandler("admin", admin_handlers.admin_panel))
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_admin_action, pattern="^admin_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handlers.handle_admin_input))

    # Регистрация обработчиков рассылки
    application.add_handler(CallbackQueryHandler(broadcast_handlers.start_broadcast, pattern="^broadcast$"))
    application.add_handler(
        MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, broadcast_handlers.handle_broadcast_content))

    # Запуск бота
    application.run_polling()


if __name__ == "__main__":
    main()