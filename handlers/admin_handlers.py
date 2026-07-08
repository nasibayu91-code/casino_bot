# handlers/admin_handlers.py
"""Обработчики для администраторов"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_IDS
from database import db
from utils.helpers import format_number

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка на администратора"""
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin_panel(message: Message):
    """Админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    stats = await db.get_total_stats()
    
    text = f"""
🛡️ <b>АДМИН-ПАНЕЛЬ</b>
━━━━━━━━━━━━━━━━━━

📊 <b>Общая статистика:</b>
• Пользователей: {stats['total_users']}
• Всего игр: {format_number(stats['total_games'])}
• Общий оборот: {format_number(stats['total_wagered'])} 💰

<b>Команды:</b>
/give [user_id] [amount] - выдать 💰
/take [user_id] [amount] - снять 💰
/ban [user_id] - заблокировать
/unban [user_id] - разблокировать
    """
    await message.answer(text, parse_mode="HTML")


@router.message(Command("give"))
async def cmd_give_coins(message: Message):
    """Выдать монеты пользователю"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        user_id = int(args[1])
        amount = int(args[2])
        
        new_balance = await db.add_balance(user_id, amount)
        await db.add_transaction(user_id, "admin_give", amount, f"Выдано администратором {message.from_user.id}")
        
        await message.answer(
            f"✅ Выдано {format_number(amount)} 💰 пользователю {user_id}\n"
            f"💰 Новый баланс: {format_number(new_balance)} 💰"
        )
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /give [user_id] [amount]")


@router.message(Command("take"))
async def cmd_take_coins(message: Message):
    """Снять монеты у пользователя"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        user_id = int(args[1])
        amount = int(args[2])
        
        new_balance = await db.add_balance(user_id, -amount)
        await db.add_transaction(user_id, "admin_take", amount, f"Снято администратором {message.from_user.id}")
        
        await message.answer(
            f"✅ Снято {format_number(amount)} 💰 у пользователя {user_id}\n"
            f"💰 Новый баланс: {format_number(new_balance)} 💰"
        )
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /take [user_id] [amount]")


@router.message(Command("ban"))
async def cmd_ban_user(message: Message):
    """Заблокировать пользователя"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id = int(message.text.split()[1])
        await db._execute(
            "UPDATE users SET is_banned = 1 WHERE user_id = ?",
            (user_id,)
        )
        await message.answer(f"✅ Пользователь {user_id} заблокирован")
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /ban [user_id]")


@router.message(Command("unban"))
async def cmd_unban_user(message: Message):
    """Разблокировать пользователя"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id = int(message.text.split()[1])
        await db._execute(
            "UPDATE users SET is_banned = 0 WHERE user_id = ?",
            (user_id,)
        )
        await message.answer(f"✅ Пользователь {user_id} разблокирован")
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /unban [user_id]")
