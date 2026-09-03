from typing import Optional

from supabase import Client

from app.core.supabase import get_supabase

EVIDENCE_BUCKET = "evidence-vault"


def init_storage() -> str:
    supabase = get_supabase()
    try:
        supabase.storage.create_bucket(
            EVIDENCE_BUCKET,
            options={"public": False},
        )
    except Exception:
        pass
    return EVIDENCE_BUCKET


def upload_evidence_bytes(object_key: str, data: bytes, content_type: str) -> None:
    supabase = get_supabase()
    supabase.storage.from_(EVIDENCE_BUCKET).upload(
        path=object_key,
        file=data,
        file_options={"content-type": content_type},
    )


def download_evidence_bytes(object_name: str) -> bytes:
    supabase = get_supabase()
    return supabase.storage.from_(EVIDENCE_BUCKET).download(object_name)


def stat_evidence_bytes(object_name: str) -> int:
    supabase = get_supabase()
    files = supabase.storage.from_(EVIDENCE_BUCKET).list()
    for f in files:
        if f.get("name") == object_name.split("/")[-1]:
            return f.get("metadata", {}).get("size", 0)
    return 0


def build_presigned_url(object_name: str, expires_seconds: int) -> str:
    supabase = get_supabase()
    result = supabase.storage.from_(EVIDENCE_BUCKET).create_signed_url(
        path=object_name,
        expires_in=expires_seconds,
    )
    if isinstance(result, dict):
        return result.get("signedURL", "")
    return result


def delete_evidence_object(object_name: str) -> None:
    supabase = get_supabase()
    supabase.storage.from_(EVIDENCE_BUCKET).remove([object_name])


def list_evidence_objects(folder_path: str = "") -> list:
    supabase = get_supabase()
    return supabase.storage.from_(EVIDENCE_BUCKET).list(path=folder_path)
