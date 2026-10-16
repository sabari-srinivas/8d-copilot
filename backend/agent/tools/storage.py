"""Bytes in, URL out. Local files in dev, Cloud Storage when FILES_BACKEND=gcs."""
from pathlib import Path

from agent.config import get_settings

LOCAL_DIR = Path(__file__).resolve().parents[2] / "data" / "out" / "files"


def put_bytes(data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
    s = get_settings()
    if s.files_backend == "gcs":
        from google.cloud import storage
        blob = storage.Client(project=s.gcp_project).bucket(s.gcs_bucket).blob(key)
        blob.upload_from_string(data, content_type=content_type)
        return f"https://storage.googleapis.com/{s.gcs_bucket}/{key}"
    path = LOCAL_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"/api/files/{key}"


def get_local_path(key: str) -> Path:
    return LOCAL_DIR / key
