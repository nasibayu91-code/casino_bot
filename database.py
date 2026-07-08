# database.py
"""Асинхронная работа с базой данных SQLite"""

import aiosqlite
from datetime import datetime
from typing import Optional, Tuple, List
from config import DB_NAME, START_BALANCE


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name
        self._lock = None
    
    async def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        import asyncio
        self._lock = asyncio.Lock()
        
        async with aiosqlite.connect(self.db_name) as db:
            # Важно для многопоточности
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA busy_timeout=5000")
            await db.execute("PRAGMA synchronous=NORMAL")
            
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance INTEGER DEFAULT 0,
                    total_deposited INTEGER DEFAULT 0,
                    total_withdrawn INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0,
                    total_wins INTEGER DEFAULT 0,
                    total_losses INTEGER DEFAULT 0,
                    best_win INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    referrer_id INTEGER,
                    referral_bonus INTEGER DEFAULT 0,
                    daily_bonus_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_banned INTEGER DEFAULT 0
                )
            """)
            
            # Таблица истории игр
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
            
            # Таблица транзакций
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
    
    async def _execute(self, query: str, params: tuple = None, fetch: bool = False):
        """Безопасное выполнение запроса с блокировкой"""
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()
        
        async with self._lock:
            try:
                async with aiosqlite.connect(self.db_name) as db:
                    await db.execute("PRAGMA busy_timeout=5000")
                    if params:
                        cursor = await db.execute(query, params)
                    else:
                        cursor = await db.execute(query)
                    
                    if fetch:
                        result = await cursor.fetchall()
                    else:
                        result = None
                    
                    await db.commit()
                    return result
            except Exception as e:
                print(f"❌ DB Error: {e}")
                raise
    
    async def register_user(self, user_id: int, username: str = "", referrer_id: Optional[int] = None) -> bool:
        """Регистрация нового пользователя"""
        # Проверяем существование
        result = await self._execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,), fetch=True
        )
        
        if result:
            return False
        
        # Регистрируем
        await self._execute(
            """INSERT INTO users (user_id, username, balance, referrer_id, created_at) 
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, START_BALANCE, referrer_id, datetime.now().isoformat())
        )
        
        # Бонус рефереру
        if referrer_id and referrer_id != user_id:
            await self.add_balance(referrer_id, 100)
            await self._execute(
                "UPDATE users SET referral_bonus = referral_bonus + 100 WHERE user_id = ?",
                (referrer_id,)
            )
        
        return True
    
    async def get_user(self, user_id: int) -> Optional[dict]:
        """Получение данных пользователя"""
        result = await self._execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,), fetch=True
        )
        
        if not result:
            return None
        
        # Конвертируем в словарь
        row = result[0]
        columns = ['user_id', 'username', 'balance', 'total_deposited', 'total_withdrawn',
                   'games_played', 'total_wins', 'total_losses', 'best_win', 'level', 'xp',
                   'referrer_id', 'referral_bonus', 'daily_bonus_date', 'created_at', 'is_banned']
        return dict(zip(columns, row))
    
    async def get_balance(self, user_id: int) -> int:
        """Получение баланса"""
        result = await self._execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (user_id,), fetch=True
        )
        return result[0][0] if result else 0
    
    async def add_balance(self, user_id: int, amount: int) -> int:
        """Пополнение баланса"""
        await self._execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        return await self.get_balance(user_id)
    
    async def update_game_stats(self, user_id: int, won: bool, bet: int, profit: int):
        """Обновление игровой статистики"""
        if won:
            await self._execute(
                """UPDATE users SET 
                   games_played = games_played + 1,
                   total_wins = total_wins + 1,
                   xp = xp + ?,
                   best_win = MAX(best_win, ?)
                   WHERE user_id = ?""",
                (bet // 10, profit, user_id)
            )
        else:
            await self._execute(
                """UPDATE users SET 
                   games_played = games_played + 1,
                   total_losses = total_losses + 1,
                   xp = xp + ?
                   WHERE user_id = ?""",
                (bet // 20, user_id)
            )
    
    async def add_game_history(self, user_id: int, game_type: str, bet: int, 
                               result: str, profit: int, multiplier: float):
        """Добавление в историю игр"""
        await self._execute(
            """INSERT INTO game_history (user_id, game_type, bet, result, profit, multiplier)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, game_type, bet, result, profit, multiplier)
        )
    
    async def get_game_history(self, user_id: int, limit: int = 10) -> List[dict]:
        """Получить историю игр пользователя"""
        result = await self._execute(
            """SELECT id, user_id, game_type, bet, result, profit, multiplier, played_at 
               FROM game_history 
               WHERE user_id = ? 
               ORDER BY played_at DESC 
               LIMIT ?""",
            (user_id, limit), fetch=True
        )
        
        if not result:
            return []
        
        history = []
        for row in result:
            history.append({
                "id": row[0],
                "user_id": row[1],
                "game_type": row[2],
                "bet": row[3],
                "result": row[4],
                "profit": row[5],
                "multiplier": row[6],
                "played_at": row[7]
            })
        return history
    
    async def add_transaction(self, user_id: int, trans_type: str, amount: int, description: str):
        """Добавление транзакции"""
        await self._execute(
            """INSERT INTO transactions (user_id, type, amount, description)
               VALUES (?, ?, ?, ?)""",
            (user_id, trans_type, amount, description)
        )
    
    async def claim_daily_bonus(self, user_id: int) -> Optional[int]:
        """Ежедневный бонус"""
        import random
        today = datetime.now().strftime("%Y-%m-%d")
        user = await self.get_user(user_id)
        
        if not user or user['daily_bonus_date'] == today:
            return None
        
        bonus = random.randint(50, 200)
        await self._execute(
            "UPDATE users SET balance = balance + ?, daily_bonus_date = ? WHERE user_id = ?",
            (bonus, today, user_id)
        )
        return bonus
    
    async def get_top_players(self, limit: int = 10) -> List[dict]:
        """Топ игроков"""
        result = await self._execute(
            """SELECT user_id, username, balance, level 
               FROM users WHERE is_banned = 0 
               ORDER BY balance DESC LIMIT ?""",
            (limit,), fetch=True
        )
        
        if not result:
            return []
        
        players = []
        for row in result:
            players.append({
                "user_id": row[0],
                "username": row[1],
                "balance": row[2],
                "level": row[3]
            })
        return players
    
    async def get_user_stats(self, user_id: int) -> Optional[dict]:
        """Полная статистика"""
        return await self.get_user(user_id)
    
    async def get_referrals(self, user_id: int) -> List[dict]:
        """Список рефералов"""
        result = await self._execute(
            "SELECT user_id, username, balance FROM users WHERE referrer_id = ?",
            (user_id,), fetch=True
        )
        
        if not result:
            return []
        
        referrals = []
        for row in result:
            referrals.append({
                "user_id": row[0],
                "username": row[1],
                "balance": row[2]
            })
        return referrals
    
    async def get_total_stats(self) -> dict:
        """Общая статистика"""
        users = await self._execute("SELECT COUNT(*) FROM users", fetch=True)
        games = await self._execute("SELECT COUNT(*) FROM game_history", fetch=True)
        
        return {
            "total_users": users[0][0] if users else 0,
            "total_games": games[0][0] if games else 0,
            "total_wagered": 0
        }


# Глобальный экземпляр
db = Database()
