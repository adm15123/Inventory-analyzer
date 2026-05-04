"""
db.py — Turso (libSQL) database layer for Zamora Inventory App

Tables:
  invoices      — one row per uploaded document (invoice or bid)
  invoice_items — one row per line item in a document

Credentials come from environment variables:
  TURSO_URL    = libsql://your-db-name.turso.io  (or https://)
  TURSO_TOKEN  = your-auth-token

Local fallback: if TURSO_URL is not set, falls back to local SQLite
at data/zamora.db (useful for local dev without Turso).
"""

import json
import os
import sqlite3
import time
from datetime import datetime
from typing import Optional

import httpx
import pandas as pd


# ── Driver selection ──────────────────────────────────────────────────────────

TURSO_URL   = os.environ.get("TURSO_URL", "").replace("libsql://", "https://")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "")
USE_TURSO   = bool(TURSO_URL)

LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "zamora.db")


# ── Turso HTTP transport ──────────────────────────────────────────────────────

_http_client: httpx.Client | None = None


def _get_http_client() -> httpx.Client:
    """Return the shared httpx client, creating it once on first call."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(timeout=30)
    return _http_client


def _to_arg(v) -> dict:
    """Convert a Python value to a Turso HTTP API argument object."""
    if v is None:
        return {"type": "null"}
    return {"type": "text", "value": str(v)}


def _extract_value(cell: dict):
    """Convert a Turso response cell {type, value} to a Python value."""
    t = cell.get("type")
    v = cell.get("value")
    if t == "null" or v is None:
        return None
    if t == "integer":
        return int(v)
    if t == "real":
        return float(v)
    return v  # text / blob → string


def _parse_result(result: dict) -> list[dict]:
    """Turn a Turso execute result object into a list of row dicts."""
    cols = [c["name"] for c in result.get("cols", [])]
    if not cols:
        return []
    return [
        dict(zip(cols, (_extract_value(cell) for cell in row)))
        for row in result.get("rows", [])
    ]


def _pipeline(requests: list[dict]) -> list[dict]:
    """
    POST to /v2/pipeline and return the raw results list.
    Automatically appends the required {"type": "close"} sentinel.
    """
    payload = {"requests": requests + [{"type": "close"}]}
    client = _get_http_client()
    resp = client.post(
        f"{TURSO_URL}/v2/pipeline",
        headers={
            "Authorization": f"Bearer {TURSO_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    if not resp.is_success:
        print(f"_pipeline HTTP {resp.status_code}: {resp.text[:500]}")
    resp.raise_for_status()
    return resp.json().get("results", [])


def _turso_execute(sql: str, params: list = None) -> list[dict]:
    """
    Execute a single SQL statement against Turso and return rows as dicts.
    For INSERT/UPDATE/DELETE, returns [].
    """
    params = params or []
    stmt = {"sql": sql, "args": [_to_arg(v) for v in params]}
    results = _pipeline([{"type": "execute", "stmt": stmt}])
    if not results:
        return []
    first = results[0]
    if first.get("type") == "error":
        raise RuntimeError(f"Turso error: {first.get('error')}")
    return _parse_result(first.get("response", {}).get("result", {}))


def _turso_batch(statements: list[tuple]) -> list:
    """
    Execute multiple (sql, params) statements in one pipeline request.
    Returns list of parsed row-dict lists, one per statement.
    Raises RuntimeError if any statement returns an error.
    """
    requests = [
        {
            "type": "execute",
            "stmt": {"sql": sql, "args": [_to_arg(v) for v in (params or [])]},
        }
        for sql, params in statements
    ]
    results = _pipeline(requests)
    out = []
    for i, r in enumerate(results[: len(statements)]):
        if r.get("type") == "error":
            raise RuntimeError(f"Turso batch error at statement {i}: {r.get('error')}")
        out.append(_parse_result(r.get("response", {}).get("result", {})))
    return out


# ── Local SQLite connection ───────────────────────────────────────────────────

def _local_conn() -> sqlite3.Connection:
    """Return a local SQLite connection (dev/fallback only)."""
    os.makedirs(os.path.dirname(LOCAL_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

get_conn = _local_conn  # alias for migration scripts


# ── In-memory result cache ────────────────────────────────────────────────────

_cache: dict[str, tuple[float, object]] = {}
_LATEST_PRICES_TTL = 300   # 5 minutes
_LIST_INVOICES_TTL = 120   # 2 minutes


def _cache_get(key: str) -> object:
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() > expires_at:
        del _cache[key]
        return None
    return value


def _cache_set(key: str, value: object, ttl: float):
    _cache[key] = (time.monotonic() + ttl, value)


def cache_clear():
    """Invalidate all cached query results."""
    _cache.clear()


# ── In-memory catalog DataFrame ───────────────────────────────────────────────

_catalog_df: pd.DataFrame | None = None

_CATALOG_SQL = """
    SELECT
        ii.description   AS "Description",
        ii.item_number   AS "Item Number",
        ii.uom           AS "Unit",
        ii.unit_price    AS "Price per Unit",
        inv.date         AS "Date",
        inv.order_number AS "Invoice No.",
        ii.supplier      AS "Supply"
    FROM invoice_items ii
    JOIN invoices inv ON inv.id = ii.invoice_id
