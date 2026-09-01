from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.config import settings
from app.core.database import get_db
from app.core.storage import (
    build_presigned_url,
    download_evidence_bytes,
    upload_evidence_bytes,
)
from app.deps import get_current_user, require_case_access
from app.models.entities import Case, EvidenceDocument, ProcessingJob, User
from app.schemas.evidence import EvidenceDownloadUrlOut, EvidenceUploadOut
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


@router.post(
    "/cases/{case_id}/evidence/upload",
    response_model=EvidenceUploadOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_evidence(
    case_id: str,
    request: Request,
    file: UploadFile = File(...),
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    try:
        mime_type = resolve_evidence_mime(file.filename or "", data)
    except (EvidenceIngestionError, VirusSignatureFound) as exc:
        write_audit(
            db,
            action_type="EVIDENCE_UPLOAD_REJECTED",
            user_id=current_user.id,
            case_id=case.case_id,
            metadata={"filename": file.filename, "reason": exc.detail},
            ip_address=_client_ip(request),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    try:
        signature = scan_for_viruses(data)
    except EvidenceIngestionError as exc:
        write_audit(
            db,
            action_type="EVIDENCE_SCAN_FAILED",
            user_id=current_user.id,
            case_id=case.case_id,
            metadata={"filename": file.filename, "reason": exc.detail},
            ip_address=_client_ip(request),
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    content_hash = sha256_hex(data)
    storage_path = f"cases/{case.case_id}/{content_hash}/{file.filename}"
    upload_evidence_bytes(storage_path, data, mime_type)

    document = EvidenceDocument(
        case_id=case.id,
        original_filename=file.filename,
        mime_type=mime_type,
        file_size_bytes=len(data),
        sha256_hash=content_hash,
        storage_path=storage_path,
        uploaded_by_user_id=current_user.id,
        is_quarantined=bool(signature is not None),
    )
    db.add(document)
    try:
        db.commit()
        db.refresh(document)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An identical file has already been uploaded to this case",
        )

    write_audit(
        db,
        action_type="EVIDENCE_UPLOADED",
        user_id=current_user.id,
        case_id=case.case_id,
        metadata={
            "document_id": document.id,
            "filename": file.filename,
            "sha256": content_hash,
            "mime_type": mime_type,
            "size_bytes": len(data),
        },
        ip_address=_client_ip(request),
    )
    return EvidenceUploadOut(
        document_id=document.id,
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
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.scalar(
        select(EvidenceDocument).where(
            EvidenceDocument.id == document_id,
            EvidenceDocument.case_id == case.id,
        )
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if settings.STORAGE_BACKEND != "minio":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Presigned URLs require the MinIO storage backend; use the stream endpoint in local mode",
        )

    url = build_presigned_url(document.storage_path, DOWNLOAD_URL_EXPIRY_SECONDS)

    write_audit(
        db,
        action_type="EVIDENCE_DOWNLOAD_URL",
        user_id=current_user.id,
        case_id=case.case_id,
        metadata={
            "document_id": document.id,
            "filename": document.original_filename,
            "expires_in_seconds": DOWNLOAD_URL_EXPIRY_SECONDS,
        },
        ip_address=_client_ip(request),
    )
    return EvidenceDownloadUrlOut(
        document_id=document.id,
        filename=document.original_filename,
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
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.scalar(
        select(EvidenceDocument).where(
            EvidenceDocument.id == document_id,
            EvidenceDocument.case_id == case.id,
        )
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if document.is_quarantined:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is quarantined and cannot be processed",
        )

    data = download_evidence_bytes(document.storage_path)

    job = ProcessingJob(
        document_id=document.id,
        schema_version=EVIDENCE_SCHEMA_VERSION,
        route="",
        extraction_method="",
        status=PROCESS_STATUS_FAILED,
    )
    db.add(job)
    db.flush()

    try:
        evidence = process_document(
            mime_type=document.mime_type,
            data=data,
            doc_sha256=document.sha256_hash,
            case_id=case.case_id,
            schema_version=EVIDENCE_SCHEMA_VERSION,
        )
    except Exception as exc:
        job.status = PROCESS_STATUS_FAILED
        job.error = str(exc)[:1000]
        db.commit()
        write_audit(
            db,
            action_type="EVIDENCE_PROCESSING_FAILED",
            user_id=current_user.id,
            case_id=case.case_id,
            metadata={"document_id": document.id, "error": job.error},
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document processing failed: {exc}",
        )

    job.route = evidence["route"]
    job.extraction_method = evidence["extraction_method"]
    job.detection_index = evidence["detection_index"]
    job.ocr_pending_pages = evidence["ocr_pending_pages"] or []
    job.evidence_payload = evidence
    job.status = PROCESS_STATUS_OCR_PENDING if evidence["ocr_pending_pages"] else PROCESS_STATUS_COMPLETED
    job.error = None
    db.commit()
    db.refresh(job)

    write_audit(
        db,
        action_type="EVIDENCE_PROCESSED",
        user_id=current_user.id,
        case_id=case.case_id,
        metadata={
            "document_id": document.id,
            "route": evidence["route"],
            "method": evidence["extraction_method"],
            "status": job.status,
            "blocks": len(evidence["blocks"]),
            "ocr_pending_pages": job.ocr_pending_pages,
        },
        ip_address=_client_ip(request),
    )
    return job


@router.get(
    "/cases/{case_id}/evidence/{document_id}/stream",
    status_code=status.HTTP_200_OK,
)
def evidence_stream(
    case_id: str,
    document_id: int,
    request: Request,
    case: Case = Depends(require_case_access),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from fastapi.responses import Response

    document = db.scalar(
        select(EvidenceDocument).where(
            EvidenceDocument.id == document_id,
            EvidenceDocument.case_id == case.id,
        )
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if settings.STORAGE_BACKEND == "minio":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Use the download-url endpoint with the MinIO backend",
        )

    data = download_evidence_bytes(document.storage_path)
    write_audit(
        db,
        action_type="EVIDENCE_STREAMED",
        user_id=current_user.id,
        case_id=case.case_id,
        metadata={"document_id": document.id, "filename": document.original_filename},
        ip_address=_client_ip(request),
    )
    return Response(
        content=data,
        media_type=document.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{document.original_filename}"'},
    )