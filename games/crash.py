# games/crash.py
"""Логика игры Crash"""

import random
import asyncio
from typing import Optional


class CrashGame:
    """Игра Crash - множитель растет, нужно успеть забрать"""
    
    def __init__(self):
        self.crash_point = self._generate_crash_point()
        self.current_multiplier = 1.0
        self.is_crashed = False
    
    def _generate_crash_point(self) -> float:
        """Генерация точки краша"""
        # Используем экспоненциальное распределение
        # 50% шанс что краш будет > 2x
        # 10% шанс что краш будет > 10x
        # 1% шанс что краш будет > 50x
        
        rand = random.random()
        if rand < 0.01:  # 1% - супер большой множитель
            return round(random.uniform(50, 100), 1)
        elif rand < 0.10:  # 10% - большой множитель
            return round(random.uniform(10, 50), 1)
        elif rand < 0.30:  # 20% - средний множитель
            return round(random.uniform(3, 10), 1)
        else:  # 70% - маленький множитель
            return round(random.uniform(0.5, 3), 1)
    
    def update_multiplier(self) -> float:
        """Обновление множителя (каждую секунду)"""
        if self.is_crashed:
            return 0
        
        # Увеличиваем множитель
        self.current_multiplier += random.uniform(0.05, 0.15)
        self.current_multiplier = round(self.current_multiplier, 2)
        
        # Проверяем краш
        if self.current_multiplier >= self.crash_point:
            self.is_crashed = True
            return 0
        
        return self.current_multiplier
    
    def cash_out(self, bet: int) -> dict:
        """Забрать выигрыш"""
        if self.is_crashed:
            return {
                "won": False,
                "multiplier": 0,
                "profit": -bet,
                "crash_point": self.crash_point
            }
        
        profit = int(bet * self.current_multiplier)
        return {
            "won": True,
            "multiplier": self.current_multiplier,
            "profit": profit,
            "crash_point": self.crash_point
        }
    
    @staticmethod
    def get_initial_data(bet: int) -> dict:
        """Получить начальные данные для игры"""
        crash = CrashGame()
        return {
            "bet": bet,
            "crash_point": crash.crash_point,
            "game": crash
        }