import hashlib
import io

import pymupdf
import pytest
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import validate_chain
from app.models.entities import AuditTrail, EvidenceDocument, ProcessingJob
from tests.conftest import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    INVESTIGATOR_1,
    INVESTIGATOR_2,
    TEST_ENGINE,
    client,
    login_headers,
)

CASE = {"case_id": "RTR-CASE-2026-001", "title": "Document Router Fixture", "description": "fixture"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_digital_pdf(n_pages: int = 1, footer: str = "") -> bytes:
    doc = pymupdf.open()
    for i in range(n_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Financial Fraud Investigation Brief {footer} {i + 1}", fontname="helv", fontsize=14)
        page.insert_text((72, 100), "Subject: Ramesh Gurjar", fontname="helv", fontsize=11)
        page.insert_text((72, 120), "Amount suspected: Rs 4,50,000", fontname="helv", fontsize=11)
    body = doc.tobytes()
    doc.close()
    return body


def _make_scanned_like_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect((72, 72, 200, 120), color=(0, 0, 0), width=1)
    body = doc.tobytes()
    doc.close()
    return body


def _make_xlsx(rows=None) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "CDR"
    ws.append(["phone_a", "phone_b", "duration_sec", "tower_id"])
    for row in rows or [
        ["+919999999999", "+919888888888", 120, "PUNE-01"],
        ["+919888888888", "+917003456789", 44, "PUNE-02"],
    ]:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _make_csv() -> bytes:
    header = "phone_a,phone_b,duration_sec,tower_id\n"
    rows = "+919999999999,+919888888888,120,PUNE-01\n+919888888888,+917003456789,44,PUNE-02\n"
    return (header + rows).encode("utf-8")


@pytest.fixture
def setup_case():
    inv1 = login_headers(INVESTIGATOR_1["username"], INVESTIGATOR_1["password"])
    resp = client.post("/api/v1/cases/create", json=CASE, headers=inv1)
    assert resp.status_code in (201, 409), resp.text
    return inv1


def _upload_and_process(setup_case, filename, data):
    up = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/upload",
        files={"file": (filename, data, "application/octet-stream")},
        headers=setup_case,
    )
    assert up.status_code == 201, up.text
    doc_id = up.json()["document_id"]
    proc = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/{doc_id}/process",
        headers=setup_case,
    )
    return up.json(), proc


def test_process_digital_pdf_routes_and_extracts(setup_case):
    data = _make_digital_pdf(footer="DIG-UNIQUE-BRIEF")
    up, proc = _upload_and_process(setup_case, "brief.pdf", data)
    assert proc.status_code == 201, proc.text
    body = proc.json()
    assert body["route"] == "NATIVE_DIGITAL_PDF"
    assert body["extraction_method"] == "pymupdf_native_text"
    assert body["status"] == "COMPLETED"
    assert body["ocr_pending_pages"] == []
    payload = body["evidence_payload"]
    assert payload["schema_version"] == "1.0.0"
    assert payload["doc_sha256"] == up["sha256"]
    assert payload["case_id"] == CASE["case_id"]
    assert payload["blocks"]
    block = payload["blocks"][0]
    assert block["block_id"].startswith("pdf-p")
    assert block["bbox"]
    assert "BRIEF" in block["text"]


def test_process_tabular_xlsx_routes_to_tabular(setup_case):
    data = _make_xlsx()
    up, proc = _upload_and_process(setup_case, "cdr.xlsx", data)
    assert proc.status_code == 201, proc.text
    body = proc.json()
    assert body["route"] == "TABULAR"
    assert body["extraction_method"] == "tabular_parser"
    assert body["status"] == "COMPLETED"
    payload = body["evidence_payload"]
    assert payload["blocks"]
    table = payload["blocks"][0]["structured_tables"][0]
    assert table["columns"] == ["phone_a", "phone_b", "duration_sec", "tower_id"]
    assert table["rows"][0][0] == "+919999999999"


def test_process_tabular_csv_routes_to_tabular(setup_case):
    data = _make_csv()
    up, proc = _upload_and_process(setup_case, "cdr.csv", data)
    assert proc.status_code == 201, proc.text
    body = proc.json()
    assert body["route"] == "TABULAR"
    assert body["status"] == "COMPLETED"
    table = body["evidence_payload"]["blocks"][0]["structured_tables"][0]
    assert table["rows"]



def test_process_scanned_pdf_marks_ocr_pending(setup_case):
    data = _make_scanned_like_pdf()
    up, proc = _upload_and_process(setup_case, "fir_scanned.pdf", data)
    assert proc.status_code == 201, proc.text
    body = proc.json()
    assert body["route"] == "SCANNED_VISUAL_PDF"
    assert body["extraction_method"] == "ocr_pending"
    assert body["status"] == "OCR_PENDING"
    assert body["ocr_pending_pages"] == [1]
    assert body["evidence_payload"]["blocks"] == []


def test_process_requires_auth(setup_case):
    resp = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/1/process",
    )
    assert resp.status_code == 401


def test_process_without_case_access_forbidden():
    data = _make_digital_pdf(footer="FORBIDDEN-PDF")
    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    up = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/upload",
        files={"file": ("forbidden.pdf", data, "application/octet-stream")},
        headers=inv2,
    )
    assert up.status_code == 403


def test_process_unknown_document_not_found(setup_case):
    proc = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/999999/process",
        headers=setup_case,
    )
    assert proc.status_code == 404


def test_process_audit_chain_valid(setup_case):
    data = _make_xlsx()
    up, proc = _upload_and_process(setup_case, "chain.xlsx", data)
    assert proc.status_code == 201, proc.text
    with Session(TEST_ENGINE) as db:
        valid, issue = validate_chain(db)
        assert valid is True, issue
        job = db.scalar(
            select(ProcessingJob).order_by(ProcessingJob.id.desc()).limit(1)
        )
        assert job is not None
        assert job.status == "COMPLETED"
        assert job.schema_version == "1.0.0"
        event_types = [row.action_type for row in db.query(AuditTrail).all()]
    assert "EVIDENCE_PROCESSED" in event_types