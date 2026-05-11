"""
Transaction Normalizer — Converts raw POS data into Meridian's universal schema.

Every POS system returns different field names, date formats, and structures.
This module maps all of them to MERIDIAN_TRANSACTION_SCHEMA — one canonical
format used by the analytics engine, swarm agents, and dashboards.

Includes vertical extensions:
  - Automotive: VIN, labor_hours, technician, RO type, parts vs labor split
  - Cannabis: METRC tags, state compliance IDs, product category, THC/CBD %
"""
import hashlib
import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger("meridian.pos.normalizer")

MERIDIAN_TRANSACTION_SCHEMA = {
    "id": "string",
    "source_system": "string",
    "source_id": "string",
    "org_id": "string",
    "location_id": "string",
    "timestamp": "datetime",
    "total_cents": "int",
    "subtotal_cents": "int",
    "tax_cents": "int",
    "tip_cents": "int",
    "discount_cents": "int",
    "payment_method": "string",
    "payment_status": "string",
    "order_type": "string",
    "items": [
        {
            "name": "string",
            "quantity": "int",
            "unit_price_cents": "int",
            "category": "string",
            "sku": "string",
        }
    ],
    "customer_name": "string",
    "customer_id": "string",
    "employee_name": "string",
    "employee_id": "string",
    "table_number": "string",
    "guest_count": "int",
    "raw_data": "dict",
    # Automotive extensions
    "vin": "string",
    "labor_hours": "float",
    "parts_cents": "int",
    "labor_cents": "int",
    "technician": "string",
    "ro_type": "string",
    "vehicle_year": "string",
    "vehicle_make": "string",
    "vehicle_model": "string",
    # Cannabis extensions
    "metrc_tag": "string",
    "compliance_id": "string",
    "thc_percent": "float",
    "cbd_percent": "float",
    "product_category": "string",
    "weight_grams": "float",
    "batch_id": "string",
}


def normalize_transaction(
    raw: dict,
    system_key: str,
    org_id: str = "",
    location_id: str = "",
) -> dict:
    normalized: dict[str, Any] = {
        "source_system": system_key,
        "org_id": org_id,
        "location_id": location_id,
        "raw_data": raw,
    }

    normalized["source_id"] = _extract_id(raw, system_key)
    normalized["id"] = _generate_meridian_id(system_key, normalized["source_id"])
    normalized["timestamp"] = _extract_timestamp(raw)
    normalized["total_cents"] = _extract_cents(raw, _TOTAL_KEYS)
    normalized["subtotal_cents"] = _extract_cents(raw, _SUBTOTAL_KEYS)
    normalized["tax_cents"] = _extract_cents(raw, _TAX_KEYS)
    normalized["tip_cents"] = _extract_cents(raw, _TIP_KEYS)
    normalized["discount_cents"] = _extract_cents(raw, _DISCOUNT_KEYS)
    normalized["payment_method"] = _extract_string(raw, _PAYMENT_KEYS)
    normalized["payment_status"] = _extract_string(raw, _STATUS_KEYS) or "completed"
    normalized["order_type"] = _extract_string(raw, _ORDER_TYPE_KEYS) or "dine_in"
    normalized["items"] = _extract_items(raw)
    normalized["customer_name"] = _extract_string(raw, _CUSTOMER_KEYS)
    normalized["customer_id"] = _extract_string(raw, ["customer_id", "customerId", "guestId", "patron_id"])
    normalized["employee_name"] = _extract_string(raw, _EMPLOYEE_KEYS)
    normalized["employee_id"] = _extract_string(raw, ["employee_id", "employeeId", "staffId", "server_id"])
    normalized["table_number"] = _extract_string(raw, ["table", "tableNumber", "table_number", "table_name"])
    normalized["guest_count"] = _extract_int(raw, ["guests", "guestCount", "guest_count", "covers", "party_size"])

    _apply_automotive_extensions(raw, normalized)
    _apply_cannabis_extensions(raw, normalized)

    if not normalized["total_cents"] and normalized["subtotal_cents"]:
        normalized["total_cents"] = normalized["subtotal_cents"] + normalized["tax_cents"]

    return normalized


