import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('8280338020:AAF89sCUSzDNLKf2dZ0AW_Swh7r764boY2Q')
ADMIN_IDS = [356633485]  # Найди через @userinfobot
WEBHOOK_URL = os.getenv('https://loyalty-telegram-bot-2igj.onrender.com')  # URL твоего Render сервиса

# Конфигурация бота
BOT_CONFIG = {
    'welcome_bonus': 100,
    'cashback_percent': 5,
    'max_user_id': 3000
}