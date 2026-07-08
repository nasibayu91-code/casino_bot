# config.py
"""Конфигурация бота - загрузка из .env"""

import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота от @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в .env файле!")

# Настройки базы данных
DB_NAME = os.getenv("DB_NAME", "casino.db")

# Игровые константы
START_BALANCE = int(os.getenv("START_BALANCE", 1000))
MIN_BET = int(os.getenv("MIN_BET", 100))
MAX_BET = int(os.getenv("MAX_BET", 10000))

# Бонусы
DAILY_BONUS_MIN = int(os.getenv("DAILY_BONUS_MIN", 50))
DAILY_BONUS_MAX = int(os.getenv("DAILY_BONUS_MAX", 200))
REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", 100))
REFERRAL_PERCENT = int(os.getenv("REFERRAL_PERCENT", 5))

# Администраторы (ID пользователей)
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "123456789,987654321").split(",")]
