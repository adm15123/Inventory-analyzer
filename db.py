"""
db.py — Turso (libSQL) database layer for Zamora Inventory App

Tables:
  invoices      — one row per uploaded document (invoice or bid)
  invoice_items — one row per line item in a document

Credentials come from environment variables:
  TURSO_URL    = libsql://your-db-name.turso.io
  TURSO_TOKEN  = your-auth-token

Local fallback: if TURSO_URL is not set, falls back to local SQLite
at data/zamora.db (useful for local dev without Turso).
"""

import os
import sqlite3
import time
from typing import Optional
import pandas as pd

# ── Driver selection ──────────────────────────────────────────────────────────
TURSO_URL   = os.environ.get("TURSO_URL", "").replace("libsql://", "https://")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "")
USE_TURSO   = bool(TURSO_URL)

if USE_TURSO:
    import libsql_client  # pip install libsql-client

# Local fallback path (only used if TURSO_URL is not set)
LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "zamora.db")


# ── Turso client (module-level singleton) ─────────────────────────────────────

_turso_client = None

def _get_turso_client():
    """Return the shared Turso client, creating it once on first call."""
    global _turso_client
    if _turso_client is None:
        _turso_client = libsql_client.create_client_sync(
            url=TURSO_URL,
            auth_token=TURSO_TOKEN,
        )
    return _turso_client


# ── Connection helpers ────────────────────────────────────────────────────────

def _local_conn() -> sqlite3.Connection:
    """Return a local SQLite connection (dev/fallback only)."""
    os.makedirs(os.path.dirname(LOCAL_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

get_conn = _local_conn  # alias for migration scripts


def _turso_execute(sql: str, params: list = None) -> list[dict]:
    """
    Execute a single SQL statement against Turso and return rows as dicts.
    For INSERT/UPDATE/DELETE, returns [] but commits the change.
    """
    params = params or []
    client = _get_turso_client()
    result = client.execute(sql, params)
    if result.rows:
        columns = [col for col in result.columns]
        return [dict(zip(columns, row)) for row in result.rows]
    return []


def _turso_batch(statements: list[tuple]) -> list:
    """
    Execute multiple SQL statements in a single Turso batch (atomic).
    Each item in `statements` is a (sql, params) tuple.
    Returns list of ResultSet objects.
    """
    client = _get_turso_client()
    batch = [
        libsql_client.Statement(sql, params)
        for sql, params in statements
    ]
    return client.batch(batch)


# ── In-memory cache ───────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, object]] = {}
_LATEST_PRICES_TTL = 300   # 5 minutes
_LIST_INVOICES_TTL = 120   # 2 minutes


def _cache_get(key: str) -> object:
    """Return cached value if still fresh, else None."""
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
    """Return the in-memory catalog DataFrame."""
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
    """

    if USE_TURSO:
        # Split DDL into individual statements for Turso batch
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
        # Check for duplicate
        existing = _turso_execute(
            "SELECT id FROM invoices WHERE order_number = ? AND doc_type = ?",
            [order_number, doc_type],
        )
        if existing:
            return -1

        # Insert invoice header
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

        # Get the new invoice id
        rows = _turso_execute(
            "SELECT id FROM invoices WHERE order_number = ? AND doc_type = ? ORDER BY id DESC LIMIT 1",
            [order_number, doc_type],
        )
        invoice_id = rows[0]["id"]

        # Insert all items in a single batch
        item_statements = [
            (
                """INSERT INTO invoice_items
                   (invoice_id, item_number, description, uom, quantity, unit_price, supplier)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    invoice_id,
                    item["item_number"],
                    item["description"],
                    item["uom"],
                    item["quantity"],
                    item["unit_price"],
                    parsed.get("supplier", "LPS"),
                ],
            )
            for item in parsed["items"]
        ]
        if item_statements:
            _turso_batch(item_statements)

    else:
        # ── Local SQLite path ──────────────────────────────────────────────
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
            rows = [
                (
                    invoice_id,
                    item["item_number"],
                    item["description"],
                    item["uom"],
                    item["quantity"],
                    item["unit_price"],
                    parsed.get("supplier", "LPS"),
                )
                for item in parsed["items"]
            ]
            conn.executemany(
                """INSERT INTO invoice_items
                   (invoice_id, item_number, description, uom, quantity, unit_price, supplier)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )

    cache_clear()
    return invoice_id


def search_items(query: str, supplier: Optional[str] = None, limit: int = 200) -> list[dict]:
    """
    Full-text search across description and item_number.
    Returns rows ordered by invoice date DESC (newest price first).
    Not cached — results must always be fresh.
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
    params = [query, query]

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
    Used to populate the catalog for autocomplete / Material List.
    Cached for 5 minutes; cache is invalidated on save_parsed_document().
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
    params = []
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
    Cached for 2 minutes; cache is invalidated on save_parsed_document().
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
