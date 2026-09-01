import os

from app.core.audit import compute_tamper_hash, validate_chain
from tests.conftest import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    INVESTIGATOR_1,
    INVESTIGATOR_2,
    TestingSessionLocal,
    client,
    login_headers,
)
from app.models.entities import AuditTrail

CASE_3 = {"case_id": "CASE-2026-003", "title": "Audit Trails Must Exist", "description": "Test case"}


def _count_audit_events() -> int:
    db = TestingSessionLocal()
    try:
        return db.query(AuditTrail).count()
    finally:
        db.close()


def test_audit_trail_logs_signup_login_case_create_request_decide():
    before = _count_audit_events()

    inv1 = login_headers(INVESTIGATOR_1["username"], INVESTIGATOR_1["password"])
    client.post("/api/v1/cases/create", json=CASE_3, headers=inv1)

    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    client.post(f"/api/v1/cases/{CASE_3['case_id']}/request-access", headers=inv2)

    from tests.conftest import admin_headers
    from app.models.entities import User

    db = TestingSessionLocal()
    inv2_user = db.query(User).filter(User.username == INVESTIGATOR_2["username"]).first()
    db.close()

    client.post(
        "/api/v1/admin/decide-access",
        json={"case_id": CASE_3["case_id"], "user_id": inv2_user.id, "decision": "APPROVE"},
        headers=admin_headers(),
    )

    after = _count_audit_events()
    assert after > before


def test_audit_chain_hash_is_consistent():
    ok, problem = validate_chain(TestingSessionLocal())
    assert ok, f"Audit chain broken: {problem}"


def test_tampering_breaks_chain():
    db = TestingSessionLocal()
    first_event = db.query(AuditTrail).order_by(AuditTrail.event_id.asc()).first()

    original_metadata = dict(first_event.metadata_json)
    ok_before, _ = validate_chain(db)
    assert ok_before

    first_event.metadata_json = {"tampered": True}
    db.commit()

    ok_after, problem = validate_chain(db)

    first_event.metadata_json = original_metadata
    db.commit()
    db.close()

    assert ok_after is False, "Chain should detect modification"
    assert problem is not None


def test_compute_tamper_hash_is_deterministic():
    from datetime import datetime

    class FakeEntry:
        event_id = 1
        user_id = 2
        case_id = "CASE-X"
        action_type = "TEST"
        metadata_json = {"b": [1, 2], "a": "x"}
        ip_address = "127.0.0.1"
        timestamp = datetime(2026, 1, 1, 12, 0, 0)

    h1 = compute_tamper_hash(FakeEntry(), "0" * 64)
    h2 = compute_tamper_hash(FakeEntry(), "0" * 64)
    assert h1 == h2
    assert os.environ.get("SECRET_KEY") is not None