import hashlib

import pytest

from tests.conftest import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    INVESTIGATOR_1,
    INVESTIGATOR_2,
    TEST_ENGINE,
    client,
    login_headers,
)
from app.core.audit import validate_chain
from app.models.entities import AuditTrail
from sqlalchemy.orm import Session

CASE = {"case_id": "EVID-CASE-9001", "title": "Ingestion Fixture Case", "description": "fixture"}


def _valid_pdf() -> bytes:
    return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< >>\nendobj\ntrailer\n<< >>\n%%EOF\n"


def _valid_png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _valid_jpeg() -> bytes:
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01" + b"\x00" * 48


def _valid_tiff() -> bytes:
    return b"II*\x00\x08\x00\x00\x00\x00\x00\x00\x00" + b"\x00" * 16


def _valid_csv() -> bytes:
    return b"name,phone\r\nramesh,+91-9999999999\r\nsita,+91-9888888888\r\n"


def _valid_xls() -> bytes:
    return b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64


def _spoofed_exe_named_pdf() -> bytes:
    return b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 64


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def setup_case():
    inv1 = login_headers(INVESTIGATOR_1["username"], INVESTIGATOR_1["password"])
    resp = client.post("/api/v1/cases/create", json=CASE, headers=inv1)
    if resp.status_code not in (201, 409):
        assert False, resp.text
    return inv1


VALIDS = [
    ("scanned.pdf", _valid_pdf, "application/pdf"),
    ("scanned.png", _valid_png, "image/png"),
    ("scanned.jpg", _valid_jpeg, "image/jpeg"),
    ("photo.tiff", _valid_tiff, "image/tiff"),
    ("ledger.csv", _valid_csv, "text/csv"),
    ("spreadsheet.xls", _valid_xls, "application/vnd.ms-excel"),
]


@pytest.mark.parametrize("filename,builder,expected_mime", VALIDS)
def test_upload_valid_evidence(setup_case, filename, builder, expected_mime):
    data = builder()
    resp = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/upload",
        files={"file": (filename, data, "application/octet-stream")},
        headers=setup_case,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["filename"] == filename
    assert body["mime_type"] == expected_mime
    assert body["sha256"] == _sha256(data)
    assert body["size_bytes"] == len(data)
    assert isinstance(body["document_id"], int)


def test_upload_spoofed_exe_named_pdf_rejected(setup_case):
    data = _spoofed_exe_named_pdf()
    resp = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/upload",
        files={"file": ("evil.exe.pdf", data, "application/octet-stream")},
        headers=setup_case,
    )
    assert resp.status_code == 415


def test_upload_requires_auth(setup_case):
    data = _valid_pdf()
    resp = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/upload",
        files={"file": ("a.pdf", data, "application/octet-stream")},
    )
    assert resp.status_code == 401


def test_upload_without_case_access_forbidden():
    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    data = _valid_pdf()
    resp = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/upload",
        files={"file": ("a.pdf", data, "application/octet-stream")},
        headers=inv2,
    )
    assert resp.status_code == 403


def test_download_url_without_access_forbidden(setup_case):
    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    resp = client.get(f"/api/v1/cases/{CASE['case_id']}/evidence/1/download-url", headers=inv2)
    assert resp.status_code == 403


def test_stream_roundtrip_local_backend(setup_case):
    data = _valid_jpeg() + b"RT-UNIQUE-ROUNDTRIP"
    up = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/upload",
        files={"file": ("rt.jpg", data, "application/octet-stream")},
        headers=setup_case,
    )
    assert up.status_code == 201, up.text
    doc_id = up.json()["document_id"]
    stream = client.get(f"/api/v1/cases/{CASE['case_id']}/evidence/{doc_id}/stream", headers=setup_case)
    assert stream.status_code == 200, stream.text
    assert stream.content == data
    assert stream.headers["content-type"] == "image/jpeg"


def test_download_url_in_local_mode_rejected(setup_case):
    data = _valid_pdf() + b"LOCAL-MODE-URL-CHECK-PDF"
    up = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/upload",
        files={"file": ("local.pdf", data, "application/octet-stream")},
        headers=setup_case,
    )
    assert up.status_code == 201, up.text
    doc_id = up.json()["document_id"]
    resp = client.get(f"/api/v1/cases/{CASE['case_id']}/evidence/{doc_id}/download-url", headers=setup_case)
    assert resp.status_code == 409


def test_audit_chain_valid_after_evidence_events(setup_case):
    data = _valid_csv() + b"CHAIN-AUDIT-FIXTURE-UNIQUE-CSV"
    up = client.post(
        f"/api/v1/cases/{CASE['case_id']}/evidence/upload",
        files={"file": ("chain.csv", data, "application/octet-stream")},
        headers=setup_case,
    )
    assert up.status_code == 201, up.text
    with Session(TEST_ENGINE) as db:
        valid, issue = validate_chain(db)
        assert valid is True, issue
        event_types = [row.action_type for row in db.query(AuditTrail).all()]
    assert "EVIDENCE_UPLOADED" in event_types
    assert "CASE_CREATED" in event_types


def test_duplicate_upload_conflict(setup_case):
    data = _valid_tiff() + b"DUPLICATE-FIXTURE-UNIQUE-TIFF"
    kwargs = {
        "files": {"file": ("dup.tiff", data, "application/octet-stream")},
        "headers": setup_case,
    }
    first = client.post(f"/api/v1/cases/{CASE['case_id']}/evidence/upload", **kwargs)
    assert first.status_code == 201, first.text
    second = client.post(f"/api/v1/cases/{CASE['case_id']}/evidence/upload", **kwargs)
    assert second.status_code == 409