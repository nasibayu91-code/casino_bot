# keyboards/reply_kb.py
"""Reply-клавиатуры (обычные кнопки)"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура с кнопками"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Игры"), KeyboardButton(text="💰 Баланс")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🎁 Бонус")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )


def get_games_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для быстрого доступа к играм"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎲 Dice"), KeyboardButton(text="📈 Crash")],
            [KeyboardButton(text="💣 Mines"), KeyboardButton(text="🎰 Слоты")],
            [KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )