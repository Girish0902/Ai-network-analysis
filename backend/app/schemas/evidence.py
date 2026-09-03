from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EvidenceUploadOut(BaseModel):
    document_id: int
    filename: str
    sha256: str
    mime_type: str
    size_bytes: int


class EvidenceDownloadUrlOut(BaseModel):
    document_id: int
    filename: str
    url: str
    expires_in_seconds: int


class EvidenceDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    is_quarantined: bool
    created_at: datetime
    processing_status: Optional[str] = None
    processing_error: Optional[str] = None