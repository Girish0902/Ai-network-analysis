from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class EvidenceBlock(BaseModel):
    case_id: str
    doc_sha256: str
    page_number: int
    block_id: str
    bbox: List[float]
    extraction_method: str
    confidence: float
    detected_language: Optional[str] = None
    text: Optional[str] = None
    structured_tables: Optional[List[Dict[str, Any]]] = None
    schema_version: str


class UnifiedEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    case_id: str
    doc_sha256: str
    schema_version: str
    route: str
    extraction_method: str
    detection_index: Dict[str, Any]
    ocr_pending_pages: List[int]
    blocks: List[EvidenceBlock]


class ProcessingJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    schema_version: str
    route: str
    extraction_method: str
    status: str
    detection_index: Optional[Dict[str, Any]] = None
    ocr_pending_pages: Optional[List[int]] = None
    evidence_payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Any = None