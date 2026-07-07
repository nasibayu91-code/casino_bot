# config.py
"""Конфигурация бота"""

# Токен бота от @BotFather
BOT_TOKEN = "8713801403:AAEQK8iraJVa33w9AyUIyhGTFrnHGbZ1918"

# Настройки базы данных
DB_NAME = "casino.db"

# Игровые константы
START_BALANCE = 1000  # Стартовый баланс новых пользователей
MIN_BET = 100  # Минимальная ставка
MAX_BET = 10000  # Максимальная ставка

# Бонусы
DAILY_BONUS_MIN = 50
DAILY_BONUS_MAX = 200
REFERRAL_BONUS = 100  # Бонус за приглашенного друга
REFERRAL_PERCENT = 5  # Процент от ставок реферала

# Администраторы (ID пользователей)
ADMIN_IDS = [123456789, 987654321]  # Замените на реальные ID