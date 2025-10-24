# main.py
import logging
import os
import asyncio
from flask import Flask, request
from telegram import Update

from bot import create_application
from config import BOT_TOKEN

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
application = None


@app.route('/')
def index():
    return "🤖 Telegram Loyalty Bot is running via Webhook!"


def set_commands():
    """Установка команд бота"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from commands import set_bot_commands
        loop.run_until_complete(set_bot_commands())
        loop.close()
        logger.info("✅ Команды бота установлены")
    except Exception as e:
        logger.error(f"❌ Ошибка установки команд: {e}")


# В main.py функция init_bot() должна выглядеть так:
def init_bot():
    """Инициализация бота"""
    global application

    try:
        # Создаем приложение
        application = create_application()
        logger.info("✅ Приложение бота создано")

        # Инициализируем приложение (БЕЗ application.start())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.initialize())
        logger.info("✅ Приложение инициализировано")

        # Устанавливаем webhook
        webhook_url = os.environ.get('RENDER_EXTERNAL_URL', '') + '/webhook'
        if webhook_url.startswith('https://'):
            loop.run_until_complete(application.bot.set_webhook(webhook_url))
            logger.info(f"✅ Webhook установлен: {webhook_url}")
        else:
            logger.warning("⚠️ Webhook URL не найден или не HTTPS")

        logger.info("✅ Бот готов к работе")
        return application

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации бота: {e}")
        return None


@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик webhook от Telegram"""
    global application

    if application is None:
        logger.error("❌ Application не инициализирована")
        return 'error', 500

    try:
        # Получаем обновление
        update_data = request.get_json()

        # Логируем входящее сообщение
        if 'message' in update_data and 'text' in update_data['message']:
            user_id = update_data['message']['from']['id']
            text = update_data['message']['text']
            logger.info(f"📨 Сообщение от {user_id}: {text}")

        # Создаем объект Update
        update = Update.de_json(update_data, application.bot)

        # ⭐ ВАЖНО: Используем create_task для асинхронной обработки
        import asyncio
        async def process_async():
            try:
                await application.process_update(update)
                logger.info("✅ Обновление обработано")
            except Exception as e:
                if "Event loop is closed" not in str(e):
                    logger.error(f"❌ Ошибка обработки: {e}")

        # Запускаем асинхронно
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_async())
        loop.close()

        return 'ok'

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return 'error', 500


# Инициализируем бот при импорте
application = init_bot()

# Устанавливаем команды бота после инициализации
set_commands()

if __name__ == '__main__':
    # Запускаем Flask
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 Запуск Flask сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)