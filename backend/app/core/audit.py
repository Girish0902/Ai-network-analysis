import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.entities import AuditTrail, utcnow


_CANONICAL = "|"
_HASH_FIELDS = [
    "event_id",
    "user_id",
    "case_id",
    "action_type",
    "metadata_json",
    "ip_address",
    "timestamp",
]


def _canonicalize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.isoformat(timespec="microseconds")
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def compute_tamper_hash(entry: AuditTrail, prev_hash: str) -> str:
    payload = _CANONICAL.join(_canonicalize(getattr(entry, field)) for field in _HASH_FIELDS)
    payload = f"{prev_hash}{_CANONICAL}{payload}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_audit(
    db: Session,
    action_type: str,
    user_id: Optional[int] = None,
    case_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    additional_hash_fields: Optional[Dict[str, Any]] = None,
) -> AuditTrail:
    last = db.query(AuditTrail).order_by(AuditTrail.event_id.desc()).first()
    prev_hash = last.tamper_hash if last else "0" * 64

    entry = AuditTrail(
        user_id=user_id,
        case_id=case_id,
        action_type=action_type,
        metadata_json=metadata,
        ip_address=ip_address,
        timestamp=utcnow(),
    )

    extra = dict(additional_hash_fields or {})
    for field, value in extra.items():
        setattr(entry, field, value)

    db.add(entry)
    db.flush()

    entry.tamper_hash = compute_tamper_hash(entry, prev_hash)
    db.commit()
    db.refresh(entry)
    return entry


def validate_chain(db: Session) -> tuple[bool, Optional[str]]:
    rows = db.query(AuditTrail).order_by(AuditTrail.event_id.asc()).all()
    prev_hash = "0" * 64
    for row in rows:
        if row.tamper_hash != compute_tamper_hash(row, prev_hash):
            return False, f"Hash mismatch at event_id={row.event_id}"
        prev_hash = row.tamper_hash
    return True, None