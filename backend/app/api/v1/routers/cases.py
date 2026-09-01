from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.database import get_db
from app.deps import get_current_user, require_case_access
from app.models.entities import AccessStatus, Case, CaseAccess, User, UserRole, utcnow
from app.schemas.case import CaseCreate, CaseRead, CaseWorkspace

router = APIRouter(prefix="/cases", tags=["cases"])


def _client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@router.post("/create", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.scalar(select(Case).where(Case.case_id == payload.case_id))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Case ID already exists")

    case = Case(
        case_id=payload.case_id,
        title=payload.title,
        description=payload.description,
        created_by_user_id=current_user.id,
    )
    db.add(case)
    db.flush()

    access = CaseAccess(
        user_id=current_user.id,
        case_id=case.id,
        access_status=AccessStatus.APPROVED.value,
        requested_at=case.created_at,
        reviewed_at=case.created_at,
        reviewed_by_admin_id=current_user.id if current_user.role == UserRole.ADMIN.value else None,
    )
    db.add(access)
    try:
        db.commit()
        db.refresh(case)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Case ID already exists")

    write_audit(
        db,
        action_type="CASE_CREATED",
        user_id=current_user.id,
        case_id=case.case_id,
        metadata={"title": case.title},
        ip_address=_client_ip(request),
    )
    write_audit(
        db,
        action_type="CASE_ACCESS_GRANTED_AUTO",
        user_id=current_user.id,
        case_id=case.case_id,
        metadata={"method": "creator_auto_grant"},
        ip_address=_client_ip(request),
    )
    return case


@router.post("/{case_id}/request-access")
def request_access(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.scalar(select(Case).where(Case.case_id == case_id))
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if current_user.role == UserRole.ADMIN.value:
        return {"detail": "Administrators automatically have access to all cases"}

    access = db.scalar(
        select(CaseAccess).where(
            CaseAccess.user_id == current_user.id,
            CaseAccess.case_id == case.id,
        )
    )

    if access is None:
        access = CaseAccess(user_id=current_user.id, case_id=case.id)
        db.add(access)
        db.commit()
        status_ = AccessStatus.PENDING.value
    elif access.access_status == AccessStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access request already pending")
    elif access.access_status == AccessStatus.APPROVED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access already approved")
    else:
        access.access_status = AccessStatus.PENDING.value
        access.requested_at = utcnow()
        access.reviewed_at = None
        access.reviewed_by_admin_id = None
        db.commit()
        status_ = AccessStatus.PENDING.value

    write_audit(
        db,
        action_type="CASE_ACCESS_REQUESTED",
        user_id=current_user.id,
        case_id=case.case_id,
        metadata={"status": status_},
        ip_address=_client_ip(request),
    )
    return {"detail": "Access request submitted", "case_id": case.case_id, "status": status_}


@router.get("/{case_id}/workspace", response_model=CaseWorkspace)
def workspace(
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    access = db.scalar(
        select(CaseAccess).where(
            CaseAccess.user_id == current_user.id,
            CaseAccess.case_id == case.id,
        )
    )
    return CaseWorkspace(
        case=case,
        role=current_user.role,
        access_status=access.access_status if access else None,
        message="Access granted",
    )