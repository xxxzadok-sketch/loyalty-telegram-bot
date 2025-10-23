import logging
import os
import threading
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from flask import Flask, request

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

# Инициализация Flask
app = Flask(__name__)

# Глобальная переменная для application
application = None


def setup_handlers(app_instance):
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
    app_instance.add_handler(reg_conv_handler)
    app_instance.add_handler(book_conv_handler)
    app_instance.add_handler(redeem_conv_handler)

    # Обработчики команд
    app_instance.add_handler(CommandHandler('admin', admin_handler))
    app_instance.add_handler(CommandHandler('menu', show_main_menu))

    # Обработчики callback запросов
    app_instance.add_handler(CallbackQueryHandler(user_button_handler, pattern='^(balance|history|main_menu)$'))
    app_instance.add_handler(CallbackQueryHandler(admin_button_handler, pattern='^admin_'))
    app_instance.add_handler(CallbackQueryHandler(admin_back_handler, pattern='^admin_back$'))

    # Обработчик текстовых сообщений для помощи
    app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_handler))


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


@app.route('/')
def index():
    return "🤖 Telegram Loyalty Bot is running via Webhook!"


@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик webhook от Telegram"""
    try:
        if not application:
            return 'Bot not initialized', 500

        # Обрабатываем обновление от Telegram
        update = Update.de_json(request.get_json(), application.bot)
        application.process_update(update)
        return 'ok'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'error', 500


def start_polling():
    """Запуск бота через polling"""
    try:
        logger.info("🤖 Запуск бота через polling...")
        application.run_polling()
    except Exception as e:
        logger.error(f"❌ Ошибка polling: {e}")


def init_bot():
    """Инициализация бота"""
    global application

    logger.info("🚀 Инициализация бота...")

    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден")
        return False

    logger.info(f"✅ BOT_TOKEN загружен: {BOT_TOKEN[:10]}...")

    # Инициализация базы данных
    try:
        db = Database()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")
        return False

    # Создание приложения
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        logger.info("✅ Приложение бота создано")
    except Exception as e:
        logger.error(f"❌ Ошибка создания приложения: {e}")
        return False

    # Настройка обработчиков
    try:
        setup_handlers(application)
        logger.info("✅ Обработчики настроены")
    except Exception as e:
        logger.error(f"❌ Ошибка настройки обработчиков: {e}")
        return False

    # Устанавливаем webhook ИЛИ polling
    webhook_url = os.environ.get('RENDER_EXTERNAL_URL', '') + '/webhook'

    if webhook_url and webhook_url.startswith('https://'):
        try:
            # Удаляем старый webhook и устанавливаем новый
            application.bot.delete_webhook()
            application.bot.set_webhook(webhook_url)
            logger.info(f"✅ Webhook установлен: {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка webhook: {e}")
            logger.info("🔄 Переключаемся на polling...")
            # Запускаем polling в отдельном потоке
            polling_thread = threading.Thread(target=start_polling)
            polling_thread.daemon = True
            polling_thread.start()
            return True
    else:
        logger.info("🔄 Webhook URL не найден, используем polling")
        # Запускаем polling в отдельном потоке
        polling_thread = threading.Thread(target=start_polling)
        polling_thread.daemon = True
        polling_thread.start()
        return True


def run_flask():
    """Запуск Flask сервера"""
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Flask запускается на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    logger.info("🎯 Запуск приложения...")

    # Инициализируем бота
    bot_initialized = init_bot()

    if not bot_initialized:
        logger.error("❌ Не удалось инициализировать бота")
    else:
        logger.info("✅ Бот успешно инициализирован")

    # Запускаем Flask
    run_flask()