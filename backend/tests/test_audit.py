from app.core.audit import validate_chain
from tests.conftest import (
    INVESTIGATOR_1,
    INVESTIGATOR_2,
    client,
    login_headers,
    supabase,
)

CASE_3 = {"case_id": "CASE-2026-003", "title": "Audit Trails Must Exist", "description": "Test case"}


def _count_audit_events() -> int:
    return len(
        supabase.table("audit_trails").select("event_id").execute().data
    )


def test_audit_trail_logs_login_case_create_request_decide():
    before = _count_audit_events()

    inv1 = login_headers(INVESTIGATOR_1["username"], INVESTIGATOR_1["password"])
    client.post("/api/v1/cases/create", json=CASE_3, headers=inv1)

    inv2 = login_headers(INVESTIGATOR_2["username"], INVESTIGATOR_2["password"])
    client.post(f"/api/v1/cases/{CASE_3['case_id']}/request-access", headers=inv2)

    from tests.conftest import admin_headers, user_id_by_username

    inv2_user_id = user_id_by_username(INVESTIGATOR_2["username"])
    client.post(
        "/api/v1/admin/decide-access",
        json={"case_id": CASE_3["case_id"], "user_id": inv2_user_id, "decision": "APPROVE"},
        headers=admin_headers(),
    )

    after = _count_audit_events()
    assert after > before


def test_audit_chain_hash_is_consistent():
    ok, problem = validate_chain(supabase)
    assert ok, f"Audit chain broken: {problem}"


def test_tampering_breaks_chain():
    rows = (
        supabase.table("audit_trails")
        .select("*")
        .order("event_id", asc=True)
        .limit(1)
        .execute()
    ).data
    assert rows
    first = rows[0]

    ok_before, _ = validate_chain(supabase)
    assert ok_before

    supabase.table("audit_trails").update(
        {"metadata_json": {"tampered": True}}
    ).eq("event_id", first["event_id"]).execute()

    ok_after, problem = validate_chain(supabase)

    supabase.table("audit_trails").update(
        {"metadata_json": first["metadata_json"]}
    ).eq("event_id", first["event_id"]).execute()

    assert ok_after is False, "Chain should detect modification"
    assert problem is not None
