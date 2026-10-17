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
        # This flat https://storage.googleapis.com/... URL is handed straight to a
        # browser <img src> (defect photo, reflow chart) — it is NOT routed through
        # our own API, so it only resolves if the bucket grants public read. With
        # uniform bucket-level access (the default, and what GCS_BUCKET is deployed
        # with) per-object ACLs / blob.make_public() don't work at all; the fix is a
        # bucket-level IAM binding: `gsutil iam ch allUsers:objectViewer
        # gs://<GCS_BUCKET>`. Found live during Task 16 deploy verification — the
        # investigation ran end to end and the URL was returned correctly, but the
        # <img> 403'd because nobody had granted this. Do it once per bucket, not
        # per deploy; a fresh bucket needs it applied again.
        return f"https://storage.googleapis.com/{s.gcs_bucket}/{key}"
    path = LOCAL_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"/api/files/{key}"


def get_local_path(key: str) -> Path:
    """Resolve `key` under LOCAL_DIR, refusing anything that escapes it.

    The public `/api/files/{key:path}` route in main.py serves whatever this returns
    with no auth other than the demo code, so a path that climbs out of LOCAL_DIR
    would let anyone read arbitrary files off the container (confirmed exploitable:
    `GET /api/files/%2e%2e/%2e%2e/%2e%2e/pyproject.toml` returned the file before this
    check existed — the percent-encoded `..` survives Starlette's own path routing,
    where a literal `../` in the URL would already have been normalised away). A plain
    `key.startswith("..")` check is not enough for the same reason: it only catches the
    decoded literal, not an encoded or otherwise disguised equivalent. Resolving the
    path and checking containment with `is_relative_to` is robust to both.
    """
    path = (LOCAL_DIR / key).resolve()
    if not path.is_relative_to(LOCAL_DIR.resolve()):
        raise ValueError("path escapes the files directory")
    return path
