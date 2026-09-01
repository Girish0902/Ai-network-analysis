from pydantic import BaseModel


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