import logging
import os
import threading

import psycopg
from flask import g
from psycopg.rows import dict_row

log = logging.getLogger("showcase")

SCHEMA = """
CREATE TABLE IF NOT EXISTS todos (
    id          SERIAL PRIMARY KEY,
    title       TEXT        NOT NULL,
    done        BOOLEAN     NOT NULL DEFAULT FALSE,
    author      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

_schema_ready = False
_schema_lock = threading.Lock()


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


def connect() -> psycopg.Connection:
    # prepare_threshold=None disables server-side prepared statements, which
    # keeps us compatible with Neon's pooled (PgBouncer) connection string.
    return psycopg.connect(
        database_url(),
        row_factory=dict_row,
        autocommit=True,
        prepare_threshold=None,
        connect_timeout=10,
    )


def ensure_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        with connect() as conn, conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(424242)")
            conn.execute(SCHEMA)
        _schema_ready = True
        log.info("Database schema ready")


def get_conn() -> psycopg.Connection:
    if "db" not in g:
        g.db = connect()
    return g.db


def close_conn(_exc=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def run(query: str, params: tuple = ()) -> list[dict]:
    cur = get_conn().execute(query, params)
    return cur.fetchall() if cur.description else []
