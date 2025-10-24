import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
DATABASE_URL = os.getenv('DATABASE_URL')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен")