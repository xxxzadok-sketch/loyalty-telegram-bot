# bot.py
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from database import Database

# Импорт обработчиков
from handlers.user_handlers import *
from handlers.booking_handlers import *
from handlers.redemption_handlers import *
from handlers.admin_handlers import *
from handlers.broadcast_handlers import *

# ДОБАВЬТЕ ЭТУ СТРОКУ:
from main import help_handler

logger = logging.getLogger(__name__)


def create_application():
    """Создание и настройка приложения бота"""
    from config import BOT_TOKEN

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден")

    # Инициализация базы данных
    db = Database()
    logger.info("✅ База данных инициализирована")

    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Настройка обработчиков
    setup_handlers(application)
    logger.info("✅ Обработчики настроены")

    return application


def setup_handlers(app):
    """Настройка всех обработчиков"""
    # Обработчик регистрации пользователя
    reg_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_last_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CONFIRM: [CallbackQueryHandler(confirm_registration, pattern='^confirm_')]
        },
        fallbacks=[CommandHandler('cancel', cancel_registration)],
        name="user_registration"
    )

    # Обработчик бронирования стола
    book_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_booking, pattern='^book_table$')],
        states={
            BOOK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_booking_date)],
            BOOK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_booking_time)],
            BOOK_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_booking_guests)],
            BOOK_CONFIRM: [CallbackQueryHandler(confirm_booking, pattern='^booking_')]
        },
        fallbacks=[CommandHandler('cancel', cancel_booking)],
        name="table_booking"
    )

    # Обработчик списания баллов
    redeem_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_redemption, pattern='^redeem_points$')],
        states={
            REDEEM_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_redemption_amount)]
        },
        fallbacks=[CommandHandler('cancel', cancel_redemption)],
        name="points_redemption"
    )

    # Добавляем все обработчики
    app.add_handler(reg_conv_handler)
    app.add_handler(book_conv_handler)
    app.add_handler(redeem_conv_handler)

    # Обработчики команд
    app.add_handler(CommandHandler('admin', admin_handler))
    app.add_handler(CommandHandler('menu', show_main_menu))

    # Обработчики callback запросов
    app.add_handler(CallbackQueryHandler(user_button_handler, pattern='^(balance|history|main_menu)$'))
    app.add_handler(CallbackQueryHandler(admin_button_handler, pattern='^admin_'))
    app.add_handler(CallbackQueryHandler(admin_back_handler, pattern='^admin_back$'))

    # Обработчик текстовых сообщений для помощи
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_handler))