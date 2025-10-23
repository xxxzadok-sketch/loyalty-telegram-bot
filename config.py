import os

# Используем os.environ для Render
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables!")

ADMIN_IDS = [123456789]  # Замени на свой ID

BOT_CONFIG = {
    'welcome_bonus': 100,
    'cashback_percent': 5,
    'max_user_id': 3000
}

print(f"✅ BOT_TOKEN loaded: {BOT_TOKEN[:10]}...")  # Для отладки