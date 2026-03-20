"""Tests for storage backend (using in-memory implementation)."""

from __future__ import annotations

# skipcq: PYL-R0201
import pytest

from grounded.api.storage import InMemoryStorage, get_storage, set_storage


class TestInMemoryStorage:
    def test_upload_and_download_pdf(self) -> None:
        storage = InMemoryStorage()
        pdf_bytes = b"%PDF-1.4 fake content"
        key = storage.upload_pdf("tenant-1", "job-1", pdf_bytes)
        assert key == "tenant-1/job-1/input.pdf"
        assert storage.download_pdf(key) == pdf_bytes

    def test_download_missing_raises(self) -> None:
        storage = InMemoryStorage()
        with pytest.raises(FileNotFoundError):
            storage.download_pdf("nonexistent/key")

    def test_upload_results(self) -> None:
        storage = InMemoryStorage()
        results = b'{"passed": true}'
        key = storage.upload_results("tenant-1", "job-1", results)
        assert key == "tenant-1/job-1/results.json"
        assert storage.download_pdf(key) == results  # reuses same dict

    def test_generate_presigned_url(self) -> None:
        storage = InMemoryStorage()
        url = storage.generate_presigned_url("tenant-1/job-1/input.pdf")
        assert "fake-presigned" in url
        assert "tenant-1/job-1/input.pdf" in url

    def test_delete_file(self) -> None:
        storage = InMemoryStorage()
        storage.upload_pdf("tenant-1", "job-1", b"data")
        key = "tenant-1/job-1/input.pdf"
        storage.delete_file(key)
        with pytest.raises(FileNotFoundError):
            storage.download_pdf(key)

    def test_delete_nonexistent_no_error(self) -> None:
        storage = InMemoryStorage()
        storage.delete_file("does/not/exist")  # Should not raise


class TestStorageSingleton:
    def test_set_and_get_storage(self) -> None:
        mem = InMemoryStorage()
        set_storage(mem)
        assert get_storage() is mem

    def test_get_storage_returns_same_instance(self) -> None:
        mem = InMemoryStorage()
        set_storage(mem)
        assert get_storage() is get_storage()
