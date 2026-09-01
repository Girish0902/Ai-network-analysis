import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-2026-aaaaaaaaaaaaaaaaaaaaaaaaaaaa"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["ADMIN_PASSWORD"] = "AdminTestPass2026!"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOCAL_STORAGE_ROOT"] = os.path.join(
    os.environ.get("TEST_TMPDIR", os.path.join(os.path.dirname(__file__), "_uploads")),
    "evidence-vault",
)
os.environ["CLAMAV_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.entities import User, UserRole  # noqa: E402

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=TEST_ENGINE)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

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


def _create_user_if_missing(username: str, email: str, password: str, badge_number: str) -> User:
    db = TestingSessionLocal()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.close()
        return existing
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        badge_number=badge_number,
        role=UserRole.INVESTIGATOR.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def create_admin_user() -> User:
    db = TestingSessionLocal()
    existing = db.query(User).filter(User.role == UserRole.ADMIN.value).first()
    if existing:
        db.close()
        return existing
    admin = User(
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        hashed_password=hash_password(ADMIN_PASSWORD),
        badge_number=ADMIN_BADGE,
        role=UserRole.ADMIN.value,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    db.close()
    return admin


def admin_headers() -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"username_or_email": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def login_headers(username: str, password: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"username_or_email": username, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


create_admin_user()
_create_user_if_missing(
    INVESTIGATOR_1["username"],
    INVESTIGATOR_1["email"],
    INVESTIGATOR_1["password"],
    INVESTIGATOR_1["badge_number"],
)
_create_user_if_missing(
    INVESTIGATOR_2["username"],
    INVESTIGATOR_2["email"],
    INVESTIGATOR_2["password"],
    INVESTIGATOR_2["badge_number"],
)