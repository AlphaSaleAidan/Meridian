"""
OCR Service — Extract structured data from receipts, invoices, and menus.

Uses PaddleOCR for text extraction, then LLM for structure parsing.
Supports: receipt photos, invoice PDFs, menu images.

Extracted costs are wired into the inventory agent for cost tracking.
"""
import logging
import re
from typing import Any, Optional

logger = logging.getLogger("meridian.documents.ocr")

_ocr_engine = None


def _get_ocr():
    """Lazy-load PaddleOCR to avoid heavy import at startup."""
    global _ocr_engine
    if _ocr_engine is not None:
        return _ocr_engine

    try:
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        return _ocr_engine
    except ImportError:
        logger.warning("paddleocr not installed — OCR unavailable")
        return None


def extract_text(image_path: str) -> list[str]:
    """Extract raw text lines from an image."""
    ocr = _get_ocr()
    if not ocr:
        return []

    result = ocr.ocr(image_path, cls=True)
    lines = []
    if result and result[0]:
        for line in result[0]:
            text = line[1][0] if line[1] else ""
            if text.strip():
                lines.append(text.strip())
    return lines


def parse_receipt(lines: list[str]) -> dict[str, Any]:
    """Parse receipt text into structured data."""
    items = []
    total_cents = 0
    vendor = ""
    date_str = ""

    money_pattern = re.compile(r"\$?\d+\.\d{2}")
    date_pattern = re.compile(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}")

    for i, line in enumerate(lines):
        if i == 0 and not money_pattern.search(line):
            vendor = line

        date_match = date_pattern.search(line)
        if date_match and not date_str:
            date_str = date_match.group()

        money_match = money_pattern.findall(line)
        if money_match:
            amount_str = money_match[-1].replace("$", "")
            amount_cents = int(float(amount_str) * 100)

            lower = line.lower()
            if any(kw in lower for kw in ("total", "amount due", "balance")):
                total_cents = amount_cents
            elif any(kw in lower for kw in ("tax", "tip", "gratuity")):
                continue
            else:
                name = money_pattern.sub("", line).strip().rstrip("$. ")
                if name and len(name) > 1:
                    items.append({
                        "name": name,
                        "price_cents": amount_cents,
                        "quantity": 1,
                    })

    if not total_cents and items:
        total_cents = sum(i["price_cents"] for i in items)

    return {
        "type": "receipt",
        "vendor": vendor,
        "date": date_str,
        "items": items,
        "total_cents": total_cents,
        "raw_lines": len(lines),
    }


def parse_invoice(lines: list[str]) -> dict[str, Any]:
    """Parse invoice text into structured data."""
    items = []
    total_cents = 0
    invoice_number = ""
    vendor = ""

    money_pattern = re.compile(r"\$?\d{1,3}(?:,\d{3})*\.\d{2}")
    invoice_pattern = re.compile(r"(?:inv|invoice|#)\s*[:\-]?\s*(\w+)", re.IGNORECASE)

    for i, line in enumerate(lines):
        if i < 3 and not money_pattern.search(line):
            if not vendor:
                vendor = line

        inv_match = invoice_pattern.search(line)
        if inv_match and not invoice_number:
            invoice_number = inv_match.group(1)

        money_match = money_pattern.findall(line)
        if money_match:
            amount_str = money_match[-1].replace("$", "").replace(",", "")
            amount_cents = int(float(amount_str) * 100)

            lower = line.lower()
            if any(kw in lower for kw in ("total", "amount due", "balance due", "grand total")):
                total_cents = amount_cents
            elif any(kw in lower for kw in ("subtotal", "sub total")):
                if not total_cents:
                    total_cents = amount_cents
            elif any(kw in lower for kw in ("tax", "shipping", "freight")):
                continue
            else:
                name = money_pattern.sub("", line).strip().rstrip("$. ")
                if name and len(name) > 1:
                    items.append({
                        "name": name,
                        "unit_cost_cents": amount_cents,
                        "quantity": 1,
                    })

    return {
        "type": "invoice",
        "vendor": vendor,
        "invoice_number": invoice_number,
        "items": items,
        "total_cents": total_cents,
        "raw_lines": len(lines),
    }


def parse_menu(lines: list[str]) -> dict[str, Any]:
    """Parse menu photo into items with prices."""
    items = []
    money_pattern = re.compile(r"\$?\d+\.\d{2}")
    current_category = ""

    for line in lines:
        money_match = money_pattern.findall(line)
        if money_match:
            price_str = money_match[-1].replace("$", "")
            price_cents = int(float(price_str) * 100)
            name = money_pattern.sub("", line).strip().rstrip("$. -")
            if name and len(name) > 1:
                items.append({
                    "name": name,
                    "price_cents": price_cents,
                    "category": current_category,
                })
        elif line.isupper() or (len(line) < 30 and not any(c.isdigit() for c in line)):
            current_category = line

    return {
        "type": "menu",
        "items": items,
        "categories": list({i["category"] for i in items if i["category"]}),
        "raw_lines": len(lines),
    }


async def scan_document(
    image_path: str,
    doc_type: str = "auto",
) -> dict[str, Any]:
    """Scan a document and return structured data.

    Args:
        image_path: Path to image file
        doc_type: "receipt", "invoice", "menu", or "auto"
    """
    lines = extract_text(image_path)
    if not lines:
        return {"type": doc_type, "error": "No text detected", "items": [], "raw_lines": 0}

    if doc_type == "auto":
        text_lower = " ".join(lines[:5]).lower()
        if any(kw in text_lower for kw in ("invoice", "bill to", "purchase order")):
            doc_type = "invoice"
        elif any(kw in text_lower for kw in ("menu", "appetizer", "entree", "dessert")):
            doc_type = "menu"
        else:
            doc_type = "receipt"

    if doc_type == "receipt":
        return parse_receipt(lines)
    elif doc_type == "invoice":
        return parse_invoice(lines)
    elif doc_type == "menu":
        return parse_menu(lines)
    else:
        return parse_receipt(lines)
