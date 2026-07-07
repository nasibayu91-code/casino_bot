# handlers/game_handlers.py
"""Полноценные игры с анимациями и правильной логикой"""

import asyncio
import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import DiceEmoji

from database import db
from utils.helpers import format_number, validate_bet

router = Router()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
SLOT_SYMBOLS = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣', '🌟']
DICE_EMOJIS = {1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅'}


def get_main_menu_keyboard():
    """Главное меню игр"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎲 Dice", callback_data="game_dice")
    builder.button(text="🎰 Слоты", callback_data="game_slots")
    builder.button(text="📈 Crash", callback_data="game_crash")
    builder.button(text="💣 Mines", callback_data="game_mines")
    builder.button(text="🎡 Рулетка", callback_data="game_roulette")
    builder.adjust(2)
    return builder.as_markup()


# ==================== ГЛАВНОЕ МЕНЮ ИГР ====================
@router.message(F.text == "🎮 Игры")
@router.callback_query(F.data == "menu_games")
async def show_games(event: Message | CallbackQuery):
    """Показать меню игр"""
    text = """
🎮 <b>ИГРОВОЙ ЗАЛ</b>
━━━━━━━━━━━━━━━━━━
🎲 <b>Dice</b> — бросай кубик
🎰 <b>Слоты</b> — крути барабаны
📈 <b>Crash</b> — лови множитель
💣 <b>Mines</b> — ищи алмазы
🎡 <b>Рулетка</b> — ставь на цвет

Выберите игру:
    """
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")


# ==================== DICE (КУБИК) ====================
@router.callback_query(F.data == "game_dice")
async def dice_menu(callback: CallbackQuery):
    """Меню выбора режима Dice"""
    user = await db.get_user(callback.from_user.id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🎯 Угадать число (x5.8)", callback_data="dice_guess")
    builder.button(text="⚖️ Чёт/Нечет (x1.9)", callback_data="dice_evenodd")
    builder.button(text="📊 Больше/Меньше (x1.9)", callback_data="dice_hilo")
    builder.button(text="🔙 Назад", callback_data="menu_games")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"🎲 <b>DICE</b>\n\n💰 Баланс: <b>{format_number(user['balance'])} 💰</b>\n\nВыберите режим:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "dice_guess")
async def dice_guess_menu(callback: CallbackQuery):
    """Выбор числа"""
    builder = InlineKeyboardBuilder()
    for i in range(1, 7):
        builder.button(text=f"{DICE_EMOJIS[i]} {i}", callback_data=f"dice_play_guess_{i}")
    builder.button(text="🔙 Назад", callback_data="game_dice")
    builder.adjust(3, 3, 1)
    
    await callback.message.edit_text(
        "🎯 Выберите число от 1 до 6:\n💰 Ставка: 100 💰 | x5.8",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "dice_evenodd")
async def dice_evenodd_menu(callback: CallbackQuery):
    """Чёт/Нечет"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚖️ ЧЁТНОЕ", callback_data="dice_play_evenodd_even")
    builder.button(text="⚖️ НЕЧЁТНОЕ", callback_data="dice_play_evenodd_odd")
    builder.button(text="🔙 Назад", callback_data="game_dice")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(
        "⚖️ Чёт или Нечет?\n💰 Ставка: 100 💰 | x1.9",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "dice_hilo")
async def dice_hilo_menu(callback: CallbackQuery):
    """Больше/Меньше"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📈 БОЛЬШЕ 3", callback_data="dice_play_hilo_high")
    builder.button(text="📉 МЕНЬШЕ 4", callback_data="dice_play_hilo_low")
    builder.button(text="🔙 Назад", callback_data="game_dice")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(
        "📊 Больше 3 или Меньше 4?\n💰 Ставка: 100 💰 | x1.9",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dice_play_"))
async def dice_play(callback: CallbackQuery):
    """Игра в кости"""
    parts = callback.data.split("_")
    mode = parts[2]  # guess, evenodd, hilo
    choice = parts[3] if len(parts) > 3 else None
    
    bet = 100
    user = await db.get_user(callback.from_user.id)
    
    if user['balance'] < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    # Списываем ставку
    await db.add_balance(callback.from_user.id, -bet)
    
    # 🎲 Бросаем анимированный кубик
    dice_msg = await callback.message.answer_dice(emoji=DiceEmoji.DICE)
    await asyncio.sleep(4.2)  # Ждём окончания анимации
    
    dice_value = dice_msg.dice.value
    
    # Определяем победу
    won = False
    multiplier = 0
    
    if mode == "guess":
        won = (dice_value == int(choice))
        multiplier = 5.8 if won else 0
        choice_text = f"Число {DICE_EMOJIS[int(choice)]} {choice}"
    elif mode == "evenodd":
        is_even = dice_value % 2 == 0
        won = (choice == "even" and is_even) or (choice == "odd" and not is_even)
        multiplier = 1.9 if won else 0
        choice_text = "ЧЁТНОЕ" if choice == "even" else "НЕЧЁТНОЕ"
    elif mode == "hilo":
        won = (choice == "high" and dice_value > 3) or (choice == "low" and dice_value < 4)
        multiplier = 1.9 if won else 0
        choice_text = "БОЛЬШЕ 3" if choice == "high" else "МЕНЬШЕ 4"
    
    # Начисляем выигрыш
    if won:
        winnings = int(bet * multiplier)
        await db.add_balance(callback.from_user.id, winnings)
        profit = winnings
    else:
        profit = -bet
    
    await db.update_game_stats(callback.from_user.id, won, bet, abs(profit))
    user = await db.get_user(callback.from_user.id)
    
    # Результат
    emoji = "🎉" if won else "💀"
    result_line = f"+{format_number(profit)} 💰" if won else f"{format_number(profit)} 💰"
    
    text = f"""
{emoji} <b>DICE</b>
━━━━━━━━━━━━━━
🎲 Выпало: {DICE_EMOJIS[dice_value]} <b>{dice_value}</b>
🎯 Ставка: {choice_text}
💰 {result_line} (x{multiplier})

