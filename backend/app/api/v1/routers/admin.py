from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.database import get_db
from app.deps import require_admin
from app.models.entities import AccessStatus, Case, CaseAccess, User, utcnow
from app.schemas.admin import AccessDecision, AccessDecisionOut, PendingRequestOut

router = APIRouter(prefix="/admin", tags=["admin"])


def _client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@router.get("/pending-requests", response_model=list[PendingRequestOut])
def pending_requests(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    rows = (
        db.execute(
            select(CaseAccess, User, Case)
            .join(User, CaseAccess.user_id == User.id)
            .join(Case, CaseAccess.case_id == Case.id)
            .where(CaseAccess.access_status == AccessStatus.PENDING.value)
            .order_by(CaseAccess.requested_at.asc())
        )
        .all()
    )
    return [
        PendingRequestOut(
            user_id=ca.user_id,
            username=user.username,
            badge_number=user.badge_number,
            case_id=case.case_id,
            status=ca.access_status,
            created_at=ca.requested_at,
        )
        for ca, user, case in rows
    ]


@router.post("/decide-access", response_model=AccessDecisionOut)
def decide_access(
    payload: AccessDecision,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    decision = payload.decision.strip().upper()
    mapping = {
        "APPROVE": AccessStatus.APPROVED,
        "REJECT": AccessStatus.REJECTED,
        "APPROVED": AccessStatus.APPROVED,
        "REJECTED": AccessStatus.REJECTED,
    }
    resolved = mapping.get(decision)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="decision must be APPROVE or REJECT",
        )

    case = db.scalar(select(Case).where(Case.case_id == payload.case_id))
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    access = db.scalar(
        select(CaseAccess).where(
            CaseAccess.user_id == user.id,
            CaseAccess.case_id == case.id,
        )
    )
    if access is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")
    if access.access_status == AccessStatus.APPROVED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access already approved")
    if access.access_status == AccessStatus.REJECTED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access already rejected")

    new_status = AccessStatus.APPROVED.value if resolved == AccessStatus.APPROVED else AccessStatus.REJECTED.value
    access.access_status = new_status
    access.reviewed_at = utcnow()
    access.reviewed_by_admin_id = admin.id
    db.commit()

    write_audit(
        db,
        action_type="CASE_ACCESS_DECIDED",
        user_id=admin.id,
        case_id=case.case_id,
        metadata={
            "target_user_id": user.id,
            "target_username": user.username,
            "decision": new_status,
        },
        ip_address=_client_ip(request),
    )
    return AccessDecisionOut(
        user_id=user.id,
        case_id=case.case_id,
        status=new_status,
        message=f"Access {new_status.lower()} for {user.username}",
    )