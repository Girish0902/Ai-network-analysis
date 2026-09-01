import enum
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    INVESTIGATOR = "INVESTIGATOR"


class CaseStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class AccessStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    badge_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), default=UserRole.INVESTIGATOR.value, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    cases: Mapped[list["Case"]] = relationship(back_populates="created_by", foreign_keys="Case.created_by_user_id")
    accesses: Mapped[list["CaseAccess"]] = relationship(back_populates="user", foreign_keys="CaseAccess.user_id")
    evidence_uploads: Mapped[list["EvidenceDocument"]] = relationship(
        back_populates="uploaded_by", foreign_keys="EvidenceDocument.uploaded_by_user_id"
    )


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=CaseStatus.OPEN.value, nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    created_by: Mapped["User"] = relationship(back_populates="cases", foreign_keys=[created_by_user_id])
    accesses: Mapped[list["CaseAccess"]] = relationship(back_populates="case", foreign_keys="CaseAccess.case_id")
    evidence_documents: Mapped[list["EvidenceDocument"]] = relationship(
        back_populates="case", foreign_keys="EvidenceDocument.case_id"
    )


class CaseAccess(Base):
    __tablename__ = "case_accesses"
    __table_args__ = (Index("uq_case_access_user_case", "user_id", "case_id", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    access_status: Mapped[str] = mapped_column(
        String(16), default=AccessStatus.PENDING.value, nullable=False, index=True
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    user: Mapped["User"] = relationship(back_populates="accesses", foreign_keys=[user_id])
    case: Mapped["Case"] = relationship(back_populates="accesses", foreign_keys=[case_id])
    reviewed_by: Mapped[Optional["User"]] = relationship(foreign_keys=[reviewed_by_admin_id])


class EvidenceDocument(Base):
    __tablename__ = "evidence_documents"
    __table_args__ = (UniqueConstraint("case_id", "sha256_hash", name="uq_evidence_case_sha256"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    is_quarantined: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    case: Mapped["Case"] = relationship(back_populates="evidence_documents", foreign_keys=[case_id])
    uploaded_by: Mapped["User"] = relationship(back_populates="evidence_uploads", foreign_keys=[uploaded_by_user_id])
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(back_populates="document", foreign_keys="ProcessingJob.document_id")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("evidence_documents.id"), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    route: Mapped[str] = mapped_column(String(32), nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    detection_index: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ocr_pending_pages: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    evidence_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    document: Mapped["EvidenceDocument"] = relationship()


class AuditTrail(Base):
    __tablename__ = "audit_trails"

    event_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    case_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    tamper_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="0" * 64, index=True)