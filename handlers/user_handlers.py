# handlers/user_handlers.py
"""Обработчики пользовательских команд"""

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from keyboards.inline_kb import get_main_menu, get_profile_keyboard
from keyboards.reply_kb import get_main_reply_keyboard
from utils.helpers import (
    format_number, generate_referral_link,
    calculate_level_progress, get_win_rate
)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or f"User{user_id}"
    
    # Проверяем реферальную ссылку
    referrer_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            referrer_id = int(command.args.split("_")[1])
        except (ValueError, IndexError):
            pass
    
    # Регистрируем пользователя
    is_new = await db.register_user(user_id, username, referrer_id)
    user = await db.get_user(user_id)
    
    if is_new:
        welcome_text = f"""
🎰 <b>ДОБРО ПОЖАЛОВАТЬ В CASINO BOT!</b>

👤 Игрок: @{username}
💰 Стартовый баланс: <b>{format_number(user['balance'])} 💰</b>

🎮 Доступные игры:
• 🎲 Dice - угадай число
• 📈 Crash - поймай множитель
• 💣 Mines - избегай мин

🎁 Ежедневный бонус: /bonus
👥 Пригласи друга: /referral
        """
        if referrer_id:
            welcome_text += f"\n🎉 Вы зарегистрированы по реферальной ссылке!"
    else:
        welcome_text = f"""
🎰 <b>С ВОЗВРАЩЕНИЕМ!</b>

💰 Баланс: <b>{format_number(user['balance'])} 💰</b>
⭐ Уровень: {user['level']}
        """
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль")
async def cmd_profile(message: Message):
    """Показать профиль пользователя"""
    user = await db.get_user_stats(message.from_user.id)
    
    if not user:
        await message.answer("❌ Пользователь не найден. Используйте /start")
        return
    
    level, current_xp, next_xp, progress = calculate_level_progress(user['xp'])
    win_rate = get_win_rate(user['total_wins'], user['total_losses'])
    
    # Прогресс-бар уровня
    bar_length = 10
    filled = int(progress / 10)
    progress_bar = "█" * filled + "░" * (bar_length - filled)
    
    profile_text = f"""
👤 <b>ПРОФИЛЬ ИГРОКА</b>
━━━━━━━━━━━━━━━━━━
🆔 ID: <code>{message.from_user.id}</code>
👤 Username: @{user['username'] or 'Нет'}

💰 Баланс: <b>{format_number(user['balance'])} 💰</b>
📥 Пополнено: {format_number(user['total_deposited'])} 💰
📤 Выведено: {format_number(user['total_withdrawn'])} 💰

⭐ Уровень: {level} [{progress_bar}] {progress:.0f}%
✨ Опыт: {current_xp}/{next_xp}

🎮 Статистика игр:
• Всего игр: {user['games_played']}
• Побед: {user['total_wins']}
• Поражений: {user['total_losses']}
• Винрейт: {win_rate}%
• Лучший выигрыш: {format_number(user['best_win'])} 💰

👥 Рефералов: {len(await db.get_referrals(message.from_user.id))}
💰 Реферальный бонус: {format_number(user['referral_bonus'])} 💰

📅 Дата регистрации: {user['created_at'][:10]}
    """
    
    await message.answer(
        profile_text,
        reply_markup=get_profile_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("balance"))
@router.message(F.text == "💰 Баланс")
async def cmd_balance(message: Message):
    """Показать баланс"""
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ Используйте /start для регистрации")
        return
    
    await message.answer(
        f"💰 <b>ВАШ БАЛАНС</b>\n\n"
        f"💎 <b>{format_number(user['balance'])} 💰</b>\n\n"
        f"Используйте /profile для полной статистики",
        parse_mode="HTML"
    )


@router.message(Command("bonus"))
@router.message(F.text == "🎁 Бонус")
async def cmd_daily_bonus(message: Message):
    """Получить ежедневный бонус"""
    bonus = await db.claim_daily_bonus(message.from_user.id)
    
    if bonus:
        user = await db.get_user(message.from_user.id)
        await message.answer(
            f"🎁 <b>ЕЖЕДНЕВНЫЙ БОНУС!</b>\n\n"
            f"+{format_number(bonus)} 💰\n"
            f"💰 Баланс: <b>{format_number(user['balance'])} 💰</b>\n\n"
            f"Приходите завтра за новым бонусом!",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "⏰ <b>БОНУС УЖЕ ПОЛУЧЕН!</b>\n\n"
            "Приходите завтра за новым бонусом 🎁",
            parse_mode="HTML"
        )


