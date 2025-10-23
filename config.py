import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [123456789]  # ЗАМЕНИ НА СВОЙ TELEGRAM ID

# Конфигурация бота
BOT_CONFIG = {
    'welcome_bonus': 100,
    'cashback_percent': 5,
    'max_user_id': 3000
}