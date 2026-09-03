from tests.conftest import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    INVESTIGATOR_1,
    INVESTIGATOR_2,
    admin_headers,
    client,
    login_headers,
    user_id_by_username,
)

_counter = [0]


def _next_case_id() -> str:
    _counter[0] += 1
    return f"CASE-2026-{910 + _counter[0]}"


def _setup() -> str:
    case_id = _next_case_id()
    inv1 = login_headers(INVESTIGATOR_1["username"], INVESTIGATOR_1["password"])
    create = client.post(
        "/api/v1/cases/create",
        json={"case_id": case_id, "title": f"Admin Flow Case {case_id}"},
        headers=inv1,
    )
    assert create.status_code == 201, create.text

    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    req = client.post(f"/api/v1/cases/{case_id}/request-access", headers=inv2)
    assert req.status_code == 200, req.text
    return case_id


def _inv2_id() -> str:
    return user_id_by_username(INVESTIGATOR_2["username"])


def test_pending_requests_admin_only():
    _setup()
    admin = admin_headers()
    resp = client.get("/api/v1/admin/pending-requests", headers=admin)
    assert resp.status_code == 200
    items = resp.json()
    assert any(i["username"] == INVESTIGATOR_2["username"] for i in items)


def test_pending_requests_forbidden_for_investigator():
    _setup()
    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    resp = client.get("/api/v1/admin/pending-requests", headers=inv2)
    assert resp.status_code == 403


def test_pending_requests_requires_auth():
    resp = client.get("/api/v1/admin/pending-requests")
    assert resp.status_code == 401


def _decide(case_id: str, decision: str):
    admin = admin_headers()
    return client.post(
        "/api/v1/admin/decide-access",
        json={"case_id": case_id, "user_id": _inv2_id(), "decision": decision},
        headers=admin,
    )


def test_decide_access_approve_grants_workspace():
    case_id = _setup()
    resp = _decide(case_id, "APPROVE")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "APPROVED"

    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    ws = client.get(f"/api/v1/cases/{case_id}/workspace", headers=inv2)
    assert ws.status_code == 200
    assert ws.json()["access_status"] == "APPROVED"


def test_decide_access_reject_blocks_workspace():
    case_id = _setup()
    resp = _decide(case_id, "REJECT")
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    ws = client.get(f"/api/v1/cases/{case_id}/workspace", headers=inv2)
    assert ws.status_code == 403


def test_decide_access_invalid_decision():
    case_id = _setup()
    resp = _decide(case_id, "MAYBE")
    assert resp.status_code == 422


def test_admin_has_full_case_bypass():
    case_id = _setup()
    admin = admin_headers()
    resp = client.get(f"/api/v1/cases/{case_id}/workspace", headers=admin)
    assert resp.status_code == 200
    assert resp.json()["role"] == "ADMIN"


def test_rejected_access_can_be_re_requested():
    case_id = _setup()
    assert _decide(case_id, "REJECT").status_code == 200

    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    req = client.post(f"/api/v1/cases/{case_id}/request-access", headers=inv2)
    assert req.status_code == 200
    assert req.json()["status"] == "PENDING"


def test_approve_after_reject_reequest_grants_workspace():
    case_id = _setup()
    _decide(case_id, "REJECT")

    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    client.post(f"/api/v1/cases/{case_id}/request-access", headers=inv2)

    resp = client.post(
        "/api/v1/admin/decide-access",
        json={"case_id": case_id, "user_id": _inv2_id(), "decision": "APPROVE"},
        headers=admin_headers(),
    )
    assert resp.status_code == 200
    ws = client.get(f"/api/v1/cases/{case_id}/workspace", headers=inv2)
    assert ws.status_code == 200
    assert ws.json()["access_status"] == "APPROVED"
