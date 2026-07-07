# utils/helpers.py
"""Вспомогательные функции"""

from typing import Optional
import random


def format_number(num: int) -> str:
    """Форматирование числа с разделителями"""
    return f"{num:,}"


def generate_referral_link(bot_username: str, user_id: int) -> str:
    """Генерация реферальной ссылки"""
    return f"https://t.me/{bot_username}?start=ref_{user_id}"


def calculate_level_progress(xp: int) -> tuple:
    """Расчет прогресса уровня"""
    level = 1 + xp // 100
    current_level_xp = xp % 100
    next_level_xp = 100
    progress_percent = (current_level_xp / next_level_xp) * 100
    return level, current_level_xp, next_level_xp, progress_percent


def get_random_daily_bonus() -> int:
    """Генерация случайного ежедневного бонуса"""
    return random.randint(50, 200)


def validate_bet(bet: int, balance: int, min_bet: int = 100, max_bet: int = 10000) -> tuple:
    """
    Проверка ставки
    
    Returns:
        (is_valid, error_message)
    """
    if bet < min_bet:
        return False, f"❌ Минимальная ставка: {min_bet} 💰"
    
    if bet > max_bet:
        return False, f"❌ Максимальная ставка: {max_bet} 💰"
    
    if bet > balance:
        return False, f"❌ Недостаточно средств! Ваш баланс: {balance} 💰"
    
    return True, ""


def get_win_rate(wins: int, losses: int) -> float:
    """Расчет процента побед"""
    total = wins + losses
    if total == 0:
        return 0.0
    return round((wins / total) * 100, 1)