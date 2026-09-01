import pytest

from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME, INVESTIGATOR_1, INVESTIGATOR_2, client, login_headers

CASE_1 = {"case_id": "CASE-2026-001", "title": "Financial Fraud Ring", "description": "Suspected circular fund transfers"}


def _create_case(headers, payload=CASE_1):
    return client.post("/api/v1/cases/create", json=payload, headers=headers)


def test_create_case_auto_grants_access_to_creator():
    inv1 = login_headers(INVESTIGATOR_1["username"], INVESTIGATOR_1["password"])
    resp = _create_case(inv1)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["case_id"] == CASE_1["case_id"]
    assert body["status"] == "OPEN"
    assert body["created_by_user_id"] > 0


def test_create_case_duplicate_id_conflict():
    inv1 = login_headers(INVESTIGATOR_1["username"], INVESTIGATOR_1["password"])
    resp = _create_case(inv1)
    assert resp.status_code == 409


def test_create_case_requires_auth():
    resp = client.post("/api/v1/cases/create", json=CASE_1)
    assert resp.status_code == 401


def test_create_case_invalid_id_pattern():
    inv1 = login_headers(INVESTIGATOR_1["username"], INVESTIGATOR_1["password"])
    resp = client.post("/api/v1/cases/create", json={**CASE_1, "case_id": "bad id!"}, headers=inv1)
    assert resp.status_code == 422


def test_workspace_without_access_forbidden():
    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    resp = client.get(f"/api/v1/cases/{CASE_1['case_id']}/workspace", headers=inv2)
    assert resp.status_code == 403


def test_workspace_unknown_case_not_found():
    inv1 = login_headers(INVESTIGATOR_1["username"], INVESTIGATOR_1["password"])
    resp = client.get("/api/v1/cases/CASE-NOPE-999/workspace", headers=inv1)
    assert resp.status_code == 404


def test_creator_can_open_workspace():
    inv1 = login_headers(INVESTIGATOR_1["username"], INVESTIGATOR_1["password"])
    resp = client.get(f"/api/v1/cases/{CASE_1['case_id']}/workspace", headers=inv1)
    assert resp.status_code == 200
    body = resp.json()
    assert body["case"]["case_id"] == CASE_1["case_id"]
    assert body["access_status"] == "APPROVED"


def test_request_access_creates_pending():
    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    resp = client.post(f"/api/v1/cases/{CASE_1['case_id']}/request-access", headers=inv2)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PENDING"


def test_request_access_duplicate_pending_conflict():
    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    resp = client.post(f"/api/v1/cases/{CASE_1['case_id']}/request-access", headers=inv2)
    assert resp.status_code == 409


def test_request_access_unknown_case():
    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    resp = client.post("/api/v1/cases/CASE-NOPE-999/request-access", headers=inv2)
    assert resp.status_code == 404


def test_admin_request_access_auto_granted():
    admin = login_headers(ADMIN_USERNAME, ADMIN_PASSWORD)
    resp = client.post(f"/api/v1/cases/{CASE_1['case_id']}/request-access", headers=admin)
    assert resp.status_code == 200
    assert "Administrators automatically have access" in resp.json()["detail"]