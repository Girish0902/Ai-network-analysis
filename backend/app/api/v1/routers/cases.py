from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from supabase import Client

from app.core.audit import write_audit
from app.core.supabase import get_supabase
from app.deps import get_current_user, require_case_access
from app.schemas.case import CaseCreate, CaseRead, CaseWorkspace, MyCase
from datetime import datetime

router = APIRouter(prefix="/cases", tags=["cases"])


def _client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@router.get("/my", response_model=list[MyCase])
def list_my_cases(
    request: Request,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") == "ADMIN":
        cases = supabase.table("cases").select("*").order("created_at", desc=True).execute()
        results = []
        seen = set()
        for case in cases.data:
            if case["id"] in seen:
                continue
            seen.add(case["id"])
            results.append(
                MyCase(
                    id=case["id"],
                    case_id=case["case_id"],
                    title=case["title"],
                    description=case.get("description"),
                    status=case["status"],
                    created_by_user_id=case["created_by_user_id"],
                    created_at=case["created_at"],
                    access_status=None,
                    role=current_user["role"],
                )
            )
        return results

    accesses = supabase.table("case_accesses").select("*, cases(*)").eq("user_id", current_user["id"]).execute()
    results = []
    for access in accesses.data:
        case = access.get("cases")
        if case:
            results.append(
                MyCase(
                    id=case["id"],
                    case_id=case["case_id"],
                    title=case["title"],
                    description=case.get("description"),
                    status=case["status"],
                    created_by_user_id=case["created_by_user_id"],
                    created_at=case["created_at"],
                    access_status=access.get("access_status"),
                    role=current_user["role"],
                )
            )
    return results


@router.post("/create", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreate,
    request: Request,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    existing = supabase.table("cases").select("*").eq("case_id", payload.case_id).execute()
    if existing.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Case ID already exists")

    result = supabase.table("cases").insert(
        {
            "case_id": payload.case_id,
            "title": payload.title,
            "description": payload.description,
            "created_by_user_id": current_user["id"],
        }
    ).execute()

    if not result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create case")

    case_data = result.data[0]

    supabase.table("case_accesses").insert(
        {
            "user_id": current_user["id"],
            "case_id": case_data["id"],
            "access_status": "APPROVED",
            "reviewed_at": datetime.utcnow().isoformat(),
            "reviewed_by_admin_id": current_user["id"] if current_user.get("role") == "ADMIN" else None,
        }
    ).execute()

    write_audit(
        supabase,
        action_type="CASE_CREATED",
        user_id=current_user["id"],
        case_id=case_data["case_id"],
        metadata={"title": payload.title},
        ip_address=_client_ip(request),
    )
    write_audit(
        supabase,
        action_type="CASE_ACCESS_GRANTED_AUTO",
        user_id=current_user["id"],
        case_id=case_data["case_id"],
        metadata={"method": "creator_auto_grant"},
        ip_address=_client_ip(request),
    )

    return CaseRead(
        id=case_data["id"],
        case_id=case_data["case_id"],
        title=case_data["title"],
        description=case_data.get("description"),
        status=case_data["status"],
        created_by_user_id=case_data["created_by_user_id"],
        created_at=case_data["created_at"],
    )


@router.post("/{case_id}/request-access")
def request_access(
    case_id: str,
    request: Request,
    supabase: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_user),
):
    case = supabase.table("cases").select("*").eq("case_id", case_id).execute()
    if not case.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case_data = case.data[0]

    if current_user.get("role") == "ADMIN":
        return {"detail": "Administrators automatically have access to all cases"}

    access = supabase.table("case_accesses").select("*").eq("user_id", current_user["id"]).eq("case_id", case_data["id"]).execute()

    if not access.data:
        supabase.table("case_accesses").insert(
            {
                "user_id": current_user["id"],
                "case_id": case_data["id"],
            }
        ).execute()
        access_status = "PENDING"
    elif access.data[0].get("access_status") == "PENDING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access request already pending")
    elif access.data[0].get("access_status") == "APPROVED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access already approved")
    else:
        supabase.table("case_accesses").update(
            {
                "access_status": "PENDING",
                "requested_at": datetime.utcnow().isoformat(),
                "reviewed_at": None,
                "reviewed_by_admin_id": None,
            }
        ).eq("id", access.data[0]["id"]).execute()
        access_status = "PENDING"

    write_audit(
        supabase,
        action_type="CASE_ACCESS_REQUESTED",
        user_id=current_user["id"],
        case_id=case_data["case_id"],
        metadata={"status": access_status},
        ip_address=_client_ip(request),
    )
    return {"detail": "Access request submitted", "case_id": case_data["case_id"], "status": access_status}


@router.get("/{case_id}/workspace", response_model=CaseWorkspace)
def workspace(
    case: dict = Depends(require_case_access),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    access = supabase.table("case_accesses").select("*").eq("user_id", current_user["id"]).eq("case_id", case["id"]).execute()
    access_status = access.data[0].get("access_status") if access.data else None

    return CaseWorkspace(
        case=CaseRead(
            id=case["id"],
            case_id=case["case_id"],
            title=case["title"],
            description=case.get("description"),
            status=case["status"],
            created_by_user_id=case["created_by_user_id"],
            created_at=case["created_at"],
        ),
        role=current_user["role"],
        access_status=access_status,
        message="Access granted",
    )
