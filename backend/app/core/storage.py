import io
from datetime import timedelta
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings


class LocalResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        return None

    def release_conn(self) -> None:
        return None


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def bucket_exists(self, bucket: str) -> bool:
        return (self.root / bucket).is_dir()

    def make_bucket(self, bucket: str) -> None:
        (self.root / bucket).mkdir(parents=True, exist_ok=True)

    def put_object(
        self,
        bucket: str,
        object_name: str,
        data: Any,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> Any:
        target = self.root / bucket / object_name
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as handle:
            handle.write(data.read())
        return target

    def get_object(self, bucket: str, object_name: str) -> LocalResponse:
        target = self.root / bucket / object_name
        return LocalResponse(target.read_bytes())

    def stat_object(self, bucket: str, object_name: str) -> Any:
        target = self.root / bucket / object_name
        return SimpleStat(size=target.stat().st_size)


class SimpleStat:
    def __init__(self, size: int) -> None:
        self.size = size


_client: Optional[Any] = None


def get_storage() -> Any:
    global _client
    if _client is None:
        if settings.STORAGE_BACKEND == "minio":
            from minio import Minio

            _client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=settings.MINIO_SECURE,
            )
        else:
            _client = LocalFileStorage(Path(settings.LOCAL_STORAGE_ROOT))
    return _client


def is_minio_backend() -> bool:
    return settings.STORAGE_BACKEND == "minio"


def init_storage() -> str:
    client = get_storage()
    bucket = settings.MINIO_BUCKET_NAME
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    return bucket


def upload_evidence_bytes(object_key: str, data: bytes, content_type: str) -> None:
    bucket = settings.MINIO_BUCKET_NAME
    get_storage().put_object(
        bucket,
        object_key,
        io.BytesIO(data),
        len(data),
        content_type=content_type,
    )


def download_evidence_bytes(object_name: str) -> bytes:
    client = get_storage()
    response = client.get_object(settings.MINIO_BUCKET_NAME, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def stat_evidence_bytes(object_name: str) -> int:
    return get_storage().stat_object(settings.MINIO_BUCKET_NAME, object_name).size


def build_presigned_url(object_name: str, expires_seconds: int) -> str:
    if not is_minio_backend():
        raise RuntimeError("Presigned URLs are only available with the MinIO storage backend")
    return get_storage().presigned_get_object(
        settings.MINIO_BUCKET_NAME,
        object_name,
        expires=timedelta(seconds=expires_seconds),
    )