"""


def load_catalog_to_memory():
    """Pull every item row from the DB into _catalog_df once at startup."""
    global _catalog_df
    if USE_TURSO:
        rows = _turso_execute(_CATALOG_SQL)
        _catalog_df = pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=["Description", "Item Number", "Unit", "Price per Unit",
                     "Date", "Invoice No.", "Supply"]
        )
    else:
        with _local_conn() as conn:
            _catalog_df = pd.read_sql_query(_CATALOG_SQL, conn)


def get_catalog_df() -> pd.DataFrame | None:
    return _catalog_df


def refresh_catalog():
    """Reload the catalog from the DB (call after a new upload)."""
    load_catalog_to_memory()


# ── Public API ────────────────────────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    ddl = """
        CREATE TABLE IF NOT EXISTS invoices (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type      TEXT NOT NULL,
            order_number  TEXT NOT NULL,
            date          TEXT,
            job_name      TEXT,
            supplier      TEXT DEFAULT 'LPS',
            filename      TEXT,
            imported_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS invoice_items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id    INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
            item_number   TEXT,
            description   TEXT NOT NULL,
            uom           TEXT,
            quantity      REAL DEFAULT 0,
            unit_price    REAL DEFAULT 0,
            supplier      TEXT DEFAULT 'LPS'
        );

        CREATE INDEX IF NOT EXISTS idx_items_description
            ON invoice_items (description);

        CREATE INDEX IF NOT EXISTS idx_items_item_number
            ON invoice_items (item_number);

        CREATE INDEX IF NOT EXISTS idx_items_supplier
            ON invoice_items (supplier);

        CREATE TABLE IF NOT EXISTS users (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            email            TEXT UNIQUE NOT NULL,
            role             TEXT DEFAULT 'user',
            active           INTEGER DEFAULT 1,
            failed_attempts  INTEGER DEFAULT 0,
            last_failed      TEXT
        );

        INSERT OR IGNORE INTO users (email, role, active)
            VALUES ('zamoraplumbing01@gmail.com', 'admin', 1);

        CREATE TABLE IF NOT EXISTS login_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            email     TEXT NOT NULL,
            logged_at TEXT DEFAULT (datetime('now')),
            ip        TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_login_history_email
            ON login_history (email);
    """

    if USE_TURSO:
        statements = [
            (stmt.strip(), [])
            for stmt in ddl.split(";")
            if stmt.strip()
        ]
        _turso_batch(statements)
    else:
        with _local_conn() as conn:
            conn.executescript(ddl)


def save_parsed_document(parsed: dict, filename: str = "") -> int:
    """
    Insert a parsed PDF result into the DB.
    Returns the new invoice id, or -1 if already imported (duplicate).
    Clears the cache so subsequent reads reflect the new data.
    """
    order_number = parsed["order_number"]
    doc_type     = parsed["doc_type"]

    if USE_TURSO:
        existing = _turso_execute(
            "SELECT id FROM invoices WHERE order_number = ? AND doc_type = ?",
            [order_number, doc_type],
        )
        if existing:
            return -1

        _turso_execute(
            """INSERT INTO invoices (doc_type, order_number, date, job_name, supplier, filename)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                doc_type,
                order_number,
                parsed.get("date", ""),
                parsed.get("job_name", ""),
                parsed.get("supplier", "LPS"),
                filename,
            ],
        )

        rows = _turso_execute(
            "SELECT id FROM invoices WHERE order_number = ? AND doc_type = ? ORDER BY id DESC LIMIT 1",
            [order_number, doc_type],
        )
        invoice_id = rows[0]["id"]

        item_statements = [
            (
                """INSERT INTO invoice_items
                   (invoice_id, item_number, description, uom, quantity, unit_price, supplier)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    invoice_id,
                    item.get("item_number", ""),
                    item.get("description", ""),
                    item.get("uom", ""),
                    item.get("quantity", 0),
                    item.get("unit_price", 0),
                    parsed.get("supplier", "LPS"),
                ],
            )
            for item in parsed["items"]
        ]
        if item_statements:
            _turso_batch(item_statements)

    else:
        with _local_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM invoices WHERE order_number = ? AND doc_type = ?",
                (order_number, doc_type),
            ).fetchone()
            if existing:
                return -1

            cur = conn.execute(
                """INSERT INTO invoices (doc_type, order_number, date, job_name, supplier, filename)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    doc_type,
                    order_number,
                    parsed.get("date", ""),
                    parsed.get("job_name", ""),
                    parsed.get("supplier", "LPS"),
                    filename,
                ),
            )
            invoice_id = cur.lastrowid
            conn.executemany(
                """INSERT INTO invoice_items
                   (invoice_id, item_number, description, uom, quantity, unit_price, supplier)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        invoice_id,
                        item.get("item_number", ""),
                        item.get("description", ""),
                        item.get("uom", ""),
                        item.get("quantity", 0),
                        item.get("unit_price", 0),
                        parsed.get("supplier", "LPS"),
                    )
                    for item in parsed["items"]
                ],
            )

    cache_clear()
    return invoice_id


def search_items(query: str, supplier: Optional[str] = None, limit: int = 200) -> list[dict]:
    """
    Full-text search across description and item_number.
    Returns rows ordered by invoice date DESC. Not cached.
    """
    sql = """
        SELECT
            ii.description   AS "Description",
            ii.item_number   AS "Item Number",
            ii.uom           AS "Unit",
            ii.unit_price    AS "Price per Unit",
            inv.date         AS "Date",
            inv.order_number AS "Invoice No.",
            ii.supplier      AS "Supply"
        FROM invoice_items ii
        JOIN invoices inv ON inv.id = ii.invoice_id
        WHERE (
            ii.description LIKE '%' || ? || '%'
            OR ii.item_number LIKE '%' || ? || '%'
        )
    """
    params: list = [query, query]

    if supplier:
        sql += " AND ii.supplier = ?"
        params.append(supplier)

    sql += " ORDER BY inv.date DESC LIMIT ?"
    params.append(limit)

    if USE_TURSO:
        return _turso_execute(sql, params)
    else:
        with _local_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]


def get_latest_prices(supplier: Optional[str] = None) -> list[dict]:
    """
    Returns the latest price for every unique description per supplier.
    Cached for 5 minutes.
    """
    cache_key = f"latest_prices:{supplier or 'all'}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    sql = """
        SELECT
            ii.description  AS "Description",
            ii.item_number  AS "Item Number",
            ii.uom          AS "Unit",
            ii.unit_price   AS "Price per Unit",
            inv.date        AS "Date",
            ii.supplier     AS "Supply"
        FROM invoice_items ii
        JOIN invoices inv ON inv.id = ii.invoice_id
        WHERE inv.date = (
            SELECT MAX(inv2.date)
            FROM invoice_items ii2
            JOIN invoices inv2 ON inv2.id = ii2.invoice_id
            WHERE LOWER(TRIM(ii2.description)) = LOWER(TRIM(ii.description))
              AND ii2.supplier = ii.supplier
        )
    """
    params: list = []
    if supplier:
        sql += " AND ii.supplier = ?"
        params.append(supplier)
    sql += " ORDER BY ii.description"

    if USE_TURSO:
        result = _turso_execute(sql, params)
    else:
        with _local_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            result = [dict(r) for r in rows]

    _cache_set(cache_key, result, _LATEST_PRICES_TTL)
    return result


def list_invoices() -> list[dict]:
    """
    Return all imported documents with item counts, newest first.
    Cached for 2 minutes.
    """
    cache_key = "list_invoices"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    sql = """
        SELECT
            id, doc_type, order_number, date, job_name,
            supplier, filename, imported_at,
            (SELECT COUNT(*) FROM invoice_items WHERE invoice_id = invoices.id) AS item_count
        FROM invoices
        ORDER BY imported_at DESC
    """
    if USE_TURSO:
        result = _turso_execute(sql)
    else:
        with _local_conn() as conn:
            rows = conn.execute(sql).fetchall()
            result = [dict(r) for r in rows]

    _cache_set(cache_key, result, _LIST_INVOICES_TTL)
    return result


def delete_invoice(invoice_id: int):
    """Delete an invoice and all its items (CASCADE handles items)."""
    sql    = "DELETE FROM invoices WHERE id = ?"
    params = [invoice_id]

    if USE_TURSO:
        _turso_execute(sql, params)
    else:
        with _local_conn() as conn:
            conn.execute(sql, (invoice_id,))

    cache_clear()


# ── User whitelist helpers ─────────────────────────────────────────────────────

_USER_COLS = "id, email, role, active, failed_attempts, last_failed"


def get_user(email: str) -> dict | None:
    sql = f"SELECT {_USER_COLS} FROM users WHERE email = ?"
    if USE_TURSO:
        rows = _turso_execute(sql, [email])
    else:
        with _local_conn() as conn:
            rows = [dict(r) for r in conn.execute(sql, (email,)).fetchall()]
    return rows[0] if rows else None


def list_users() -> list[dict]:
    sql = f"SELECT {_USER_COLS} FROM users ORDER BY email"
    if USE_TURSO:
        return _turso_execute(sql)
    else:
        with _local_conn() as conn:
            return [dict(r) for r in conn.execute(sql).fetchall()]


def add_user(email: str, role: str = "user") -> bool:
    """Insert a new whitelisted user. Returns False if email already exists."""
    check = "SELECT id FROM users WHERE email = ?"
    insert = "INSERT INTO users (email, role, active) VALUES (?, ?, 1)"
    if USE_TURSO:
        if _turso_execute(check, [email]):
            return False
        _turso_execute(insert, [email, role])
    else:
        with _local_conn() as conn:
            if conn.execute(check, (email,)).fetchone():
                return False
            conn.execute(insert, (email, role))
    return True


def set_user_active(email: str, active: int):
    sql = "UPDATE users SET active = ? WHERE email = ?"
    if USE_TURSO:
        _turso_execute(sql, [active, email])
    else:
        with _local_conn() as conn:
            conn.execute(sql, (active, email))


def set_user_role(email: str, role: str):
    sql = "UPDATE users SET role = ? WHERE email = ?"
    if USE_TURSO:
        _turso_execute(sql, [role, email])
    else:
        with _local_conn() as conn:
            conn.execute(sql, (role, email))


def increment_failed_attempts(email: str) -> int:
    """Increments counter, records timestamp, returns new count."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    update = "UPDATE users SET failed_attempts = failed_attempts + 1, last_failed = ? WHERE email = ?"
    select = "SELECT failed_attempts FROM users WHERE email = ?"
    if USE_TURSO:
        _turso_execute(update, [now, email])
        rows = _turso_execute(select, [email])
    else:
        with _local_conn() as conn:
            conn.execute(update, (now, email))
            rows = [dict(r) for r in conn.execute(select, (email,)).fetchall()]
    return rows[0]["failed_attempts"] if rows else 0


def reset_failed_attempts(email: str):
    sql = "UPDATE users SET failed_attempts = 0, last_failed = NULL WHERE email = ?"
    if USE_TURSO:
        _turso_execute(sql, [email])
    else:
        with _local_conn() as conn:
            conn.execute(sql, (email,))


# ── Login history ──────────────────────────────────────────────────────────────

def log_login(email: str, ip: str = None):
    """Record a successful login event."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    sql = "INSERT INTO login_history (email, logged_at, ip) VALUES (?, ?, ?)"
    if USE_TURSO:
        _turso_execute(sql, [email, now, ip or ""])
    else:
        with _local_conn() as conn:
            conn.execute(sql, (email, now, ip or ""))


def get_login_history(email: str = None, limit: int = 200) -> list[dict]:
    """Return login events newest-first, optionally filtered by email."""
    if email:
        sql = """
            SELECT id, email, logged_at, ip
            FROM login_history
            WHERE email = ?
            ORDER BY logged_at DESC
            LIMIT ?
        """
        params = [email, limit]
    else:
        sql = """
            SELECT id, email, logged_at, ip
            FROM login_history
            ORDER BY logged_at DESC
            LIMIT ?
        """
        params = [limit]

    if USE_TURSO:
        return _turso_execute(sql, params)
    else:
        with _local_conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
