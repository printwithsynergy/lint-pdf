"""Integration tests for viewer config + capability fill-in endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from lintpdf.api.models import (
    BrandProfile,
    BrandProfileType,
    Job,
    JobStatus,
    PreflightSource,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

from tests.api.conftest import PLACEHOLDER_TENANT_ID


def _seed_job(
    db: Session,
    *,
    preflight_source: PreflightSource = PreflightSource.MINIMAL,
    data_capabilities: dict | None = None,
    brand_profile_id_override: uuid.UUID | None = None,
    unbranded_override: bool = False,
) -> Job:
    job = Job(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        status=JobStatus.COMPLETE,
        profile_id="lintpdf-default",
        file_key="seed/key.pdf",
        file_name="seed.pdf",
        file_size=1024,
        created_at=datetime.now(timezone.utc),
        preflight_source=preflight_source,
        data_capabilities=data_capabilities,
        brand_profile_id_override=brand_profile_id_override,
        unbranded_override=unbranded_override,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


# ---------------------------------------------------------------------------
# Viewer config — capabilities + preflight_source projection
# ---------------------------------------------------------------------------


class TestViewerConfigProjection:
    """``GET /viewer/jobs/{id}/config`` surfaces per-job capability state."""

    @staticmethod
    def test_minimal_job_exposes_capabilities_and_source(
        client: TestClient, db_session: Session
    ) -> None:
        job = _seed_job(
            db_session,
            preflight_source=PreflightSource.MINIMAL,
            data_capabilities={
                "findings": False,
                "separations": False,
                "tac": False,
                "thumbnails": True,
                "metadata": True,
            },
        )

        resp = client.get(f"/api/v1/viewer/jobs/{job.id}/config")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["preflight_source"] == "minimal"
        assert data["capabilities"]["findings"] is False
        assert data["capabilities"]["separations"] is False
        assert data["capabilities"]["thumbnails"] is True
        # AI-Explain + EPM verdict surface flags must always advertise true.
        # Per-call gating happens inside the explain endpoint via cost-cap.
        assert data["capabilities"]["ai_explain"] is True
        assert data["capabilities"]["epm_verdict"] is True

    @staticmethod
    def test_brand_anonymous_query_strips_chrome(client: TestClient, db_session: Session) -> None:
        job = _seed_job(db_session)
        resp = client.get(f"/api/v1/viewer/jobs/{job.id}/config?brand=anonymous")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["anonymous"] is True
        assert data["brand_name"] is None
        assert data["brand_logo_url"] is None
        assert data["brand_primary_color"] is None
        assert data["brand_accent_color"] is None
        assert data["tenant_name"] is None
        assert data["support_email"] is None

    @staticmethod
    def test_brand_lintpdf_query_restores_lintpdf_chrome(
        client: TestClient, db_session: Session
    ) -> None:
        # Even if the tenant default is anonymous, ``?brand=lintpdf`` wins.
        from lintpdf.api.models import Tenant

        t = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        assert t is not None
        t.unbranded_by_default = True
        db_session.commit()

        job = _seed_job(db_session)
        resp = client.get(f"/api/v1/viewer/jobs/{job.id}/config?brand=lintpdf")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["anonymous"] is False
        assert data["brand_name"] == "LintPDF"

    @staticmethod
    def test_job_unbranded_override_wins_over_tenant_default(
        client: TestClient, db_session: Session
    ) -> None:
        # Tenant has a branded profile as default…
        profile = BrandProfile(
            id=uuid.uuid4(),
            tenant_id=PLACEHOLDER_TENANT_ID,
            name="Branded",
            profile_type=BrandProfileType.CUSTOM,
            brand_name="BrokerCo",
            primary_color="#ff00aa",
        )
        db_session.add(profile)
        from lintpdf.api.models import Tenant

        t = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        assert t is not None
        t.default_brand_profile_id = profile.id
        db_session.commit()

        # …but the job was submitted with ``unbranded=true``.
        job = _seed_job(db_session, unbranded_override=True)
        resp = client.get(f"/api/v1/viewer/jobs/{job.id}/config")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["anonymous"] is True
        assert data["brand_name"] is None


# ---------------------------------------------------------------------------
# POST /viewer/jobs/{id}/capabilities/{capability}
# ---------------------------------------------------------------------------


class TestCapabilityFillEndpoint:
    """Fill-in endpoint enqueues a single-analyzer task and 404/422's cleanly."""

    @staticmethod
    def test_queues_task_for_fillable_capability(
        client: TestClient, db_session: Session, monkeypatch
    ) -> None:
        from lintpdf.queue import tasks as queue_tasks

        mock_task = MagicMock()
        mock_task.id = "task-abc-123"
        monkeypatch.setattr(
            queue_tasks.fill_capability, "apply_async", MagicMock(return_value=mock_task)
        )

        job = _seed_job(
            db_session,
            data_capabilities={"findings": True, "separations": False},
        )
        resp = client.post(f"/api/v1/viewer/jobs/{job.id}/capabilities/separations")
        assert resp.status_code == 202, resp.text
        body = resp.json()
        assert body["status"] == "queued"
        assert body["capability"] == "separations"
        assert body["task_id"] == "task-abc-123"

    @staticmethod
    def test_short_circuits_when_already_filled(client: TestClient, db_session: Session) -> None:
        job = _seed_job(
            db_session,
            data_capabilities={"findings": True, "separations": True},
        )
        resp = client.post(f"/api/v1/viewer/jobs/{job.id}/capabilities/separations")
        assert resp.status_code == 202, resp.text
        assert resp.json()["status"] == "already_filled"

    @staticmethod
    def test_non_fillable_capability_returns_422(client: TestClient, db_session: Session) -> None:
        job = _seed_job(db_session, data_capabilities={"findings": False})
        # ``findings`` itself isn't an on-demand fillable capability —
        # the fill-in registry only covers separations/tac/fonts/images.
        resp = client.post(f"/api/v1/viewer/jobs/{job.id}/capabilities/findings")
        assert resp.status_code == 422
        assert "cannot be filled" in resp.json()["detail"].lower()

    @staticmethod
    def test_unknown_job_returns_404(client: TestClient) -> None:
        resp = client.post(f"/api/v1/viewer/jobs/{uuid.uuid4()}/capabilities/separations")
        assert resp.status_code == 404

    @staticmethod
    def test_bad_uuid_returns_404(client: TestClient) -> None:
        resp = client.post("/api/v1/viewer/jobs/not-a-uuid/capabilities/separations")
        assert resp.status_code == 404
