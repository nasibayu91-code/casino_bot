# keyboards/inline_kb.py
"""Inline-клавиатуры для бота"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 Игры", callback_data="menu_games")
    builder.button(text="💰 Баланс", callback_data="menu_balance")
    builder.button(text="👤 Профиль", callback_data="menu_profile")
    builder.button(text="🎁 Бонус", callback_data="menu_bonus")
    builder.button(text="👥 Рефералы", callback_data="menu_referrals")
    builder.button(text="🏆 Топ", callback_data="menu_top")
    builder.button(text="❓ Помощь", callback_data="menu_help")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def get_games_menu() -> InlineKeyboardMarkup:
    """Меню выбора игр"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎲 Dice", callback_data="game_dice")
    builder.button(text="📈 Crash", callback_data="game_crash")
    builder.button(text="💣 Mines", callback_data="game_mines")
    builder.button(text="🎰 Слоты", callback_data="game_slots")
    builder.button(text="🔙 Назад", callback_data="menu_back")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_dice_bet_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора ставки для Dice"""
    builder = InlineKeyboardBuilder()
    builder.button(text="100 💰", callback_data="dice_bet_100")
    builder.button(text="500 💰", callback_data="dice_bet_500")
    builder.button(text="1000 💰", callback_data="dice_bet_1000")
    builder.button(text="🔙 Назад", callback_data="game_dice_back")
    builder.adjust(3, 1)
    return builder.as_markup()


def get_crash_game_keyboard(multiplier: float = 1.0) -> InlineKeyboardMarkup:
    """Клавиатура для игры Crash"""
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💰 Забрать (x{multiplier:.1f})", callback_data=f"crash_cashout_{multiplier:.1f}")
    builder.button(text="🔙 Выйти", callback_data="crash_exit")
    builder.adjust(1)
    return builder.as_markup()


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура профиля"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="profile_stats")
    builder.button(text="📜 История игр", callback_data="profile_history")
    builder.button(text="🔙 Назад", callback_data="menu_back")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_back_button(callback_data: str = "menu_back") -> InlineKeyboardMarkup:
    """Кнопка 'Назад'"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data=callback_data)
    return builder.as_markup()