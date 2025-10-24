from flask import Flask, request
from telegram import Update
import config
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Инициализация бота
from main import application as bot_application

@app.route('/webhook', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(), bot_application.bot)
    await bot_application.process_update(update)
    return 'OK', 200

@app.route('/')
def index():
    return 'Bot is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)