import io
from typing import Any, Dict, List, Optional

import pandas as pd
from openpyxl import load_workbook

from app.services.mime_detection import (
    MIME_CSV,
    MIME_PDF,
    MIME_XLS,
    MIME_XLSX,
)


class ParseError(Exception):
    def __init__(self, detail: str, status_code: int = 422) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _safe_cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def parse_pdf_blocks(data: bytes) -> List[Dict[str, Any]]:
    """Extract text blocks with bbox from a native digital PDF (Branch 2)."""
    try:
        import pymupdf
    except ImportError as exc:  # pragma: no cover
        raise ParseError("PyMuPDF is not installed; cannot parse PDFs") from exc

    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # pymupdf raises FileDataError / others
        raise ParseError(f"Invalid or unreadable PDF: {exc}") from exc

    blocks: List[Dict[str, Any]] = []
    try:
        for page_number, page in enumerate(document, start=1):
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                bbox = block.get("bbox")
                text = ""
                for line in block.get("lines", []):
                    spans_text = "".join(span.get("text", "") for span in line.get("spans", []))
                    if spans_text:
                        text += spans_text + "\n"
                text = text.rstrip("\n")
                if not text.strip():
                    continue
                blocks.append(
                    {
                        "page_number": page_number,
                        "block_id": f"pdf-p{page_number}-b{len(blocks) + 1}",
                        "bbox": _normalize_bbox(bbox),
                        "text": text,
                    }
                )
    finally:
        document.close()
    return blocks


def _normalize_bbox(bbox: tuple) -> List[float]:
    if not bbox or len(bbox) != 4:
        return [0.0, 0.0, 0.0, 0.0]
    x0, y0, x1, y1 = bbox
    return [
        round(float(x0), 2),
        round(float(y0), 2),
        round(float(x1), 2),
        round(float(y1), 2),
    ]


def parse_tabular_blocks(data: bytes, mime_type: str) -> List[Dict[str, Any]]:
    """Extract rows from xlsx/xls/csv into a single tabular block (Branch 1)."""
    if mime_type == MIME_CSV:
        try:
            frame = pd.read_csv(io.BytesIO(data))
        except Exception as exc:
            raise ParseError(f"Could not parse CSV: {exc}") from exc
        return _frame_to_table(frame, "csv")

    if mime_type == MIME_XLSX:
        return _parse_xlsx(data, "xlsx")

    if mime_type == MIME_XLS:
        try:
            frame = pd.read_excel(io.BytesIO(data))
        except Exception as exc:
            raise ParseError(f"Could not parse XLS: {exc}") from exc
        return _frame_to_table(frame, "xls")

    raise ParseError(f"Unsupported tabular mime type: {mime_type}")


def _parse_xlsx(data: bytes, source: str) -> List[Dict[str, Any]]:
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise ParseError(f"Could not open XLSX workbook: {exc}") from exc

    tables: List[Dict[str, Any]] = []
    try:
        for sheet in workbook.worksheets:
            rows: List[List[Any]] = []
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    rows.append([_safe_cell(cell) for cell in row])
            if not rows:
                continue
            columns = [str(cell) if cell is not None else "" for cell in rows[0]]
            body = rows[1:]
            tables.append(
                {
                    "table_name": sheet.title,
                    "detected_language": "en",
                    "columns": columns,
                    "rows": body,
                }
            )
    finally:
        workbook.close()
    return _tables_to_blocks(tables, source)


def _frame_to_table(frame: pd.DataFrame, source: str) -> List[Dict[str, Any]]:
    tables = []
    columns = [str(c) for c in frame.columns]
    rows = frame.values.tolist()
    tables.append(
        {
            "table_name": "sheet1",
            "detected_language": "en",
            "columns": columns,
            "rows": rows,
        }
    )
    return _tables_to_blocks(tables, source)


def _tables_to_blocks(tables: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    for index, table in enumerate(tables, start=1):
        blocks.append(
            {
                "page_number": 1,
                "block_id": f"{source}-table-{index}",
                "bbox": [0.0, 0.0, 0.0, 0.0],
                "structured_tables": [table],
                "detected_language": table.get("detected_language", "en"),
            }
        )
    return blocks