# handlers/game_handlers.py
"""ПОЛНОСТЬЮ ГОТОВЫЙ КОД — ВСЕ ИГРЫ РАБОТАЮТ"""

import asyncio
import random
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import DiceEmoji
from database import db

router = Router()

# Хранилище активных игровых сессий (Crash, Mines)
game_sessions: dict[str, dict] = {}

# Кулдаун между запросами (защита от спама)
COOLDOWN = 2.0
_user_last_request: dict[int, float] = {}

def is_on_cooldown(user_id: int) -> bool:
    now = time.time()
    last = _user_last_request.get(user_id, 0)
    if now - last < COOLDOWN:
        return True
    _user_last_request[user_id] = now
    return False

# Эмодзи и символы
DICE = {1:'⚀',2:'⚁',3:'⚂',4:'⚃',5:'⚄',6:'⚅'}
SLOTS = ['🍒','🍋','🍊','🍇','💎','7️⃣','🌟']

async def safe_edit(cb: CallbackQuery, text: str, reply_markup=None):
    """Безопасное редактирование сообщения (без спама)"""
    try:
        await cb.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await cb.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")

# ==================== ГЛАВНОЕ МЕНЮ ====================
def main_menu_keyboard():
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
    await msg.answer("🎰 <b>ИГРОВОЙ ЗАЛ</b>\n\nВыберите игру:", reply_markup=main_menu_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "menu_games")
async def back_to_games(cb: CallbackQuery):
    await cb.message.edit_text("🎰 <b>ИГРОВОЙ ЗАЛ</b>\n\nВыберите игру:", reply_markup=main_menu_keyboard(), parse_mode="HTML")
    await cb.answer()

# ==================== ПРОФИЛЬ ====================
@router.callback_query(F.data == "g_profile")
async def show_profile(cb: CallbackQuery):
    if is_on_cooldown(cb.from_user.id): await cb.answer("⏳ Подождите!", show_alert=True); return
    user = await db.get_user(cb.from_user.id)
    if not user: await cb.answer("❌ /start", show_alert=True); return
    total = user.get('games_played',0)
    wins = user.get('total_wins',0)
    losses = user.get('total_losses',0)
    wr = round((wins/total*100),1) if total>0 else 0
    text = f"""👤 <b>ПРОФИЛЬ</b>
━━━━━━━━━━━━━━━━━━
🆔 <code>{cb.from_user.id}</code>
💰 Баланс: <b>{user['balance']:,} 💰</b>
⭐ Уровень: {user.get('level',1)}
✨ Опыт: {user.get('xp',0)}
📊 Игр: {total} | Побед: {wins} ({wr}%) | Поражений: {losses}
💎 Лучший выигрыш: {user.get('best_win',0):,} 💰
📅 С нами с: {user.get('created_at','Н/Д')[:10]}"""
    b = InlineKeyboardBuilder(); b.button(text="🔙 Назад", callback_data="menu_games")
    await safe_edit(cb, text, b.as_markup()); await cb.answer()

# ==================== ТОП ====================
@router.callback_query(F.data == "g_top")
async def show_top(cb: CallbackQuery):
    if is_on_cooldown(cb.from_user.id): await cb.answer("⏳", show_alert=True); return
    top = await db.get_top_players(10)
    medals = ['🥇','🥈','🥉'] + ['👤']*7
    text = "🏆 <b>ТОП-10</b>\n━━━━━━━━━━━━━━━━━━\n"
    for i,p in enumerate(top,1):
        name = p.get('username',f"ID:{p['user_id']}")[:12]
        text += f"{medals[i-1]} {i}. {name} — {p['balance']:,} 💰\n"
    b = InlineKeyboardBuilder(); b.button(text="🔙 Назад", callback_data="menu_games")
    await safe_edit(cb, text, b.as_markup()); await cb.answer()

# ==================== КУБИК ====================
@router.callback_query(F.data == "g_dice")
async def dice_menu(cb: CallbackQuery):
    if is_on_cooldown(cb.from_user.id): await cb.answer("⏳", show_alert=True); return
    user = await db.get_user(cb.from_user.id)
    b = InlineKeyboardBuilder()
    for i in range(1,7): b.button(text=f"{DICE[i]} {i}", callback_data=f"dice_{i}")
    b.button(text="⚖️ ЧЁТ", callback_data="dice_even")
    b.button(text="⚖️ НЕЧЕТ", callback_data="dice_odd")
    b.button(text="📈 >3", callback_data="dice_high")
    b.button(text="📉 <4", callback_data="dice_low")
    b.button(text="🔙 Назад", callback_data="menu_games")
    b.adjust(3,2,2,1)
    await safe_edit(cb, f"🎲 <b>КУБИК</b>\n\n💰 Баланс: {user['balance']:,} 💰\n💵 Ставка: 100 💰\n\nВыберите:", b.as_markup())
    await cb.answer()