@router.message(Command("referral"))
async def cmd_referral(message: Message):
    """Показать реферальную информацию"""
    bot_info = await message.bot.get_me()
    ref_link = generate_referral_link(bot_info.username, message.from_user.id)
    referrals = await db.get_referrals(message.from_user.id)
    user = await db.get_user(message.from_user.id)
    
    referrals_text = ""
    if referrals:
        referrals_text = "\n<b>Ваши рефералы:</b>\n"
        for i, ref in enumerate(referrals[:10], 1):
            referrals_text += f"{i}. @{ref['username'] or 'Unknown'} - {format_number(ref['balance'])} 💰\n"
    
    text = f"""
👥 <b>РЕФЕРАЛЬНАЯ ПРОГРАММА</b>
━━━━━━━━━━━━━━━━━━

🔗 Ваша ссылка:
<code>{ref_link}</code>

💰 Бонус за друга: 100 💰
📊 Процент от ставок: 5%

👤 Приглашено: {len(referrals)}
💎 Заработано: {format_number(user['referral_bonus'])} 💰
{referrals_text}

📤 Отправьте ссылку друзьям!
    """
    
    await message.answer(text, parse_mode="HTML")


@router.message(Command("top"))
async def cmd_top(message: Message):
    """Показать топ игроков"""
    top_players = await db.get_top_players(10)
    
    if not top_players:
        await message.answer("🏆 Топ игроков пока пуст")
        return    
    medals = ['🥇', '🥈', '🥉'] + ['👤'] * 7
    text = "🏆 <b>ТОП-10 ИГРОКОВ</b>\n━━━━━━━━━━━━━━━━━━\n"
    
    for i, player in enumerate(top_players, 1):
        username = player['username'] or f"ID:{player['user_id']}"
        text += f"{medals[i-1]} {i}. {username[:15]} - {format_number(player['balance'])} 💰 (Ур.{player['level']})\n"
    
    await message.answer(text, parse_mode="HTML")


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message):
    """Показать справку"""
    help_text = """
❓ <b>ПОМОЩЬ ПО БОТУ</b>
━━━━━━━━━━━━━━━━━━

<b>📋 Основные команды:</b>
/start - регистрация
/profile - ваш профиль
/balance - проверить баланс
/bonus - ежедневный бонус
/referral - пригласить друга
/top - топ игроков

<b>🎮 Игры:</b>
🎲 Dice - угадай число от 1 до 6
📈 Crash - поймай множитель
💣 Mines - открой безопасные ячейки

<b>💰 Финансы:</b>
• Стартовый баланс: 1000 💰
• Мин. ставка: 100 💰
• Бонус за друга: 100 💰

<b>📞 Поддержка:</b> @admin
    """
    await message.answer(help_text, parse_mode="HTML")


# Обработчики callback-запросов меню
@router.callback_query(F.data == "menu_back")
async def back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "🎰 <b>ГЛАВНОЕ МЕНЮ</b>\n\nВыберите действие:",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "menu_profile")
async def menu_profile(callback: CallbackQuery):
    """Показать профиль через меню"""
    user = await db.get_user_stats(callback.from_user.id)
    if user:
        await cmd_profile(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu_balance")
async def menu_balance(callback: CallbackQuery):
    """Показать баланс через меню"""
    await cmd_balance(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu_bonus")
async def menu_bonus(callback: CallbackQuery):
    """Получить бонус через меню"""
    await cmd_daily_bonus(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu_referrals")
async def menu_referrals(callback: CallbackQuery):
    """Показать рефералов через меню"""
    await cmd_referral(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu_top")
async def menu_top(callback: CallbackQuery):
    """Показать топ через меню"""
    await cmd_top(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu_help")
async def menu_help(callback: CallbackQuery):
    """Показать помощь через меню"""
    await cmd_help(callback.message)
    await callback.answer()