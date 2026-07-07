# main.py
"""Главный файл запуска бота"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database import db
from handlers import user_handlers, game_handlers, admin_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    """Установка команд бота в меню"""
    commands = [
        BotCommand(command="start", description="🚀 Начать игру"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="balance", description="💰 Баланс"),
        BotCommand(command="bonus", description="🎁 Ежедневный бонус"),
        BotCommand(command="referral", description="👥 Рефералы"),
        BotCommand(command="top", description="🏆 Топ игроков"),
        BotCommand(command="help", description="❓ Помощь"),
    ]
    await bot.set_my_commands(commands)


async def main():
    """Точка входа"""
    logger.info("=" * 50)
    logger.info("Запуск Casino Bot...")
    
    # Инициализация базы данных
    await db.init_db()
    logger.info("✅ База данных инициализирована")
    
    # Создание бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрация обработчиков
    dp.include_router(user_handlers.router)
    dp.include_router(game_handlers.router)
    dp.include_router(admin_handlers.router)
    
    # Установка команд
    await set_commands(bot)
    
    # Информация о боте
    bot_info = await bot.get_me()
    logger.info(f"✅ Бот @{bot_info.username} запущен!")
    logger.info("=" * 50)
    
    try:
        # Запуск поллинга
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())