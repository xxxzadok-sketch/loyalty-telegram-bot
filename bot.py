from flask import Flask, request
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Простая проверка работы
        logging.info("Webhook received")
        return 'OK', 200
    except Exception as e:
        logging.error(f"Error: {e}")
        return 'ERROR', 500

@app.route('/')
def index():
    return 'Bot is running!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)