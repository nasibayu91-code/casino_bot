# database.py
import aiosqlite
import random
from datetime import datetime
from config import DB_NAME, START_BALANCE

class Database:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    async def init_db(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA busy_timeout=5000")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance INTEGER DEFAULT 1000,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0,
                    total_wins INTEGER DEFAULT 0,
                    total_losses INTEGER DEFAULT 0,
                    best_win INTEGER DEFAULT 0,
                    referrer_id INTEGER,
                    referral_bonus INTEGER DEFAULT 0,
                    daily_bonus_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_banned INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS game_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    game_type TEXT,
                    bet INTEGER,
                    result TEXT,
                    profit INTEGER,
                    multiplier REAL,
                    played_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT,
                    amount INTEGER,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def get_user(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def register_user(self, user_id, username="", referrer_id=None):
        user = await self.get_user(user_id)
        if user:
            return False
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "INSERT INTO users (user_id, username, balance, referrer_id, created_at) VALUES (?,?,?,?,?)",
                (user_id, username, START_BALANCE, referrer_id, datetime.now().isoformat())
            )
            await db.commit()
        return True

    async def add_balance(self, user_id, amount):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    async def update_game_stats(self, user_id, won, bet, profit):
        async with aiosqlite.connect(self.db_name) as db:
            if won:
                await db.execute(
                    """UPDATE users SET games_played = games_played + 1,
                       total_wins = total_wins + 1,
                       xp = xp + ?,
                       best_win = MAX(best_win, ?)
                       WHERE user_id = ?""",
                    (bet // 10, profit, user_id)
                )
            else:
                await db.execute(
                    """UPDATE users SET games_played = games_played + 1,
                       total_losses = total_losses + 1,
                       xp = xp + ?
                       WHERE user_id = ?""",
                    (bet // 20, user_id)
                )
            await db.commit()

    async def add_game_history(self, user_id, game_type, bet, result, profit, multiplier):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "INSERT INTO game_history (user_id, game_type, bet, result, profit, multiplier, played_at) VALUES (?,?,?,?,?,?,?)",
                (user_id, game_type, bet, result, profit, multiplier, datetime.now().isoformat())
            )
            await db.commit()

    async def claim_daily(self, user_id):
        user = await self.get_user(user_id)
        today = datetime.now().strftime("%Y-%m-%d")
        if user and user.get('daily_bonus_date') != today:
            bonus = random.randint(50, 200)
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    "UPDATE users SET balance = balance + ?, daily_bonus_date = ? WHERE user_id = ?",
                    (bonus, today, user_id)
                )
                await db.commit()
            return bonus
        return None

    async def get_top_players(self, limit=10):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id, username, balance, level FROM users WHERE is_banned=0 ORDER BY balance DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in await cursor.fetchall()]

    # ---------- НОВЫЕ МЕТОДЫ ----------
    async def get_game_history(self, user_id, limit=5):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM game_history WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            )
            return [dict(row) for row in await cursor.fetchall()]

    async def get_referrals(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id, username, balance FROM users WHERE referrer_id=?",
                (user_id,)
            )
            return [dict(row) for row in await cursor.fetchall()]
