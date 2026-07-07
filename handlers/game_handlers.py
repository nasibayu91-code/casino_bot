# handlers/game_handlers.py
"""АРХИТЕКТУРА БЕЗ СПАМА: ОДНО СООБЩЕНИЕ + ЗАЩИТА ОТ ДВОЙНЫХ КЛИКОВ"""

import asyncio
import random
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import DiceEmoji
from database import db

router = Router()

# ==================== СИСТЕМА ЗАЩИТЫ ОТ СПАМ-КЛИКОВ ====================
# Хранит время последнего действия пользователя
# Ключ: user_id, Значение: timestamp последнего запроса
_user_cooldowns: dict[int, float] = {}

# Минимальный интервал между запросами (в секундах)
COOLDOWN_SECONDS = 2.0

def is_on_cooldown(user_id: int) -> bool:
    """
    Проверяет, не слишком ли быстро пользователь нажимает кнопки.
    Возвращает True, если нужно заблокировать запрос (кулдаун не прошёл).
    Возвращает False, если запрос можно обработать.
    """
    now = time.time()
    last_request = _user_cooldowns.get(user_id, 0)
    
    if now - last_request < COOLDOWN_SECONDS:
        return True  # Ещё не прошло 2 секунды — блокируем
    
    _user_cooldowns[user_id] = now
    return False


# ==================== ИГРОВОЕ ХРАНИЛИЩЕ ====================
# Хранит состояние активных игр (Crash, Mines)
game_sessions: dict[str, dict] = {}


