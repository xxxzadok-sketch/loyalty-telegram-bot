import logging
import os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters

from config import BOT_TOKEN
from database import Database

# Импорт обработчиков
from handlers.user_handlers import *
from handlers.booking_handlers import *
from handlers.redemption_handlers import *
from handlers.admin_handlers import *
from handlers.broadcast_handlers import *

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def setup_handlers(application):
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

    # Обработчик админ-панели (начисление баллов)
    admin_add_points_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_points, pattern='^admin_add_points$')],
        states={
            ADMIN_ADD_POINTS_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_for_add_points)],
            ADMIN_ADD_POINTS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount_for_add_points)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_operation)],
        name="admin_add_points"
    )

    # Обработчик админ-панели (списание баллов)
    admin_remove_points_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_remove_points, pattern='^admin_remove_points$')],
        states={
            ADMIN_REMOVE_POINTS_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_for_remove_points)],
            ADMIN_REMOVE_POINTS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount_for_remove_points)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_operation)],
        name="admin_remove_points"
    )

    # Обработчик рассылки
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_broadcast, pattern='^admin_broadcast$')],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, get_broadcast_message)],
            BROADCAST_CONFIRM: [CallbackQueryHandler(confirm_broadcast, pattern='^broadcast_')]
        },
        fallbacks=[CommandHandler('cancel', cancel_broadcast)],
        name="admin_broadcast"
    )

    # Добавляем все обработчики
    application.add_handler(reg_conv_handler)
    application.add_handler(book_conv_handler)
    application.add_handler(redeem_conv_handler)
    application.add_handler(admin_add_points_conv)
    application.add_handler(admin_remove_points_conv)
    application.add_handler(broadcast_conv)

    # Обработчики команд
    application.add_handler(CommandHandler('admin', admin_handler))
    application.add_handler(CommandHandler('menu', show_main_menu))

    # Обработчики callback запросов
    application.add_handler(CallbackQueryHandler(user_button_handler, pattern='^(balance|history|main_menu)$'))
    application.add_handler(CallbackQueryHandler(admin_button_handler, pattern='^admin_'))
    application.add_handler(CallbackQueryHandler(admin_back_handler, pattern='^admin_back$'))
    application.add_handler(CallbackQueryHandler(admin_button_handler, pattern='^(admin_approve_|admin_reject_)'))

    # Обработчик текстовых сообщений (для помощи)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_handler))


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    help_text = """
🤖 Команды бота:

/start - Начать регистрацию
/menu - Главное меню
/admin - Панель администратора (только для админов)

💎 Система лояльности:
• Регистрация с получением 100 бонусных баллов
• Бронирование столов
• Списание баллов (требует подтверждения админа)
• История операций

🎫 Для бронирования стола используйте кнопку в меню.
    """
    await update.message.reply_text(help_text)


def main():
    """Основная функция запуска бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден в переменных окружения")
        print("Пожалуйста, установите BOT_TOKEN в файле .env")
        return

    # Инициализация базы данных
    db = Database()
    logger.info("✅ База данных инициализирована")

    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Настройка обработчиков
    setup_handlers(application)
    logger.info("✅ Обработчики настроены")

    # Запуск бота
    logger.info("🤖 Бот запускается...")
    print("=" * 50)
    print("🤖 Бот системы лояльности запущен!")
    print(f"🐍 Python version: 3.12")
    print(f"💾 База данных: loyalty.db")
    print("=" * 50)

    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        print(f"❌ Ошибка: {e}")


if __name__ == '__main__':
    main()