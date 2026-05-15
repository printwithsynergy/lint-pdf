"""Tests for tile warming, annotation comments, and markup PDF export.

Covers the features shipped in the finish-the-viewer + warming plans:

* ``warm_viewer_tiles`` Celery task (happy path + Redis semaphore +
  idempotent locks).
* ``GET /api/v1/viewer/jobs/{id}/tile-warming`` (auth) and the
  ``/public/{token}/...`` mirror.
* ``viewer_annotations`` / ``viewer_annotation_comments`` CRUD —
  dashboard author attribution via ``X-Visitor-Email`` header.
* ``generate_markup_pdf`` report renderer (end-to-end smoke).

Test storage is InMemoryStorage (wired by the conftest) and a SQLite
in-memory DB, so these tests don't depend on R2 / Postgres / Celery /
Redis beyond the mocks set up below.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from lintpdf.api.models import (
    Job,
    JobStatus,
    PreflightSource,
    ViewerAnnotationComment,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

from tests.api.conftest import PLACEHOLDER_TENANT_ID

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seed_complete_job(db: Session, page_count: int = 3) -> Job:
    """Seed a COMPLETE job ready for warming / annotation tests."""
    job = Job(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        status=JobStatus.COMPLETE,
        profile_id="lintpdf-default",
        file_key="seed/key.pdf",
        file_name="seed.pdf",
        file_size=1024,
        page_count=page_count,
        created_at=datetime.now(timezone.utc),
        preflight_source=PreflightSource.ENGINE,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class FakeRedis:
    """Minimal in-memory Redis shim covering the commands our task uses.

    We only need: ``set(key, val, nx, ex)``, ``get``, ``delete``,
    ``hset``, ``hget``, ``hgetall``, ``expire``, ``incr``, ``decr``.
    Everything else raises to surface test-level mistakes early.
    """

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}
        self._hashes: dict[str, dict[str, str]] = {}

    # String ops ----------------------------------------------------
    def set(self, key: str, value: Any, *, nx: bool = False, ex: int | None = None) -> bool:
        _ = ex
        if nx and key in self._values:
            return False
        self._values[key] = value
        return True

    def get(self, key: str) -> Any:
        return self._values.get(key)

    def delete(self, key: str) -> int:
        existed = key in self._values or key in self._hashes
        self._values.pop(key, None)
        self._hashes.pop(key, None)
        return 1 if existed else 0

    def setex(self, key: str, ttl: int, value: Any) -> bool:
        _ = ttl
        self._values[key] = value
        return True

    def incr(self, key: str) -> int:
        current = int(self._values.get(key, 0))
        current += 1
        self._values[key] = current
        return current

    def decr(self, key: str) -> int:
        current = int(self._values.get(key, 0))
        current -= 1
        self._values[key] = current
        return current

    def expire(self, key: str, ttl: int) -> bool:
        _ = (key, ttl)
        return True

    # Hash ops ------------------------------------------------------
    def hset(self, key: str, *, mapping: dict[str, str] | None = None, **kwargs: Any) -> int:
        payload = dict(mapping or {})
        payload.update(kwargs)
        self._hashes.setdefault(key, {}).update(payload)
        return len(payload)

    def hget(self, key: str, field: str) -> Any:
        return self._hashes.get(key, {}).get(field)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))


# ---------------------------------------------------------------------------
# warm_viewer_tiles task
# ---------------------------------------------------------------------------


class TestWarmViewerTiles:
    """The background tile-warming Celery task."""

    def _patch(self, monkeypatch, db: Session, redis: FakeRedis) -> None:
        """Wire the task's injected globals to the test fixtures.

        ``warm_viewer_tiles`` does deferred imports for every dep, so
        we patch at the source modules (what the ``from ... import``
        inside the task resolves to).
        """
        import lintpdf.api.database as database
        import lintpdf.api.middleware as mw
        import lintpdf.rendering as rendering
        from lintpdf.queue import tasks as qtasks

        monkeypatch.setattr(database, "get_db_session", lambda: db)
        monkeypatch.setattr(mw, "get_redis_client", lambda: redis)

        # Stub the PDF downloader so the task doesn't touch real storage.
        monkeypatch.setattr(
            qtasks,
            "_download_pdf_with_fallback",
            lambda *_a, **_kw: b"%PDF-1.4\n%fake",
        )

        # Stub the renderer — the task just wants bytes; we don't
        # exercise Ghostscript here.
        monkeypatch.setattr(
            rendering,
            "render_page_to_image",
            lambda *_a, **_kw: b"\x89PNG\r\n\x1a\nfake",
        )

        # Skip spot-channel warming in the happy-path tests; a separate
        # test exercises that branch explicitly.
        monkeypatch.setenv("LINTPDF_TILE_WARMING_INCLUDE_SEPARATIONS", "false")

        # Force synchronous apply_async so the "deferred" branch we
        # test below doesn't leave a real Celery message behind.
        monkeypatch.setattr(qtasks.warm_viewer_tiles, "apply_async", MagicMock(), raising=False)

    def test_happy_path_publishes_complete(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        redis = FakeRedis()
        self._patch(monkeypatch, db_session, redis)
        job = _seed_complete_job(db_session, page_count=4)

        from lintpdf.queue.tasks import _tile_warm_status_key, warm_viewer_tiles

        result = warm_viewer_tiles(str(job.id))

        assert result["status"] == "complete"
        assert result["rendered"] == 4
        assert result["total"] == 4

        # Status hash reflects completion.
        status = redis.hgetall(_tile_warm_status_key(str(job.id)))
        assert status["status"] == "complete"
        assert status["rendered"] == "4"
        assert status["total"] == "4"
        assert "completed_at" in status

    def test_no_redis_returns_skip(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import lintpdf.api.middleware as mw

        monkeypatch.setattr(mw, "get_redis_client", lambda: None)

        from lintpdf.queue.tasks import warm_viewer_tiles

        result = warm_viewer_tiles("nonexistent-id")
        assert result == {"status": "no_redis", "job_id": "nonexistent-id"}

    def test_lock_prevents_double_warming(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        redis = FakeRedis()
        self._patch(monkeypatch, db_session, redis)
        job = _seed_complete_job(db_session)

        from lintpdf.queue.tasks import _tile_warm_lock_key, warm_viewer_tiles

        # Pre-populate the lock key: a second run should bail out.
        redis.set(_tile_warm_lock_key(str(job.id)), "already", nx=False, ex=600)

        result = warm_viewer_tiles(str(job.id))
        assert result == {"status": "locked", "job_id": str(job.id)}

    def test_not_complete_job_is_skipped(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        redis = FakeRedis()
        self._patch(monkeypatch, db_session, redis)

        job = Job(
            id=uuid.uuid4(),
            tenant_id=PLACEHOLDER_TENANT_ID,
            status=JobStatus.PROCESSING,
            profile_id="lintpdf-default",
            file_key="x.pdf",
            file_name="x.pdf",
            file_size=1,
            page_count=1,
            created_at=datetime.now(timezone.utc),
            preflight_source=PreflightSource.ENGINE,
        )
        db_session.add(job)
        db_session.commit()

        from lintpdf.queue.tasks import warm_viewer_tiles

        result = warm_viewer_tiles(str(job.id))
        assert result["status"] == "not_complete"

    def test_tenant_semaphore_defers_when_over_cap(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        redis = FakeRedis()
        self._patch(monkeypatch, db_session, redis)
        monkeypatch.setenv("LINTPDF_TILE_WARMING_PER_TENANT_MAX", "1")
        job = _seed_complete_job(db_session)

        from lintpdf.queue.tasks import (
            _tile_warm_tenant_semaphore_key,
            warm_viewer_tiles,
        )

        # Pretend another worker is already holding the only slot.
        redis.set(
            _tile_warm_tenant_semaphore_key(str(PLACEHOLDER_TENANT_ID)),
            1,
            nx=False,
            ex=900,
        )

        result = warm_viewer_tiles(str(job.id))
        assert result["status"] == "deferred"
        assert result["cap"] == 1


# ---------------------------------------------------------------------------
# /tile-warming endpoint
# ---------------------------------------------------------------------------


class TestTileWarmingEndpoint:
    """``GET /api/v1/viewer/jobs/{id}/tile-warming`` returns Redis state."""

    def test_returns_disabled_when_redis_absent(
        self,
        client: TestClient,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import lintpdf.api.middleware as mw

        monkeypatch.setattr(mw, "get_redis_client", lambda: None)
        job = _seed_complete_job(db_session, page_count=5)

        resp = client.get(f"/api/v1/viewer/jobs/{job.id}/tile-warming")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "disabled"
        assert body["total"] == 5
        assert body["rendered"] == 0

    def test_returns_in_progress_from_redis(
        self,
        client: TestClient,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        redis = FakeRedis()
        import lintpdf.api.middleware as mw

        monkeypatch.setattr(mw, "get_redis_client", lambda: redis)

        job = _seed_complete_job(db_session, page_count=10)

        from lintpdf.queue.tasks import _tile_warm_status_key

        redis.hset(
            _tile_warm_status_key(str(job.id)),
            mapping={
                "status": "in_progress",
                "rendered": "3",
                "total": "10",
                "dpi": "150",
                "started_at": "2026-04-14T10:00:00Z",
                "updated_at": "2026-04-14T10:00:05Z",
            },
        )

        resp = client.get(f"/api/v1/viewer/jobs/{job.id}/tile-warming")
        body = resp.json()
        assert body["status"] == "in_progress"
        assert body["rendered"] == 3
        assert body["total"] == 10
        assert body["percent"] == 30

    def test_returns_404_for_unknown_job(self, client: TestClient) -> None:
        resp = client.get(f"/api/v1/viewer/jobs/{uuid.uuid4()}/tile-warming")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Annotation + comment CRUD
# ---------------------------------------------------------------------------


class TestAnnotationsAndComments:
    """Authenticated CRUD surface for viewer annotations + threaded comments."""

    def _create_note(self, client: TestClient, job_id: str) -> dict:
        resp = client.post(
            f"/api/v1/viewer/jobs/{job_id}/annotations",
            json={
                "page_num": 1,
                "kind": "note",
                "geometry": {"x": 100.0, "y": 200.0},
                "color": "#ff0000",
                "text": "Check this",
            },
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    def test_create_annotation_prefers_visitor_email_header(
        self, client: TestClient, db_session: Session
    ) -> None:
        job = _seed_complete_job(db_session)

        resp = client.post(
            f"/api/v1/viewer/jobs/{job.id}/annotations",
            json={
                "page_num": 1,
                "kind": "rect",
                "geometry": {"x0": 10, "y0": 10, "x1": 100, "y1": 100},
            },
            headers={"X-Visitor-Email": "alice@example.com"},
        )
        assert resp.status_code == 201
        assert resp.json()["author_email"] == "alice@example.com"

    def test_comment_create_fans_out_to_prior_commenters(
        self,
        client: TestClient,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        job = _seed_complete_job(db_session)
        note = self._create_note(client, str(job.id))

        # Seed a prior comment from a second user so fan-out has a target.
        prior = ViewerAnnotationComment(
            id=uuid.uuid4(),
            annotation_id=uuid.UUID(note["id"]),
            tenant_id=PLACEHOLDER_TENANT_ID,
            share_token=None,
            author_email="alice@example.com",
            body="First",
        )
        db_session.add(prior)
        db_session.commit()

        sent: list[dict[str, str]] = []

        # Phase 5 W2: route handler now accepts an EmailService via
        # FastAPI dependency injection. Override get_email_service with
        # a spy that captures every send_annotation_comment call.
        from lintpdf.services.email import EmailResult, get_email_service

        class _SpyEmailService:
            def send_annotation_comment(self, **kwargs: Any) -> EmailResult:
                sent.append(kwargs)
                return EmailResult(success=True, email_id="mock-id")

            # The Protocol declares 4 methods; tests only exercise this one.
            def send_overage_started(self, **_: Any) -> EmailResult:
                return EmailResult(success=True, email_id="mock-id")

            def send_rate_limit_warning(self, **_: Any) -> EmailResult:
                return EmailResult(success=True, email_id="mock-id")

            def send_report(self, **_: Any) -> EmailResult:
                return EmailResult(success=True, email_id="mock-id")

        client.app.dependency_overrides[get_email_service] = lambda: _SpyEmailService()
        # Restore on test exit so other tests aren't affected.
        monkeypatch.setattr(
            client.app,
            "dependency_overrides",
            client.app.dependency_overrides,
        )

        resp = client.post(
            f"/api/v1/viewer/jobs/{job.id}/annotations/{note['id']}/comments",
            json={"body": "Second reply"},
            headers={"X-Visitor-Email": "bob@example.com"},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["author_email"] == "bob@example.com"

        # Alice (prior commenter) gets notified; Bob (sender) does not.
        recipients = {call["to"] for call in sent}
        assert "alice@example.com" in recipients
        assert "bob@example.com" not in recipients

    def test_list_comments_orders_by_created_at(
        self, client: TestClient, db_session: Session
    ) -> None:
        job = _seed_complete_job(db_session)
        note = self._create_note(client, str(job.id))

        for body in ["one", "two", "three"]:
            resp = client.post(
                f"/api/v1/viewer/jobs/{job.id}/annotations/{note['id']}/comments",
                json={"body": body},
                headers={"X-Visitor-Email": "author@example.com"},
            )
            assert resp.status_code == 201

        resp = client.get(f"/api/v1/viewer/jobs/{job.id}/annotations/{note['id']}/comments")
        assert resp.status_code == 200
        rows = resp.json()
        assert [r["body"] for r in rows] == ["one", "two", "three"]


# ---------------------------------------------------------------------------
# Markup PDF renderer
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Rendering moved to lens-server")
class TestMarkupPdfRenderer:
    """``generate_markup_pdf`` stamps reviewer markup + appendix onto a PDF."""

    @staticmethod
    def _tiny_pdf() -> bytes:
        """Render a 2-page minimal PDF via pikepdf for the renderer to stamp."""
        import pikepdf

        pdf = pikepdf.new()
        for _ in range(2):
            pdf.add_blank_page(page_size=(612, 792))
        buf: bytes = b""
        import io

        out = io.BytesIO()
        pdf.save(out)
        buf = out.getvalue()
        pdf.close()
        return buf

    def test_generate_markup_pdf_stamps_all_primitives(self) -> None:
        """All five annotation kinds + appendix page render without error."""
        from lintpdf.reports.markup_pdf_report import generate_markup_pdf

        pdf_bytes = self._tiny_pdf()
        note_id = str(uuid.uuid4())
        annotations = [
            {
                "id": str(uuid.uuid4()),
                "page_num": 1,
                "kind": "rect",
                "geometry": {"x0": 50, "y0": 50, "x1": 200, "y1": 150},
                "color": "#ff0000",
                "text": None,
                "author_email": "alice@example.com",
                "created_at": "2026-04-14T10:00:00Z",
            },
            {
                "id": str(uuid.uuid4()),
                "page_num": 1,
                "kind": "circle",
                "geometry": {"cx": 300, "cy": 300, "rx": 40, "ry": 30},
                "color": "#0000ff",
                "text": None,
                "author_email": "alice@example.com",
                "created_at": "2026-04-14T10:01:00Z",
            },
            {
                "id": str(uuid.uuid4()),
                "page_num": 2,
                "kind": "arrow",
                "geometry": {"x0": 100, "y0": 100, "x1": 400, "y1": 400},
                "color": "#00ff00",
                "text": None,
                "author_email": "alice@example.com",
                "created_at": "2026-04-14T10:02:00Z",
            },
            {
                "id": str(uuid.uuid4()),
                "page_num": 2,
                "kind": "freehand",
                "geometry": {
                    "points": [{"x": 50, "y": 50}, {"x": 75, "y": 100}, {"x": 120, "y": 80}],
                },
                "color": "#ff00ff",
                "text": None,
                "author_email": "alice@example.com",
                "created_at": "2026-04-14T10:03:00Z",
            },
            {
                "id": note_id,
                "page_num": 1,
                "kind": "note",
                "geometry": {"x": 250, "y": 500},
                "color": "#f59e0b",
                "text": "Review this headline",
                "author_email": "alice@example.com",
                "created_at": "2026-04-14T10:04:00Z",
            },
        ]
        comments = {
            note_id: [
                {
                    "author_email": "bob@example.com",
                    "body": "Agreed — needs a rewrite.",
                    "created_at": "2026-04-14T10:05:00Z",
                },
            ]
        }

        result = generate_markup_pdf(
            pdf_bytes,
            annotations,
            comments,
            branding_name="Test Brand",
        )

        assert result.startswith(b"%PDF")
        # Result is original 2 pages + at least one appendix page.
        import pikepdf

        with pikepdf.open(__import__("io").BytesIO(result)) as check:
            assert len(check.pages) >= 3
