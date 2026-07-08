# main.py для Render (Web Service)
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import BOT_TOKEN
from database import db
from handlers import user_handlers, game_handlers, admin_handlers

PORT = 10000
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
    logger.info("=" * 50)
    logger.info("Запуск Casino Bot...")
    await db.init_db()
    logger.info("✅ База данных инициализирована")
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(user_handlers.router)
    dp.include_router(game_handlers.router)
    dp.include_router(admin_handlers.router)
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Начать"),
        BotCommand(command="help", description="❓ Помощь")
    ])
    bot_info = await bot.get_me()
    logger.info(f"✅ Бот @{bot_info.username} запущен!")
    await start_web()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
