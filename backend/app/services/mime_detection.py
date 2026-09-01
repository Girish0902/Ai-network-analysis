import io
import zipfile
from pathlib import Path

MIME_PDF = "application/pdf"
MIME_PNG = "image/png"
MIME_JPEG = "image/jpeg"
MIME_TIFF = "image/tiff"
MIME_CSV = "text/csv"
MIME_XLS = "application/vnd.ms-excel"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

ALLOWED_MIME_TYPES = frozenset(
    {
        MIME_PDF,
        MIME_PNG,
        MIME_JPEG,
        MIME_TIFF,
        MIME_CSV,
        MIME_XLS,
        MIME_XLSX,
    }
)

_EXT_ALLOWED = {
    ".pdf": {MIME_PDF},
    ".png": {MIME_PNG},
    ".jpg": {MIME_JPEG},
    ".jpeg": {MIME_JPEG},
    ".tif": {MIME_TIFF},
    ".tiff": {MIME_TIFF},
    ".csv": {MIME_CSV},
    ".xls": {MIME_XLS},
    ".xlsx": {MIME_XLSX},
}

_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_XLSX_MAGIC = b"PK\x03\x04"
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class MimeDetectionError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _is_probably_text(data: bytes) -> bool:
    sample = data[:4096]
    if not sample:
        return False
    if b"\x00" in sample:
        return False
    try:
        text = sample.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return False
    for ch in text:
        codepoint = ord(ch)
        if codepoint < 32 and ch not in "\t\r\n":
            return False
    return True


def _is_csv_content(data: bytes) -> bool:
    sample = data[:4096]
    if not _is_probably_text(data):
        return False
    return b"," in sample and (b"\n" in sample or b"\r" in sample)


def _verify_xlsx(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names:
                return False
            content_types = archive.read("[Content_Types].xml").decode("utf-8", "ignore")
            if "spreadsheetml.sheet" not in content_types:
                return False
            return any(name.startswith("xl/") for name in names)
    except (zipfile.BadZipFile, OSError, KeyError):
        return False


def _binary_signature(data: bytes) -> str | None:
    head = data[:64]
    if head.startswith(b"%PDF-"):
        return MIME_PDF
    if head.startswith(_PNG_SIG):
        return MIME_PNG
    if head.startswith(b"\xff\xd8\xff"):
        return MIME_JPEG
    if head.startswith(b"II*\x00") or head.startswith(b"MM\x00*"):
        return MIME_TIFF
    if head.startswith(_OLE2_MAGIC):
        return MIME_XLS
    if head.startswith(_XLSX_MAGIC):
        return "application/zip"
    return None


def detect_mime(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    allowed = _EXT_ALLOWED.get(ext)
    if allowed is None:
        raise MimeDetectionError(f"File extension '{ext or 'none'}' is not an allowed evidence type")

    signature = _binary_signature(data)

    if signature is not None and signature in allowed:
        return signature

    if signature == "application/zip" and ext == ".xlsx" and _verify_xlsx(data):
        return MIME_XLSX

    if ext == ".csv" and _is_csv_content(data):
        return MIME_CSV

    raise MimeDetectionError("File content does not match the allowed evidence type for this extension")