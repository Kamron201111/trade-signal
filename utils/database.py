import sqlite3
import json
from datetime import datetime, date

DB_PATH = "trading_bot.db"

DEFAULT_PRICES = {"weekly": 5.0, "monthly": 15.0, "quarterly": 35.0}
DEFAULT_PAYMENT = {
    "card": "8600 XXXX XXXX XXXX",
    "name": "Karta egasi",
    "note": "To'lov izohiga Telegram username yozing",
    "confirm_time": "1-2 soat"
}

def init_db_sync():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
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
    for key, value in [("prices", json.dumps(DEFAULT_PRICES)), ("payment", json.dumps(DEFAULT_PAYMENT))]:
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
    print("✅ Database tayyor!")

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

async def get_user(user_id):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

async def register_user(user_id, username, full_name, phone):
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO users (user_id, username, full_name, phone, registered_at) VALUES (?,?,?,?,?)",
        (user_id, username, full_name, phone, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

async def get_daily_usage(user_id):
    today = date.today().isoformat()
    conn = _get_conn()
    row = conn.execute("SELECT count FROM daily_usage WHERE user_id=? AND usage_date=?", (user_id, today)).fetchone()
    conn.close()
    return row[0] if row else 0

async def increment_usage(user_id):
    today = date.today().isoformat()
    conn = _get_conn()
    conn.execute(
        "INSERT INTO daily_usage (user_id, usage_date, count) VALUES (?,?,1) ON CONFLICT(user_id, usage_date) DO UPDATE SET count=count+1",
        (user_id, today)
    )
    conn.commit()
    conn.close()

async def is_premium(user_id):
    conn = _get_conn()
    row = conn.execute("SELECT is_premium, premium_until FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if not row or not row[0]:
        return False
    if row[1] and datetime.fromisoformat(row[1]) < datetime.now():
        conn2 = _get_conn()
        conn2.execute("UPDATE users SET is_premium=0 WHERE user_id=?", (user_id,))
        conn2.commit()
        conn2.close()
        return False
    return True

async def activate_premium(user_id, plan):
    from datetime import timedelta
    days = {"weekly": 7, "monthly": 30, "quarterly": 90}
    until = datetime.now() + timedelta(days=days.get(plan, 30))
    conn = _get_conn()
    conn.execute("UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?", (until.isoformat(), user_id))
    conn.commit()
    conn.close()

async def save_payment_request(user_id, plan, amount, file_id):
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO payment_requests (user_id, plan, amount, screenshot_file_id, created_at) VALUES (?,?,?,?,?)",
        (user_id, plan, amount, file_id, datetime.now().isoformat())
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid

async def get_pending_payments():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM payment_requests WHERE status='pending' ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def approve_payment(payment_id, plan, user_id):
    conn = _get_conn()
    conn.execute(
        "UPDATE payment_requests SET status='approved', processed_at=? WHERE id=?",
        (datetime.now().isoformat(), payment_id)
    )
    conn.commit()
    conn.close()
    await activate_premium(user_id, plan)

async def get_setting(key):
    conn = _get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

async def update_setting(key, value):
    conn = _get_conn()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, json.dumps(value)))
    conn.commit()
    conn.close()

async def save_analysis(user_id, data):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO analyses (user_id,pair,signal,entry,sl,tp,balance,risk_amount,lot_size,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (user_id, data.get("pair"), data.get("signal"), data.get("entry"), data.get("sl"),
         data.get("tp"), data.get("balance"), data.get("risk_amount"), data.get("lot_suggestion"), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

async def get_all_users():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY registered_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
