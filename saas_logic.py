import sqlite3
import os
import uuid
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "saas.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tokens table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tokens (
        token TEXT PRIMARY KEY,
        user_id TEXT,
        plan TEXT DEFAULT 'free',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Usage logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT,
        action TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (token) REFERENCES tokens (token)
    )
    """)

    # Tasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        token TEXT,
        type TEXT,
        status TEXT DEFAULT 'pending',
        payload TEXT,
        result_url TEXT,
        error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (token) REFERENCES tokens (token)
    )
    """)
    
    # Register default tokens
    cursor.execute("INSERT OR IGNORE INTO tokens (token, user_id, plan) VALUES (?, ?, ?)", 
                   ("b2831286e14844faa0782f69d4649825", "guest_premium", "premium"))
    cursor.execute("INSERT OR IGNORE INTO tokens (token, user_id, plan) VALUES (?, ?, ?)", 
                   ("e5b1cf863b6f4fa3a3bcc1bab27bb754", "guest_free", "free"))

    conn.commit()
    conn.close()

def create_token(user_id, plan="free"):
    token = str(uuid.uuid4()).replace("-", "")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tokens (token, user_id, plan) VALUES (?, ?, ?)", (token, user_id, plan))
    conn.commit()
    conn.close()
    return token

def get_token_info(token):
    if not token:
        return None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tokens WHERE token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def log_usage(token, action):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO usage_logs (token, action) VALUES (?, ?)", (token, action))
    conn.commit()
    conn.close()

def check_quota(token):
    """
    Check if the token has exceeded its daily quota.
    Free: 10 actions/day
    Premium: 1000 actions/day (effectively unlimited for human use)
    """
    info = get_token_info(token)
    if not info:
        return False, "Ungültiger Token"
    
    limit = 10 if info['plan'] == 'free' else 1000
    today = date.today().isoformat()
    
    conn = get_db()
    cursor = conn.cursor()
    # Check usage for today
    cursor.execute("""
        SELECT COUNT(*) FROM usage_logs 
        WHERE token = ? AND date(timestamp) = date(?)
    """, (token, today))
    count = cursor.fetchone()[0]
    conn.close()
    
    if count >= limit:
        return False, f"Limit erreicht ({count}/{limit}). Bitte auf Premium upgraden."
    
    return True, f"{count}/{limit} verbraucht"

def add_task(token, task_type, payload):
    task_id = str(uuid.uuid4())
    conn = get_db()
    cursor = conn.cursor()
    import json
    cursor.execute("""
        INSERT INTO tasks (id, token, type, payload) 
        VALUES (?, ?, ?, ?)
    """, (task_id, token, task_type, json.dumps(payload)))
    conn.commit()
    conn.close()
    return task_id

def update_task(task_id, status, result_url=None, error=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks 
        SET status = ?, result_url = ?, error = ? 
        WHERE id = ?
    """, (status, result_url, error, task_id))
    conn.commit()
    conn.close()

def get_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

if __name__ == "__main__":
    init_db()
    print("SaaS Database initialized.")
    # Create a test token if none exists
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM tokens").fetchone()[0] == 0:
        t = create_token("admin", "premium")
        print(f"Test Admin Token (Premium) created: {t}")
        t_free = create_token("guest", "free")
        print(f"Test Guest Token (Free) created: {t_free}")
    conn.close()