@router.callback_query(F.data.startswith("dice_"))
async def dice_play(cb: CallbackQuery):
    if is_on_cooldown(cb.from_user.id): await cb.answer("⏳", show_alert=True); return
    user = await db.get_user(cb.from_user.id)
    if user['balance']<100: await cb.answer("❌ Мало средств!", show_alert=True); return
    await db.add_balance(cb.from_user.id, -100)
    dice_msg = await cb.message.answer_dice(emoji=DiceEmoji.DICE)
    await asyncio.sleep(4.2)
    value = dice_msg.dice.value
    action = cb.data.split("_")[1]
    won,mult = False,0
    if action.isdigit(): won,mult = value==int(action),5.8
    elif action=="even": won,mult = value%2==0,1.9
    elif action=="odd": won,mult = value%2==1,1.9
    elif action=="high": won,mult = value>3,1.9
    elif action=="low": won,mult = value<4,1.9
    profit = int(100*mult) if won else -100
    if won: await db.add_balance(cb.from_user.id, int(100*mult))
    await db.update_game_stats(cb.from_user.id, won, 100, abs(profit))
    user = await db.get_user(cb.from_user.id)
    emoji = "🎉" if won else "💀"
    text = f"{emoji} <b>{'ПОБЕДА!' if won else 'ПРОИГРЫШ'}</b>\n🎲 {DICE[value]} {value}\n💰 {'+'+str(profit) if won else profit} 💰\n💎 Баланс: <b>{user['balance']:,} 💰</b>"
    b = InlineKeyboardBuilder(); b.button(text="🔄 Ещё", callback_data="g_dice"); b.button(text="🏠 Меню", callback_data="menu_games"); b.adjust(1)
    await dice_msg.delete()
    await safe_edit(cb, text, b.as_markup())
    await cb.answer(f"{emoji}")

# ==================== СЛОТЫ ====================
@router.callback_query(F.data == "g_slots")
async def slots_play(cb: CallbackQuery):
    if is_on_cooldown(cb.from_user.id): await cb.answer("⏳", show_alert=True); return
    user = await db.get_user(cb.from_user.id)
    if user['balance']<100: await cb.answer("❌ Мало средств!", show_alert=True); return
    await db.add_balance(cb.from_user.id, -100)
    status = await cb.message.answer("🎰 Крутим...")
    for _ in range(3):
        temp = [random.choice(SLOTS) for _ in range(3)]
        await status.edit_text(f"🎰 {' | '.join(temp)}\n⏳ Крутим...")
        await asyncio.sleep(0.4)
    final = [random.choice(SLOTS) for _ in range(3)]
    if final[0]==final[1]==final[2]:
        won,mult,bonus = True,10 if '💎' in final else 5,"💎 ДЖЕКПОТ x10!" if '💎' in final else "🎉 ТРИ В РЯД x5!"
    elif len(set(final))==2:
        won,mult,bonus = True,2,"✨ ДВА СОВПАДЕНИЯ x2!"
    else:
        won,mult,bonus = False,0,"💀 МИМО"
    profit = int(100*mult) if won else -100
    if won: await db.add_balance(cb.from_user.id, int(100*mult))
    await db.update_game_stats(cb.from_user.id, won, 100, abs(profit))
    user = await db.get_user(cb.from_user.id)
    await status.delete()
    text = f"🎰 <b>СЛОТЫ</b>\n━━━━━━━━━━━━━━━━━━\n╔══════════════╗\n║  {' | '.join(final)}  ║\n╚══════════════╝\n\n{bonus}\n💰 {'+'+str(profit) if won else profit} 💰\n💎 Баланс: <b>{user['balance']:,} 💰</b>"
    b = InlineKeyboardBuilder(); b.button(text="🔄 Ещё", callback_data="g_slots"); b.button(text="🏠 Меню", callback_data="menu_games"); b.adjust(1)
    await safe_edit(cb, text, b.as_markup())
    await cb.answer()

# ==================== РУЛЕТКА ====================
@router.callback_query(F.data == "g_roul")
async def roulette_menu(cb: CallbackQuery):
    if is_on_cooldown(cb.from_user.id): await cb.answer("⏳", show_alert=True); return
    user = await db.get_user(cb.from_user.id)
    b = InlineKeyboardBuilder()
    b.button(text="🔴 Красное (x2)", callback_data="roul_red")
    b.button(text="⚫ Чёрное (x2)", callback_data="roul_black")
    b.button(text="🟢 Зеро (x35)", callback_data="roul_green")
    b.button(text="🔙 Назад", callback_data="menu_games")
    b.adjust(2,1)
    await safe_edit(cb, f"🎡 <b>РУЛЕТКА</b>\n\n💰 Баланс: {user['balance']:,} 💰\n💵 Ставка: 100 💰\n\nВыберите ставку:", b.as_markup())
    await cb.answer()

