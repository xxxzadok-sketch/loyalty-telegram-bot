import logging
import os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from flask import Flask
import threading

from config import BOT_TOKEN
from database import Database
from handlers.user_handlers import start, show_main_menu
from handlers.admin_handlers import admin_handler
from handlers.user_handlers import user_button_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/')
def home():
    return "🤖 Bot is running!"


def run_bot():
    """Запуск бота с polling"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        # Базовые обработчики
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('menu', show_main_menu))
        application.add_handler(CommandHandler('admin', admin_handler))
        application.add_handler(CallbackQueryHandler(user_button_handler))

        logger.info("🤖 Бот запускается через polling...")
        application.run_polling()
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")


if __name__ == '__main__':
    # Инициализация базы данных
    db = Database()


    # Запускаем Flask
    def run_flask():
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port, debug=False)


    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Запускаем бота
    run_bot()