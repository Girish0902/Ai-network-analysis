from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.core.audit import write_audit
from app.core.supabase import get_supabase

bearer_scheme = HTTPBearer(auto_error=False)

AuthBearer = Depends(bearer_scheme)


def _get_token_payload(credentials: Optional[HTTPAuthorizationCredentials]) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = AuthBearer,
    supabase: Client = Depends(get_supabase),
) -> dict:
    token = _get_token_payload(credentials)

    try:
        user_response = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user_response.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = user_response.user.id

    profile = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if not profile.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User profile not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    profile_data = profile.data[0]
    if not profile_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    profile_data["email"] = user_response.user.email
    return profile_data


def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def _get_client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def require_case_access(
    case_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
) -> dict:
    case = supabase.table("cases").select("*").eq("case_id", case_id).execute()
    if not case.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case_data = case.data[0]

    if current_user.get("role") == "ADMIN":
        write_audit(
            supabase,
            action_type="CASE_ACCESS_OPEN",
            user_id=current_user["id"],
            case_id=case_data["case_id"],
            metadata={"method": "case_access", "access": "admin_bypass"},
            ip_address=_get_client_ip(request),
        )
        return case_data

    access = supabase.table("case_accesses").select("*").eq("user_id", current_user["id"]).eq("case_id", case_data["id"]).execute()
    if not access.data or access.data[0].get("access_status") != "APPROVED":
        access_status = access.data[0].get("access_status") if access.data else "NO_REQUEST"
        write_audit(
            supabase,
            action_type="CASE_ACCESS_DENIED",
            user_id=current_user["id"],
            case_id=case_data["case_id"],
            metadata={"method": "case_access", "status": access_status},
            ip_address=_get_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No approved access to this case",
        )

    write_audit(
        supabase,
        action_type="CASE_ACCESS_OPEN",
        user_id=current_user["id"],
        case_id=case_data["case_id"],
        metadata={"method": "case_access", "access": "approved"},
        ip_address=_get_client_ip(request),
    )
    return case_data
