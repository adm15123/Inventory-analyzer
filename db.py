"""
db.py — SQLite database layer for Zamora Inventory App

Tables:
  invoices   — one row per uploaded document (invoice or bid)
  invoice_items — one row per line item in a document

The DB file lives at  data/zamora.db  (same folder as your Excel files).
"""

import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "zamora.db")


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows accessible as dicts
    conn.execute("PRAGMA journal_mode=WAL")  # safe for concurrent reads
    return conn


def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS invoices (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_type      TEXT NOT NULL,          -- 'invoice' or 'bid'
                order_number  TEXT NOT NULL,
                date          TEXT,                   -- YYYY-MM-DD
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

            -- Index for fast description search
            CREATE INDEX IF NOT EXISTS idx_items_description
                ON invoice_items (description COLLATE NOCASE);

            CREATE INDEX IF NOT EXISTS idx_items_item_number
                ON invoice_items (item_number);

            CREATE INDEX IF NOT EXISTS idx_items_supplier
                ON invoice_items (supplier);
        """)


def save_parsed_document(parsed: dict, filename: str = "") -> int:
    """
    Insert a parsed PDF result into the DB.
    Returns the new invoice id.
    """
    with get_conn() as conn:
        # Check for duplicate — same order_number + doc_type
        existing = conn.execute(
            "SELECT id FROM invoices WHERE order_number = ? AND doc_type = ?",
            (parsed["order_number"], parsed["doc_type"])
        ).fetchone()

        if existing:
            return -1  # signal: already imported

        cur = conn.execute(
            """INSERT INTO invoices (doc_type, order_number, date, job_name, supplier, filename)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                parsed["doc_type"],
                parsed["order_number"],
                parsed.get("date", ""),
                parsed.get("job_name", ""),
                parsed.get("supplier", "LPS"),
                filename,
            )
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
            rows
        )
        return invoice_id


def search_items(query: str, supplier: Optional[str] = None, limit: int = 200) -> list[dict]:
    """
    Full-text search across description and item_number.
    Returns list of dicts with latest price per description.
    """
    sql = """
        SELECT
            ii.description                        AS "Description",
            ii.item_number                        AS "Item Number",
            ii.uom                                AS "Unit",
            ii.unit_price                         AS "Price per Unit",
            inv.date                              AS "Date",
            inv.order_number                      AS "Invoice No.",
            ii.supplier                           AS "Supply"
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

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_latest_prices(supplier: Optional[str] = None) -> list[dict]:
    """
    Returns the latest price for every unique description
    (used to populate the catalog for autocomplete).
    """
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

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def list_invoices() -> list[dict]:
    """Return all imported documents, newest first."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, doc_type, order_number, date, job_name,
                      supplier, filename, imported_at,
                      (SELECT COUNT(*) FROM invoice_items WHERE invoice_id = invoices.id) AS item_count
               FROM invoices ORDER BY imported_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def delete_invoice(invoice_id: int):
    """Delete an invoice and all its items (CASCADE handles items)."""
    with get_conn() as conn:
        conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
