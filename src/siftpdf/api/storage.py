"""S3-compatible file storage for PDF uploads and results."""

from __future__ import annotations

import threading
from typing import Any

_storage_lock = threading.Lock()


class StorageBackend:
    """S3-compatible storage backend for PDF files and results.

    Supports Cloudflare R2, AWS S3, MinIO, and any S3-compatible service.
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        bucket_name: str = "lintpdf-uploads",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region: str = "auto",
    ) -> None:
        self._endpoint_url = endpoint_url
        self._bucket_name = bucket_name
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._region = region
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-initialize the S3 client."""
        if self._client is None:
            import boto3
            from botocore.config import Config as BotoConfig

            kwargs: dict[str, Any] = {
                "service_name": "s3",
                "region_name": self._region,
                "config": BotoConfig(
                    connect_timeout=10,
                    read_timeout=30,
                    retries={"max_attempts": 2},
                ),
            }
            if self._endpoint_url:
                kwargs["endpoint_url"] = self._endpoint_url
            if self._access_key_id:
                kwargs["aws_access_key_id"] = self._access_key_id
            if self._secret_access_key:
                kwargs["aws_secret_access_key"] = self._secret_access_key

            self._client = boto3.client(**kwargs)

        return self._client

    def upload_pdf(self, tenant_id: str, job_id: str, pdf_bytes: bytes) -> str:
        """Upload a PDF file to storage.

        Args:
            tenant_id: Tenant UUID string.
            job_id: Job UUID string.
            pdf_bytes: Raw PDF content.

        Returns:
            The storage key (path) where the file was stored.
        """
        key = f"{tenant_id}/{job_id}/input.pdf"
        client = self._get_client()
        client.put_object(
            Bucket=self._bucket_name,
            Key=key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
        return key

    def upload_pdf_stream(
        self,
        tenant_id: str,
        job_id: str,
        fileobj: Any,
    ) -> str:
        """Upload a PDF file from a readable file-like object.

        Unlike :py:meth:`upload_pdf` which takes the full body as ``bytes``,
        this streams the upload directly to S3 via ``upload_fileobj``
        (which internally uses multipart chunks) so the worker never
        holds more than a few MB in memory at once. This is the hot
        path for bulk-file ingest; see the 2026-04-21 engine-down
        incident where byte-resident upload bodies OOM'd the container.

        The caller is responsible for seeking ``fileobj`` back to
        position 0 before invoking this method.

        Args:
            tenant_id: Tenant UUID string.
            job_id: Job UUID string.
            fileobj: A readable, seekable file-like object positioned
                at the start of the PDF body (e.g. a
                ``tempfile.SpooledTemporaryFile``).

        Returns:
            The storage key (path) where the file was stored.
        """
        key = f"{tenant_id}/{job_id}/input.pdf"
        client = self._get_client()
        client.upload_fileobj(
            Fileobj=fileobj,
            Bucket=self._bucket_name,
            Key=key,
            ExtraArgs={"ContentType": "application/pdf"},
        )
        return key

    def download_pdf(self, file_key: str) -> bytes:
        """Download a PDF file from storage.

        Args:
            file_key: Storage key returned by upload_pdf.

        Returns:
            Raw PDF bytes.
        """
        client = self._get_client()
        response = client.get_object(Bucket=self._bucket_name, Key=file_key)
        result: bytes = response["Body"].read()
        return result

    def upload_results(self, tenant_id: str, job_id: str, results_json: bytes) -> str:
        """Upload JSON results to storage.

        Args:
            tenant_id: Tenant UUID string.
            job_id: Job UUID string.
            results_json: Serialized JSON results.

        Returns:
            The storage key where results were stored.
        """
        key = f"{tenant_id}/{job_id}/results.json"
        client = self._get_client()
        client.put_object(
            Bucket=self._bucket_name,
            Key=key,
            Body=results_json,
            ContentType="application/json",
        )
        return key

    def generate_presigned_url(self, file_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned download URL.

        Args:
            file_key: Storage key of the file.
            expires_in: URL expiration time in seconds (default 1 hour).

        Returns:
            Presigned URL string.
        """
        client = self._get_client()
        url: str = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket_name, "Key": file_key},
            ExpiresIn=expires_in,
        )
        return url

    def upload_report(self, tenant_id: str, job_id: str, fmt: str, content: bytes) -> str:
        """Upload a generated report to storage.

        Args:
            tenant_id: Tenant UUID string.
            job_id: Job UUID string.
            fmt: Report format ("html" or "pdf").
            content: Report content bytes.

        Returns:
            The storage key where the report was stored.
        """
        key = f"reports/{tenant_id}/{job_id}/report.{fmt}"
        content_type = "text/html" if fmt == "html" else "application/pdf"
        client = self._get_client()
        client.put_object(
            Bucket=self._bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return key

    def download_report(self, tenant_id: str, job_id: str, fmt: str) -> bytes:
        """Download a report from storage.

        Args:
            tenant_id: Tenant UUID string.
            job_id: Job UUID string.
            fmt: Report format ("html" or "pdf").

        Returns:
            Report content bytes.
        """
        key = f"reports/{tenant_id}/{job_id}/report.{fmt}"
        client = self._get_client()
        response = client.get_object(Bucket=self._bucket_name, Key=key)
        result: bytes = response["Body"].read()
        return result

    def report_object_exists(self, tenant_id: str, job_id: str, fmt: str) -> bool:
        """Cheap existence probe for a stored report object.

        Used by the deterministic-token fast path so we can reuse a
        previously minted artifact instead of regenerating + re-uploading
        identical bytes. A missing object returns False; any other error
        is reraised so genuine outages surface.
        """
        key = f"reports/{tenant_id}/{job_id}/report.{fmt}"
        try:
            client = self._get_client()
            client.head_object(Bucket=self._bucket_name, Key=key)
            return True
        except Exception as exc:
            # boto3 raises ClientError with .response["Error"]["Code"]
            # equal to "404" / "NoSuchKey" / "NotFound" for missing
            # objects. We don't import botocore here so the in-memory
            # backend (and future non-boto3 backends) don't need it.
            response = getattr(exc, "response", None)
            code = None
            if isinstance(response, dict):
                code = response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def delete_file(self, file_key: str) -> None:
        """Delete a file from storage.

        Args:
            file_key: Storage key of the file to delete.
        """
        client = self._get_client()
        client.delete_object(Bucket=self._bucket_name, Key=file_key)

    def upload_raw(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        cache_control: str | None = None,
    ) -> str:
        """Upload arbitrary bytes to storage at the given key.

        Args:
            key: Full storage key.
            data: Raw bytes to store.
            content_type: MIME type for the object.
            cache_control: Optional Cache-Control header for the object.

        Returns:
            The storage key.
        """
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "Bucket": self._bucket_name,
            "Key": key,
            "Body": data,
            "ContentType": content_type,
        }
        if cache_control:
            kwargs["CacheControl"] = cache_control
        client.put_object(**kwargs)
        return key

    def download_raw(self, key: str) -> bytes | None:
        """Download arbitrary bytes from storage.

        Returns None if the key does not exist.
        """
        try:
            client = self._get_client()
            response = client.get_object(Bucket=self._bucket_name, Key=key)
            result: bytes = response["Body"].read()
            return result
        except Exception:
            return None


_storage_state: dict[str, StorageBackend | None] = {"instance": None}


def get_storage() -> StorageBackend:
    """Get the configured storage backend singleton.

    Initializes from settings on first call. Tests can override via
    set_storage().

    Returns:
        Configured StorageBackend instance.
    """
    if _storage_state["instance"] is None:
        with _storage_lock:
            if _storage_state["instance"] is None:
                from siftpdf.api.config import get_settings

                settings = get_settings()

                # Strip whitespace from every S3 setting because Railway
                # (and some docker-compose envs) silently preserve leading
                # or trailing spaces around the value, and botocore's
                # bucket-name regex rejects them with a raw 500 instead of
                # failing fast at boot. Lost an afternoon debugging a
                # bucket named "lintpdf-uploads " — never again.
                def _clean(v: str | None) -> str | None:
                    return v.strip() if isinstance(v, str) else v

                _storage_state["instance"] = StorageBackend(
                    endpoint_url=_clean(settings.s3_endpoint_url),
                    bucket_name=_clean(settings.s3_bucket_name) or "lintpdf-uploads",
                    access_key_id=_clean(settings.s3_access_key_id),
                    secret_access_key=_clean(settings.s3_secret_access_key),
                    region=_clean(settings.s3_region) or "auto",
                )
    return _storage_state["instance"]  # type: ignore[return-value]


def set_storage(backend: StorageBackend) -> None:
    """Override the storage backend (for testing)."""
    _storage_state["instance"] = backend


class InMemoryStorage(StorageBackend):
    """In-memory storage backend for testing.

    Stores files in a dictionary instead of S3.
    """

    def __init__(self) -> None:
        super().__init__()
        self._files: dict[str, bytes] = {}

    def _get_client(self) -> Any:
        return None

    def upload_pdf(self, tenant_id: str, job_id: str, pdf_bytes: bytes) -> str:
        key = f"{tenant_id}/{job_id}/input.pdf"
        self._files[key] = pdf_bytes
        return key

    def upload_pdf_stream(self, tenant_id: str, job_id: str, fileobj: Any) -> str:
        """Streaming equivalent of upload_pdf for test compatibility."""
        key = f"{tenant_id}/{job_id}/input.pdf"
        self._files[key] = fileobj.read()
        return key

    def download_pdf(self, file_key: str) -> bytes:
        if file_key not in self._files:
            raise FileNotFoundError(f"File not found: {file_key}")
        return self._files[file_key]

    def upload_results(self, tenant_id: str, job_id: str, results_json: bytes) -> str:
        key = f"{tenant_id}/{job_id}/results.json"
        self._files[key] = results_json
        return key

    def generate_presigned_url(self, file_key: str, expires_in: int = 3600) -> str:
        return f"https://fake-presigned.example.com/{file_key}?expires={expires_in}"

    def upload_report(self, tenant_id: str, job_id: str, fmt: str, content: bytes) -> str:
        key = f"reports/{tenant_id}/{job_id}/report.{fmt}"
        self._files[key] = content
        return key

    def download_report(self, tenant_id: str, job_id: str, fmt: str) -> bytes:
        key = f"reports/{tenant_id}/{job_id}/report.{fmt}"
        if key not in self._files:
            raise FileNotFoundError(f"Report not found: {key}")
        return self._files[key]

    def report_object_exists(self, tenant_id: str, job_id: str, fmt: str) -> bool:
        key = f"reports/{tenant_id}/{job_id}/report.{fmt}"
        return key in self._files

    def delete_file(self, file_key: str) -> None:
        self._files.pop(file_key, None)

    def upload_raw(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        cache_control: str | None = None,
    ) -> str:
        self._files[key] = data
        return key

    def download_raw(self, key: str) -> bytes | None:
        return self._files.get(key)
