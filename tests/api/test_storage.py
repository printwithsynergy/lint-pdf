"""Tests for storage backend (using in-memory implementation)."""

from __future__ import annotations

import pytest

from siftpdf.api.storage import InMemoryStorage, get_storage, set_storage


class TestInMemoryStorage:
    @staticmethod
    def test_upload_and_download_pdf() -> None:
        storage = InMemoryStorage()
        pdf_bytes = b"%PDF-1.4 fake content"
        key = storage.upload_pdf("tenant-1", "job-1", pdf_bytes)
        assert key == "tenant-1/job-1/input.pdf"
        assert storage.download_pdf(key) == pdf_bytes

    @staticmethod
    def test_download_missing_raises() -> None:
        storage = InMemoryStorage()
        with pytest.raises(FileNotFoundError):
            storage.download_pdf("nonexistent/key")

    @staticmethod
    def test_upload_results() -> None:
        storage = InMemoryStorage()
        results = b'{"passed": true}'
        key = storage.upload_results("tenant-1", "job-1", results)
        assert key == "tenant-1/job-1/results.json"
        assert storage.download_pdf(key) == results  # reuses same dict

    @staticmethod
    def test_generate_presigned_url() -> None:
        storage = InMemoryStorage()
        url = storage.generate_presigned_url("tenant-1/job-1/input.pdf")
        assert "fake-presigned" in url
        assert "tenant-1/job-1/input.pdf" in url

    @staticmethod
    def test_delete_file() -> None:
        storage = InMemoryStorage()
        storage.upload_pdf("tenant-1", "job-1", b"data")
        key = "tenant-1/job-1/input.pdf"
        storage.delete_file(key)
        with pytest.raises(FileNotFoundError):
            storage.download_pdf(key)

    @staticmethod
    def test_delete_nonexistent_no_error() -> None:
        storage = InMemoryStorage()
        storage.delete_file("does/not/exist")  # Should not raise


class TestStorageSingleton:
    @staticmethod
    def test_set_and_get_storage() -> None:
        mem = InMemoryStorage()
        set_storage(mem)
        assert get_storage() is mem

    @staticmethod
    def test_get_storage_returns_same_instance() -> None:
        mem = InMemoryStorage()
        set_storage(mem)
        assert get_storage() is get_storage()
