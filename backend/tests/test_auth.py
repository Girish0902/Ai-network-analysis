import pytest

from tests.conftest import (
    ADMIN_BADGE,
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    INVESTIGATOR_1,
    INVESTIGATOR_2,
    client,
)

NEW_USER = {
    "username": "inv_kiran",
    "email": "kiran@police.in",
    "password": "KiranPass2026!",
    "badge_number": "2026-CID-55410",
}


def test_signup_creates_investigator_default_role():
    resp = client.post("/api/v1/auth/signup", json=NEW_USER)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "INVESTIGATOR"
    assert body["username"] == NEW_USER["username"]
    assert body["badge_number"] == NEW_USER["badge_number"]
    assert "hashed_password" not in body


def test_signup_rejects_duplicate():
    resp = client.post("/api/v1/auth/signup", json=NEW_USER)
    assert resp.status_code == 409


def test_signup_rejects_weak_password():
    payload = {**INVESTIGATOR_2, "username": "inv_weak", "badge_number": "2026-CID-99000", "password": "short"}
    resp = client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 422


def test_signup_rejects_admin_self_registration():
    payload = {
        "username": "admin123",
        "email": "adminwannabe@police.in",
        "password": "StrongPass2026!",
        "badge_number": "ADM-9999",
    }
    resp = client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 403


def test_login_returns_real_jwt():
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": INVESTIGATOR_1["username"], "password": INVESTIGATOR_1["password"]},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    assert token.count(".") == 2


def test_login_with_email_also_works():
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": INVESTIGATOR_1["email"], "password": INVESTIGATOR_1["password"]},
    )
    assert resp.status_code == 200


def test_login_wrong_password_returns_401():
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": INVESTIGATOR_1["username"], "password": "WrongPass2026!"},
    )
    assert resp.status_code == 401


def test_login_unknown_user_returns_401():
    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "nobody@nowhere.in", "password": "Whatever2026!"},
    )
    assert resp.status_code == 401


def test_login_deactivated_user_forbidden():
    from tests.conftest import TestingSessionLocal
    from app.models.entities import User

    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == INVESTIGATOR_1["username"]).first()
    user.is_active = False
    db.commit()
    db.close()

    resp = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": INVESTIGATOR_1["username"], "password": INVESTIGATOR_1["password"]},
    )
    assert resp.status_code == 403

    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == INVESTIGATOR_1["username"]).first()
    user.is_active = True
    db.commit()
    db.close()


def test_me_endpoint_rejects_no_token():
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_endpoint_returns_current_user():
    from tests.conftest import login_headers

    resp = client.get("/api/v1/auth/me", headers=login_headers(INVESTIGATOR_1["username"], INVESTIGATOR_1["password"]))
    assert resp.status_code == 200
    assert resp.json()["username"] == INVESTIGATOR_1["username"]


def test_me_endpoint_rejects_garbage_token():
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401