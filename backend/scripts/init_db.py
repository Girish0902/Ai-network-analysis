import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.supabase import get_supabase


def seed_admin() -> None:
    supabase = get_supabase()

    existing = (
        supabase.table("profiles")
        .select("*")
        .eq("role", "ADMIN")
        .limit(1)
        .execute()
    )
    if existing.data:
        print(f"[init_db] Administrator already exists: {existing.data[0]['username']}")
        return

    username = settings.ADMIN_USERNAME
    email = settings.ADMIN_EMAIL
    badge = settings.ADMIN_BADGE
    password = settings.ADMIN_PASSWORD.get_secret_value()

    while len(password) < 8:
        print("[init_db] ADMIN_PASSWORD must be at least 8 characters. Generating a random one for you...")
        password = secrets.token_urlsafe(12)

    try:
        result = supabase.auth.admin.create_user(
            {
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "username": username,
                    "badge_number": badge,
                    "role": "ADMIN",
                },
            }
        )
    except Exception as exc:
        print(f"[init_db] Failed to create administrator: {exc}")
        return

    if not result.user:
        print("[init_db] Failed to create administrator user.")
        return

    profile = (
        supabase.table("profiles")
        .select("*")
        .eq("id", result.user.id)
        .execute()
    )
    if not profile.data:
        supabase.table("profiles").insert(
            {
                "id": result.user.id,
                "username": username,
                "badge_number": badge,
                "role": "ADMIN",
            }
        ).execute()

    print(f"[init_db] Created bootstrap administrator: {username} (email={email})")
    print(f"[init_db] Keep these credentials secure. Login via POST /api/v1/auth/login")


def main() -> None:
    print("[init_db] Applying schema via Supabase SQL migration (run migration/001_initial_schema.sql in the SQL Editor).")
    seed_admin()
    print("[init_db] Done.")


if __name__ == "__main__":
    main()
