import sqlite3, json
from datetime import datetime, date, timedelta

DB_PATH = "bot.db"

DEFAULT_PRICES = {"weekly": 50000, "monthly": 150000, "quarterly": 350000}
DEFAULT_PAYMENT = {
    "card": "8600 XXXX XXXX XXXX",
    "name": "Karta egasi",
    "note": "To'lov izohiga Telegram username yozing",
    "confirm_time": "1-2 soat"
}

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            registered_at TEXT,
            is_premium INTEGER DEFAULT 0,
            premium_until TEXT,
            is_banned INTEGER DEFAULT 0,
            preferred_strategy TEXT DEFAULT 'auto'
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
            amount INTEGER,
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
            created_at TEXT
        );
    """)
    for key, val in [
        ("prices", json.dumps(DEFAULT_PRICES)),
        ("payment", json.dumps(DEFAULT_PAYMENT)),
    ]:
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key, val))
    conn.commit()
    conn.close()
    print("✅ Database tayyor!")

def db_get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def db_register_user(user_id, username, full_name, phone):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO users(user_id,username,full_name,phone,registered_at) VALUES(?,?,?,?,?)",
        (user_id, username or "", full_name, phone, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def db_is_premium(user_id):
    conn = get_conn()
    row = conn.execute("SELECT is_premium, premium_until FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if not row or not row["is_premium"]:
        return False
    if row["premium_until"]:
        if datetime.fromisoformat(row["premium_until"]) < datetime.now():
            c2 = get_conn()
            c2.execute("UPDATE users SET is_premium=0 WHERE user_id=?", (user_id,))
            c2.commit()
            c2.close()
            return False
    return True

def db_activate_premium(user_id, plan):
    days = {"weekly": 7, "monthly": 30, "quarterly": 90}
    until = datetime.now() + timedelta(days=days.get(plan, 30))
    conn = get_conn()
    conn.execute("UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?",
                 (until.isoformat(), user_id))
    conn.commit()
    conn.close()

def db_get_strategy(user_id):
    conn = get_conn()
    row = conn.execute("SELECT preferred_strategy FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row["preferred_strategy"] if row else "auto"

def db_set_strategy(user_id, strategy):
    conn = get_conn()
    conn.execute("UPDATE users SET preferred_strategy=? WHERE user_id=?", (strategy, user_id))
    conn.commit()
    conn.close()

def db_get_usage(user_id):
    today = date.today().isoformat()
    conn = get_conn()
    row = conn.execute("SELECT count FROM daily_usage WHERE user_id=? AND usage_date=?",
                       (user_id, today)).fetchone()
    conn.close()
    return row["count"] if row else 0

def db_increment_usage(user_id):
    today = date.today().isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO daily_usage(user_id,usage_date,count) VALUES(?,?,1) "
        "ON CONFLICT(user_id,usage_date) DO UPDATE SET count=count+1",
        (user_id, today)
    )
    conn.commit()
    conn.close()

def db_save_payment(user_id, plan, amount, file_id):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO payment_requests(user_id,plan,amount,screenshot_file_id,created_at) VALUES(?,?,?,?,?)",
        (user_id, plan, amount, file_id, datetime.now().isoformat())
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid

def db_get_pending():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM payment_requests WHERE status='pending' ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_approve_payment(pid, plan, user_id):
    conn = get_conn()
    conn.execute("UPDATE payment_requests SET status='approved',processed_at=? WHERE id=?",
                 (datetime.now().isoformat(), pid))
    conn.commit()
    conn.close()
    db_activate_premium(user_id, plan)

def db_reject_payment(pid):
    conn = get_conn()
    conn.execute("UPDATE payment_requests SET status='rejected',processed_at=? WHERE id=?",
                 (datetime.now().isoformat(), pid))
    conn.commit()
    conn.close()

def db_get_setting(key):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return json.loads(row["value"]) if row else None

def db_set_setting(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, json.dumps(value)))
    conn.commit()
    conn.close()

def db_get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY registered_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_save_analysis(user_id, pair, signal, entry, sl, tp, balance):
    conn = get_conn()
    conn.execute(
        "INSERT INTO analyses(user_id,pair,signal,entry,sl,tp,balance,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (user_id, pair, signal, entry, sl, tp, balance, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def db_get_stats():
    conn = get_conn()
    stats = {
        "total_users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "premium_users": conn.execute("SELECT COUNT(*) FROM users WHERE is_premium=1").fetchone()[0],
        "total_analyses": conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0],
        "approved_payments": conn.execute("SELECT COUNT(*) FROM payment_requests WHERE status='approved'").fetchone()[0],
        "revenue": conn.execute("SELECT SUM(amount) FROM payment_requests WHERE status='approved'").fetchone()[0] or 0,
    }
    conn.close()
    return stats
