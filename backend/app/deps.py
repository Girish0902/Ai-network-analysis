from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.database import get_db
from app.core.security import InvalidTokenError, decode_access_token
from app.models.entities import AccessStatus, Case, CaseAccess, User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)

AuthBearer = Depends(bearer_scheme)


def _get_token_payload(credentials: Optional[HTTPAuthorizationCredentials]) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_access_token(credentials.credentials)
    except (InvalidTokenError, JWTError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = AuthBearer,
    db: Session = Depends(get_db),
) -> User:
    payload = _get_token_payload(credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN.value:
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Case:
    case = db.scalar(select(Case).where(Case.case_id == case_id))
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if current_user.role == UserRole.ADMIN.value:
        write_audit(
            db,
            action_type="CASE_ACCESS_OPEN",
            user_id=current_user.id,
            case_id=case.case_id,
            metadata={"method": "case_access", "access": "admin_bypass"},
            ip_address=_get_client_ip(request),
        )
        return case

    access = db.scalar(
        select(CaseAccess).where(
            CaseAccess.user_id == current_user.id,
            CaseAccess.case_id == case.id,
        )
    )
    if access is None or access.access_status != AccessStatus.APPROVED.value:
        write_audit(
            db,
            action_type="CASE_ACCESS_DENIED",
            user_id=current_user.id,
            case_id=case.case_id,
            metadata={"method": "case_access", "status": access.access_status if access else "NO_REQUEST"},
            ip_address=_get_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No approved access to this case",
        )

    write_audit(
        db,
        action_type="CASE_ACCESS_OPEN",
        user_id=current_user.id,
        case_id=case.case_id,
        metadata={"method": "case_access", "access": "approved"},
        ip_address=_get_client_ip(request),
    )
    return case