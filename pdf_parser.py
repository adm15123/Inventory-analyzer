"""
pdf_parser.py — Multi-supplier PDF Parser
Handles:
  LPS (Lion Plumbing Supply): Sales Order Acknowledgement, Bid Proposal
  BPS (Berger Plumbing Supply): Invoice (Ticket)

Usage:
    from pdf_parser import parse_pdf
    result = parse_pdf("path/to/file.pdf", supplier="LPS")
    result = parse_pdf("path/to/file.pdf", supplier="BPS")
    # result = {
    #   "doc_type": "invoice" | "bid",
    #   "order_number": "3986708",
    #   "date": "2026-04-07",
    #   "job_name": "BH PRINCETON",
    #   "supplier": "LPS" | "BPS",
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
UOM_GROUP   = r'(?:EA|LF|FT|BX|PR|CS|GL|LB|SF|SQ|UN|RL|PK|ST|BD|CY|TN)'

def _parse_date(raw: str) -> str:
    """Normalise various date formats to YYYY-MM-DD."""
    raw = raw.strip()
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%m-%d-%y", "%m-%d-%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _clean_price(raw: str) -> float:
    """Remove commas and convert to float."""
    try:
        return float(str(raw).replace(",", ""))
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


# ─── LPS Invoice parser ──────────────────────────────────────────────────────

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


def _parse_lps_invoice(pdf) -> dict:
    items = []
    order_number = ""
    date_str = ""
    job_name = ""

    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text() or ""

        if page_num == 0:
            m = re.search(r'\b(\d{7})\b', text)
            if m:
                order_number = m.group(1)

            m = re.search(r'(\d{1,2}/\d{2}/\d{2,4})', text)
            if m:
                date_str = _parse_date(m.group(1))

            m = re.search(r'SHIPPING METHOD\s*\n(.+?)\n', text, re.DOTALL)
            if m:
                job_line = m.group(1).strip()
                parts = job_line.split()
                if len(parts) >= 2 and not parts[1][0].isdigit():
                    job_name = f"{parts[0]} {parts[1]}"
                elif parts:
                    job_name = parts[0]

        seen_lines = set()
        for line in text.split('\n'):
            line = line.strip()
            m = INVOICE_LINE_RE.match(line)
            if m:
                line_no = m.group(1)
                if line_no in seen_lines:
                    continue
                seen_lines.add(line_no)
                items.append({
                    "item_number": m.group(2),
                    "description": m.group(3).strip(),
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


# ─── LPS Bid parser ──────────────────────────────────────────────────────────

# Matches lines like:
#   60 70 EA T2473EPBN 85.0900 5,956.30
BID_LINE_RE = re.compile(
    r'^(\d+)\s+'                            # line number
    r'(\d+)\s+'                             # quantity
    + UOM_PATTERN + r'\s+'                  # unit of measure
    r'(\S+)\s+'                             # SKU / item number
    r'([\d,]+\.\d{2,4})\s+'               # net unit price
    r'([\d,]+\.\d{2})'                     # extended price
)

SKIP_RE = re.compile(r'^[*\-]{3,}|^(FREIGHT|ALLOW|PLEASE|NON-CANCEL|NO REFUND|---)', re.IGNORECASE)


def _parse_lps_bid(pdf) -> dict:
    items = []
    bid_number = ""
    date_str = ""
    job_name = ""

    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lines = text.split('\n')

        if page_num == 0:
            m = re.search(r'BID NUMBER[:\s]+(\d+)', text, re.IGNORECASE)
            if m:
                bid_number = m.group(1)

            m = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', text)
            if m:
                date_str = _parse_date(m.group(1))

            m = re.search(r'BID PROPOSAL\s+\S+\s*\n(.+?)\n', text)
            if m:
                job_name = m.group(1).strip()

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            m = BID_LINE_RE.match(line)
            if m:
                sku = m.group(4).lstrip("/")
                description = sku
                j = i + 1
                while j < len(lines):
                    candidate = lines[j].strip()
                    if candidate and not SKIP_RE.match(candidate):
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


# ─── LPS entry point ────────────────────────────────────────────────────────

def parse_lps_pdf(filepath: str) -> dict:
    """Parse a Lion Plumbing Supply PDF (invoice or bid)."""
    with pdfplumber.open(filepath) as pdf:
        first_text = pdf.pages[0].extract_text() or ""
        doc_type = _detect_doc_type(first_text)
        if doc_type == "invoice":
            return _parse_lps_invoice(pdf)
        elif doc_type == "bid":
            return _parse_lps_bid(pdf)
        else:
            raise ValueError(
                "Unrecognised LPS PDF format. "
                "Expected 'SALES ORDER ACKNOWLEDGEMENT' or 'BID PROPOSAL'."
            )


# ─── Berger (BPS) Invoice parser ─────────────────────────────────────────────
#
# Actual column layout (from observed PDFs):
#   Quantity  Item No  Description  Price Sell  Unit  Ext Price
#   1         CCMA10   ADAPTER CxM 1"  7.55  EACH  7.55
#
# Unit is a full uppercase word (EACH, FOOT, etc.), not the short codes used by LPS.
# Some descriptions wrap onto the next line (e.g. "BUSHING", "MIFA", "FEM").

BERGER_LINE_RE = re.compile(
    r'^(\d+)\s+'                           # quantity (integer)
    r'(\S+)\s+'                            # item number
    r'(.+?)\s+'                            # description (lazy — stops before price)
    r'([\d,]+\.\d{2,4})\s+'              # price sell
    r'([A-Z]{2,})\s+'                     # unit word (EACH, FOOT, …)
    r'([\d,]+\.\d{2})\s*$'               # ext price at end of line
)

_BERGER_HEADER_RE = re.compile(r'Quantity\s+Item\s*No', re.IGNORECASE)
_BERGER_STOP_RE   = re.compile(r'Total\s+line\s+items|Sub-?Total', re.IGNORECASE)
# Captures full ticket number including optional suffix, e.g. "473658-01"
_BERGER_TICKET_NO = re.compile(r'Ticket\s*No\s*:\s*([\w\-]+)', re.IGNORECASE)
_BERGER_TICKET_DT = re.compile(r'Ticket\s*Date\s*:\s*(\d{1,2}/\d{1,2}/\d{2,4})', re.IGNORECASE)


def parse_berger_pdf(filepath: str) -> dict:
    """Parse a Berger Plumbing Supply invoice (Ticket format)."""
    order_number = ""
    date_str = ""
    job_name = ""
    items = []

    with pdfplumber.open(filepath) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = text.split('\n')

            if page_num == 0:
                m = _BERGER_TICKET_NO.search(text)
                if m:
                    order_number = m.group(1)
                m = _BERGER_TICKET_DT.search(text)
                if m:
                    date_str = _parse_date(m.group(1))

            in_items = False
            i = 0
            while i < len(lines):
                stripped = lines[i].strip()
                i += 1

                if not in_items:
                    if _BERGER_HEADER_RE.search(stripped):
                        in_items = True
                    continue

                if _BERGER_STOP_RE.search(stripped):
                    break

                if not stripped:
                    continue

                m = BERGER_LINE_RE.match(stripped)
                if m:
                    items.append({
                        "item_number": m.group(2),
                        "description": m.group(3).strip(),
                        "uom": m.group(5),
                        "quantity": int(m.group(1)),
                        "unit_price": _clean_price(m.group(4)),
                    })
                    # Look ahead for a wrapped description continuation line
                    # (a short non-data, non-stop line immediately following)
                    while i < len(lines):
                        cont = lines[i].strip()
                        if not cont:
                            i += 1
                            continue
                        if (not BERGER_LINE_RE.match(cont)
                                and not _BERGER_STOP_RE.search(cont)
                                and not _BERGER_HEADER_RE.search(cont)):
                            items[-1]["description"] += " " + cont
                            i += 1
                        break

    return {
        "doc_type": "invoice",
        "order_number": order_number,
        "date": date_str,
        "job_name": job_name,
        "supplier": "BPS",
        "items": items,
    }


# ─── Public entry point ──────────────────────────────────────────────────────

def parse_pdf(filepath: str, supplier: str = "LPS") -> dict:
    """
    Parse a supplier PDF and return structured data.
    supplier: "LPS" (Lion Plumbing Supply) or "BPS" (Berger Plumbing Supply)
    Returns dict with doc_type, order_number, date, job_name, supplier, items.
    """
    if supplier == "BPS":
        return parse_berger_pdf(filepath)
    return parse_lps_pdf(filepath)
