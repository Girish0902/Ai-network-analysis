import os

os.environ["ADMIN_PASSWORD"] = "AdminTestPass2026!"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.supabase import get_supabase  # noqa: E402
from app.main import app  # noqa: E402

supabase = get_supabase()

client = TestClient(app)

ADMIN_USERNAME = "superadmin"
ADMIN_EMAIL = "admin@example.in"
ADMIN_BADGE = "ADM-0001"
ADMIN_PASSWORD = "AdminTestPass2026!"

INVESTIGATOR_1 = {
    "username": "inv_ravi",
    "email": "ravi@police.in",
    "password": "RaviPass2026!",
    "badge_number": "2026-CID-01842",
}
INVESTIGATOR_2 = {
    "username": "inv_sita",
    "email": "sita@police.in",
    "password": "SitaPass2026!",
    "badge_number": "2026-CCU-02917",
}

_TEST_USERNAMES = [ADMIN_USERNAME, INVESTIGATOR_1["username"], INVESTIGATOR_2["username"]]


def _cleanup_test_data() -> None:
    try:
        supabase.table("audit_trails").delete().neq("event_id", 0).execute()
    except Exception:
        pass
    try:
        supabase.table("processing_jobs").delete().neq("id", 0).execute()
    except Exception:
        pass
    try:
        supabase.table("evidence_documents").delete().neq("id", 0).execute()
    except Exception:
        pass
    try:
        supabase.table("case_accesses").delete().neq("id", 0).execute()
    except Exception:
        pass
    try:
        supabase.table("cases").delete().neq("id", 0).execute()
    except Exception:
        pass
    for username in _TEST_USERNAMES:
        profile = supabase.table("profiles").select("id").eq("username", username).execute()
        if profile.data:
            try:
                supabase.auth.admin.delete_user(profile.data[0]["id"])
            except Exception:
                pass
            supabase.table("profiles").delete().eq("id", profile.data[0]["id"]).execute()


def get_or_create_user(payload: dict, role: str):
    profile = (
        supabase.table("profiles")
        .select("*")
        .eq("username", payload["username"])
        .execute()
    )
    if profile.data:
        return profile.data[0]

    result = supabase.auth.admin.create_user(
        {
            "email": payload["email"],
            "password": payload["password"],
            "email_confirm": True,
            "user_metadata": {
                "username": payload["username"],
                "badge_number": payload["badge_number"],
                "role": role,
            },
        }
    )
    if result.user is None:
        raise RuntimeError(f"Failed to create test user {payload['username']}")
    created = (
        supabase.table("profiles")
        .select("*")
        .eq("id", result.user.id)
        .execute()
    )
    return created.data[0]


def ensure_admin() -> None:
    get_or_create_user(
        {
            "username": ADMIN_USERNAME,
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "badge_number": ADMIN_BADGE,
        },
        "ADMIN",
    )


def ensure_investigators() -> None:
    get_or_create_user(INVESTIGATOR_1, "INVESTIGATOR")
    get_or_create_user(INVESTIGATOR_2, "INVESTIGATOR")


def admin_headers() -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def login_headers(username: str, password: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def user_id_by_username(username: str) -> str:
    profile = (
        supabase.table("profiles")
        .select("id")
        .eq("username", username)
        .execute()
    )
    assert profile.data, f"User {username} not found"
    return profile.data[0]["id"]


def cleanup_between_tests() -> None:
    _cleanup_test_data()
    ensure_admin()
    ensure_investigators()


_cleanup_test_data()
ensure_admin()
ensure_investigators()

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_tests():
    cleanup_between_tests()
    yield