_TOTAL_KEYS = [
    "total", "totalAmount", "total_amount", "grandTotal", "grand_total",
    "Total", "amount", "Amount", "netTotal", "RO Total", "Invoice Total",
    "total_cents",
]
_SUBTOTAL_KEYS = [
    "subtotal", "subTotal", "sub_total", "netAmount", "net_amount",
    "pretaxTotal", "Subtotal",
]
_TAX_KEYS = [
    "tax", "taxAmount", "tax_amount", "totalTax", "total_tax", "Tax",
]
_TIP_KEYS = [
    "tip", "tipAmount", "tip_amount", "gratuity", "Tip",
]
_DISCOUNT_KEYS = [
    "discount", "discountAmount", "discount_amount", "totalDiscount", "Discount",
]
_PAYMENT_KEYS = [
    "payment_method", "paymentMethod", "paymentType", "payment_type",
    "tender", "Tender", "tenderType", "Pay Type", "Payment Type",
    "Payment", "Payment Method",
]
_STATUS_KEYS = [
    "status", "paymentStatus", "payment_status", "state", "orderStatus",
]
_ORDER_TYPE_KEYS = [
    "order_type", "orderType", "type", "diningOption", "dining_option",
    "serviceType", "service_type",
]
_CUSTOMER_KEYS = [
    "customer_name", "customerName", "customer", "guestName", "guest_name",
    "Customer Name", "patron",
]
_EMPLOYEE_KEYS = [
    "employee_name", "employeeName", "server", "Server", "cashier",
    "staff", "Technician", "technician", "Tech", "Assigned Tech",
]


def _extract_id(raw: dict, system_key: str) -> str:
    for key in ["id", "guid", "orderId", "order_id", "transactionId",
                "transaction_id", "checkId", "check_id", "receiptId",
                "receipt_id", "RO Number", "Invoice #", "Order ID",
                "Trans #", "Check Number", "Ticket #", "Receipt Number",
                "Transaction ID", "Sale ID", "source_id", "transaction_id"]:
        val = raw.get(key)
        if val:
            return str(val)
    return hashlib.md5(str(sorted(raw.items())).encode()).hexdigest()[:16]


def _generate_meridian_id(system_key: str, source_id: str) -> str:
    return f"txn_{system_key}_{source_id}"


def _extract_timestamp(raw: dict) -> str | None:
    for key in ["timestamp", "createdAt", "created_at", "date", "Date",
                "orderDate", "order_date", "closedAt", "closed_at",
                "Date/Time", "Date Closed", "Transaction Date",
                "Date Time", "Invoice Date", "Close Date", "Sale Date"]:
        val = raw.get(key)
        if val:
            return _parse_any_date(str(val))
    return None