💎 Баланс: <b>{format_number(user['balance'])} 💰</b>
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Играть ещё", callback_data="game_dice")
    builder.button(text="🎮 Все игры", callback_data="menu_games")
    builder.adjust(2)
    
    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# ==================== СЛОТЫ (РАБОЧАЯ ВЕРСИЯ ДЛЯ ANDROID) ====================
@router.callback_query(F.data == "game_slots")
async def slots_start(callback: CallbackQuery):
    """Запуск слотов"""
    user = await db.get_user(callback.from_user.id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🎰 100 💰", callback_data="slots_spin_100")
    builder.button(text="🎰 500 💰", callback_data="slots_spin_500")
    builder.button(text="💎 1000 💰", callback_data="slots_spin_1000")
    builder.button(text="🔙 Назад", callback_data="menu_games")
    builder.adjust(3, 1)
    
    await callback.message.edit_text(
        f"🎰 <b>СЛОТЫ</b>\n\n"
        f"💰 Баланс: <b>{format_number(user['balance'])} 💰</b>\n\n"
        f"🍒 3 одинаковых = x5\n"
        f"💎 Джекпот = x50\n"
        f"✨ 2 одинаковых = x2",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("slots_spin_"))
async def slots_spin(callback: CallbackQuery):
    """Крутим слоты"""
    bet = int(callback.data.split("_")[2])
    user = await db.get_user(callback.from_user.id)
    
    if user['balance'] < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    await db.add_balance(callback.from_user.id, -bet)
    
    # Удаляем меню выбора ставки
    await callback.message.delete()
    
    # Отправляем первое сообщение
    symbols = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣', '🌟']
    
    # Анимация: 4 кадра через новые сообщения
    msgs = []
    for i in range(4):
        frame = [random.choice(symbols) for _ in range(3)]
        msg = await callback.message.answer(
            f"🎰 <b>КРУТИМ...</b>\n\n"
            f"╔══════════════╗\n"
            f"║  {' | '.join(frame)}  ║\n"
            f"╚══════════════╝\n\n"
            f"⏳ {'▓' * (i+1)}{'░' * (3-i)}",
            parse_mode="HTML"
        )
        msgs.append(msg)
        await asyncio.sleep(0.5)
    
    # Удаляем промежуточные сообщения
    for msg in msgs:
        await msg.delete()
    
    # Финальный результат
    final = [random.choice(symbols) for _ in range(3)]
    
    # Определяем выигрыш
    if final[0] == final[1] == final[2]:
        if '💎' in final:
            won, multiplier, bonus = True, 50, "💎 ДЖЕКПОТ x50!"
        elif '7️⃣' in final:
            won, multiplier, bonus = True, 10, "7️⃣ СЕМЁРКИ x10!"
        else:
            won, multiplier, bonus = True, 5, "🎉 ТРИ В РЯД x5!"
    elif len(set(final)) == 2:
        won, multiplier, bonus = True, 2, "✨ ДВА СОВПАДЕНИЯ x2!"
    else:
        won, multiplier, bonus = False, 0, "💀 МИМО"
    
    if won:
        winnings = int(bet * multiplier)
        await db.add_balance(callback.from_user.id, winnings)
        profit = winnings
    else:
        profit = -bet
    
    await db.update_game_stats(callback.from_user.id, won, bet, abs(profit))
    user = await db.get_user(callback.from_user.id)
    
    emoji = "🎉" if won else "😞"
    
    text = f"""
🎰 <b>СЛОТЫ</b>
━━━━━━━━━━━━━━━━━━
╔══════════════╗
║  {' | '.join(final)}  ║
╚══════════════╝

{bonus}
{emoji} <b>{'+'+format_number(profit) if won else format_number(profit)} 💰</b>

💎 Баланс: <b>{format_number(user['balance'])} 💰</b>
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Крутить ещё", callback_data="game_slots")
    builder.button(text="🎮 Все игры", callback_data="menu_games")
    builder.adjust(2)
    
    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# ==================== CRASH (РАБОЧИЙ) ====================
@router.callback_query(F.data == "game_crash")
async def crash_start(callback: CallbackQuery):
    """Запуск Crash"""
    user = await db.get_user(callback.from_user.id)
    bet = 100
    
    if user['balance'] < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    await db.add_balance(callback.from_user.id, -bet)
    
    # Генерируем точку краша
    crash_point = round(random.uniform(1.0, 15.0), 1)
    if random.random() < 0.05:
        crash_point = 1.0  # 5% шанс мгновенного краша
    
    # Сохраняем игру
    db.set_session(callback.from_user.id, {
        "type": "crash",
        "bet": bet,
        "crash_point": crash_point,
        "current": 1.0,
        "active": True
    })
    
    await show_crash_state(callback.message, callback.from_user.id)
    await callback.answer()
    
    # Запускаем анимацию
    asyncio.create_task(crash_animation(callback.from_user.id))


async def show_crash_state(message, user_id):
    """Показать текущее состояние Crash"""
    session = db.get_session(user_id)
    if not session or not session.get("active"):
        return
    
    multiplier = session["current"]
    bet = session["bet"]
    potential = int(bet * multiplier)
    
    # Прогресс-бар
    bar_len = 15
    filled = min(int(multiplier * 2), bar_len)
    bar = "🟢" * filled + "⬜" * (bar_len - filled)
    
    text = f"""
📈 <b>CRASH</b>
━━━━━━━━━━━━━━
Множитель: <b>x{multiplier:.1f}</b>
{bar}

💰 Ставка: {format_number(bet)} 💰
💵 Потенциал: {format_number(potential)} 💰

Нажмите кнопку чтобы забрать!
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💰 ЗАБРАТЬ x{multiplier:.1f}", callback_data="crash_cashout")
    builder.adjust(1)
    
    try:
        await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except:
        pass


async def crash_animation(user_id):
    """Анимация роста множителя"""
    await asyncio.sleep(0.5)
    
    for _ in range(100):
        session = db.get_session(user_id)
        if not session or not session.get("active"):
            break
        
        session["current"] += random.uniform(0.05, 0.2)
        session["current"] = round(session["current"], 1)
        
        if session["current"] >= session["crash_point"]:
            # КРАШ!
            session["active"] = False
            db.set_session(user_id, session)
            
            user = await db.get_user(user_id)
            await db.update_game_stats(user_id, False, session["bet"], 0)
            
            # Отправляем сообщение о краше
            from aiogram import Bot
            bot = Bot.get_current()
            
            text = f"""
💥 <b>КРАШ на x{session['crash_point']}!</b>
━━━━━━━━━━━━━━━━━━
Потеряно: -{format_number(session['bet'])} 💰
💎 Баланс: <b>{format_number(user['balance'])} 💰</b>
"""
            builder = InlineKeyboardBuilder()
            builder.button(text="🔄 Играть снова", callback_data="game_crash")
            builder.button(text="🎮 Все игры", callback_data="menu_games")
            builder.adjust(2)
            
            # Не можем отправить сообщение отсюда, просто очищаем сессию
            db.clear_session(user_id)
            break
        
        db.set_session(user_id, session)
        await asyncio.sleep(0.4)


@router.callback_query(F.data == "crash_cashout")
async def crash_cashout(callback: CallbackQuery):
    """Забрать выигрыш"""
    session = db.get_session(callback.from_user.id)
    
    if not session or not session.get("active"):
        await callback.answer("❌ Игра завершена!", show_alert=True)
        return
    
    session["active"] = False
    db.set_session(callback.from_user.id, session)
    
    bet = session["bet"]
    multiplier = session["current"]
    winnings = int(bet * multiplier)
    
    await db.add_balance(callback.from_user.id, winnings)
    await db.update_game_stats(callback.from_user.id, True, bet, winnings - bet)
    db.clear_session(callback.from_user.id)
    
    user = await db.get_user(callback.from_user.id)
    
    text = f"""
🎉 <b>УСПЕШНЫЙ ВЫХОД!</b>
━━━━━━━━━━━━━━━━━━
Множитель: <b>x{multiplier:.1f}</b>
Выигрыш: <b>+{format_number(winnings)} 💰</b>
Краш на: x{session['crash_point']}

💎 Баланс: <b>{format_number(user['balance'])} 💰</b>
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Играть снова", callback_data="game_crash")
    builder.button(text="🎮 Все игры", callback_data="menu_games")
    builder.adjust(2)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer(f"🎉 +{format_number(winnings)} 💰")


# ==================== MINES (РАБОЧИЙ) ====================
@router.callback_query(F.data == "game_mines")
async def mines_start(callback: CallbackQuery):
    """Запуск Mines"""
    user = await db.get_user(callback.from_user.id)
    bet = 150
    
    if user['balance'] < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    await db.add_balance(callback.from_user.id, -bet)
    
    # Создаём поле 5x5 с 3 минами
    mines_count = 3
    total = 25
    board = ['💣'] * mines_count + ['💎'] * (total - mines_count)
    random.shuffle(board)
    
    db.set_session(callback.from_user.id, {
        "type": "mines",
        "bet": bet,
        "board": board,
        "opened": [],
        "active": True,
        "multiplier": 1.0
    })
    
    await show_mines_board(callback.message, callback.from_user.id)
    await callback.answer()


async def show_mines_board(message, user_id):
    """Показать поле Mines"""
    session = db.get_session(user_id)
    if not session:
        return
    
    board = session["board"]
    opened = session["opened"]
    multiplier = session.get("multiplier", 1.0)
    bet = session["bet"]
    
    # Создаём отображение поля
    display = ""
    for i in range(0, 25, 5):
        row = ""
        for j in range(5):
            idx = i + j
            if idx in opened:
                row += board[idx] + " "
            else:
                row += "⬜ "
        display += row + "\n"
    
    potential = int(bet * multiplier)
    
    text = f"""
💣 <b>MINES</b>
━━━━━━━━━━━━━━
{display}
Множитель: <b>x{multiplier:.1f}</b>
Потенциал: <b>{format_number(potential)} 💰</b>

Выберите ячейку или заберите выигрыш:
"""
    
    # Кнопки для открытия ячеек
    builder = InlineKeyboardBuilder()
    for i in range(25):
        if i not in opened:
            builder.button(text=str(i+1), callback_data=f"mines_open_{i}")
    builder.button(text="💰 ЗАБРАТЬ", callback_data="mines_cashout")
    builder.adjust(5, 5, 5, 5, 5, 1)
    
    try:
        await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except:
        pass


@router.callback_query(F.data.startswith("mines_open_"))
async def mines_open_cell(callback: CallbackQuery):
    """Открыть ячейку"""
    cell = int(callback.data.split("_")[2])
    session = db.get_session(callback.from_user.id)
    
    if not session or not session.get("active"):
        await callback.answer("❌ Игра завершена!", show_alert=True)
        return
    
    if cell in session["opened"]:
        await callback.answer("❌ Уже открыта!", show_alert=True)
        return
    
    session["opened"].append(cell)
    
    if session["board"][cell] == '💣':
        # Попал на мину
        session["active"] = False
        db.set_session(callback.from_user.id, session)
        
        user = await db.get_user(callback.from_user.id)
        await db.update_game_stats(callback.from_user.id, False, session["bet"], 0)
        db.clear_session(callback.from_user.id)
        
        # Показываем всё поле
        board = session["board"]
        display = ""
        for i in range(0, 25, 5):
            row = ""
            for j in range(5):
                idx = i + j
                if idx in session["opened"] or session["board"][idx] == '💣':
                    row += session["board"][idx] + " "
                else:
                    row += "⬜ "
            display += row + "\n"
        
        text = f"""
💥 <b>МИНА!</b>
━━━━━━━━━━━━━━
{display}
Потеряно: -{format_number(session['bet'])} 💰
💎 Баланс: <b>{format_number(user['balance'])} 💰</b>
"""
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Играть снова", callback_data="game_mines")
        builder.button(text="🎮 Все игры", callback_data="menu_games")
        builder.adjust(2)
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await callback.answer("💥 Мина!")
        return
    
    # Открыта безопасная ячейка
    session["multiplier"] = round(1 + len(session["opened"]) * 0.3, 1)
    db.set_session(callback.from_user.id, session)
    
    await show_mines_board(callback.message, callback.from_user.id)
    await callback.answer("✅ Безопасно!")


@router.callback_query(F.data == "mines_cashout")
async def mines_cashout(callback: CallbackQuery):
    """Забрать выигрыш в Mines"""
    session = db.get_session(callback.from_user.id)
    
    if not session or not session.get("active"):
        await callback.answer("❌ Игра завершена!", show_alert=True)
        return
    
    if not session["opened"]:
        await callback.answer("❌ Откройте хотя бы 1 ячейку!", show_alert=True)
        return
    
    session["active"] = False
    bet = session["bet"]
    multiplier = session["multiplier"]
    winnings = int(bet * multiplier)
    
    await db.add_balance(callback.from_user.id, winnings)
    await db.update_game_stats(callback.from_user.id, True, bet, winnings - bet)