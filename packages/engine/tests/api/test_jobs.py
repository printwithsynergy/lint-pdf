"""Tests for job submission and retrieval endpoints."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestSubmitJob:
    @staticmethod
    def test_submit_pdf(client: TestClient, minimal_pdf_bytes: bytes) -> None:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("test.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
            data={"profile_id": "lintpdf-default"},
        )
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"

    def test_submit_with_default_profile(
        self, client: TestClient, minimal_pdf_bytes: bytes
    ) -> None:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("test.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 202

    @staticmethod
    def test_submit_non_pdf_rejected(client: TestClient) -> None:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("test.txt", BytesIO(b"hello world"), "text/plain")},
        )
        assert response.status_code == 422

    @staticmethod
    def test_submit_empty_file_rejected(client: TestClient) -> None:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("test.pdf", BytesIO(b""), "application/pdf")},
        )
        assert response.status_code == 422

    @staticmethod
    def test_submit_invalid_pdf_rejected(client: TestClient) -> None:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("test.pdf", BytesIO(b"not a pdf"), "application/pdf")},
        )
        assert response.status_code == 422


class TestGetJob:
    @staticmethod
    def test_get_pending_job(client: TestClient, minimal_pdf_bytes: bytes) -> None:
        submit = client.post(
            "/api/v1/jobs",
            files={"file": ("test.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
        )
        job_id = submit.json()["job_id"]

        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["profile_id"] == "lintpdf-default"
        assert data["file_name"] == "test.pdf"

    @staticmethod
    def test_get_nonexistent_job(client: TestClient) -> None:
        response = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestListJobs:
    @staticmethod
    def test_list_empty(client: TestClient) -> None:
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["jobs"] == []
        assert data["page"] == 1

    @staticmethod
    def test_list_after_submit(client: TestClient, minimal_pdf_bytes: bytes) -> None:
        client.post(
            "/api/v1/jobs",
            files={"file": ("test.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
        )
        response = client.get("/api/v1/jobs")
        data = response.json()
        assert data["total"] == 1
        assert len(data["jobs"]) == 1

    @staticmethod
    def test_pagination(client: TestClient, minimal_pdf_bytes: bytes) -> None:
        for _ in range(5):
            client.post(
                "/api/v1/jobs",
                files={"file": ("test.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
            )
        response = client.get("/api/v1/jobs?page=1&page_size=2")
        data = response.json()
        assert data["total"] == 5
        assert len(data["jobs"]) == 2
        assert data["page_size"] == 2


class TestDeleteJob:
    @staticmethod
    def test_delete_job(client: TestClient, minimal_pdf_bytes: bytes) -> None:
        submit = client.post(
            "/api/v1/jobs",
            files={"file": ("test.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
        )
        job_id = submit.json()["job_id"]
        response = client.delete(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 204

        get = client.get(f"/api/v1/jobs/{job_id}")
        assert get.status_code == 404

    @staticmethod
    def test_delete_nonexistent(client: TestClient) -> None:
        response = client.delete("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
