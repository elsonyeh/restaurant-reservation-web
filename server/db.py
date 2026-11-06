"""資料庫連線：使用 psycopg2 連線池，查詢結果以 dict 回傳。"""
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(
            1, 10,
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD") or None,
            dbname=os.getenv("DB_NAME"),
            connect_timeout=8,
        )
    return _pool


@contextmanager
def transaction():
    """取得一個連線並開始交易；正常結束 COMMIT，發生例外 ROLLBACK。"""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def fetch_all(sql, params=None):
    with transaction() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetch_one(sql, params=None):
    with transaction() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql, params=None):
    """執行 INSERT / UPDATE / DELETE；有 RETURNING 時回傳第一列，否則回傳影響筆數。"""
    with transaction() as cur:
        cur.execute(sql, params)
        if cur.description:
            return cur.fetchone()
        return cur.rowcount
