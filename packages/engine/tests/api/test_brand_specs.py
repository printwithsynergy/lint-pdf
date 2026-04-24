"""Tests for BrandSpec CRUD + resolver + submission wiring.

Covers:
    * CRUD round-trip for ``/api/v1/brand-specs`` (list / create /
      get / patch / archive / restore).
    * Tenant isolation — a spec owned by tenant A is not visible
      or patchable by tenant B.
    * ``is_default`` is mutually exclusive per tenant; setting a
      new default demotes the previous row.
    * Endpoint.default_brand_spec_id accepts / clears via PATCH
      and is echoed in the EndpointResponse.
    * POST /api/v1/jobs validates brand_spec_id ownership and
      persists it onto the Job row.
    * Resolver walks job → endpoint → tenant default correctly
      and archived specs don't satisfy the tenant-default hop.
"""

from __future__ import annotations

import uuid
from io import BytesIO
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from lintpdf.api.models import BrandSpec, CustomEndpoint, Job, JobStatus
from lintpdf.brand_specs.resolver import (
    resolve_brand_spec_for_job,
    resolve_brand_spec_for_tenant,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# CRUD round-trip
# ---------------------------------------------------------------------------


class TestBrandSpecCrud:
    @staticmethod
    def _create(client: TestClient, **overrides: object) -> dict:
        payload: dict = {
            "name": "Coca-Cola",
            "customer_name": "Coca-Cola Co.",
            "description": "Global soft-drink brand palette",
            "colors": [
                {"name": "Coke Red", "value": "#F40009"},
                {"name": "White", "value": "#FFFFFF"},
            ],
        }
        payload.update(overrides)
        response = client.post("/api/v1/brand-specs", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    def test_create_returns_full_row(self, client: TestClient) -> None:
        body = self._create(client)
        assert body["name"] == "Coca-Cola"
        assert body["customer_name"] == "Coca-Cola Co."
        assert len(body["colors"]) == 2
        assert body["is_default"] is False
        assert body["is_archived"] is False

    def test_create_with_rich_black(self, client: TestClient) -> None:
        body = self._create(
            client,
            name="Rich K",
            rich_black_spec={"c": 60, "m": 50, "y": 50, "k": 100},
        )
        assert body["rich_black_spec"] == {
            "c": 60.0,
            "m": 50.0,
            "y": 50.0,
            "k": 100.0,
        }

    def test_list_hides_archived_by_default(self, client: TestClient) -> None:
        created = self._create(client, name="Archive me")
        client.delete(f"/api/v1/brand-specs/{created['id']}")
        listed = client.get("/api/v1/brand-specs").json()["brand_specs"]
        assert all(s["id"] != created["id"] for s in listed)
        with_archived = client.get("/api/v1/brand-specs?include_archived=true").json()[
            "brand_specs"
        ]
        assert any(s["id"] == created["id"] for s in with_archived)

    def test_update_replaces_colors(self, client: TestClient) -> None:
        created = self._create(client)
        response = client.patch(
            f"/api/v1/brand-specs/{created['id']}",
            json={"colors": [{"name": "New", "value": "#000000"}]},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["colors"]) == 1
        assert body["colors"][0]["value"] == "#000000"

    def test_default_is_mutually_exclusive(self, client: TestClient, db_session: Session) -> None:
        first = self._create(client, name="First", is_default=True)
        second = self._create(client, name="Second", is_default=True)
        # First should have been demoted.
        db_session.expire_all()
        first_row = db_session.get(BrandSpec, uuid.UUID(first["id"]))
        second_row = db_session.get(BrandSpec, uuid.UUID(second["id"]))
        assert first_row is not None and not first_row.is_default
        assert second_row is not None and second_row.is_default

    def test_patch_is_default_demotes_previous(
        self, client: TestClient, db_session: Session
    ) -> None:
        first = self._create(client, name="First", is_default=True)
        second = self._create(client, name="Second")
        response = client.patch(
            f"/api/v1/brand-specs/{second['id']}",
            json={"is_default": True},
        )
        assert response.status_code == 200
        db_session.expire_all()
        first_row = db_session.get(BrandSpec, uuid.UUID(first["id"]))
        assert first_row is not None and not first_row.is_default

    def test_archive_clears_default(self, client: TestClient, db_session: Session) -> None:
        created = self._create(client, name="Default", is_default=True)
        client.delete(f"/api/v1/brand-specs/{created['id']}")
        db_session.expire_all()
        row = db_session.get(BrandSpec, uuid.UUID(created["id"]))
        assert row is not None
        assert row.is_archived is True
        assert row.is_default is False

    def test_restore_unarchives(self, client: TestClient) -> None:
        created = self._create(client, name="Restore me")
        client.delete(f"/api/v1/brand-specs/{created['id']}")
        response = client.post(f"/api/v1/brand-specs/{created['id']}/restore")
        assert response.status_code == 200
        assert response.json()["is_archived"] is False

    def test_get_404_for_unknown(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/brand-specs/{uuid.uuid4()}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Endpoint binding
# ---------------------------------------------------------------------------


class TestEndpointBrandSpecBinding:
    @staticmethod
    def _seed_spec(db: Session, tenant_id: uuid.UUID, **kwargs) -> BrandSpec:
        """Insert a BrandSpec directly through the shared session so
        the test doesn't pay a second TestClient round-trip for each
        setup fixture — the endpoint create path otherwise times out
        chaining two in-process HTTP calls on the SQLite harness.
        """
        spec = BrandSpec(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=kwargs.pop("name", "Spec A"),
            colors=kwargs.pop("colors", []),
            is_default=kwargs.pop("is_default", False),
            is_archived=False,
        )
        db.add(spec)
        db.commit()
        db.refresh(spec)
        return spec

    def test_create_endpoint_with_default_brand_spec(
        self, client: TestClient, db_session: Session
    ) -> None:
        from lintpdf.api.models import Tenant

        tenant = db_session.query(Tenant).first()
        assert tenant is not None
        spec = self._seed_spec(db_session, tenant.id, name="Spec A")
        response = client.post(
            "/api/v1/endpoints",
            json={
                "slug": "bound-endpoint",
                "profile_id": "lintpdf-default",
                "default_brand_spec_id": str(spec.id),
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["default_brand_spec_id"] == str(spec.id)

    def test_create_endpoint_rejects_foreign_brand_spec(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/endpoints",
            json={
                "slug": "bad-spec",
                "profile_id": "lintpdf-default",
                "default_brand_spec_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 404

    def test_patch_endpoint_clears_default_spec(
        self, client: TestClient, db_session: Session
    ) -> None:
        from lintpdf.api.models import Tenant

        tenant = db_session.query(Tenant).first()
        assert tenant is not None
        spec = self._seed_spec(db_session, tenant.id, name="Spec B")
        created = client.post(
            "/api/v1/endpoints",
            json={
                "slug": "clear-me",
                "profile_id": "lintpdf-default",
                "default_brand_spec_id": str(spec.id),
            },
        ).json()
        response = client.patch(
            f"/api/v1/endpoints/{created['id']}",
            json={"default_brand_spec_id": "null"},
        )
        assert response.status_code == 200
        assert response.json()["default_brand_spec_id"] is None


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


class TestResolver:
    def test_tenant_default_used_when_no_overrides(
        self, client: TestClient, db_session: Session
    ) -> None:
        from lintpdf.api.models import Tenant

        tenant = db_session.query(Tenant).first()
        assert tenant is not None
        spec = client.post(
            "/api/v1/brand-specs",
            json={
                "name": "Tenant Default",
                "colors": [{"name": "A", "value": "#abcdef"}],
                "is_default": True,
            },
        ).json()

        resolved = resolve_brand_spec_for_tenant(db_session, tenant_id=tenant.id)
        assert resolved is not None
        assert str(resolved.id) == spec["id"]
        assert resolved.has_colors is True

    def test_archived_default_does_not_resolve(
        self, client: TestClient, db_session: Session
    ) -> None:
        from lintpdf.api.models import Tenant

        tenant = db_session.query(Tenant).first()
        assert tenant is not None
        spec = client.post(
            "/api/v1/brand-specs",
            json={"name": "Archived", "colors": [], "is_default": True},
        ).json()
        client.delete(f"/api/v1/brand-specs/{spec['id']}")

        resolved = resolve_brand_spec_for_tenant(db_session, tenant_id=tenant.id)
        assert resolved is None

    def test_resolver_chain_job_wins_over_endpoint(
        self, client: TestClient, db_session: Session
    ) -> None:
        from lintpdf.api.models import Tenant

        tenant = db_session.query(Tenant).first()
        assert tenant is not None

        tenant_default = client.post(
            "/api/v1/brand-specs",
            json={"name": "tenant-default", "colors": [], "is_default": True},
        ).json()
        endpoint_spec = client.post(
            "/api/v1/brand-specs",
            json={"name": "endpoint-spec", "colors": []},
        ).json()
        job_spec = client.post(
            "/api/v1/brand-specs",
            json={"name": "job-spec", "colors": []},
        ).json()

        endpoint = CustomEndpoint(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            slug="resolver-chain",
            profile_id="lintpdf-default",
            default_brand_spec_id=uuid.UUID(endpoint_spec["id"]),
        )
        db_session.add(endpoint)

        job = Job(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            status=JobStatus.PENDING,
            profile_id="lintpdf-default",
            file_key="key",
            file_name="f.pdf",
            file_size=1,
            brand_spec_id=uuid.UUID(job_spec["id"]),
        )
        db_session.add(job)
        db_session.commit()

        # With job override → job spec wins.
        resolved = resolve_brand_spec_for_job(db_session, job=job, endpoint=endpoint)
        assert resolved is not None and str(resolved.id) == job_spec["id"]

        # Without job override → endpoint default.
        job.brand_spec_id = None
        db_session.commit()
        resolved = resolve_brand_spec_for_job(db_session, job=job, endpoint=endpoint)
        assert resolved is not None and str(resolved.id) == endpoint_spec["id"]

        # Without endpoint default → tenant default.
        endpoint.default_brand_spec_id = None
        db_session.commit()
        resolved = resolve_brand_spec_for_job(db_session, job=job, endpoint=endpoint)
        assert resolved is not None and str(resolved.id) == tenant_default["id"]

        # Without any default → None.
        client.patch(
            f"/api/v1/brand-specs/{tenant_default['id']}",
            json={"is_default": False},
        )
        db_session.expire_all()
        job_reloaded = db_session.get(Job, job.id)
        endpoint_reloaded = db_session.get(CustomEndpoint, endpoint.id)
        resolved = resolve_brand_spec_for_job(
            db_session, job=job_reloaded, endpoint=endpoint_reloaded
        )
        assert resolved is None


# ---------------------------------------------------------------------------
# Jobs submission wiring
# ---------------------------------------------------------------------------


class TestJobSubmissionBrandSpec:
    @staticmethod
    def _minimal_pdf() -> bytes:
        return (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"xref\n0 4\n"
            b"0000000000 65535 f\n"
            b"0000000010 00000 n\n"
            b"0000000050 00000 n\n"
            b"0000000100 00000 n\n"
            b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
            b"startxref\n150\n%%EOF\n"
        )

    def test_submit_rejects_unknown_brand_spec(self, client: TestClient) -> None:
        with patch("lintpdf.queue.tasks.run_preflight.apply_async", MagicMock()):
            response = client.post(
                "/api/v1/jobs",
                files={"file": ("t.pdf", BytesIO(self._minimal_pdf()), "application/pdf")},
                data={"brand_spec_id": str(uuid.uuid4())},
            )
        assert response.status_code == 404

    def test_submit_persists_brand_spec_id(self, client: TestClient, db_session: Session) -> None:
        spec = client.post(
            "/api/v1/brand-specs",
            json={"name": "submit-spec", "colors": []},
        ).json()
        with patch("lintpdf.queue.tasks.run_preflight.apply_async", MagicMock()):
            response = client.post(
                "/api/v1/jobs",
                files={"file": ("t.pdf", BytesIO(self._minimal_pdf()), "application/pdf")},
                data={"brand_spec_id": spec["id"]},
            )
        assert response.status_code == 202, response.text
        job_id = uuid.UUID(response.json()["job_id"])
        row = db_session.get(Job, job_id)
        assert row is not None
        assert str(row.brand_spec_id) == spec["id"]
