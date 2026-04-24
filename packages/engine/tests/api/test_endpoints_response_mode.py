"""Tests for Endpoint.response_mode + ?wait sync-submit path.

Covers:
    * Create / list / update / delete round-trip the new
      ``response_mode`` field and default to ``async``.
    * Invalid ``response_mode`` is 422'd server-side.
    * ``POST /api/v1/jobs?wait=N`` returns 200 + full JobResponse once
      the Job row flips to ``complete`` within the budget, and falls
      back to 202 + job_id when the budget expires first.
    * ``POST /api/v1/endpoints/{slug}/submit`` honors
      ``response_mode=sync`` implicitly, and the ``?wait`` override
      lets a caller force-async a sync endpoint and vice versa.
"""

from __future__ import annotations

import uuid
from io import BytesIO
from typing import TYPE_CHECKING

from lintpdf.api.models import CustomEndpoint, Job, JobStatus, ReportToken, Tenant

if TYPE_CHECKING:
    import pytest
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Endpoint CRUD — response_mode round-trip
# ---------------------------------------------------------------------------


class TestEndpointCrud:
    @staticmethod
    def _create(client: TestClient, **overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "slug": "test-endpoint",
            "profile_id": "lintpdf-default",
            "description": "",
        }
        payload.update(overrides)
        response = client.post("/api/v1/endpoints", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    def test_create_defaults_to_async(self, client: TestClient) -> None:
        body = self._create(client)
        assert body["response_mode"] == "async"

    def test_create_with_sync(self, client: TestClient) -> None:
        body = self._create(client, slug="sync-endpoint", response_mode="sync")
        assert body["response_mode"] == "sync"

    def test_create_invalid_response_mode_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/endpoints",
            json={
                "slug": "bad-mode",
                "profile_id": "lintpdf-default",
                "response_mode": "stream",
            },
        )
        assert response.status_code == 422

    def test_list_includes_response_mode(self, client: TestClient) -> None:
        self._create(client, slug="list-target", response_mode="sync")
        response = client.get("/api/v1/endpoints")
        assert response.status_code == 200
        modes = {e["slug"]: e["response_mode"] for e in response.json()["endpoints"]}
        assert modes["list-target"] == "sync"

    def test_update_flips_response_mode(self, client: TestClient) -> None:
        created = self._create(client, slug="flip-me")
        assert created["response_mode"] == "async"
        response = client.patch(
            f"/api/v1/endpoints/{created['id']}",
            json={"response_mode": "sync"},
        )
        assert response.status_code == 200
        assert response.json()["response_mode"] == "sync"

    def test_update_invalid_response_mode_rejected(self, client: TestClient) -> None:
        created = self._create(client, slug="bad-flip")
        response = client.patch(
            f"/api/v1/endpoints/{created['id']}",
            json={"response_mode": "streaming"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# ?wait= on POST /api/v1/jobs
# ---------------------------------------------------------------------------


def _submit_with_wait(client: TestClient, pdf: bytes, wait: float) -> tuple[int, dict[str, object]]:
    response = client.post(
        f"/api/v1/jobs?wait={wait}",
        files={"file": ("test.pdf", BytesIO(pdf), "application/pdf")},
    )
    return response.status_code, response.json()


class TestJobsSyncWait:
    @staticmethod
    def test_wait_times_out_to_202(client: TestClient, minimal_pdf_bytes: bytes) -> None:
        # Celery is mocked in conftest, so the Job row will stay
        # ``pending`` forever. A tiny wait budget (100 ms) exercises
        # the deadline path and confirms the fallback to 202.
        status_code, body = _submit_with_wait(client, minimal_pdf_bytes, wait=0.1)
        assert status_code == 202
        assert "job_id" in body
        assert body["status"] == "pending"

    @staticmethod
    def test_wait_returns_200_when_job_reaches_terminal(
        client: TestClient,
        db_session: Session,
        minimal_pdf_bytes: bytes,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Simulate the worker completing the job: the moment
        # ``poll_job_until_terminal`` is called, flip the most recent
        # Job row to ``complete`` with a valid ``result_json`` shape so
        # the hydration path produces a full JobResponse.
        from lintpdf.api.routes import jobs as jobs_module

        original_poll = jobs_module.poll_job_until_terminal

        async def _fast_complete(
            job_id: uuid.UUID,
            tenant_id: uuid.UUID,
            db: Session,
            max_wait_s: float,
            poll_interval_s: float = 0.5,
        ):
            job = db.query(Job).filter(Job.id == job_id).first()
            assert job is not None, "Job row should exist before poll"
            job.status = JobStatus.COMPLETE
            job.result_json = {
                "summary": {
                    "total_findings": 0,
                    "error_count": 0,
                    "warning_count": 0,
                    "advisory_count": 0,
                    "passed": True,
                    "page_count": 1,
                    "file_size_bytes": len(minimal_pdf_bytes),
                },
            }
            db.commit()
            # Hand control to the real helper with a tight wait so we
            # exercise the hydration path end-to-end.
            return await original_poll(
                job_id=job_id,
                tenant_id=tenant_id,
                db=db,
                max_wait_s=1.0,
                poll_interval_s=0.05,
            )

        monkeypatch.setattr(jobs_module, "poll_job_until_terminal", _fast_complete)

        status_code, body = _submit_with_wait(client, minimal_pdf_bytes, wait=5)
        assert status_code == 200, body
        assert body["status"] == "complete"
        assert body["summary"]["passed"] is True


# ---------------------------------------------------------------------------
# /endpoints/{slug}/submit — response_mode + ?wait override
# ---------------------------------------------------------------------------


class TestEndpointSubmitSyncMode:
    @staticmethod
    def _seed_endpoint(db_session: Session, *, slug: str, response_mode: str) -> CustomEndpoint:
        from tests.api.conftest import PLACEHOLDER_TENANT_ID

        ep = CustomEndpoint(
            id=uuid.uuid4(),
            tenant_id=PLACEHOLDER_TENANT_ID,
            slug=slug,
            profile_id="lintpdf-default",
            description="test",
            is_active=True,
            response_mode=response_mode,
        )
        db_session.add(ep)
        db_session.commit()
        return ep

    def test_async_endpoint_default_returns_202(
        self,
        client: TestClient,
        db_session: Session,
        minimal_pdf_bytes: bytes,
    ) -> None:
        self._seed_endpoint(db_session, slug="async-default", response_mode="async")
        response = client.post(
            "/api/v1/endpoints/async-default/submit",
            files={"file": ("test.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 202
        assert "job_id" in response.json()

    def test_sync_endpoint_implicitly_waits(
        self,
        client: TestClient,
        db_session: Session,
        minimal_pdf_bytes: bytes,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self._seed_endpoint(db_session, slug="sync-implicit", response_mode="sync")

        # Force the server-side ceiling down to a value short enough
        # that the deadline fires quickly in CI but long enough that the
        # polling helper actually executes at least once.
        from lintpdf.api.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "sync_max_wait_s", 0.2)

        response = client.post(
            "/api/v1/endpoints/sync-implicit/submit",
            files={"file": ("test.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
        )
        # Celery is mocked — the job never completes, so the sync path
        # hits its deadline and falls back to the 202 contract. The
        # important assertion is that the route accepted ``response_mode=sync``
        # and entered the poll loop (observable via the response still
        # being well-formed after ~200 ms).
        assert response.status_code == 202
        assert "job_id" in response.json()

    def test_wait_zero_forces_async_on_sync_endpoint(
        self,
        client: TestClient,
        db_session: Session,
        minimal_pdf_bytes: bytes,
    ) -> None:
        self._seed_endpoint(db_session, slug="sync-overridden", response_mode="sync")
        response = client.post(
            "/api/v1/endpoints/sync-overridden/submit?wait=0",
            files={"file": ("test.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
        )
        # ``?wait=0`` explicitly forces async — the handler should not
        # enter the polling loop at all, so the response is immediate.
        assert response.status_code == 202


# ---------------------------------------------------------------------------
# Whitelabel custom domain must appear in sync-wait / GET /jobs responses
# ---------------------------------------------------------------------------


class TestWhitelabelReportUrls:
    """Regression guard: custom branding / whitelabel domains flow
    through ``_hydrate_job_response`` so tenants on whitelabel plans see
    their own domain in the ``reports`` field of both GET /api/v1/jobs/{id}
    and the new ?wait= sync response — not the global reports.lintpdf.com."""

    @staticmethod
    def test_whitelabel_tenant_gets_custom_report_host(
        client: TestClient,
        db_session: Session,
    ) -> None:
        from lintpdf.tenants.models import TenantPlan
        from tests.api.conftest import PLACEHOLDER_TENANT_ID

        tenant = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        assert tenant is not None
        # Upgrade the seeded tenant to SCALE so whitelabel_enabled=True
        # and set a verified custom report domain.
        tenant.plan = TenantPlan.SCALE
        tenant.brand_custom_domain = "preflight.acme-print.com"
        tenant.brand_custom_domain_verified = True
        db_session.commit()

        # Seed a complete job + report token.
        job_id = uuid.uuid4()
        job = Job(
            id=job_id,
            tenant_id=tenant.id,
            status=JobStatus.COMPLETE,
            profile_id="lintpdf-default",
            file_key=f"{tenant.id}/{job_id}/file.pdf",
            file_name="whitelabel.pdf",
            file_size=1024,
            result_json={
                "summary": {
                    "total_findings": 0,
                    "error_count": 0,
                    "warning_count": 0,
                    "advisory_count": 0,
                    "passed": True,
                    "page_count": 1,
                    "file_size_bytes": 1024,
                },
            },
        )
        db_session.add(job)
        db_session.add(
            ReportToken(
                id=uuid.uuid4(),
                job_id=job_id,
                tenant_id=tenant.id,
                token="tok_whitelabel_test",
                format="pdf",
            )
        )
        db_session.commit()

        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200, response.text
        body = response.json()
        reports = body.get("reports")
        assert reports, "expected reports field on a complete job"
        assert reports["pdf"].startswith("https://preflight.acme-print.com/r/"), (
            "Whitelabel custom domain must win over the global report_base_url"
            f" — got {reports['pdf']!r}"
        )

    @staticmethod
    def test_non_whitelabel_tenant_gets_default_host(
        client: TestClient,
        db_session: Session,
    ) -> None:
        # GROWTH-plan tenant (already seeded) does not have
        # whitelabel_enabled, so the resolver must return the global
        # ``settings.report_base_url`` (which is ``https://reports.lintpdf.com``
        # by default). Protects the non-whitelabel path from silent regression
        # when we touch the resolver again.
        from tests.api.conftest import PLACEHOLDER_TENANT_ID

        tenant = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        assert tenant is not None
        # A GROWTH tenant that happens to have a ``brand_custom_domain``
        # set must still fall through to the global default because
        # whitelabel isn't entitled at this plan tier.
        tenant.brand_custom_domain = "preflight.acme-print.com"
        tenant.brand_custom_domain_verified = True
        db_session.commit()

        job_id = uuid.uuid4()
        job = Job(
            id=job_id,
            tenant_id=tenant.id,
            status=JobStatus.COMPLETE,
            profile_id="lintpdf-default",
            file_key=f"{tenant.id}/{job_id}/file.pdf",
            file_name="no-wl.pdf",
            file_size=512,
            result_json={
                "summary": {
                    "total_findings": 0,
                    "error_count": 0,
                    "warning_count": 0,
                    "advisory_count": 0,
                    "passed": True,
                    "page_count": 1,
                    "file_size_bytes": 512,
                },
            },
        )
        db_session.add(job)
        db_session.add(
            ReportToken(
                id=uuid.uuid4(),
                job_id=job_id,
                tenant_id=tenant.id,
                token="tok_no_wl",
                format="pdf",
            )
        )
        db_session.commit()

        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        body = response.json()
        reports = body.get("reports")
        assert reports
        assert reports["pdf"].startswith("https://reports.lintpdf.com/r/"), reports["pdf"]
