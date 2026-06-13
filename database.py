import sqlite3
import threading
from datetime import date, datetime
from config import DB_PATH, CLIPBOARD_HISTORY_DAYS

_local = threading.local()

def _get_conn():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn

def init_db():
    conn = _get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT, original_text TEXT, result TEXT, timestamp TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS usage (
        date TEXT PRIMARY KEY, count INTEGER DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS clipboard_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT, timestamp TEXT
    )""")
    conn.commit()
    trim_clipboard_history()

# Settings
def get_setting(key, default=None):
    cur = _get_conn().execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()
    return row["value"] if row else default

def set_setting(key, value):
    _get_conn().execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    _get_conn().commit()

# Usage
def get_usage_count():
    today = date.today().isoformat()
    cur = _get_conn().execute("SELECT count FROM usage WHERE date=?", (today,))
    row = cur.fetchone()
    return row["count"] if row else 0

def increment_usage():
    today = date.today().isoformat()
    conn = _get_conn()
    conn.execute("INSERT INTO usage (date, count) VALUES (?,1) ON CONFLICT(date) DO UPDATE SET count=count+1", (today,))
    conn.commit()

# AI History
def save_history(action, original_text, result):
    conn = _get_conn()
    conn.execute("INSERT INTO history (action, original_text, result, timestamp) VALUES (?,?,?,?)",
                 (action, original_text[:500], result, datetime.now().isoformat()))
    conn.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT 30)")
    conn.commit()

def get_history():
    cur = _get_conn().execute("SELECT id, action, original_text, result, timestamp FROM history ORDER BY id DESC LIMIT 30")
    return [dict(r) for r in cur.fetchall()]

# Clipboard History
def save_clipboard(text):
    conn = _get_conn()
    conn.execute("INSERT INTO clipboard_history (text, timestamp) VALUES (?,?)",
                 (text[:10000], datetime.now().isoformat()))
    conn.commit()

def get_clipboard_history(limit=50):
    trim_clipboard_history()
    cur = _get_conn().execute(
        "SELECT id, text, timestamp FROM clipboard_history ORDER BY id DESC LIMIT ?", (limit,))
    return [dict(r) for r in cur.fetchall()]

def delete_clipboard_item(item_id):
    _get_conn().execute("DELETE FROM clipboard_history WHERE id=?", (item_id,))
    _get_conn().commit()

def delete_clipboard_items(ids):
    ids = tuple(ids)
    _get_conn().execute(f"DELETE FROM clipboard_history WHERE id IN ({','.join('?'*len(ids))})", ids)
    _get_conn().commit()

# Donation system
def get_launch_count():
    return int(get_setting("launch_count", "0"))

def increment_launch_count():
    set_setting("launch_count", str(get_launch_count() + 1))

def has_donated():
    return get_setting("donated") == "true"

def mark_donated():
    set_setting("donated", "true")

def get_donation_url():
    return get_setting("donation_url", "https://your-payment-link.com")

def set_donation_url(url):
    set_setting("donation_url", url)

def get_last_donation_reminder():
    val = get_setting("last_donation_reminder", "0")
    try:
        return int(val)
    except ValueError:
        return 0

def set_last_donation_reminder():
    from datetime import datetime
    set_setting("last_donation_reminder", str(int(datetime.now().timestamp())))

def trim_clipboard_history():
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=CLIPBOARD_HISTORY_DAYS)).isoformat()
    _get_conn().execute("DELETE FROM clipboard_history WHERE timestamp < ?", (cutoff,))
    _get_conn().execute("DELETE FROM clipboard_history WHERE id NOT IN (SELECT id FROM clipboard_history ORDER BY id DESC LIMIT 200)")
    _get_conn().commit()
