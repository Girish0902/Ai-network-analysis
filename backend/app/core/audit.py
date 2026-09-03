import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from supabase import Client


_CANONICAL = "|"


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


def _chain_hash(prev_hash: str, entry: Dict[str, Any]) -> str:
    payload = _CANONICAL.join(
        [
            prev_hash,
            _canonicalize(entry.get("user_id")),
            _canonicalize(entry.get("case_id")),
            _canonicalize(entry.get("action_type")),
            _canonicalize(entry.get("metadata_json")),
            _canonicalize(entry.get("ip_address")),
            _canonicalize(entry.get("timestamp")),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_audit(
    supabase: Client,
    action_type: str,
    user_id: Optional[str] = None,
    case_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    last = (
        supabase.table("audit_trails")
        .select("*")
        .order("event_id", desc=True)
        .limit(1)
        .execute()
    )

    prev_hash = last.data[0]["tamper_hash"] if last.data else "0" * 64

    entry = {
        "user_id": user_id,
        "case_id": case_id,
        "action_type": action_type,
        "metadata_json": metadata or {},
        "ip_address": ip_address,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    entry["tamper_hash"] = _chain_hash(prev_hash, entry)
    supabase.table("audit_trails").insert(entry).execute()


def validate_chain(supabase: Client) -> tuple[bool, Optional[str]]:
    rows = (
        supabase.table("audit_trails")
        .select("*")
        .order("event_id", asc=True)
        .execute()
    ).data

    prev_hash = "0" * 64
    for row in rows:
        entry = {
            "user_id": row.get("user_id"),
            "case_id": row.get("case_id"),
            "action_type": row.get("action_type"),
            "metadata_json": row.get("metadata_json"),
            "ip_address": row.get("ip_address"),
            "timestamp": row.get("timestamp"),
        }
        computed = _chain_hash(prev_hash, entry)
        if row.get("tamper_hash") != computed:
            return False, f"Hash mismatch at event_id={row.get('event_id')}"
        prev_hash = computed
    return True, None
