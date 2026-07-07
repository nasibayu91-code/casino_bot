# games/dice.py
"""Логика игры Dice"""

import random
from typing import Tuple


class DiceGame:
    """Игра Dice - угадай число от 1 до 6"""
    
    @staticmethod
    def play(bet: int, prediction: int = None) -> dict:
        """
        Запуск игры Dice
        
        Args:
            bet: Ставка
            prediction: Предсказанное число (1-6), если None - случайное
            
        Returns:
            dict с результатами игры
        """
        dice = random.randint(1, 6)
        
        if prediction is None:
            prediction = random.randint(1, 6)
        
        won = dice == prediction
        
        # Множитель зависит от вероятности
        multiplier = 5.8 if won else 0  # Шанс 1/6, множитель x5.8 (хаус эдж ~3.3%)
        
        return {
            "dice": dice,
            "prediction": prediction,
            "won": won,
            "multiplier": multiplier,
            "bet": bet,
            "profit": int(bet * multiplier) if won else -bet
        }
    
    @staticmethod
    def get_dice_emoji(number: int) -> str:
        """Получить emoji для числа на кубике"""
        dice_emojis = {
            1: '⚀', 2: '⚁', 3: '⚂',
            4: '⚃', 5: '⚄', 6: '⚅'
        }
        return dice_emojis.get(number, '🎲')