import os
import secrets
import sqlite3
import time
from typing import List, Optional, Set, Tuple


try:
    import psycopg2
except Exception:  # pragma: no cover - optional dependency
    psycopg2 = None

from werkzeug.security import check_password_hash, generate_password_hash


DB_URL = os.getenv("DATABASE_URL", "").strip()
SQLITE_PATH = os.getenv("SQLITE_PATH", "instance/dev.db")


def _connect_sqlite():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _connect_postgres():
    if not psycopg2:
        raise RuntimeError("psycopg2 is required for Postgres")
    conn = psycopg2.connect(DB_URL, sslmode="require")
    cur = conn.cursor()
    cur.execute("SET search_path TO xmas")
    conn.commit()
    cur.close()
    return conn


def _connect():
    if DB_URL:
        return _connect_postgres()
    return _connect_sqlite()


def init_db():
    conn = _connect()
    cur = conn.cursor()
    if DB_URL:
        cur.execute("CREATE SCHEMA IF NOT EXISTS xmas")
        cur.execute("SET search_path TO xmas")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            crowns INTEGER NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS account_items (
            account_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            PRIMARY KEY (account_id, item_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS account_names (
            account_id TEXT NOT NULL,
            name TEXT NOT NULL,
            PRIMARY KEY (account_id, name)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def _placeholder(query):
    return query if DB_URL else query.replace("%s", "?")


def create_account(first_name, last_name, email, password):
    conn = _connect()
    cur = conn.cursor()
    now = time.time()
    account_id = secrets.token_hex(16)
    password_hash = generate_password_hash(password)
    cur.execute(
        _placeholder(
            "INSERT INTO accounts (id, first_name, last_name, email, password_hash, crowns, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        ),
        (account_id, first_name, last_name, email, password_hash, 0, now, now),
    )
    conn.commit()
    conn.close()
    return account_id


def auth_account(email, password):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(_placeholder("SELECT id, password_hash FROM accounts WHERE email = %s"), (email,))
    row = cur.fetchone()
    if not row or not check_password_hash(row[1], password):
        conn.close()
        return None
    conn.close()
    return row[0]


def create_session(account_id):
    token = secrets.token_hex(24)
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        _placeholder("INSERT INTO sessions (token, account_id, created_at) VALUES (%s, %s, %s)"),
        (token, account_id, time.time()),
    )
    conn.commit()
    conn.close()
    return token


def account_from_token(token):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(_placeholder("SELECT account_id FROM sessions WHERE token = %s"), (token,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_account(account_id):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(_placeholder("SELECT crowns FROM accounts WHERE id = %s"), (account_id,))
    row = cur.fetchone()
    crowns = row[0] if row else 0
    cur.execute(_placeholder("SELECT item_id FROM account_items WHERE account_id = %s"), (account_id,))
    items = [r[0] for r in cur.fetchall()]
    cur.execute(_placeholder("SELECT name FROM account_names WHERE account_id = %s"), (account_id,))
    names = [r[0] for r in cur.fetchall()]
    conn.close()
    return crowns, set(items), names


def add_account_name(account_id, name):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        _placeholder("INSERT INTO account_names (account_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING"),
        (account_id, name),
    )
    conn.commit()
    conn.close()


def add_crowns(account_id, amount):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(_placeholder("SELECT crowns FROM accounts WHERE id = %s"), (account_id,))
    row = cur.fetchone()
    crowns = (row[0] if row else 0) + amount
    cur.execute(
        _placeholder("UPDATE accounts SET crowns = %s, updated_at = %s WHERE id = %s"),
        (crowns, time.time(), account_id),
    )
    conn.commit()
    conn.close()
    return crowns


def buy_item(account_id, item_id, cost):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(_placeholder("SELECT crowns FROM accounts WHERE id = %s"), (account_id,))
    row = cur.fetchone()
    crowns = row[0] if row else 0
    if crowns < cost:
        conn.close()
        return False, crowns
    cur.execute(
        _placeholder(
            "INSERT INTO account_items (account_id, item_id) VALUES (%s, %s) ON CONFLICT DO NOTHING"
        ),
        (account_id, item_id),
    )
    crowns -= cost
    cur.execute(
        _placeholder("UPDATE accounts SET crowns = %s, updated_at = %s WHERE id = %s"),
        (crowns, time.time(), account_id),
    )
    conn.commit()
    conn.close()
    return True, crowns


def delete_session(token):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(_placeholder("DELETE FROM sessions WHERE token = %s"), (token,))
    conn.commit()
    conn.close()
