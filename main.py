# main.py
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database import db
from handlers import user_handlers, game_handlers, admin_handlers

# Порт, который будет слушать Render (10000 — стандартный)
PORT = 10000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle(request):
    """Простой обработчик HTTP-запросов, чтобы Render видел открытый порт"""
    return web.Response(text="Bot is running")


async def start_web_server():
    """Запуск веб-сервера для проверки порта"""
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Начать игру"),
        BotCommand(command="help", description="❓ Помощь"),
    ]
    await bot.set_my_commands(commands)


async def main():
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

    # Проверка токена
    bot_info = await bot.get_me()
    logger.info(f"✅ Бот @{bot_info.username} запущен!")

    # Запуск веб-сервера (чтобы Render не ругался на отсутствие порта)
    await start_web_server()

    logger.info("📝 Бот начал приём сообщений...")
    try:
        # Запуск поллинга
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
