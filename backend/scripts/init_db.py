import os
import secrets
import sys

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.entities import User, UserRole


def seed_admin() -> None:
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.role == UserRole.ADMIN.value))
        if existing:
            print(f"[init_db] Administrator already exists: {existing.username} (id={existing.id})")
            return

        username = settings.ADMIN_USERNAME
        email = settings.ADMIN_EMAIL
        badge = settings.ADMIN_BADGE
        password = settings.ADMIN_PASSWORD.get_secret_value()

        while len(password) < 8:
            print("[init_db] ADMIN_PASSWORD must be at least 8 characters. Generating a random one for you...")
            password = secrets.token_urlsafe(12)

        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            badge_number=badge,
            role=UserRole.ADMIN.value,
        )
        db.add(user)
        db.commit()
        print(f"[init_db] Created bootstrap administrator: {username} (email={email})")
        print(f"[init_db] Keep these credentials secure. Login via POST /api/v1/auth/login")
    finally:
        db.close()


def main() -> None:
    print(f"[init_db] Creating tables on {engine.url}")
    Base.metadata.create_all(bind=engine)
    print("[init_db] Tables created (or already present).")
    seed_admin()
    print("[init_db] Done.")


if __name__ == "__main__":
    main()