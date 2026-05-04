"""
backend/storage.py
------------------
MinIO client wrapper for object storage operations.

Buckets used:
  fmea-documents  — PDFs, Excel, DOCX uploaded per session
  meetings-media  — audio/video recordings of meetings
  fmea-reports    — generated PDF reports

Key path conventions:
  fmea-documents : sessions/{session_id}/{filename}
  meetings-media : meetings/{meeting_id}/{audio|video}/{filename}
  fmea-reports   : reports/{report_id}/report.pdf

Usage:
    from backend.storage import storage
    url = await storage.upload_file(bucket, key, data, content_type)
    await storage.delete_file(bucket, key)
"""

from __future__ import annotations

import io
import os
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

# ---------------------------------------------------------------------------
# Bucket names (single source of truth)
# ---------------------------------------------------------------------------

BUCKET_DOCUMENTS = "fmea-documents"
BUCKET_MEETINGS  = "meetings-media"
BUCKET_REPORTS   = "fmea-reports"

ALL_BUCKETS = [BUCKET_DOCUMENTS, BUCKET_MEETINGS, BUCKET_REPORTS]

# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def _build_client() -> Minio:
    endpoint   = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "fmea_minio")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minio_secret")
    secure     = os.getenv("MINIO_SECURE", "false").lower() == "true"

    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


# Module-level singleton — re-used across requests
_client: Minio | None = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


# ---------------------------------------------------------------------------
# Bucket initialisation — called from main.py lifespan
# ---------------------------------------------------------------------------

import logging as _logging

async def ensure_buckets() -> None:
    """
    Creates the required buckets if they do not already exist.
    Non-fatal: logs a warning if MinIO is unreachable at startup.
    """
    _log = _logging.getLogger(__name__)
    try:
        client = get_client()
        for bucket in ALL_BUCKETS:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
        _log.info("MinIO buckets ready: %s", ALL_BUCKETS)
    except Exception as exc:
        _log.warning(
            "MinIO not reachable at startup (%s: %s) — buckets will be created on first use.",
            type(exc).__name__, exc
        )


# ---------------------------------------------------------------------------
# High-level helpers
# ---------------------------------------------------------------------------

def upload_bytes(
    bucket: str,
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Uploads raw bytes to MinIO.

    Returns the object key (same as `key` parameter).
    """
    client = get_client()
    client.put_object(
        bucket_name=bucket,
        object_name=key,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return key


def upload_file(
    bucket: str,
    key: str,
    file_obj: BinaryIO,
    length: int,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Uploads a file-like object to MinIO.

    Returns the object key.
    """
    client = get_client()
    client.put_object(
        bucket_name=bucket,
        object_name=key,
        data=file_obj,
        length=length,
        content_type=content_type,
    )
    return key


def download_bytes(bucket: str, key: str) -> bytes:
    """Downloads an object and returns its content as bytes."""
    client = get_client()
    response = client.get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_file(bucket: str, key: str) -> None:
    """Deletes an object. Silently ignores if object does not exist."""
    client = get_client()
    try:
        client.remove_object(bucket, key)
    except S3Error as exc:
        if exc.code != "NoSuchKey":
            raise


def get_presigned_url(
    bucket: str,
    key: str,
    expires_seconds: int = 3600,
) -> str:
    """
    Returns a pre-signed GET URL valid for `expires_seconds`.
    Useful for serving files directly to the browser without proxying.
    """
    from datetime import timedelta

    client = get_client()
    return client.presigned_get_object(
        bucket_name=bucket,
        object_name=key,
        expires=timedelta(seconds=expires_seconds),
    )


# ---------------------------------------------------------------------------
# Path builders (keep naming consistent across the codebase)
# ---------------------------------------------------------------------------

def document_key(session_id: str, filename: str) -> str:
    return f"sessions/{session_id}/{filename}"


def meeting_media_key(meeting_id: str, media_type: str, filename: str) -> str:
    """media_type: 'audio' or 'video'"""
    return f"meetings/{meeting_id}/{media_type}/{filename}"


def report_key(report_id: str) -> str:
    return f"reports/{report_id}/report.pdf"
