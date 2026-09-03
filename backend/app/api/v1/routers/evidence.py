from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, UploadFile, status
from supabase import Client

from app.core.audit import write_audit
from app.core.supabase import get_supabase
from app.core.storage import (
    build_presigned_url,
    download_evidence_bytes,
    upload_evidence_bytes,
)
from app.deps import get_current_user, require_case_access
from app.schemas.evidence import EvidenceDocumentRead, EvidenceDownloadUrlOut, EvidenceUploadOut
from app.schemas.processing import ProcessingJobRead
from app.services.document_router import process_document
from app.services.ingestion import (
    EvidenceIngestionError,
    VirusSignatureFound,
    resolve_evidence_mime,
    scan_for_viruses,
    sha256_hex,
)

router = APIRouter(tags=["evidence"])

DOWNLOAD_URL_EXPIRY_SECONDS = 15 * 60

EVIDENCE_SCHEMA_VERSION = "1.0.0"

PROCESS_STATUS_COMPLETED = "COMPLETED"
PROCESS_STATUS_OCR_PENDING = "OCR_PENDING"
PROCESS_STATUS_FAILED = "FAILED"


def _client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@router.get("/cases/{case_id}/evidence", response_model=list[EvidenceDocumentRead])
def list_evidence(
    case_id: str,
    request: Request,
    case: dict = Depends(require_case_access),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    documents = (
        supabase.table("evidence_documents")
        .select("*")
        .eq("case_id", case["id"])
        .order("created_at", desc=True)
        .execute()
    ).data

    doc_ids = [doc["id"] for doc in documents]
    latest_jobs: dict = {}
    if doc_ids:
        jobs = (
            supabase.table("processing_jobs")
            .select("*")
            .in_("document_id", doc_ids)
            .order("id", asc=True)
            .execute()
        ).data
        for job in jobs:
            latest_jobs[job["document_id"]] = job

    write_audit(
        supabase,
        action_type="EVIDENCE_LISTED",
        user_id=current_user["id"],
        case_id=case["case_id"],
        metadata={"document_count": len(documents)},
        ip_address=_client_ip(request),
    )

    results = []
    for doc in documents:
        job = latest_jobs.get(doc["id"])
        results.append(
            EvidenceDocumentRead(
                id=doc["id"],
                original_filename=doc["original_filename"],
                mime_type=doc["mime_type"],
                file_size_bytes=doc["file_size_bytes"],
                sha256_hash=doc["sha256_hash"],
                is_quarantined=doc["is_quarantined"],
                created_at=doc["created_at"],
                processing_status=job["status"] if job else None,
                processing_error=job["error"] if job else None,
            )
        )
    return results


@router.post(
    "/cases/{case_id}/evidence/upload",
    response_model=EvidenceUploadOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_evidence(
    case_id: str,
    request: Request,
    file: UploadFile = File(...),
    case: dict = Depends(require_case_access),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    try:
        mime_type = resolve_evidence_mime(file.filename or "", data)
    except (EvidenceIngestionError, VirusSignatureFound) as exc:
        write_audit(
            supabase,
            action_type="EVIDENCE_UPLOAD_REJECTED",
            user_id=current_user["id"],
            case_id=case["case_id"],
            metadata={"filename": file.filename, "reason": exc.detail},
            ip_address=_client_ip(request),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    try:
        signature = scan_for_viruses(data)
    except EvidenceIngestionError as exc:
        write_audit(
            supabase,
            action_type="EVIDENCE_SCAN_FAILED",
            user_id=current_user["id"],
            case_id=case["case_id"],
            metadata={"filename": file.filename, "reason": exc.detail},
            ip_address=_client_ip(request),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    content_hash = sha256_hex(data)
    storage_path = f"cases/{case['case_id']}/{content_hash}/{file.filename}"
    upload_evidence_bytes(storage_path, data, mime_type)

    try:
        result = supabase.table("evidence_documents").insert(
            {
                "case_id": case["id"],
                "original_filename": file.filename,
                "mime_type": mime_type,
                "file_size_bytes": len(data),
                "sha256_hash": content_hash,
                "storage_path": storage_path,
                "uploaded_by_user_id": current_user["id"],
                "is_quarantined": bool(signature is not None),
            }
        ).execute()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An identical file has already been uploaded to this case",
        )

    document = result.data[0]

    write_audit(
        supabase,
        action_type="EVIDENCE_UPLOADED",
        user_id=current_user["id"],
        case_id=case["case_id"],
        metadata={
            "document_id": document["id"],
            "filename": file.filename,
            "sha256": content_hash,
            "mime_type": mime_type,
            "size_bytes": len(data),
        },
        ip_address=_client_ip(request),
    )
    return EvidenceUploadOut(
        document_id=document["id"],
        filename=file.filename,
        sha256=content_hash,
        mime_type=mime_type,
        size_bytes=len(data),
    )


@router.get(
    "/cases/{case_id}/evidence/{document_id}/download-url",
    response_model=EvidenceDownloadUrlOut,
)
def evidence_download_url(
    case_id: str,
    request: Request,
    document_id: int = Path(...),
    case: dict = Depends(require_case_access),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    document = (
        supabase.table("evidence_documents")
        .select("*")
        .eq("id", document_id)
        .eq("case_id", case["id"])
        .execute()
    )
    if not document.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    document_data = document.data[0]
    url = build_presigned_url(document_data["storage_path"], DOWNLOAD_URL_EXPIRY_SECONDS)

    write_audit(
        supabase,
        action_type="EVIDENCE_DOWNLOAD_URL",
        user_id=current_user["id"],
        case_id=case["case_id"],
        metadata={
            "document_id": document_data["id"],
            "filename": document_data["original_filename"],
            "expires_in_seconds": DOWNLOAD_URL_EXPIRY_SECONDS,
        },
        ip_address=_client_ip(request),
    )
    return EvidenceDownloadUrlOut(
        document_id=document_data["id"],
        filename=document_data["original_filename"],
        url=url,
        expires_in_seconds=DOWNLOAD_URL_EXPIRY_SECONDS,
    )


@router.post(
    "/cases/{case_id}/evidence/{document_id}/process",
    response_model=ProcessingJobRead,
    status_code=status.HTTP_201_CREATED,
)
def process_evidence(
    case_id: str,
    document_id: int,
    request: Request,
    case: dict = Depends(require_case_access),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    document = (
        supabase.table("evidence_documents")
        .select("*")
        .eq("id", document_id)
        .eq("case_id", case["id"])
        .execute()
    )
    if not document.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    document_data = document.data[0]
    if document_data.get("is_quarantined"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is quarantined and cannot be processed",
        )

    data = download_evidence_bytes(document_data["storage_path"])

    job_result = supabase.table("processing_jobs").insert(
        {
            "document_id": document_data["id"],
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "route": "",
            "extraction_method": "",
            "status": PROCESS_STATUS_FAILED,
        }
    ).execute()

    if not job_result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create job")

    job = job_result.data[0]

    try:
        evidence = process_document(
            mime_type=document_data["mime_type"],
            data=data,
            doc_sha256=document_data["sha256_hash"],
            case_id=case["case_id"],
            schema_version=EVIDENCE_SCHEMA_VERSION,
        )
    except Exception as exc:
        supabase.table("processing_jobs").update(
            {
                "status": PROCESS_STATUS_FAILED,
                "error": str(exc)[:1000],
            }
        ).eq("id", job["id"]).execute()
        write_audit(
            supabase,
            action_type="EVIDENCE_PROCESSING_FAILED",
            user_id=current_user["id"],
            case_id=case["case_id"],
            metadata={"document_id": document_data["id"], "error": str(exc)[:1000]},
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document processing failed: {exc}",
        )

    job_status = PROCESS_STATUS_OCR_PENDING if evidence["ocr_pending_pages"] else PROCESS_STATUS_COMPLETED
    updated = (
        supabase.table("processing_jobs")
        .update(
            {
                "route": evidence["route"],
                "extraction_method": evidence["extraction_method"],
                "detection_index": evidence["detection_index"],
                "ocr_pending_pages": evidence["ocr_pending_pages"] or [],
                "evidence_payload": evidence,
                "status": job_status,
                "error": None,
            }
        )
        .eq("id", job["id"])
        .execute()
    )

    job = updated.data[0]

    write_audit(
        supabase,
        action_type="EVIDENCE_PROCESSED",
        user_id=current_user["id"],
        case_id=case["case_id"],
        metadata={
            "document_id": document_data["id"],
            "route": evidence["route"],
            "method": evidence["extraction_method"],
            "status": job_status,
            "blocks": len(evidence["blocks"]),
            "ocr_pending_pages": evidence["ocr_pending_pages"],
        },
        ip_address=_client_ip(request),
    )
    return ProcessingJobRead(
        id=job["id"],
        document_id=job["document_id"],
        schema_version=job["schema_version"],
        route=job["route"],
        extraction_method=job["extraction_method"],
        status=job["status"],
        detection_index=job.get("detection_index"),
        ocr_pending_pages=job.get("ocr_pending_pages"),
        evidence_payload=job.get("evidence_payload"),
        error=job.get("error"),
        created_at=job.get("created_at"),
    )


@router.get(
    "/cases/{case_id}/evidence/{document_id}/stream",
    status_code=status.HTTP_200_OK,
)
def evidence_stream(
    case_id: str,
    document_id: int,
    request: Request,
    case: dict = Depends(require_case_access),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    from fastapi.responses import Response

    document = (
        supabase.table("evidence_documents")
        .select("*")
        .eq("id", document_id)
        .eq("case_id", case["id"])
        .execute()
    )
    if not document.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    document_data = document.data[0]
    data = download_evidence_bytes(document_data["storage_path"])

    write_audit(
        supabase,
        action_type="EVIDENCE_STREAMED",
        user_id=current_user["id"],
        case_id=case["case_id"],
        metadata={"document_id": document_data["id"], "filename": document_data["original_filename"]},
        ip_address=_client_ip(request),
    )
    return Response(
        content=data,
        media_type=document_data["mime_type"],
        headers={"Content-Disposition": f'attachment; filename="{document_data["original_filename"]}"'},
    )
