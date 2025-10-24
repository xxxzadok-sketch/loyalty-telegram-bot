from flask import Flask, request
from telegram import Update
import logging
import os
import asyncio

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Инициализация базы данных
from database import init_db

init_db()

# Импорт основного приложения
from main import application as bot_application


@app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        json_data = request.get_json()
        update = Update.de_json(json_data, bot_application.bot)
        await bot_application.process_update(update)
        return 'OK', 200
    except Exception as e:
        logging.error(f"Error processing update: {e}")
        return 'ERROR', 500


@app.route('/')
def index():
    return 'Bot is live! Use /start in Telegram.'


@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"https://{request.host}/webhook"
    try:
        # Используем asyncio для запуска асинхронной функции
        async def set_wh():
            await bot_application.bot.set_webhook(webhook_url)

        asyncio.run(set_wh())
        return f'Webhook set to: {webhook_url}'
    except Exception as e:
        return f'Error setting webhook: {e}'


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)