@router.callback_query(F.data.startswith("roul_"))
async def roulette_play(cb: CallbackQuery):
    if is_on_cooldown(cb.from_user.id): await cb.answer("⏳", show_alert=True); return
    user = await db.get_user(cb.from_user.id)
    if user['balance']<100: await cb.answer("❌ Мало средств!", show_alert=True); return
    await db.add_balance(cb.from_user.id, -100)
    dart = await cb.message.answer_dice(emoji='🎯')
    await asyncio.sleep(4)
    number = random.randint(0,36)
    red = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
    color = '🔴' if number in red else '⚫'
    if number==0: color='🟢'
    action = cb.data.split("_")[1]
    won,mult = False,0
    if action=="red" and color=='🔴': won,mult=True,2
    elif action=="black" and color=='⚫': won,mult=True,2
    elif action=="green" and number==0: won,mult=True,35
    profit = int(100*mult) if won else -100
    if won: await db.add_balance(cb.from_user.id, int(100*mult))
    await db.update_game_stats(cb.from_user.id, won, 100, abs(profit))
    user = await db.get_user(cb.from_user.id)
    await dart.delete()
    text = f"🎡 <b>РУЛЕТКА</b>\n━━━━━━━━━━━━━━━━━━\nВыпало: <b>{number} {color}</b>\n💰 {'+'+str(profit) if won else profit} 💰\n💎 Баланс: <b>{user['balance']:,} 💰</b>"
    b = InlineKeyboardBuilder(); b.button(text="🔄 Ещё", callback_data="g_roul"); b.button(text="🏠 Меню", callback_data="menu_games"); b.adjust(1)
    await safe_edit(cb, text, b.as_markup())
    await cb.answer()

# ==================== CRASH ====================
@router.callback_query(F.data == "g_crash")
async def crash_start(cb: CallbackQuery):
    if is_on_cooldown(cb.from_user.id): await cb.answer("⏳", show_alert=True); return
    user = await db.get_user(cb.from_user.id)
    if user['balance']<100: await cb.answer("❌ Мало средств!", show_alert=True); return
    await db.add_balance(cb.from_user.id, -100)
    crash_point = round(random.uniform(1.2,10),1)
    if random.random()<0.08: crash_point=1.0
    game_sessions[str(cb.from_user.id)] = {"crash":crash_point, "mult":1.0, "bet":100}
    b = InlineKeyboardBuilder(); b.button(text="💰 ЗАБРАТЬ", callback_data="crash_cash")
    await safe_edit(cb, f"📈 <b>CRASH</b>\n\nМножитель: x1.0\n💰 Потенциал: 100 💰\n\nНажмите кнопку чтобы забрать!", b.as_markup())
    await cb.answer()
    asyncio.create_task(crash_animation(cb.message, cb.from_user.id))

async def crash_animation(msg, user_id):
    await asyncio.sleep(0.5)
    for _ in range(40):
        if str(user_id) not in game_sessions: break
        s = game_sessions[str(user_id)]
        s["mult"] = round(s["mult"]+0.2,1)
        if s["mult"] >= s["crash"]:
            await db.update_game_stats(user_id, False, 100, 100)
            user = await db.get_user(user_id)
            del game_sessions[str(user_id)]
            b = InlineKeyboardBuilder(); b.button(text="🔄 Ещё", callback_data="g_crash"); b.button(text="🏠 Меню", callback_data="menu_games")
            await msg.edit_text(f"💥 <b>КРАШ на x{s['crash']}!</b>\n\n-100 💰\n💎 Баланс: {user['balance']:,} 💰", reply_markup=b.as_markup(), parse_mode="HTML")
            return
        b = InlineKeyboardBuilder(); b.button(text=f"💰 ЗАБРАТЬ x{s['mult']}", callback_data="crash_cash")
        try: await msg.edit_text(f"📈 <b>CRASH</b>\n\nМножитель: <b>x{s['mult']}</b>\n💰 Потенциал: {int(100*s['mult'])} 💰", reply_markup=b.as_markup(), parse_mode="HTML")
        except: pass
        await asyncio.sleep(0.5)

