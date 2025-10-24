import logging
import os
import threading
import asyncio
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


def init_bot():
    """Инициализация бота"""
    global application

    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден")
        return

    # Инициализация базы данных
    db = Database()
    logger.info("✅ База данных инициализирована")

    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Настройка обработчиков
    setup_handlers(application)
    logger.info("✅ Обработчики настроены")

    # Устанавливаем webhook СИНХРОННО
    webhook_url = os.environ.get('RENDER_EXTERNAL_URL', '') + '/webhook'
    if webhook_url and webhook_url.startswith('https://'):
        try:
            # Используем run_method для синхронного вызова асинхронной функции
            application.run_method(lambda: application.bot.set_webhook(webhook_url))
            logger.info(f"✅ Webhook установлен: {webhook_url}")
        except Exception as e:
            logger.error(f"❌ Ошибка установки webhook: {e}")
    else:
        logger.info("ℹ️ Webhook URL не найден")

    return application  # ← ВОЗВРАЩАЕМ application


# Инициализируем бот сразу при импорте
application = init_bot()


@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик webhook от Telegram"""
    try:
        # Обрабатываем обновление от Telegram
        update = Update.de_json(request.get_json(), application.bot)

        # Используем run_method для синхронного вызова асинхронной функции
        application.run_method(lambda: application.process_update(update))

        return 'ok'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'error', 500


async def main():
    """Основная асинхронная функция"""
    logger.info("🎯 Запуск приложения...")

    # Инициализируем бота
    bot_initialized = await init_bot()

    if not bot_initialized:
        logger.error("❌ Не удалось инициализировать бота")
    else:
        logger.info("✅ Бот успешно инициализирован")

    # Запускаем Flask в отдельном потоке
    def run_flask():
        port = int(os.environ.get("PORT", 5000))
        logger.info(f"🌐 Flask запускается на порту {port}")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()


if __name__ == '__main__':
    # Запускаем Flask сервер (блокирующий вызов)
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 Запуск Flask сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)