def _parse_any_date(value: str) -> str | None:
    if not value:
        return None

    if re.match(r"^\d{10}$", value):
        return datetime.utcfromtimestamp(int(value)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if re.match(r"^\d{13}$", value):
        return datetime.utcfromtimestamp(int(value) / 1000).strftime("%Y-%m-%dT%H:%M:%SZ")

    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue

    return value


def _extract_cents(raw: dict, keys: list[str]) -> int:
    for key in keys:
        val = raw.get(key)
        if val is None:
            continue
        if isinstance(val, int) and key.endswith("_cents"):
            return val
        try:
            cleaned = re.sub(r"[^\d.\-]", "", str(val))
            if cleaned:
                return int(round(float(cleaned) * 100))
        except (ValueError, OverflowError):
            continue
    return 0


def _extract_string(raw: dict, keys: list[str]) -> str:
    for key in keys:
        val = raw.get(key)
        if val:
            return str(val).strip()
    return ""


def _extract_int(raw: dict, keys: list[str]) -> int:
    for key in keys:
        val = raw.get(key)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                continue
    return 0


def _extract_items(raw: dict) -> list[dict]:
    for key in ["items", "lineItems", "line_items", "orderItems",
                "order_items", "details", "products", "entries"]:
        items_raw = raw.get(key)
        if isinstance(items_raw, list):
            return [_normalize_item(item) for item in items_raw]

    items_str = raw.get("items") or raw.get("Items") or raw.get("Item") or raw.get("Menu Item")
    if isinstance(items_str, str) and items_str:
        return [{"name": items_str.strip(), "quantity": 1, "unit_price_cents": 0, "category": "", "sku": ""}]

    return []


def _normalize_item(item: dict) -> dict:
    if not isinstance(item, dict):
        return {"name": str(item), "quantity": 1, "unit_price_cents": 0, "category": "", "sku": ""}

    name = (
        item.get("name") or item.get("itemName") or item.get("item_name")
        or item.get("description") or item.get("productName") or ""
    )
    quantity = 1
    for qk in ["quantity", "qty", "count", "amount"]:
        if qk in item:
            try:
                quantity = int(item[qk])
            except (ValueError, TypeError):
                pass
            break

    price = 0
    for pk in ["price", "unitPrice", "unit_price", "amount", "cost"]:
        if pk in item:
            try:
                cleaned = re.sub(r"[^\d.\-]", "", str(item[pk]))
                price = int(round(float(cleaned) * 100))
            except (ValueError, OverflowError):
                pass
            break

    category = item.get("category") or item.get("categoryName") or item.get("group") or ""
    sku = item.get("sku") or item.get("barcode") or item.get("upc") or ""

    return {
        "name": str(name).strip(),
        "quantity": quantity,
        "unit_price_cents": price,
        "category": str(category).strip(),
        "sku": str(sku).strip(),
    }


def _apply_automotive_extensions(raw: dict, normalized: dict):
    vin = raw.get("vin") or raw.get("VIN") or raw.get("vehicle_vin") or ""
    if not vin:
        return

    normalized["vin"] = str(vin).strip().upper()

    for key in ["labor_hours", "Labour Hours", "Labor Hours", "Labor Hrs", "Hours"]:
        val = raw.get(key)
        if val is not None:
            try:
                normalized["labor_hours"] = float(re.sub(r"[^\d.]", "", str(val)))
            except ValueError:
                pass
            break

    for key in ["technician", "Technician", "Tech", "Assigned Tech", "tech_name"]:
        val = raw.get(key)
        if val:
            normalized["technician"] = str(val).strip()
            break

    parts = raw.get("parts_total") or raw.get("partsAmount") or raw.get("parts")
    if parts:
        try:
            normalized["parts_cents"] = int(round(float(re.sub(r"[^\d.\-]", "", str(parts))) * 100))
        except (ValueError, OverflowError):
            pass

    labor = raw.get("labor_total") or raw.get("laborAmount") or raw.get("labor")
    if labor:
        try:
            normalized["labor_cents"] = int(round(float(re.sub(r"[^\d.\-]", "", str(labor))) * 100))
        except (ValueError, OverflowError):
            pass

    normalized["ro_type"] = raw.get("ro_type") or raw.get("type") or raw.get("service_type") or "general"

    if len(str(vin)) == 17:
        normalized["vehicle_year"] = _decode_vin_year(vin)


def _decode_vin_year(vin: str) -> str:
    year_codes = "ABCDEFGHJKLMNPRSTVWXY123456789"
    year_start = 2010
    char = vin[9].upper()
    idx = year_codes.find(char)
    if idx >= 0:
        return str(year_start + idx)
    return ""


def _apply_cannabis_extensions(raw: dict, normalized: dict):
    metrc = raw.get("metrc_tag") or raw.get("METRC Tag") or raw.get("Track ID") or ""
    if not metrc:
        compliance = raw.get("compliance_id") or raw.get("State License") or raw.get("License Number") or ""
        if not compliance:
            return
        normalized["compliance_id"] = str(compliance).strip()
        return

    normalized["metrc_tag"] = str(metrc).strip()
    normalized["compliance_id"] = (
        raw.get("compliance_id") or raw.get("State License")
        or raw.get("License Number") or raw.get("license") or ""
    )

    for key in ["thc_percent", "thc", "THC %", "THC"]:
        val = raw.get(key)
        if val is not None:
            try:
                normalized["thc_percent"] = float(re.sub(r"[^\d.]", "", str(val)))
            except ValueError:
                pass
            break

    for key in ["cbd_percent", "cbd", "CBD %", "CBD"]:
        val = raw.get(key)
        if val is not None:
            try:
                normalized["cbd_percent"] = float(re.sub(r"[^\d.]", "", str(val)))
            except ValueError:
                pass
            break

    normalized["product_category"] = (
        raw.get("product_category") or raw.get("category")
        or raw.get("type") or ""
    )

    for key in ["weight_grams", "weight", "net_weight", "grams"]:
        val = raw.get(key)
        if val is not None:
            try:
                normalized["weight_grams"] = float(re.sub(r"[^\d.]", "", str(val)))
            except ValueError:
                pass
            break

    normalized["batch_id"] = raw.get("batch_id") or raw.get("batch") or raw.get("lot") or ""
