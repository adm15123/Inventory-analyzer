"""
pdf_parser.py — Lion Plumbing Supply PDF Parser
Handles two document types:
  1. Sales Order Acknowledgement (invoice)
  2. Bid Proposal

Usage:
    from pdf_parser import parse_pdf
    result = parse_pdf("path/to/file.pdf")
    # result = {
    #   "doc_type": "invoice" | "bid",
    #   "order_number": "3986708",
    #   "date": "2026-04-07",
    #   "job_name": "BH PRINCETON",
    #   "supplier": "LPS",
    #   "items": [
    #     {
    #       "item_number": "060600L",
    #       "description": "4 HXH PVCDWV COUPLING (25)",
    #       "uom": "EA",
    #       "quantity": 10,
    #       "unit_price": 3.2410,
    #     }, ...
    #   ]
    # }
"""

import re
import pdfplumber
from datetime import datetime
from typing import Optional


# ─── helpers ────────────────────────────────────────────────────────────────

UOM_PATTERN = r'(EA|LF|FT|BX|PR|CS|GL|LB|SF|SQ|UN|RL|PK|ST|BD|CY|TN)'

def _parse_date(raw: str) -> str:
    """Normalise various date formats to YYYY-MM-DD."""
    raw = raw.strip()
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%m-%d-%y", "%m-%d-%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw  # return as-is if nothing matches


def _clean_price(raw: str) -> float:
    """Remove commas and convert to float."""
    try:
        return float(raw.replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def _detect_doc_type(text: str) -> str:
    """Return 'invoice', 'bid', or 'unknown'."""
    upper = text.upper()
    if "SALES ORDER ACKNOWLEDGEMENT" in upper:
        return "invoice"
    if "BID PROPOSAL" in upper:
        return "bid"
    return "unknown"


# ─── Invoice parser ─────────────────────────────────────────────────────────

# Matches lines like:
#   001 060600L 4 HXH PVCDWV COUPLING (25) EA 10 10 0 3.2410 32.41
INVOICE_LINE_RE = re.compile(
    r'^(\d{3})\s+'                          # 3-digit line number
    r'(\S+)\s+'                             # item/SKU number
    r'(.+?)\s+'                             # description (lazy)
    + UOM_PATTERN + r'\s+'                  # unit of measure
    r'(\d+)\s+'                             # ordered qty
    r'(\d+)\s+'                             # shipped qty
    r'[\dV]\s+'                             # B/O flag
    r'([\d.]+)\s+'                          # unit price
    r'([\d,]+\.\d{2})'                      # net price
)


def _parse_invoice(pdf) -> dict:
    items = []
    order_number = ""
    date_str = ""
    job_name = ""

    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text() or ""

        # Extract header metadata from first page only
        if page_num == 0:
            # Order number — 7-digit number near top
            m = re.search(r'\b(\d{7})\b', text)
            if m:
                order_number = m.group(1)

            # Date — first m/dd/yy or m/dd/yyyy pattern
            m = re.search(r'(\d{1,2}/\d{2}/\d{2,4})', text)
            if m:
                date_str = _parse_date(m.group(1))

            # Job name — line after "SHIPPING METHOD" header row
            m = re.search(
                r'SHIPPING METHOD\s*\n(.+?)\n',
                text, re.DOTALL
            )
            if m:
                # e.g. "BH PRINCETON 100100 WS WS 4/07/26 OUR TRUCK"
                job_line = m.group(1).strip()
                job_name = job_line.split()[0] if job_line else ""
                # grab first two tokens as job name if second isn't numeric
                parts = job_line.split()
                if len(parts) >= 2 and not parts[1][0].isdigit():
                    job_name = f"{parts[0]} {parts[1]}"

        # Parse item lines
        seen_lines = set()
        for line in text.split('\n'):
            line = line.strip()
            m = INVOICE_LINE_RE.match(line)
            if m:
                line_no = m.group(1)
                if line_no in seen_lines:
                    continue
                seen_lines.add(line_no)

                # Clean up description — remove trailing pack-size like (25)
                description = m.group(3).strip()

                items.append({
                    "item_number": m.group(2),
                    "description": description,
                    "uom": m.group(4),
                    "quantity": int(m.group(6)),   # shipped qty
                    "unit_price": _clean_price(m.group(7)),
                })

    return {
        "doc_type": "invoice",
        "order_number": order_number,
        "date": date_str,
        "job_name": job_name,
        "supplier": "LPS",
        "items": items,
    }


# ─── Bid parser ─────────────────────────────────────────────────────────────

# Matches lines like:
#   60 70 EA T2473EPBN 85.0900 5,956.30
BID_LINE_RE = re.compile(
    r'^(\d+)\s+'                            # line number
    r'(\d+)\s+'                             # quantity
    + UOM_PATTERN + r'\s+'                  # unit of measure
    r'(\S+)\s+'                             # SKU / item number
    r'([\d,]+\.\d{2,4})\s+'                # net unit price
    r'([\d,]+\.\d{2})'                      # extended price
)

# Lines to skip when looking for description after SKU line
SKIP_RE = re.compile(r'^[*\-]{3,}|^(FREIGHT|ALLOW|PLEASE|NON-CANCEL|NO REFUND|---)', re.IGNORECASE)


def _parse_bid(pdf) -> dict:
    items = []
    bid_number = ""
    date_str = ""
    job_name = ""

    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lines = text.split('\n')

        if page_num == 0:
            # Bid number — 7-digit number
            m = re.search(r'\b(\d{7})\b', text)
            if m:
                bid_number = m.group(1)

            # Date — nn/nn/nn
            m = re.search(r'(\d{2}/\d{2}/\d{2,4})', text)
            if m:
                date_str = _parse_date(m.group(1))

            # Job name — line after "BID PROPOSAL" header
            m = re.search(r'BID PROPOSAL\s+\S+\s*\n(.+?)\n', text)
            if m:
                job_name = m.group(1).strip()

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            m = BID_LINE_RE.match(line)
            if m:
                sku = m.group(4)

                # Look ahead for description line (next non-empty, non-noise line)
                description = sku  # fallback
                j = i + 1
                while j < len(lines):
                    candidate = lines[j].strip()
                    if candidate and not SKIP_RE.match(candidate):
                        # Make sure it's not another data line
                        if not BID_LINE_RE.match(candidate):
                            description = candidate
                        break
                    j += 1

                items.append({
                    "item_number": sku,
                    "description": description,
                    "uom": m.group(3),
                    "quantity": int(m.group(2)),
                    "unit_price": _clean_price(m.group(5)),
                })
            i += 1

    return {
        "doc_type": "bid",
        "order_number": bid_number,
        "date": date_str,
        "job_name": job_name,
        "supplier": "LPS",
        "items": items,
    }


# ─── Public entry point ─────────────────────────────────────────────────────

def parse_pdf(filepath: str) -> dict:
    """
    Parse a Lion Plumbing Supply PDF (invoice or bid).
    Returns a dict with doc_type, order_number, date, job_name, supplier, items.
    Raises ValueError if the document type cannot be detected.
    """
    with pdfplumber.open(filepath) as pdf:
        # Read first page text to detect type
        first_text = pdf.pages[0].extract_text() or ""
        doc_type = _detect_doc_type(first_text)

        if doc_type == "invoice":
            return _parse_invoice(pdf)
        elif doc_type == "bid":
            return _parse_bid(pdf)
        else:
            raise ValueError(
                "Unrecognised PDF format. "
                "Expected 'SALES ORDER ACKNOWLEDGEMENT' or 'BID PROPOSAL'."
            )
