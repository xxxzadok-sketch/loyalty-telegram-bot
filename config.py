import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('8280338020:AAEPSrOAulipX1IYNGO_vppatAdsC0yc-t4')
ADMIN_IDS = [356633485]  ## Замени на свой ID из @userinfobot
WEBHOOK_URL = os.getenv('https://loyalty-telegram-bot-1tej.onrender.com')  # URL твоего Render сервиса

# Конфигурация бота
BOT_CONFIG = {
    'welcome_bonus': 100,
    'cashback_percent': 5,
    'max_user_id': 3000
}