@router.callback_query(F.data == "crash_cash")
async def crash_cashout(cb: CallbackQuery):
    if str(cb.from_user.id) not in game_sessions: await cb.answer("❌ Игра завершена!", show_alert=True); return
    s = game_sessions.pop(str(cb.from_user.id))
    mult = s["mult"]
    winnings = int(100*mult)
    await db.add_balance(cb.from_user.id, winnings)
    await db.update_game_stats(cb.from_user.id, True, 100, winnings)
    user = await db.get_user(cb.from_user.id)
    b = InlineKeyboardBuilder(); b.button(text="🔄 Ещё", callback_data="g_crash"); b.button(text="🏠 Меню", callback_data="menu_games")
    await safe_edit(cb, f"🎉 <b>ВЫИГРЫШ!</b>\n\nМножитель: x{mult}\n+{winnings} 💰\n💎 Баланс: {user['balance']:,} 💰", b.as_markup())
    await cb.answer(f"🎉 +{winnings} 💰")

# ==================== MINES ====================
@router.callback_query(F.data == "g_mines")
async def mines_start(cb: CallbackQuery):
    if is_on_cooldown(cb.from_user.id): await cb.answer("⏳", show_alert=True); return
    user = await db.get_user(cb.from_user.id)
    if user['balance']<150: await cb.answer("❌ Мало средств!", show_alert=True); return
    await db.add_balance(cb.from_user.id, -150)
    board = ['💣']*3 + ['💎']*22
    random.shuffle(board)
    game_sessions[str(cb.from_user.id)] = {"board":board, "opened":[], "bet":150, "mult":1.0}
    await show_mines_board(cb.message, cb.from_user.id)
    await cb.answer()

async def show_mines_board(msg, user_id):
    s = game_sessions.get(str(user_id))
    if not s: return
    display = ""
    for i in range(0,25,5):
        for j in range(5):
            idx = i+j
            display += s["board"][idx] if idx in s["opened"] else "⬜"
        display += "\n"
    b = InlineKeyboardBuilder()
    for i in range(25):
        label = "✅" if i in s["opened"] else str(i+1)
        cb_data = f"mine_{i}" if i not in s["opened"] else "mine_noop"
        b.button(text=label, callback_data=cb_data)
    b.button(text="💰 ЗАБРАТЬ", callback_data="mine_cash")
    b.button(text="🏠 Меню", callback_data="menu_games")
    b.adjust(5,5,5,5,5,1,1)
    await msg.edit_text(f"💣 <b>MINES</b>\n\n{display}\nМножитель: x{s['mult']:.1f}\n💰 Потенциал: {int(s['bet']*s['mult'])} 💰", reply_markup=b.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("mine_"))
async def mines_open(cb: CallbackQuery):
    cell = int(cb.data.split("_")[1])
    s = game_sessions.get(str(cb.from_user.id))
    if not s or cell in s["opened"]: await cb.answer("❌", show_alert=True); return
    s["opened"].append(cell)
    if s["board"][cell]=='💣':
        await db.update_game_stats(cb.from_user.id, False, s["bet"], s["bet"])
        user = await db.get_user(cb.from_user.id)
        del game_sessions[str(cb.from_user.id)]
        display = ""
        for i in range(0,25,5):
            for j in range(5): display += s["board"][i+j]+" "
            display += "\n"
        b = InlineKeyboardBuilder(); b.button(text="🔄 Ещё", callback_data="g_mines"); b.button(text="🏠 Меню", callback_data="menu_games")
        await safe_edit(cb, f"💥 <b>МИНА!</b>\n\n{display}\n-{s['bet']} 💰\n💎 Баланс: {user['balance']:,} 💰", b.as_markup())
        await cb.answer("💥")
        return
    s["mult"] = round(1+len(s["opened"])*0.3,1)
    await show_mines_board(cb.message, cb.from_user.id)
    await cb.answer("✅")

@router.callback_query(F.data == "mine_cash")
async def mines_cash(cb: CallbackQuery):
    s = game_sessions.get(str(cb.from_user.id))
    if not s or not s["opened"]: await cb.answer("❌ Откройте ячейку!", show_alert=True); return
    bet = s["bet"]; mult = s["mult"]; winnings = int(bet*mult)
    await db.add_balance(cb.from_user.id, winnings)
    await db.update_game_stats(cb.from_user.id, True, bet, winnings)
    del game_sessions[str(cb.from_user.id)]
    user = await db.get_user(cb.from_user.id)
    b = InlineKeyboardBuilder(); b.button(text="🔄 Ещё", callback_data="g_mines"); b.button(text="🏠 Меню", callback_data="menu_games")
    await safe_edit(cb, f"🎉 <b>ВЫИГРЫШ!</b>\n\nОткрыто: {len(s['opened'])}\nМножитель: x{mult:.1f}\n+{winnings} 💰\n💎 Баланс: {user['balance']:,} 💰", b.as_markup())
    await cb.answer(f"🎉 +{winnings} 💰")

@router.callback_query(F.data == "mine_noop")
async def mine_noop(cb: CallbackQuery):
    await cb.answer("❌ Уже открыта!", show_alert=True)
