# handlers/game_handlers.py
"""Обработчики игр - РАБОЧАЯ ВЕРСИЯ ДЛЯ RENDER"""

import asyncio
import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import DiceEmoji

from database import db
from utils.helpers import format_number

router = Router()

DICE_EMOJIS = {1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅'}
SLOTS = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣', '🌟']


def menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎲 Кубик", callback_data="game_dice")
    builder.button(text="🎰 Слоты", callback_data="game_slots")
    builder.button(text="🎡 Рулетка", callback_data="game_roulette")
    builder.button(text="📈 Crash", callback_data="game_crash")
    builder.button(text="💣 Mines", callback_data="game_mines")
    builder.adjust(2)
    return builder.as_markup()


# ==================== МЕНЮ ====================
@router.message(F.text == "🎮 Игры")
@router.callback_query(F.data == "menu_games")
async def show_games(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        await event.message.answer("🎮 <b>ВЫБЕРИТЕ ИГРУ:</b>", reply_markup=menu_keyboard(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer("🎮 <b>ВЫБЕРИТЕ ИГРУ:</b>", reply_markup=menu_keyboard(), parse_mode="HTML")


# ==================== КУБИК ====================
@router.callback_query(F.data == "game_dice")
async def dice_menu(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎯 Угадать число (x5.8)", callback_data="dice_mode_guess")
    builder.button(text="⚖️ Чёт/Нечет (x1.9)", callback_data="dice_mode_evenodd")
    builder.button(text="📊 Больше/Меньше (x1.9)", callback_data="dice_mode_hilo")
    builder.button(text="🔙 Назад", callback_data="menu_games")
    builder.adjust(1)
    
    await callback.message.answer("🎲 <b>ВЫБЕРИТЕ РЕЖИМ:</b>", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "dice_mode_guess")
async def dice_guess_menu(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    for i in range(1, 7):
        builder.button(text=f"{DICE_EMOJIS[i]} {i}", callback_data=f"dice_guess_{i}")
    builder.button(text="🔙 Назад", callback_data="game_dice")
    builder.adjust(3, 3, 1)
    await callback.message.answer("🎯 Выберите число (100💰, x5.8):", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "dice_mode_evenodd")
async def dice_evenodd_menu(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="⚖️ ЧЁТНОЕ", callback_data="dice_evenodd_even")
    builder.button(text="⚖️ НЕЧЁТНОЕ", callback_data="dice_evenodd_odd")
    builder.button(text="🔙 Назад", callback_data="game_dice")
    builder.adjust(2, 1)
    await callback.message.answer("⚖️ Чёт или Нечет? (100💰, x1.9):", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "dice_mode_hilo")
async def dice_hilo_menu(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="📈 БОЛЬШЕ 3", callback_data="dice_hilo_high")
    builder.button(text="📉 МЕНЬШЕ 4", callback_data="dice_hilo_low")
    builder.button(text="🔙 Назад", callback_data="game_dice")
    builder.adjust(2, 1)
    await callback.message.answer("📊 Больше или Меньше? (100💰, x1.9):", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("dice_guess_"))
async def dice_guess_play(callback: CallbackQuery):
    choice = int(callback.data.split("_")[2])
    bet = 100
    user = await db.get_user(callback.from_user.id)
    
    if user['balance'] < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    await db.add_balance(callback.from_user.id, -bet)
    dice_msg = await callback.message.answer_dice(emoji=DiceEmoji.DICE)
    await asyncio.sleep(4.2)
    
    dice_value = dice_msg.dice.value
    won = (dice_value == choice)
    multiplier = 5.8 if won else 0
    
    if won:
        winnings = int(bet * multiplier)
        await db.add_balance(callback.from_user.id, winnings)
        profit = winnings
    else:
        profit = -bet
    
    await db.update_game_stats(callback.from_user.id, won, bet, abs(profit))
    user = await db.get_user(callback.from_user.id)
    
    text = f"{'🎉 ПОБЕДА!' if won else '💀 ПРОИГРЫШ'}\n🎲 {DICE_EMOJIS[dice_value]} {dice_value}\n💰 {'+'+str(profit) if won else profit} 💰\n💎 Баланс: {user['balance']} 💰"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Ещё", callback_data="game_dice")
    builder.adjust(1)
    
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("dice_evenodd_"))
async def dice_evenodd_play(callback: CallbackQuery):
    choice = callback.data.split("_")[2]
    bet = 100
    user = await db.get_user(callback.from_user.id)
    
    if user['balance'] < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    await db.add_balance(callback.from_user.id, -bet)
    dice_msg = await callback.message.answer_dice(emoji=DiceEmoji.DICE)
    await asyncio.sleep(4.2)
    
    dice_value = dice_msg.dice.value
    is_even = dice_value % 2 == 0
    won = (choice == "even" and is_even) or (choice == "odd" and not is_even)
    multiplier = 1.9 if won else 0
    
    profit = int(bet * multiplier) if won else -bet
    if won:
        await db.add_balance(callback.from_user.id, int(bet * multiplier))
    
    await db.update_game_stats(callback.from_user.id, won, bet, abs(profit))
    user = await db.get_user(callback.from_user.id)
    
    text = f"{'🎉' if won else '💀'} Выпало: {DICE_EMOJIS[dice_value]} {dice_value} ({'Чёт' if is_even else 'Нечет'})\n💰 {'+'+str(profit) if won else profit} 💰\n💎 Баланс: {user['balance']} 💰"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Ещё", callback_data="game_dice")
    builder.adjust(1)
    
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("dice_hilo_"))
async def dice_hilo_play(callback: CallbackQuery):
    choice = callback.data.split("_")[2]
    bet = 100
    user = await db.get_user(callback.from_user.id)
    
    if user['balance'] < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    await db.add_balance(callback.from_user.id, -bet)
    dice_msg = await callback.message.answer_dice(emoji=DiceEmoji.DICE)
    await asyncio.sleep(4.2)
    
    dice_value = dice_msg.dice.value
    won = (choice == "high" and dice_value > 3) or (choice == "low" and dice_value < 4)
    multiplier = 1.9 if won else 0
    
    profit = int(bet * multiplier) if won else -bet
    if won:
        await db.add_balance(callback.from_user.id, int(bet * multiplier))
    
    await db.update_game_stats(callback.from_user.id, won, bet, abs(profit))
    user = await db.get_user(callback.from_user.id)
    
    text = f"{'🎉' if won else '💀'} Выпало: {DICE_EMOJIS[dice_value]} {dice_value}\n💰 {'+'+str(profit) if won else profit} 💰\n💎 Баланс: {user['balance']} 💰"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Ещё", callback_data="game_dice")
    builder.adjust(1)
    
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# ==================== СЛОТЫ (РАБОЧИЕ) ====================
@router.callback_query(F.data == "game_slots")
async def slots_start(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🎰 100 💰", callback_data="slots_100")
    builder.button(text="🎰 500 💰", callback_data="slots_500")
    builder.button(text="💎 1000 💰", callback_data="slots_1000")
    builder.button(text="🔙 Назад", callback_data="menu_games")
    builder.adjust(3, 1)
    
    await callback.message.answer(
        f"🎰 <b>СЛОТЫ</b>\n💰 Баланс: {user['balance']} 💰\n\nВыберите ставку:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("slots_"))
async def slots_spin(callback: CallbackQuery):
    bet = int(callback.data.split("_")[1])
    user = await db.get_user(callback.from_user.id)
    
    if user['balance'] < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    await db.add_balance(callback.from_user.id, -bet)
    
    # Анимация: 3 сообщения
    for i in range(3):
        temp = [random.choice(SLOTS) for _ in range(3)]
        msg = await callback.message.answer(f"🎰 {' | '.join(temp)} ⏳")
        await asyncio.sleep(0.5)
        await msg.delete()
    
    # Результат
    final = [random.choice(SLOTS) for _ in range(3)]
    
    if final[0] == final[1] == final[2]:
        if '💎' in final:
            won, mult, bonus = True, 50, "💎 ДЖЕКПОТ x50!"
        elif '7️⃣' in final:
            won, mult, bonus = True, 10, "7️⃣ x10!"
        else:
            won, mult, bonus = True, 5, "🎉 x5!"
    elif len(set(final)) == 2:
        won, mult, bonus = True, 2, "✨ x2!"
    else:
        won, mult, bonus = False, 0, "💀 Мимо"
    
    profit = int(bet * mult) if won else -bet
    if won:
        await db.add_balance(callback.from_user.id, int(bet * mult))
    
    await db.update_game_stats(callback.from_user.id, won, bet, abs(profit))
    user = await db.get_user(callback.from_user.id)
    
    text = f"🎰 {' | '.join(final)}\n{bonus}\n💰 {'+'+str(profit) if won else profit} 💰\n💎 Баланс: {user['balance']} 💰"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Ещё", callback_data="game_slots")
    builder.adjust(1)
    
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# ==================== РУЛЕТКА ====================
@router.callback_query(F.data == "game_roulette")
async def roulette_start(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔴 Красное (x2)", callback_data="roul_red")
    builder.button(text="⚫ Чёрное (x2)", callback_data="roul_black")
    builder.button(text="🟢 Зеро (x35)", callback_data="roul_green")
    builder.button(text="🔙 Назад", callback_data="menu_games")
    builder.adjust(2, 2)
    
    await callback.message.answer("🎡 <b>РУЛЕТКА</b>\n💰 100 💰\n\nВыберите цвет:", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("roul_"))
async def roulette_spin(callback: CallbackQuery):
    choice = callback.data.split("_")[1]
    bet = 100
    user = await db.get_user(callback.from_user.id)
    
    if user['balance'] < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    await db.add_balance(callback.from_user.id, -bet)
    
    dart = await callback.message.answer_dice(emoji='🎯')
    await asyncio.sleep(4)
    
    number = random.randint(0, 36)
    red = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
    color = '🔴' if number in red else '⚫'
    if number == 0: color = '🟢'
    
    won = False
    mult = 0
    if choice == 'red' and color == '🔴': won, mult = True, 2
    elif choice == 'black' and color == '⚫': won, mult = True, 2
    elif choice == 'green' and number == 0: won, mult = True, 35
    
    profit = int(bet * mult) if won else -bet
    if won:
        await db.add_balance(callback.from_user.id, int(bet * mult))
    
    await db.update_game_stats(callback.from_user.id, won, bet, abs(profit))
    user = await db.get_user(callback.from_user.id)
    
    text = f"🎡 {number} {color}\n{'🎉 +'+str(profit) if won else '💀 '+str(profit)} 💰\n💎 Баланс: {user['balance']} 💰"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Ещё", callback_data="game_roulette")
    builder.adjust(1)
    
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# ==================== CRASH ====================
@router.callback_query(F.data == "game_crash")
async def crash_start(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    bet = 100
    
    if user['balance'] < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    await db.add_balance(callback.from_user.id, -bet)
    
    crash_point = round(random.uniform(1.5, 10.0), 1)
    if random.random() < 0.08:
        crash_point = 1.0
    
    # Сохраняем в БД через сессию
    db.data["sessions"][str(callback.from_user.id)] = {
        "crash_point": crash_point,
        "current": 1.0,
        "bet": bet
    }
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 ЗАБРАТЬ", callback_data="crash_cashout")
    builder.adjust(1)
    
    msg = await callback.message.answer("📈 Запуск...", reply_markup=builder.as_markup())
    await callback.answer()
    
    # Анимация
    for i in range(30):
        await asyncio.sleep(0.5)
        session = db.data["sessions"].get(str(callback.from_user.id))
        if not session:
            break
        
        session["current"] += 0.2
        session["current"] = round(session["current"], 1)
        
        if session["current"] >= crash_point:
            await db.update_game_stats(callback.from_user.id, False, bet, bet)
            user = await db.get_user(callback.from_user.id)
            del db.data["sessions"][str(callback.from_user.id)]
            
            await msg.edit_text(f"💥 КРАШ x{crash_point}!\n-{bet} 💰\n💎 {user['balance']} 💰")
            return
        
        try:
            await msg.edit_text(
                f"📈 x{session['current']} | 💰 {int(bet*session['current'])} 💰\nКнопка внизу ⬇️",
                reply_markup=builder.as_markup()
            )
        except:
            pass


@router.callback_query(F.data == "crash_cashout")
async def crash_cashout(callback: CallbackQuery):
    session = db.data["sessions"].get(str(callback.from_user.id))
    
    if not session:
        await callback.answer("❌ Нет активной игры!", show_alert=True)
        return
    
    bet = session["bet"]
    mult = session["current"]
    winnings = int(bet * mult)
    
    await db.add_balance(callback.from_user.id, winnings)
    await db.update_game_stats(callback.from_user.id, True, bet, winnings)
    del db.data["sessions"][str(callback.from_user.id)]
    
    user = await db.get_user(callback.from_user.id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Ещё", callback_data="game_crash")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"🎉 ВЫИГРЫШ x{mult}!\n+{winnings} 💰\n💎 {user['balance']} 💰",
        reply_markup=builder.as_markup()
    )
    await callback.answer(f"🎉 +{winnings} 💰")


# ==================== MINES ====================

@router.callback_query(F.data == "game_mines")
async def mines_start(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    bet = 150
    
    if user['balance'] < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    await db.add_balance(callback.from_user.id, -bet)
    
    # Создаем поле: 3 мины, остальные алмазы
    board = ['💣'] * 3 + ['💎'] * 22
    random.shuffle(board)
    
    db.data["sessions"][str(callback.from_user.id)] = {
        "board": board,
        "opened": [],
        "bet": bet,
        "mult": 1.0
    }
    
    # Отправляем сообщение
    msg = await callback.message.answer("💣 Инициализация игры...")
    await show_mines(msg, callback.from_user.id)
    await callback.answer()

async def show_mines(message: Message, user_id: int):
    session = db.data["sessions"].get(str(user_id))
    if not session:
        return
    
    board = session["board"]
    opened = session["opened"]
    mult = session["mult"]
    bet = session["bet"]
    
    display = ""
    for i in range(0, 25, 5):
        for j in range(5):
            idx = i + j
            display += "⬜ " if idx not in opened else ("💣 " if board[idx] == '💣' else "💎 ")
        display += "\n"
    
    builder = InlineKeyboardBuilder()
    for i in range(25):
        if i in opened:
            builder.button(text="✅", callback_data="mine_done")
        else:
            builder.button(text=str(i+1), callback_data=f"mine_{i}")
    
    builder.button(text="💰 ЗАБРАТЬ", callback_data="mine_cash")
    builder.adjust(5, 5, 5, 5, 5, 1)
    
    await message.edit_text(
        f"💣 <b>MINES</b>\n\n{display}\n📈 Множитель: x{mult:.1f}\n💰 Текущий выигрыш: {int(bet*mult)} 💰",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("mine_"))
async def mines_open(callback: CallbackQuery):
    cell = int(callback.data.split("_")[1])
    session = db.data["sessions"].get(str(callback.from_user.id))
    
    if not session:
        await callback.answer("Игра не найдена!", show_alert=True)
        return
    
    if cell in session["opened"]:
        await callback.answer("Уже открыто")
        return
    
    session["opened"].append(cell)
    
    # Если попал на мину
    if session["board"][cell] == '💣':
        user = await db.get_user(callback.from_user.id)
        await db.update_game_stats(callback.from_user.id, False, session["bet"], session["bet"])
        del db.data["sessions"][str(callback.from_user.id)]
        
        # Показываем полное поле
        display = ""
        for i in range(0, 25, 5):
            for j in range(5):
                display += session["board"][i+j] + " "
            display += "\n"
            
        await callback.message.edit_text(f"💥 МИНА!\n\n{display}\n\n-{session['bet']} 💰\n💎 Баланс: {user['balance']} 💰")
        await callback.answer("💥")
        return
    
    # Если чисто
    session["mult"] = round(1 + len(session["opened"]) * 0.3, 1)
    await show_mines(callback.message, callback.from_user.id)
    await callback.answer("✅")

@router.callback_query(F.data == "mine_cash")
async def mines_cash(callback: CallbackQuery):
    session = db.data["sessions"].get(str(callback.from_user.id))
    
    if not session or not session["opened"]:
        await callback.answer("Сначала сделай ход!", show_alert=True)
        return
    
    bet = session["bet"]
    mult = session["mult"]
    winnings = int(bet * mult)
    
    await db.add_balance(callback.from_user.id, winnings)
    await db.update_game_stats(callback.from_user.id, True, bet, winnings)
    del db.data["sessions"][str(callback.from_user.id)]
    
    user = await db.get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"🎉 <b>ВЫИГРЫШ!</b>\n\nВы забрали: {winnings} 💰 (x{mult})\n💎 Баланс: {user['balance']} 💰",
        parse_mode="HTML"
    )
    await callback.answer(f"🎉 +{winnings} 💰")

@router.callback_query(F.data == "mine_done")
async def mine_done(callback: CallbackQuery):
    await callback.answer("Уже открыто!")
