# commands.py
from telegram import Bot
from config import BOT_TOKEN


async def set_bot_commands():
    """Установка команд меню бота"""
    bot = Bot(token=BOT_TOKEN)

    commands = [
        ('start', 'Начать регистрацию'),
        ('menu', 'Главное меню'),
        ('admin', 'Панель администратора')
    ]

    await bot.set_my_commands(commands)
    print("✅ Команды бота установлены")


if __name__ == '__main__':
    import asyncio

    asyncio.run(set_bot_commands())