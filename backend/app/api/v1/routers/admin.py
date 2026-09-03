from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from supabase import Client

from app.core.audit import write_audit
from app.core.supabase import get_supabase
from app.deps import require_admin
from app.schemas.admin import AccessDecision, AccessDecisionOut, PendingRequestOut

router = APIRouter(prefix="/admin", tags=["admin"])


def _client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@router.get("/pending-requests", response_model=list[PendingRequestOut])
def pending_requests(
    request: Request,
    supabase: Client = Depends(get_supabase),
    admin: dict = Depends(require_admin),
):
    rows = (
        supabase.table("case_accesses")
        .select("*, profiles!case_accesses_user_id_fkey(*), cases(*)")
        .eq("access_status", "PENDING")
        .order("requested_at", asc=True)
        .execute()
    )

    results = []
    for row in rows.data:
        profile = row.get("profiles")
        case = row.get("cases")
        if not profile or not case:
            continue
        results.append(
            PendingRequestOut(
                user_id=profile["id"],
                username=profile["username"],
                badge_number=profile["badge_number"],
                case_id=case["case_id"],
                status=row["access_status"],
                created_at=row.get("requested_at"),
            )
        )
    return results


@router.post("/decide-access", response_model=AccessDecisionOut)
def decide_access(
    payload: AccessDecision,
    request: Request,
    supabase: Client = Depends(get_supabase),
    admin: dict = Depends(require_admin),
):
    decision = payload.decision.strip().upper()
    mapping = {
        "APPROVE": "APPROVED",
        "REJECT": "REJECTED",
        "APPROVED": "APPROVED",
        "REJECTED": "REJECTED",
    }
    resolved = mapping.get(decision)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="decision must be APPROVE or REJECT",
        )

    case = supabase.table("cases").select("*").eq("case_id", payload.case_id).execute()
    if not case.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case_data = case.data[0]

    user = supabase.table("profiles").select("*").eq("id", payload.user_id).execute()
    if not user.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_data = user.data[0]

    access = (
        supabase.table("case_accesses")
        .select("*")
        .eq("user_id", user_data["id"])
        .eq("case_id", case_data["id"])
        .execute()
    )
    if not access.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")

    access_data = access.data[0]
    if access_data.get("access_status") == "APPROVED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access already approved")
    if access_data.get("access_status") == "REJECTED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access already rejected")

    supabase.table("case_accesses").update(
        {
            "access_status": resolved,
            "reviewed_at": datetime.utcnow().isoformat(),
            "reviewed_by_admin_id": admin["id"],
        }
    ).eq("id", access_data["id"]).execute()

    write_audit(
        supabase,
        action_type="CASE_ACCESS_DECIDED",
        user_id=admin["id"],
        case_id=case_data["case_id"],
        metadata={
            "target_user_id": user_data["id"],
            "target_username": user_data["username"],
            "decision": resolved,
        },
        ip_address=_client_ip(request),
    )

    return AccessDecisionOut(
        user_id=user_data["id"],
        case_id=case_data["case_id"],
        status=resolved,
        message=f"Access {resolved.lower()} for {user_data['username']}",
    )
