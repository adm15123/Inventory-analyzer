"""
migrate_excel_to_turso.py

Migrates all Excel supply data into Turso (or local SQLite fallback).
Run once from your project root:

    python migrate_excel_to_turso.py

Safe to re-run — skips duplicate invoice numbers per supplier.
"""

import os
import sys
from datetime import datetime
from data_utils import (
    load_default_file, load_supply2_file, load_supply3_file, load_supply4_file,
    get_current_dataframe,
)
from db import get_conn, USE_TURSO, _turso_execute, _turso_batch

import libsql_client  # only used if USE_TURSO

# ── Supplier metadata ─────────────────────────────────────────────────────────
SUPPLIES = [
    {
        "key":      "supply1",
        "code":     "BPS",
        "loader":   load_default_file,
        "item_col": "Item Number",
    },
    {
        "key":      "supply2",
        "code":     "S2",
        "loader":   load_supply2_file,
        "item_col": "Item No.",          # different column name in supply2
    },
    {
        "key":      "supply3",
        "code":     "LPS",
        "loader":   load_supply3_file,
        "item_col": "Item Number",
    },
    {
        "key":      "supply4",
        "code":     "BOND",
        "loader":   load_supply4_file,
        "item_col": "Item Number",
    },
]


def already_imported(order_number: str, supplier: str) -> bool:
    """Check if this invoice was already migrated."""
    sql    = "SELECT id FROM invoices WHERE order_number = ? AND supplier = ?"
    params = [order_number, supplier]
    if USE_TURSO:
        rows = _turso_execute(sql, params)
        return len(rows) > 0
    else:
        with get_conn() as conn:
            row = conn.execute(sql, (order_number, supplier)).fetchone()
            return row is not None


def insert_invoice(doc_type, order_number, date, supplier, filename) -> int:
    """Insert invoice header, return new id."""
    sql    = """INSERT INTO invoices (doc_type, order_number, date, job_name, supplier, filename)
                VALUES (?, ?, ?, ?, ?, ?)"""
    params = ["invoice", order_number, date, "", supplier, filename]

    if USE_TURSO:
        _turso_execute(sql, params)
        rows = _turso_execute(
            "SELECT id FROM invoices WHERE order_number = ? AND supplier = ? ORDER BY id DESC LIMIT 1",
            [order_number, supplier],
        )
        return rows[0]["id"]
    else:
        with get_conn() as conn:
            cur = conn.execute(sql, tuple(params))
            return cur.lastrowid


def insert_items_batch(rows: list):
    """Insert a batch of invoice_items rows."""
    sql = """INSERT INTO invoice_items
             (invoice_id, item_number, description, uom, quantity, unit_price, supplier)
             VALUES (?, ?, ?, ?, ?, ?, ?)"""
    if USE_TURSO:
        statements = [(sql, list(r)) for r in rows]
        _turso_batch(statements)
    else:
        with get_conn() as conn:
            conn.executemany(sql, rows)


def migrate_supply(supply: dict):
    """Migrate one supply's Excel data into the DB."""
    code     = supply["code"]
    item_col = supply["item_col"]

    print(f"\n── {code} ({supply['key']}) ──────────────────────────")

    # Load the dataframe
    supply["loader"]()
    df = get_current_dataframe(supply["key"])

    if df is None or df.empty:
        print(f"  ⚠ No data found, skipping.")
        return

    # Ensure Date column is usable
    if "Date" not in df.columns:
        print(f"  ⚠ No Date column, skipping.")
        return

    # Group rows by Invoice No. so each invoice becomes one row in `invoices`
    invoice_col = "Invoice No." if "Invoice No." in df.columns else None
    if invoice_col is None:
        # No invoice number column — treat all rows as one synthetic invoice
        df["_invoice"] = f"MIGRATED-{code}"
    else:
        df["_invoice"] = df[invoice_col].astype(str).str.strip()

    # Group by invoice number
    grouped    = df.groupby("_invoice")
    total      = len(grouped)
    skipped    = 0
    inserted   = 0

    for invoice_no, group in grouped:
        if already_imported(invoice_no, code):
            skipped += 1
            continue

        # Use the earliest date in this invoice group
        date_val = group["Date"].dropna()
        if date_val.empty:
            date_str = ""
        else:
            date_str = date_val.min().strftime("%Y-%m-%d")

        # Insert invoice header
        invoice_id = insert_invoice(
            doc_type     = "invoice",
            order_number = invoice_no,
            date         = date_str,
            supplier     = code,
            filename     = f"migrated_from_excel_{code}.xlsx",
        )

        # Build item rows
        item_rows = []
        for _, row in group.iterrows():
            item_rows.append((
                invoice_id,
                str(row.get(item_col, "") or "").strip(),
                str(row.get("Description", "") or "").strip(),
                str(row.get("Unit", "") or "").strip(),
                0,   # quantity not tracked in Excel history
                float(row.get("Price per Unit", 0) or 0),
                code,
            ))

        insert_items_batch(item_rows)
        inserted += 1

    print(f"  ✓ {inserted} invoices inserted, {skipped} already existed ({total} total)")


def main():
    print("=" * 55)
    print("  Excel → Turso Migration")
    print(f"  Mode: {'Turso cloud' if USE_TURSO else 'Local SQLite fallback'}")
    print("=" * 55)

    if not USE_TURSO:
        print("\n⚠  TURSO_URL not set — writing to local zamora.db instead.")
        print("   Set TURSO_URL and TURSO_TOKEN env vars to migrate to Turso.\n")

    for supply in SUPPLIES:
        migrate_supply(supply)

    print("\n✅ Migration complete!")

    # Summary
    sql = "SELECT supplier, COUNT(*) as invoices FROM invoices GROUP BY supplier"
    if USE_TURSO:
        rows = _turso_execute(sql)
    else:
        with get_conn() as conn:
            rows = [dict(r) for r in conn.execute(sql).fetchall()]

    print("\nInvoices in DB by supplier:")
    for r in rows:
        print(f"  {r['supplier']}: {r['invoices']} invoices")

    sql2 = "SELECT COUNT(*) as total FROM invoice_items"
    if USE_TURSO:
        total = _turso_execute(sql2)[0]["total"]
    else:
        with get_conn() as conn:
            total = conn.execute(sql2).fetchone()[0]

    print(f"\nTotal line items in DB: {total:,}")


if __name__ == "__main__":
    main()
