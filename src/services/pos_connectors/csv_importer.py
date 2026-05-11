"""
CSV Importer — Handles file upload and parsing for non-API POS systems.

For Tier 3-5 systems with auth_type == "csv_only", merchants export data
manually (or via email report) and upload CSVs to Meridian. This module
maps vendor-specific columns to Meridian's universal schema using the
csv_columns dict from the registry.

Supports: CSV, TSV, Excel (.xlsx), and pipe-delimited.
"""
import csv
import io
import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger("meridian.pos.csv_importer")


class CSVImporter:

    def __init__(self, system_key: str, csv_columns: dict[str, str]):
        self._system_key = system_key
        self._columns = csv_columns
        self._errors: list[str] = []

    @property
    def errors(self) -> list[str]:
        return list(self._errors)

    def parse(self, file_content: bytes | str, filename: str = "") -> list[dict]:
        self._errors = []

        if isinstance(file_content, bytes):
            file_content = file_content.decode("utf-8-sig")

        ext = filename.rsplit(".", 1)[-1].lower() if filename else "csv"

        if ext in ("xlsx", "xls"):
            return self._parse_excel(file_content, filename)

        dialect = self._detect_dialect(file_content)
        reader = csv.DictReader(io.StringIO(file_content), dialect=dialect)

        records = []
        for i, row in enumerate(reader, start=2):
            try:
                record = self._map_row(row)
                if record:
                    records.append(record)
            except Exception as e:
                self._errors.append(f"Row {i}: {e}")
                if len(self._errors) > 100:
                    self._errors.append("Too many errors — stopped at row 100")
                    break

        logger.info(f"[{self._system_key}] Parsed {len(records)} records, {len(self._errors)} errors")
        return records

    def _detect_dialect(self, content: str) -> csv.Dialect:
        sample = content[:4096]
        try:
            return csv.Sniffer().sniff(sample, delimiters=",\t|;")
        except csv.Error:
            return csv.excel

    def _map_row(self, row: dict[str, str]) -> dict | None:
        mapped: dict[str, Any] = {"_source_system": self._system_key}

        for meridian_field, csv_header in self._columns.items():
            value = self._find_column(row, csv_header)
            if value is None:
                continue

            if meridian_field == "timestamp":
                mapped["timestamp"] = self._parse_date(value)
            elif meridian_field == "total_cents":
                mapped["total_cents"] = self._parse_money(value)
            elif meridian_field == "labor_hours":
                mapped["labor_hours"] = self._parse_float(value)
            else:
                mapped[meridian_field] = value.strip()

        if not mapped.get("transaction_id") and not mapped.get("timestamp"):
            return None

        return mapped

    def _find_column(self, row: dict[str, str], header: str) -> str | None:
        if header in row:
            return row[header]

        header_lower = header.lower().strip()
        for col_name, val in row.items():
            if col_name.lower().strip() == header_lower:
                return val

        for col_name, val in row.items():
            if header_lower in col_name.lower():
                return val

        return None

    def _parse_date(self, value: str) -> str | None:
        if not value or not value.strip():
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y",
            "%m/%d/%y %H:%M",
            "%m/%d/%y",
        ]

        value = value.strip()
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue

        return value

    def _parse_money(self, value: str) -> int:
        if not value:
            return 0
        cleaned = re.sub(r"[^\d.\-]", "", value.strip())
        if not cleaned:
            return 0
        try:
            return int(round(float(cleaned) * 100))
        except (ValueError, OverflowError):
            return 0

    def _parse_float(self, value: str) -> float:
        if not value:
            return 0.0
        cleaned = re.sub(r"[^\d.\-]", "", value.strip())
        try:
            return float(cleaned)
        except (ValueError, OverflowError):
            return 0.0

    def _parse_excel(self, file_content: str | bytes, filename: str) -> list[dict]:
        try:
            import openpyxl
        except ImportError:
            self._errors.append("openpyxl not installed — cannot parse Excel files")
            return []

        try:
            if isinstance(file_content, str):
                file_content = file_content.encode("latin-1")

            wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
            ws = wb.active
            if ws is None:
                self._errors.append("No active worksheet found")
                return []

            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return []

            headers = [str(h) if h else "" for h in rows[0]]
            records = []

            for i, row in enumerate(rows[1:], start=2):
                row_dict = {headers[j]: str(cell) if cell is not None else "" for j, cell in enumerate(row) if j < len(headers)}
                try:
                    record = self._map_row(row_dict)
                    if record:
                        records.append(record)
                except Exception as e:
                    self._errors.append(f"Row {i}: {e}")

            return records
        except Exception as e:
            self._errors.append(f"Excel parse error: {e}")
            return []


def import_csv_for_system(
    system_key: str,
    csv_columns: dict[str, str],
    file_content: bytes | str,
    filename: str = "",
) -> tuple[list[dict], list[str]]:
    importer = CSVImporter(system_key, csv_columns)
    records = importer.parse(file_content, filename)
    return records, importer.errors
