import asyncio, logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import BOT_TOKEN
from database import db
from handlers import user_handlers, game_handlers, admin_handlers

PORT = 100000
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle(request):
    return web.Response(text="Bot running")

async def start_web():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Web server on port {PORT}")

async def main():
    await db.init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(user_handlers.router)
    dp.include_router(game_handlers.router)
    dp.include_router(admin_handlers.router)
    await bot.set_my_commands([BotCommand(command="start", description="Старт")])
    me = await bot.get_me()
    logger.info(f"Бот @{me.username} запущен")
    await start_web()
    await dp.start_polling(bot)

asyncio.run(main())    logger.info("=" * 50)
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
