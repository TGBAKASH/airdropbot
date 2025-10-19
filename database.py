# database.py
import sqlite3
from typing import List, Tuple, Optional

DB = "users.db"

def _conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chain TEXT,
            address TEXT UNIQUE,
            notifications_enabled INTEGER DEFAULT 1,
            last_balance TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS airdrops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            url TEXT,
            added_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()

# ---- Users ----
def ensure_user(user_id: int, username: str = "", first_name: str = ""):
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE id=?", (user_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (id, username, first_name) VALUES (?, ?, ?)",
                        (user_id, username, first_name))
            conn.commit()

def list_users() -> List[int]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users")
        return [r[0] for r in cur.fetchall()]

# ---- Wallets ----
def add_wallet(user_id: int, chain: str, address: str) -> bool:
    address = address.strip()
    with _conn() as conn:
        cur = conn.cursor()
        # avoid duplicates globally
        cur.execute("SELECT id FROM wallets WHERE lower(address)=?", (address.lower(),))
        if cur.fetchone():
            return False
        cur.execute("INSERT INTO wallets (user_id, chain, address) VALUES (?, ?, ?)",
                    (user_id, chain, address))
        conn.commit()
        return True

def get_user_wallets(user_id: int) -> List[Tuple[str,str,int]]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT chain, address, notifications_enabled FROM wallets WHERE user_id=?", (user_id,))
        return cur.fetchall()

def delete_wallet(address: str):
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM wallets WHERE address=?", (address,))
        conn.commit()

def list_all_wallets() -> List[Tuple[int,str,str]]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, chain, address FROM wallets")
        return cur.fetchall()

# ---- Airdrops ----
def add_airdrop(title: str, content: str, url: str, added_by: int):
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO airdrops (title, content, url, added_by) VALUES (?, ?, ?, ?)",
                    (title[:300], content[:4000], url or "", added_by))
        conn.commit()

def list_airdrops(limit: int = 50):
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, content, url, added_by, created_at FROM airdrops ORDER BY id DESC LIMIT ?", (limit,))
        return cur.fetchall()

def delete_airdrop(aid: int):
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM airdrops WHERE id=?", (aid,))
        conn.commit()
