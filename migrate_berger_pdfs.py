"""
migrate_berger_pdfs.py — Batch import Berger (BPS) invoice PDFs into Turso.

Usage:
    python migrate_berger_pdfs.py           # dry run — parse only, no saves
    python migrate_berger_pdfs.py --save    # parse and save to Turso
"""

import argparse
import os
import sys

FOLDER = os.path.join(os.path.dirname(__file__), "Invoices berger")


def main():
    parser = argparse.ArgumentParser(description="Migrate Berger PDF invoices to Turso.")
    parser.add_argument("--save", action="store_true", help="Save parsed documents to Turso.")
    args = parser.parse_args()

    if not os.path.isdir(FOLDER):
        print(f"ERROR: folder not found: {FOLDER}")
        sys.exit(1)

    pdf_files = sorted(
        f for f in os.listdir(FOLDER) if f.lower().endswith(".pdf")
    )

    if not pdf_files:
        print(f"No PDF files found in: {FOLDER}")
        sys.exit(0)

    from pdf_parser import parse_pdf

    if args.save:
        from db import init_db, save_parsed_document, refresh_catalog
        init_db()

    total_items = 0
    warnings = 0
    saved = 0
    skipped = 0
    errors = 0

    if not args.save:
        # Dry-run header
        print(f"\nDRY RUN — scanning: {FOLDER}\n")
        print(f"{'File':<35} {'Order No.':<15} {'Date':<12} {'Items':>5}  First Item")
        print("-" * 95)

    for filename in pdf_files:
        filepath = os.path.join(FOLDER, filename)
        try:
            result = parse_pdf(filepath, supplier="BPS")
        except Exception as e:
            if args.save:
                print(f"  ✗ ERROR   {filename}: {e}")
                errors += 1
            else:
                print(f"  {'ERROR':<34} — parse failed: {e}")
                warnings += 1
            continue

        order_no   = result.get("order_number", "") or ""
        date_str   = result.get("date", "") or ""
        items      = result.get("items", [])
        item_count = len(items)
        first_item = items[0]["description"][:40] if items else "(none)"

        warn_flags = []
        if item_count == 0:
            warn_flags.append("0 items")
        if not order_no:
            warn_flags.append("no order number")
        if not date_str:
            warn_flags.append("no date")
        if warn_flags:
            warnings += 1

        total_items += item_count

        if args.save:
            flag = "  [!] " + ", ".join(warn_flags) if warn_flags else ""
            try:
                invoice_id = save_parsed_document(result, filename=filename)
                if invoice_id == -1:
                    print(f"  SKIP   {filename}  (duplicate: {order_no}){flag}")
                    skipped += 1
                else:
                    print(f"  OK     {filename}  -> invoice_id={invoice_id}  ({item_count} items){flag}")
                    saved += 1
            except Exception as e:
                print(f"  ERROR  {filename}: {e}")
                errors += 1
        else:
            warn_str = f"  [!] {', '.join(warn_flags)}" if warn_flags else ""
            short_name = filename[:34]
            print(f"  {short_name:<34} {order_no:<15} {date_str:<12} {item_count:>5}  {first_item}{warn_str}")

    # Summary
    print()
    if args.save:
        print("-- Save summary ---------------------------------")
        print(f"  PDFs processed : {len(pdf_files)}")
        print(f"  Saved          : {saved}")
        print(f"  Skipped (dup)  : {skipped}")
        print(f"  Errors         : {errors}")
        print(f"  Total items    : {total_items}")
        if saved > 0:
            refresh_catalog()
            print("  Catalog refreshed.")
    else:
        print("-- Dry-run summary ------------------------------")
        print(f"  PDFs found     : {len(pdf_files)}")
        print(f"  Total items    : {total_items}")
        print(f"  Warnings       : {warnings}")
        print()
        print("Run with --save to import into Turso.")
    print()


if __name__ == "__main__":
    main()
