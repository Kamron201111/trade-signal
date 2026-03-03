"""
🗄️ Database - SQLite (bepul, deploy uchun qulay)
"""
import aiosqlite
import json
from datetime import datetime, date
from config import DEFAULT_PRICES, DEFAULT_PAYMENT

DB_PATH = "trading_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                registered_at TEXT,
                is_premium INTEGER DEFAULT 0,
                premium_until TEXT,
                is_banned INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id INTEGER,
                usage_date TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, usage_date)
            );

            CREATE TABLE IF NOT EXISTS payment_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan TEXT,
                amount REAL,
                screenshot_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                processed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                pair TEXT,
                signal TEXT,
                entry REAL,
                sl REAL,
                tp REAL,
                balance REAL,
                risk_amount REAL,
                lot_size REAL,
                created_at TEXT
            );
        """)
        
        # Default sozlamalar
        settings = [
            ("prices", json.dumps(DEFAULT_PRICES)),
            ("payment", json.dumps(DEFAULT_PAYMENT)),
        ]
        for key, value in settings:
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        await db.commit()
    print("✅ Database tayyor!")

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()

async def register_user(user_id: int, username: str, full_name: str, phone: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (user_id, username, full_name, phone, registered_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, full_name, phone, datetime.now().isoformat()))
        await db.commit()

async def get_daily_usage(user_id: int) -> int:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT count FROM daily_usage WHERE user_id=? AND usage_date=?",
            (user_id, today)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def increment_usage(user_id: int):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO daily_usage (user_id, usage_date, count) VALUES (?, ?, 1)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET count = count + 1
        """, (user_id, today))
        await db.commit()

async def is_premium(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_premium, premium_until FROM users WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row or not row[0]:
                return False
            if row[1] and datetime.fromisoformat(row[1]) < datetime.now():
                await db.execute("UPDATE users SET is_premium=0 WHERE user_id=?", (user_id,))
                await db.commit()
                return False
            return True

async def activate_premium(user_id: int, plan: str):
    from datetime import timedelta
    days = {"weekly": 7, "monthly": 30, "quarterly": 90}
    until = datetime.now() + timedelta(days=days.get(plan, 30))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?",
            (until.isoformat(), user_id)
        )
        await db.commit()

async def save_payment_request(user_id: int, plan: str, amount: float, file_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO payment_requests (user_id, plan, amount, screenshot_file_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, plan, amount, file_id, datetime.now().isoformat()))
        await db.commit()
        return cur.lastrowid

async def get_pending_payments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payment_requests WHERE status='pending' ORDER BY created_at DESC"
        ) as cur:
            return await cur.fetchall()

async def approve_payment(payment_id: int, plan: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payment_requests SET status='approved', processed_at=? WHERE id=?",
            (datetime.now().isoformat(), payment_id)
        )
        await db.commit()
    await activate_premium(user_id, plan)

async def get_setting(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return json.loads(row[0]) if row else None

async def update_setting(key: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value))
        )
        await db.commit()

async def save_analysis(user_id: int, data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO analyses (user_id, pair, signal, entry, sl, tp, balance, risk_amount, lot_size, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, data['pair'], data['signal'], data['entry'],
            data['sl'], data['tp'], data['balance'], data['risk_amount'],
            data['lot_size'], datetime.now().isoformat()
        ))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY registered_at DESC") as cur:
            return await cur.fetchall()