# ==================== ЭМОДЗИ И СИМВОЛЫ ====================
DICE = {1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅'}
SLOTS = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣', '🌟']


# ==================== ГЛАВНОЕ МЕНЮ ====================
def main_menu_keyboard():
    """Создаёт клавиатуру главного меню (всегда одна и та же структура)"""
    b = InlineKeyboardBuilder()
    b.button(text="🎲 Кубик", callback_data="g_dice")
    b.button(text="🎰 Слоты", callback_data="g_slots")
    b.button(text="🎡 Рулетка", callback_data="g_roul")
    b.button(text="📈 Crash", callback_data="g_crash")
    b.button(text="💣 Mines", callback_data="g_mines")
    b.button(text="👤 Профиль", callback_data="g_profile")
    b.button(text="🏆 Топ", callback_data="g_top")
    b.adjust(2, 2, 2, 1)
    return b.as_markup()


@router.message(F.text == "🎮 Игры")
async def show_games(msg: Message):
    """
    Первый вход в игры — создаём ОДНО сообщение с меню.
    Все последующие действия будут редактировать ЭТО же сообщение.
    """
    await msg.answer(
        "🎰 <b>ИГРОВОЙ ЗАЛ</b>\n\nВыберите игру:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "menu_games")
async def back_to_games(cb: CallbackQuery):
    """
    Возврат в главное меню — РЕДАКТИРУЕМ текущее сообщение.
    Никаких новых сообщений! Чат остаётся чистым.
    """
    await cb.message.edit_text(
        "🎰 <b>ИГРОВОЙ ЗАЛ</b>\n\nВыберите игру:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await cb.answer()


# ==================== УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК С ЗАЩИТОЙ ====================
async def safe_edit(cb: CallbackQuery, text: str, reply_markup=None):
    """
    Безопасное редактирование сообщения с защитой от ошибок.
    Если сообщение нельзя отредактировать — отправляет новое.
    """
    try:
        await cb.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        # Если редактирование не удалось — отправляем новое сообщение
        await cb.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")


# ==================== ПРОФИЛЬ ====================
@router.callback_query(F.data == "g_profile")
async def show_profile(cb: CallbackQuery):
    """Профиль игрока — всё в одном сообщении через edit_text"""
    if is_on_cooldown(cb.from_user.id):
        await cb.answer("⏳ Подождите пару секунд!", show_alert=True)
        return

    user = await db.get_user(cb.from_user.id)
    if not user:
        await cb.answer("❌ Зарегистрируйтесь: /start", show_alert=True)
        return

    total = user.get('games_played', 0)
    wins = user.get('total_wins', 0)
    losses = user.get('total_losses', 0)
    winrate = round((wins / total * 100), 1) if total > 0 else 0

    text = f"""
👤 <b>ПРОФИЛЬ ИГРОКА</b>
━━━━━━━━━━━━━━━━━━
🆔 ID: <code>{cb.from_user.id}</code>
💰 Баланс: <b>{user['balance']:,} 💰</b>
⭐ Уровень: {user.get('level', 1)}
✨ Опыт: {user.get('xp', 0)}

📊 <b>Статистика:</b>
🎮 Всего игр: {total}
🏆 Побед: {wins} ({winrate}%)
💀 Поражений: {losses}
💎 Лучший выигрыш: {user.get('best_win', 0):,} 💰
📅 С нами с: {user.get('created_at', 'Н/Д')[:10]}
"""
    b = InlineKeyboardBuilder()
    b.button(text="🔙 Назад", callback_data="menu_games")
    b.adjust(1)

    await safe_edit(cb, text, b.as_markup())
    await cb.answer()


# ==================== ТОП ИГРОКОВ ====================
@router.callback_query(F.data == "g_top")
async def show_top(cb: CallbackQuery):
    """Топ-10 игроков — редактируем сообщение"""
    if is_on_cooldown(cb.from_user.id):
        await cb.answer("⏳ Подождите пару секунд!", show_alert=True)
        return

    top = await db.get_top_players(10)
    medals = ['🥇', '🥈', '🥉'] + ['👤'] * 7
    text = "🏆 <b>ТОП-10 ИГРОКОВ</b>\n━━━━━━━━━━━━━━━━━━\n"

    for i, player in enumerate(top, 1):
        name = player.get('username', f"ID:{player['user_id']}")[:12]
        text += f"{medals[i-1]} {i}. {name} — {player['balance']:,} 💰\n"

    b = InlineKeyboardBuilder()
    b.button(text="🔙 Назад", callback_data="menu_games")
    b.adjust(1)

    await safe_edit(cb, text, b.as_markup())
    await cb.answer()


# ==================== КУБИК (DICE) — ПРИМЕР ИДЕАЛЬНОГО ОБРАБОТЧИКА ====================
@router.callback_query(F.data == "g_dice")
async def dice_menu(cb: CallbackQuery):
    """
    Меню кубика.
    ВАЖНО: is_on_cooldown в начале каждого обработчика!
    """
    if is_on_cooldown(cb.from_user.id):
        await cb.answer("⏳ Подождите пару секунд!", show_alert=True)
        return

    user = await db.get_user(cb.from_user.id)
    b = InlineKeyboardBuilder()
    for i in range(1, 7):
        b.button(text=f"{DICE[i]} {i}", callback_data=f"dice_{i}")
    b.button(text="⚖️ ЧЁТ", callback_data="dice_even")
    b.button(text="⚖️ НЕЧЕТ", callback_data="dice_odd")
    b.button(text="📈 >3", callback_data="dice_high")
    b.button(text="📉 <4", callback_data="dice_low")
    b.button(text="🔙 Назад", callback_data="menu_games")
    b.adjust(3, 2, 2, 1)

    await safe_edit(
        cb,
        f"🎲 <b>КУБИК</b>\n\n"
        f"💰 Баланс: {user['balance']:,} 💰\n"
        f"💵 Ставка: 100 💰\n\n"
        f"Выберите число или режим:",
        b.as_markup()
    )
    await cb.answer()


@router.callback_query(F.data.startswith("dice_"))
async def dice_play(cb: CallbackQuery):
    """
    Игра в кубик.
    1. Проверка кулдауна
    2. Проверка баланса
    3. Списание ставки
    4. Анимация кубика
    5. Расчёт результата
    6. Обновление БД
    7. Редактирование сообщения
    """
    if is_on_cooldown(cb.from_user.id):
        await cb.answer("⏳ Слишком быстро! Подождите.", show_alert=True)
        return

    user = await db.get_user(cb.from_user.id)
    if user['balance'] < 100:
        await cb.answer("❌ Недостаточно средств! Минимум 100 💰", show_alert=True)
        return

    # Списание ставки
    await db.add_balance(cb.from_user.id, -100)

    # Анимация кубика
    dice_msg = await cb.message.answer_dice(emoji=DiceEmoji.DICE)
    await asyncio.sleep(4.2)

    value = dice_msg.dice.value
    action = cb.data.split("_")[1]

    # Определение результата
    won, mult = False, 0
    if action.isdigit():
        won, mult = (value == int(action)), 5.8
    elif action == "even":
        won, mult = (value % 2 == 0), 1.9
    elif action == "odd":
        won, mult = (value % 2 == 1), 1.9
    elif action == "high":
        won, mult = (value > 3), 1.9
    elif action == "low":
        won, mult = (value < 4), 1.9

    profit = int(100 * mult) if won else -100
    if won:
        await db.add_balance(cb.from_user.id, int(100 * mult))

    await db.update_game_stats(cb.from_user.id, won, 100, abs(profit))
    user = await db.get_user(cb.from_user.id)

    emoji = "🎉" if won else "💀"
    result_text = "ПОБЕДА!" if won else "ПРОИГРЫШ"

    text = f"""
{emoji} <b>{result_text}</b>
━━━━━━━━━━━━━━━━━━
🎲 Выпало: {DICE[value]} <b>{value}</b>
💰 {'+'+str(profit) if won else profit} 💰
💎 Баланс: <b>{user['balance']:,} 💰</b>
"""
    b = InlineKeyboardBuilder()
    b.button(text="🔄 Бросить ещё", callback_data="g_dice")
    b.button(text="🏠 В меню", callback_data="menu_games")
    b.adjust(1)

    await dice_msg.delete()
    await safe_edit(cb, text, b.as_markup())
    await cb.answer(f"{emoji} {result_text}")


# ==================== СЛОТЫ (SLOTS) ====================
@router.callback_query(F.data == "g_slots")
async def slots_play(cb: CallbackQuery):
    """Слоты: анимация + результат — всё в одном сообщении"""
    if is_on_cooldown(cb.from_user.id):
        await cb.answer("⏳ Подождите пару секунд!", show_alert=True)
        return

    user = await db.get_user(cb.from_user.id)
    if user['balance'] < 100:
        await cb.answer("❌ Недостаточно средств!", show_alert=True)
        return

    await db.add_balance(cb.from_user.id, -100)

    # Анимация вращения
    status_msg = await cb.message.answer("🎰 Крутим барабаны...")
    for _ in range(3):
        temp = [random.choice(SLOTS) for _ in range(3)]
        await status_msg.edit_text(f"🎰 {' | '.join(temp)}\n⏳ Крутим...")
        await asyncio.sleep(0.4)

    final = [random.choice(SLOTS) for _ in range(3)]

    if final[0] == final[1] == final[2]:
        won, mult, bonus = True, 10 if '💎' in final else 5, "💎 ДЖЕКПОТ x10!" if '💎' in final else "🎉 ТРИ В РЯД x5!"
    elif len(set(final)) == 2:
        won, mult, bonus = True, 2, "✨ ДВА СОВПАДЕНИЯ x2!"
    else:
        won, mult, bonus = False, 0, "💀 МИМО"

    profit = int(100 * mult) if won else -100
    if won:
        await db.add_balance(cb.from_user.id, int(100 * mult))

    await db.update_game_stats(cb.from_user.id, won, 100, abs(profit))
    user = await db.get_user(cb.from_user.id)
    await status_msg.delete()

    text = f"""
🎰 <b>СЛОТЫ</b>
━━━━━━━━━━━━━━━━━━
╔══════════════╗
║  {' | '.join(final)}  ║
╚══════════════╝

{bonus}
💰 {'+'+str(profit) if won else profit} 💰
💎 Баланс: <b>{user['balance']:,} 💰</b>
"""
    b = InlineKeyboardBuilder()
    b.button(text="🔄 Крутить ещё", callback_data="g_slots")
    b.button(text="🏠 В меню", callback_data="menu_games")
    b.adjust(1)

    await safe_edit(cb, text, b.as_markup())
    await cb.answer()


# ==================== РУЛЕТКА (ROULETTE) ====================
@router.callback_query(F.data == "g_roul")
async def roulette_menu(cb: CallbackQuery):
    """Меню рулетки"""
    if is_on_cooldown(cb.from_user.id):
        await cb.answer("⏳ Подождите пару секунд!", show_alert=True)
        return

    user = await db.get_user(cb.from_user.id)
    b = InlineKeyboardBuilder()
    b.button(text="🔴 Красное (x2)", callback_data="roul_red")
    b.button(text="⚫ Чёрное (x2)", callback_data="roul_black")
    b.button(text="🟢 Зеро (x35)", callback_data="roul_green")
    b.button(text="🔙 Назад", callback_data="menu_games")
    b.adjust(2, 1)

    await safe_edit(
        cb,
        f"🎡 <b>РУЛЕТКА</b>\n\n💰 Баланс: {user['balance']:,} 💰\n💵 Ставка: 100 💰\n\nВыберите ставку:",
        b.as_markup()
    )
    await cb.answer()


@router.callback_query(F.data.startswith("roul_"))
async def roulette_play(cb: CallbackQuery):
    """Игра в рулетку"""
    if is_on_cooldown(cb.from_user.id):
        await cb.answer("⏳ Подождите!", show_alert=True)
        return

    user = await db.get_user(cb.from_user.id)
    if user['balance'] < 100:
        await cb.answer("❌ Недостаточно средств!", show_alert=True)
        return

    await db.add_balance(cb.from_user.id, -100)

    dart = await cb.message.answer_dice(emoji='🎯')
    await asyncio.sleep(4)

    number = random.randint(0, 36)
    red = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
    color = '🔴' if number in red else '⚫'
    if number == 0:
        color = '🟢'

    action = cb.data.split("_")[1]
    won, mult = False, 0

    if action == "red" and color == '🔴':
        won, mult = True, 2
    elif action == "black" and color == '⚫':
        won, mult = True, 2
    elif action == "green" and number == 0:
        won, mult = True, 35

    profit = int(100 * mult) if won else -100
    if won:
        await db.add_balance(cb.from_user.id, int(100 * mult))

    await db.update_game_stats(cb.from_user.id, won, 100, abs(profit))
    user = await db.get_user(cb.from_user.id)
    await dart.delete()

    text = f"""
🎡 <b>РУЛЕТКА</b>
━━━━━━━━━━━━━━━━━━
Выпало: <b>{number} {color}</b>
💰 {'+'+str(profit) if won else profit} 💰
💎 Баланс: <b>{user['balance']:,} 💰</b>
"""
    b = InlineKeyboardBuilder()
    b.button(text="🔄 Крутить ещё", callback_data="g_roul")
    b.button(text="🏠 В меню", callback_data="menu_games")
    b.adjust(1)

    await safe_edit(cb, text, b.as_markup())
    await cb.answer()


# ==================== CRASH ====================
@router.callback_query(F.data == "g_crash")
async def crash_start(cb: CallbackQuery):
    """Crash: запуск игры"""
    if is_on_cooldown(cb.from_user.id):
        await cb.answer("⏳ Подождите!", show_alert=True)
        return

    user = await db.get_user(cb.from_user.id)
    if user['balance'] < 100:
        await cb.answer("❌ Недостаточно средств!", show_alert=True)
        return

    await db.add_balance(cb.from_user.id, -100)

    crash_point = round(random.uniform(1.2, 10), 1)
    if random.random() < 0.08:
        crash_point = 1.0

    game_sessions[str(cb.from_user.id)] = {"crash": crash_point, "mult": 1.0, "bet": 100}

    b = InlineKeyboardBuilder()
    b.button(text="💰 ЗАБРАТЬ", callback_data="crash_cash")

    await safe_edit(
        cb,
        f"📈 <b>CRASH</b>\n\nМножитель: x1.0\n💰 Потенциал: 100 💰\n\nНажмите кнопку чтобы забрать!",
        b.as_markup()
    )
    await cb.answer()

    asyncio.create_task(crash_animation(cb.message, cb.from_user.id))


async def crash_animation(msg, user_id):
    """Анимация роста множителя"""
    await asyncio.sleep(0.5)

    for _ in range(40):
        if str(user_id) not in game_sessions:
            break

        session = game_sessions[str(user_id)]
        session["mult"] = round(session["mult"] + 0.2, 1)

        if session["mult"] >= session["crash"]:
            await db.update_game_stats(user_id, False, 100, 100)
            user = await db.get_user(user_id)
            del game_sessions[str(user_id)]

            b = InlineKeyboardBuilder()
            b.button(text="🔄 Играть снова", callback_data="g_crash")
            b.button(text="🏠 В меню", callback_data="menu_games")

            await msg.edit_text(
                f"💥 <b>КРАШ на x{session['crash']}!</b>\n\n-100 💰\n💎 Баланс: {user['balance']:,} 💰",
                reply_markup=b.as_markup(),
                parse_mode="HTML"
            )
            return

        b = InlineKeyboardBuilder()
        b.button(text=f"💰 ЗАБРАТЬ x{session['mult']}", callback_data="crash_cash")

        try:
            await msg.edit_text(
                f"📈 <b>CRASH</b>\n\nМножитель: <b>x{session['mult']}</b>\n💰 Потенциал: {int(100*session['mult'])} 💰",
                reply_markup=b.as_markup(),
                parse_mode="HTML"
            )
        except:
            pass

        await asyncio.sleep(0.5)


@router.callback_query(F.data == "crash_cash")
async def crash_cashout(cb: CallbackQuery):
    """Забрать выигрыш в Crash"""
    if str(cb.from_user.id) not in game_sessions:
        await cb.answer("❌ Игра завершена!", show_alert=True)
        return

    session = game_sessions.pop(str(cb.from_user.id))
    mult = session["mult"]
    winnings = int(100 * mult)

    await db.add_balance(cb.from_user.id, winnings)
    await db.update_game_stats(cb.from_user.id, True, 100, winnings)
    user = await db.get_user(cb.from_user.id)

    b = InlineKeyboardBuilder()
    b.button(text="🔄 Играть снова", callback_data="g_crash")
    b.button(text="🏠 В меню", callback_data="menu_games")

    await safe_edit(
        cb,
        f"🎉 <b>ВЫИГРЫШ!</b>\n\nМножитель: x{mult}\nВыигрыш: +{winnings} 💰\n💎 Баланс: {user['balance']:,} 💰",
        b.as_markup()
    )
    await cb.answer(f"🎉 +{winnings} 💰")


# ==================== MINES ====================
@router.callback_query(F.data == "g_mines")
async def mines_start(cb: CallbackQuery):
    """Mines: создание поля 5x5"""
    if is_on_cooldown(cb.from_user.id):
        await cb.answer("⏳ Подождите пару секунд!", show_alert=True)
        return

    user = await db.get_user(cb.from_user.id)
    if user['balance'] < 150:
        await cb.answer("❌ Недостаточно средств!", show_alert=True)
        return

    await db.add_balance(cb.from_user.id, -150)

    board = ['💣'] * 3 + ['💎'] * 22
    random.shuffle(board)

    game_sessions[str(cb.from_user.id)] = {
        "board": board,
        "opened": [],
        "bet": 150,
        "mult": 1.0
    }

    await show_mines_board(cb.message, cb.from_user.id)
    await cb.answer()


async def show_mines_board(msg, user_id):
    """Отображение сетки Mines 5x5"""
    s = game_sessions.get(str(user_id))
    if not s:
        return

    display = ""
    for i in range(0, 25, 5):
        for j in range(5):
            idx = i + j
            display += s["board"][idx] if idx in s["opened"] else "⬜"
        display += "\n"

    b = InlineKeyboardBuilder()
    for i in range(25):
        label = "✅" if i in s["opened"] else str(i + 1)
        cb_data = f"mine_{i}" if i not in s["opened"] else "mine_noop"
        b.button(text=label, callback_data=cb_data)
    b.button(text="💰 ЗАБРАТЬ", callback_data="mine_cash")
    b.button(text="🏠 В меню", callback_data="menu_games")
    b.adjust(5, 5, 5, 5, 5, 1, 1)

    await msg.edit_text(
        f"💣 <b>MINES</b>\n\n{display}\nМножитель: x{s['mult']:.1f}\n💰 Потенциал: {int(s['bet']*s['mult'])} 💰",
        reply_markup=b.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("mine_"))
async def mines_open(cb: CallbackQuery):
    """Открытие ячейки в Mines"""
    cell = int(cb.data.split("_")[1])
    s = game_sessions.get(str(cb.from_user.id))

    if not s or cell in s["opened"]:
        await cb.answer("❌", show_alert=True)
        return

    s["opened"].append(cell)

    if s["board"][cell] == '💣':
        await db.update_game_stats(cb.from_user.id, False, s["bet"], s["bet"])
        user = await db.get_user(cb.from_user.id)
        del game_sessions[str(cb.from_user.id)]

        display = ""
        for i in range(0, 25, 5):
            for j in range(5):
                display += s["board"][i + j] + " "
            display += "\n"

        b = InlineKeyboardBuilder()
        b.button(text="🔄 Играть снова", callback_data="g_mines")
        b.button(text="🏠 В меню", callback_data="menu_games")

        await safe_edit(
            cb,
            f"💥 <b>МИНА!</b>\n\n{display}\n-{s['bet']} 💰\n💎 Баланс: {user['balance']:,} 💰",
            b.as_markup()
        )
        await cb.answer("💥")
        return

    s["mult"] = round(1 + len(s["opened"]) * 0.3, 1)
    await show_mines_board(cb.message, cb.from_user.id)
    await cb.answer("✅")


@router.callback_query(F.data == "mine_cash")
async def mines_cash(cb: CallbackQuery):
    """Забрать выигрыш в Mines"""
    s = game_sessions.get(str(cb.from_user.id))

    if not s or not s["opened"]:
        await cb.answer("❌ Откройте хотя бы 1 ячейку!", show_alert=True)
        return

    bet = s["bet"]
    mult = s["mult"]
    winnings = int(bet * mult)

    await db.add_balance(cb.from_user.id, winnings)
    await db.update_game_stats(cb.from_user.id, True, bet, winnings)
    del game_sessions[str(cb.from_user.id)]

    user = await db.get_user(cb.from_user.id)

    b = InlineKeyboardBuilder()
    b.button(text="🔄 Играть снова", callback_data="g_mines")
    b.button(text="🏠 В меню"
    callback_data="menu_games")

    await safe_edit(
        cb,
        f"🎉 <b>ВЫИГРЫШ!</b>\n\nОткрыто ячеек: {len(s['opened'])}\nМножитель: x{mult:.1f}\n+{winnings} 💰\n💎 Баланс: {user['balance']:,} 💰",
        b.as_markup()
    )
    await cb.answer(f"🎉 +{winnings} 💰")


@router.callback_query(F.data == "mine_noop")
async def mine_noop(cb: CallbackQuery):
    await cb.answer("❌ Уже открыта!", show_alert=True)
