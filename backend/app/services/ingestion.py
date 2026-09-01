import hashlib
import io
from typing import Optional

from app.core.config import settings
from app.services.mime_detection import MimeDetectionError, detect_mime


class EvidenceIngestionError(Exception):
    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class EvidenceMimeRejected(EvidenceIngestionError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, 415)


class VirusSignatureFound(EvidenceIngestionError):
    def __init__(self, signature: str) -> None:
        super().__init__(f"Malware signature detected: {signature}", 400)
        self.signature = signature


class ClamAVUnavailable(EvidenceIngestionError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, 503)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_evidence_mime(filename: str, data: bytes) -> str:
    try:
        return detect_mime(filename, data)
    except MimeDetectionError as exc:
        raise EvidenceMimeRejected(exc.detail) from exc


def scan_for_viruses(data: bytes) -> Optional[str]:
    if not settings.CLAMAV_ENABLED:
        return None
    try:
        import pyclamd

        daemon = pyclamd.ClamdNetworkSocket(
            host=settings.CLAMAV_HOST,
            port=settings.CLAMAV_PORT,
            timeout=5.0,
        )
        if not daemon.ping():
            raise ClamAVUnavailable("ClamAV daemon did not respond to ping")
        status, signature, *_ = daemon.instream(io.BytesIO(data))
    except (pyclamd.ConnectionError, pyclamd.SocketError, OSError) as exc:
        raise ClamAVUnavailable(f"ClamAV daemon unreachable at {settings.CLAMAV_HOST}:{settings.CLAMAV_PORT}: {exc}") from exc

    if status == "FOUND":
        return signature
    return None