from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.audit import write_audit
from app.core.supabase import get_supabase
from app.deps import get_current_user
from app.schemas.auth import Token, UserLogin, UserRead, UserSignup
from supabase import Client

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(payload: UserSignup, request: Request, supabase: Client = Depends(get_supabase)):
    if payload.username.lower().startswith("admin") or payload.email.lower().startswith("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator accounts cannot self-register. Contact system administrator.",
        )

    existing = supabase.table("profiles").select("*").eq("username", payload.username).execute()
    if existing.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")

    existing = supabase.table("profiles").select("*").eq("badge_number", payload.badge_number).execute()
    if existing.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Badge number already registered")

    try:
        result = supabase.auth.sign_up(
            {
                "email": payload.email,
                "password": payload.password,
                "options": {
                    "data": {
                        "username": payload.username,
                        "badge_number": payload.badge_number,
                        "role": "INVESTIGATOR",
                    }
                },
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signup failed: {str(exc)}",
        )

    if result.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed. Email may already be in use.",
        )

    profile = supabase.table("profiles").select("*").eq("id", result.user.id).execute()
    if not profile.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile creation failed",
        )

    write_audit(
        supabase,
        action_type="USER_SIGNUP",
        user_id=result.user.id,
        metadata={"username": payload.username, "role": "INVESTIGATOR"},
        ip_address=_client_ip(request),
    )

    profile_data = profile.data[0]
    return UserRead(
        id=profile_data["id"],
        username=profile_data["username"],
        email=payload.email,
        badge_number=profile_data["badge_number"],
        role=profile_data["role"],
        is_active=profile_data["is_active"],
        created_at=profile_data["created_at"],
    )


@router.post("/login", response_model=Token)
def login(payload: UserLogin, request: Request, supabase: Client = Depends(get_supabase)):
    identifier = payload.username_or_email.strip()

    profile = supabase.table("profiles").select("*").or_(f"username.eq.{identifier},email.eq.{identifier}").execute()
    if not profile.data:
        write_audit(
            supabase,
            action_type="LOGIN_FAILED",
            metadata={"identifier": identifier},
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )

    profile_data = profile.data[0]
    email = profile_data.get("email", identifier)

    try:
        result = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": payload.password,
            }
        )
    except Exception as exc:
        write_audit(
            supabase,
            action_type="LOGIN_FAILED",
            user_id=profile_data["id"],
            metadata={"identifier": identifier},
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )

    if not profile_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    write_audit(
        supabase,
        action_type="LOGIN_SUCCESS",
        user_id=profile_data["id"],
        metadata={"username": profile_data["username"], "role": profile_data["role"]},
        ip_address=_client_ip(request),
    )

    return Token(access_token=result.session.access_token)


@router.get("/me", response_model=UserRead)
def me(current_user: dict = Depends(get_current_user)):
    return UserRead(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user.get("email", ""),
        badge_number=current_user["badge_number"],
        role=current_user["role"],
        is_active=current_user.get("is_active", True),
        created_at=current_user.get("created_at", ""),
    )
