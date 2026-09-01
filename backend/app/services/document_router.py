from typing import Dict, List, Optional

import pymupdf

from app.services.mime_detection import (
    MIME_CSV,
    MIME_PDF,
    MIME_XLS,
    MIME_XLSX,
)
from app.services.parsers import parse_pdf_blocks, parse_tabular_blocks

ROUTE_TABULAR = "TABULAR"
ROUTE_NATIVE_PDF = "NATIVE_DIGITAL_PDF"
ROUTE_SCANNED = "SCANNED_VISUAL_PDF"

branch_by_mime = {
    MIME_CSV: ROUTE_TABULAR,
    MIME_XLS: ROUTE_TABULAR,
    MIME_XLSX: ROUTE_TABULAR,
}

_MIN_TEXT_CHARS = 20


def detect_pdf_route(data: bytes) -> str:
    """Determine whether a PDF is native-digital (has extractable text) or scanned."""
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Invalid or unreadable PDF: {exc}") from exc

    page_count = document.page_count
    pages_with_text = 0
    try:
        for page in document:
            page_text = page.get_text("text") or ""
            if len(page_text.strip()) >= _MIN_TEXT_CHARS:
                pages_with_text += 1
    finally:
        document.close()

    if page_count == 0:
        return ROUTE_SCANNED
    text_ratio = pages_with_text / max(page_count, 1)
    if text_ratio >= 0.5:
        return ROUTE_NATIVE_PDF
    return ROUTE_SCANNED


def route_document(mime_type: str, data: bytes) -> str:
    if mime_type == MIME_PDF:
        return detect_pdf_route(data)
    return branch_by_mime.get(mime_type, ROUTE_SCANNED)


class _DetectionIndex:
    def __init__(self) -> None:
        self.total_pages = 0
        self.native_pages = 0
        self.scanned_pages = 0
        self.total_blocks = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "total_pages": self.total_pages,
            "native_digital_pages": self.native_pages,
            "scanned_pages": self.scanned_pages,
            "total_blocks": self.total_blocks,
            "text_presence": {
                "native_pages_ratio": round(self.native_pages / self.total_pages, 4)
                if self.total_pages
                else 0.0,
                "scanned_pages_ratio": round(self.scanned_pages / self.total_pages, 4)
                if self.total_pages
                else 0.0,
            },
        }


def _unify_block(
    block: Dict[str, object],
    doc_sha256: str,
    method: str,
    confidence: float,
    schema_version: str,
) -> Dict[str, object]:
    return {
        "case_id": block.get("case_id"),
        "doc_sha256": doc_sha256,
        "page_number": block.get("page_number"),
        "block_id": block.get("block_id"),
        "bbox": block.get("bbox", [0.0, 0.0, 0.0, 0.0]),
        "extraction_method": method,
        "confidence": confidence,
        "detected_language": block.get("detected_language"),
        "text": block.get("text"),
        "structured_tables": block.get("structured_tables"),
        "schema_version": schema_version,
    }


def process_document(
    mime_type: str,
    data: bytes,
    doc_sha256: str,
    case_id: str,
    schema_version: str,
) -> Dict[str, object]:
    """Run the Document & Page Router and produce a Unified Evidence JSON.

    Returns the parsed evidence payload with branch routing metadata. Scanned
    pages that require OCR/HTR are reported with zero extraction blocks and a
    per-page OCR_PENDING flag so the async pipeline can pick them up later.
    """
    if mime_type in (MIME_CSV, MIME_XLS, MIME_XLSX):
        blocks = parse_tabular_blocks(data, mime_type)
        route = ROUTE_TABULAR
        method = "tabular_parser"
        confidence = 0.95
        detection_index = {
            "total_pages": 1,
            "native_digital_pages": 1,
            "scanned_pages": 0,
            "total_blocks": len(blocks),
            "text_presence": {
                "native_pages_ratio": 1.0,
                "scanned_pages_ratio": 0.0,
            },
        }
        ocr_pending_pages = []
    elif mime_type == MIME_PDF:
        route = detect_pdf_route(data)
        if route == ROUTE_NATIVE_PDF:
            blocks = parse_pdf_blocks(data)
            method = "pymupdf_native_text"
            confidence = 0.97
        else:
            blocks = []
            method = "ocr_pending"
            confidence = 0.0
        detection_index = _pdf_detection_index(data)
        ocr_pending_pages = detection_index.get("ocr_pending_pages", [])
    else:
        raise ValueError(f"Unsupported mime type for processing: {mime_type}")

    unified_blocks = [
        _unify_block(block | {"case_id": case_id}, doc_sha256, method, confidence, schema_version)
        for block in blocks
    ]

    return {
        "case_id": case_id,
        "doc_sha256": doc_sha256,
        "schema_version": schema_version,
        "route": route,
        "extraction_method": method,
        "detection_index": detection_index,
        "ocr_pending_pages": ocr_pending_pages,
        "blocks": unified_blocks,
    }


def _pdf_detection_index(data: bytes) -> Dict[str, object]:
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Invalid or unreadable PDF: {exc}") from exc

    total = document.page_count
    native = 0
    try:
        for page in document:
            page_text = page.get_text("text") or ""
            if len(page_text.strip()) >= _MIN_TEXT_CHARS:
                native += 1
    finally:
        document.close()

    scanned = total - native
    pending = list(range(1, total + 1)) if total else []
    if native == total:
        pending = []

    index = _DetectionIndex()
    index.total_pages = total
    index.native_pages = native
    index.scanned_pages = scanned
    result = index.to_dict()
    result["total_pages"] = total
    result["native_digital_pages"] = native
    result["scanned_pages"] = scanned
    result["ocr_pending_pages"] = pending
    return result