"""Tests for corpus testing endpoints."""

from __future__ import annotations

import io
import uuid
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

_MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    b"xref\n0 4\n0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
)


@pytest.fixture(autouse=True)
def _mock_corpus_task(monkeypatch):
    """Prevent execute_corpus_run from dispatching for API tests."""
    from lintpdf.queue import tasks

    monkeypatch.setattr(
        tasks.execute_corpus_run, "apply_async", MagicMock()
    )


class TestCreateAssay:
    def test_create_assay_returns_201(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/corpus/assays",
            files={"file": ("test.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            data={"name": "My assay"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My assay"
        assert "id" in data
        assert data["expected_findings"] is None

    def test_create_assay_stores_pdf_hash(self, client: TestClient) -> None:
        import hashlib

        expected_hash = hashlib.sha256(_MINIMAL_PDF).hexdigest()
        resp = client.post(
            "/api/v1/corpus/assays",
            files={"file": ("test.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            data={"name": "hash-test"},
        )
        assert resp.status_code == 201
        assert resp.json()["pdf_hash"] == expected_hash


class TestListAssays:
    def test_list_returns_created_assay(self, client: TestClient) -> None:
        client.post(
            "/api/v1/corpus/assays",
            files={"file": ("a.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            data={"name": "assay-list-test"},
        )
        resp = client.get("/api/v1/corpus/assays")
        assert resp.status_code == 200
        data = resp.json()
        names = [a["name"] for a in data["assays"]]
        assert "assay-list-test" in names
        assert data["total"] >= 1

    def test_list_empty_initially(self, client: TestClient) -> None:
        resp = client.get("/api/v1/corpus/assays")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestGetAssay:
    def test_get_existing_assay(self, client: TestClient) -> None:
        create = client.post(
            "/api/v1/corpus/assays",
            files={"file": ("b.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            data={"name": "get-test"},
        )
        assay_id = create.json()["id"]
        resp = client.get(f"/api/v1/corpus/assays/{assay_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == assay_id

    def test_get_missing_assay_404(self, client: TestClient) -> None:
        resp = client.get(f"/api/v1/corpus/assays/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestUpdateExpectations:
    def test_patch_sets_expected_findings(self, client: TestClient) -> None:
        create = client.post(
            "/api/v1/corpus/assays",
            files={"file": ("c.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            data={"name": "expectations-test"},
        )
        assay_id = create.json()["id"]

        resp = client.patch(
            f"/api/v1/corpus/assays/{assay_id}/expectations",
            json={
                "expected_findings": [
                    {"inspection_id": "LPDF_IMG_RES", "severity": "error", "page_num": 1}
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["expected_findings"]) == 1
        assert data["expected_findings"][0]["inspection_id"] == "LPDF_IMG_RES"

    def test_patch_null_clears_expectations(self, client: TestClient) -> None:
        create = client.post(
            "/api/v1/corpus/assays",
            files={"file": ("d.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            data={"name": "clear-test"},
        )
        assay_id = create.json()["id"]

        # Set, then clear.
        client.patch(
            f"/api/v1/corpus/assays/{assay_id}/expectations",
            json={"expected_findings": [{"inspection_id": "X", "severity": "error"}]},
        )
        resp = client.patch(
            f"/api/v1/corpus/assays/{assay_id}/expectations",
            json={"expected_findings": None},
        )
        assert resp.status_code == 200
        assert resp.json()["expected_findings"] is None


class TestDeleteAssay:
    def test_delete_returns_204(self, client: TestClient) -> None:
        create = client.post(
            "/api/v1/corpus/assays",
            files={"file": ("del.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            data={"name": "to-delete"},
        )
        assay_id = create.json()["id"]
        resp = client.delete(f"/api/v1/corpus/assays/{assay_id}")
        assert resp.status_code == 204

    def test_deleted_assay_returns_404(self, client: TestClient) -> None:
        create = client.post(
            "/api/v1/corpus/assays",
            files={"file": ("del2.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            data={"name": "to-delete-2"},
        )
        assay_id = create.json()["id"]
        client.delete(f"/api/v1/corpus/assays/{assay_id}")
        assert client.get(f"/api/v1/corpus/assays/{assay_id}").status_code == 404


class TestCreateRun:
    def _create_assay(self, client: TestClient, name: str = "run-assay") -> str:
        resp = client.post(
            "/api/v1/corpus/assays",
            files={"file": (f"{name}.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            data={"name": name},
        )
        return resp.json()["id"]

    def test_create_run_returns_202(self, client: TestClient) -> None:
        assay_id = self._create_assay(client)
        resp = client.post(
            "/api/v1/corpus/runs",
            json={"profile_id": "lintpdf-default", "assay_ids": [assay_id]},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "run_id" in data
        assert data["status"] == "pending"

    def test_create_run_missing_assay_404(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/corpus/runs",
            json={"profile_id": "lintpdf-default", "assay_ids": [str(uuid.uuid4())]},
        )
        assert resp.status_code == 404

    def test_create_run_queues_celery_task(self, client: TestClient, monkeypatch) -> None:
        from unittest.mock import MagicMock
        from lintpdf.queue import tasks

        mock = MagicMock()
        monkeypatch.setattr(tasks.execute_corpus_run, "apply_async", mock)

        assay_id = self._create_assay(client, "celery-test")
        client.post(
            "/api/v1/corpus/runs",
            json={"profile_id": "lintpdf-default", "assay_ids": [assay_id]},
        )
        mock.assert_called_once()


class TestGetRun:
    def _create_run(self, client: TestClient) -> str:
        resp = client.post(
            "/api/v1/corpus/assays",
            files={"file": ("r.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            data={"name": "get-run-assay"},
        )
        assay_id = resp.json()["id"]
        run_resp = client.post(
            "/api/v1/corpus/runs",
            json={"profile_id": "lintpdf-default", "assay_ids": [assay_id]},
        )
        return run_resp.json()["run_id"]

    def test_get_run_returns_pending(self, client: TestClient) -> None:
        run_id = self._create_run(client)
        resp = client.get(f"/api/v1/corpus/runs/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    def test_get_missing_run_404(self, client: TestClient) -> None:
        resp = client.get(f"/api/v1/corpus/runs/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestGetCertificate:
    def test_certificate_404_when_run_not_passed(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/corpus/assays",
            files={"file": ("cert.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            data={"name": "cert-assay"},
        )
        assay_id = resp.json()["id"]
        run_resp = client.post(
            "/api/v1/corpus/runs",
            json={"profile_id": "lintpdf-default", "assay_ids": [assay_id]},
        )
        run_id = run_resp.json()["run_id"]
        # Run is still pending — no certificate yet.
        cert_resp = client.get(f"/api/v1/corpus/runs/{run_id}/certificate")
        assert cert_resp.status_code == 404
