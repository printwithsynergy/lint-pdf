"""Tests for the new webhook events + WebhookDelivery audit table.

Covers the happy paths for the `emit_event` → `WebhookDelivery` →
replay flow, and the state-builder helper used by ``job.state_changed``.

The celery `dispatch_webhook.delay` call is mocked globally by
``_mock_celery_delay`` in conftest.py, so the assertions here focus on:

* A ``WebhookDelivery`` row is persisted per subscribed endpoint.
* The payload stored on the row matches what the delivery would have signed.
* The replay endpoint creates a NEW row (not a mutate-in-place).
* Non-subscribed endpoints are skipped.
* Unknown `include` parameter on delivery listings 422s correctly.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from lintpdf.api.models import (
    Job,
    JobStatus,
    ViewerAnnotation,
    WebhookDelivery,
    WebhookEndpoint,
)
from tests.api.conftest import PLACEHOLDER_TENANT_ID

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


def _seed_webhook(db: Session, *, events: list[str] | None = None) -> WebhookEndpoint:
    ep = WebhookEndpoint(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        url="https://example.test/hook",
        secret="sekrit" * 4,
        events=events if events is not None else [],
        is_active=True,
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return ep


def _seed_complete_job(db: Session) -> Job:
    job = Job(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        profile_id="lintpdf-default",
        file_name="sample.pdf",
        file_size=1234,
        file_key=f"tenants/{PLACEHOLDER_TENANT_ID}/jobs/dummy.pdf",
        status=JobStatus.COMPLETE,
        result_json={
            "summary": {
                "total_findings": 0,
                "error_count": 0,
                "warning_count": 0,
                "advisory_count": 0,
                "passed": True,
                "page_count": 1,
                "file_size_bytes": 1234,
            },
            "metadata": {},
            "findings": [],
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class TestEmitEventPersistsDelivery:
    def test_one_row_per_subscribed_endpoint(self, client: TestClient, db_session: Session) -> None:
        ep1 = _seed_webhook(db_session)
        ep2 = _seed_webhook(db_session, events=["job.completed"])  # only subscribes to one
        _seed_webhook(db_session, events=["approval.chain.started"])  # should skip

        from lintpdf.webhooks.events import emit_event

        emit_event(db_session, PLACEHOLDER_TENANT_ID, "job.completed", {"hi": 1})
        db_session.commit()

        rows = (
            db_session.query(WebhookDelivery)
            .filter(WebhookDelivery.tenant_id == PLACEHOLDER_TENANT_ID)
            .all()
        )
        assert len(rows) == 2  # ep1 (all events) + ep2 (explicit subscription)
        assert {r.webhook_id for r in rows} == {ep1.id, ep2.id}
        for r in rows:
            assert r.event == "job.completed"
            assert r.payload == {"hi": 1}
            assert r.success is False  # not yet delivered
            assert r.attempt_count == 0

    def test_no_subscribers_persists_nothing(self, client: TestClient, db_session: Session) -> None:
        from lintpdf.webhooks.events import emit_event

        emit_event(db_session, PLACEHOLDER_TENANT_ID, "verdict.changed", {"x": 1})
        db_session.commit()

        rows = db_session.query(WebhookDelivery).all()
        assert rows == []


class TestJobStateChangedEvent:
    def test_payload_matches_state_endpoint_shape(
        self, client: TestClient, db_session: Session
    ) -> None:
        ep = _seed_webhook(db_session)
        job = _seed_complete_job(db_session)
        db_session.add(
            ViewerAnnotation(
                id=uuid.uuid4(),
                job_id=job.id,
                tenant_id=job.tenant_id,
                share_token=None,
                page_num=2,
                kind="note",
                geometry_json={"x": 0, "y": 0},
                color="#ff0000",
                text=None,
                author_email="r@example.com",
            )
        )
        db_session.commit()

        from lintpdf.webhooks.events import fire_job_state_changed

        fire_job_state_changed(db_session, job, job.tenant_id, reason="unit-test")
        db_session.commit()

        rows = db_session.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == ep.id).all()
        assert len(rows) == 1
        payload = rows[0].payload
        assert payload["reason"] == "unit-test"
        assert payload["job"]["job_id"] == str(job.id)
        assert payload["annotations"]["total"] == 1
        assert payload["annotations"]["by_page"] == {"2": 1}
        assert payload["verdict"]["auto_passed"] is True
        assert payload["approval_chain"] is None


class TestReplayDelivery:
    def test_replay_creates_new_row_with_same_payload(
        self, client: TestClient, db_session: Session
    ) -> None:
        ep = _seed_webhook(db_session)
        from lintpdf.webhooks.events import emit_event

        emit_event(db_session, PLACEHOLDER_TENANT_ID, "verdict.changed", {"k": "v"})
        db_session.commit()
        original = (
            db_session.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == ep.id).first()
        )
        assert original is not None

        resp = client.post(f"/api/v1/webhooks/deliveries/{original.id}/replay")
        assert resp.status_code == 201, resp.text
        new = resp.json()
        assert new["id"] != str(original.id)
        assert new["event"] == original.event
        assert new["payload"] == original.payload

        all_rows = (
            db_session.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == ep.id).all()
        )
        assert len(all_rows) == 2  # audit log grew, original preserved

    def test_replay_404_on_unknown_id(self, client: TestClient) -> None:
        resp = client.post(f"/api/v1/webhooks/deliveries/{uuid.uuid4()}/replay")
        assert resp.status_code == 404

    def test_replay_409_on_inactive_endpoint(self, client: TestClient, db_session: Session) -> None:
        ep = _seed_webhook(db_session)
        from lintpdf.webhooks.events import emit_event

        emit_event(db_session, PLACEHOLDER_TENANT_ID, "verdict.changed", {"k": 1})
        db_session.commit()
        delivery = (
            db_session.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == ep.id).first()
        )
        assert delivery is not None

        ep.is_active = False
        db_session.commit()

        resp = client.post(f"/api/v1/webhooks/deliveries/{delivery.id}/replay")
        assert resp.status_code == 409


class TestListDeliveries:
    def test_filters_by_webhook_and_event(self, client: TestClient, db_session: Session) -> None:
        ep_a = _seed_webhook(db_session)
        _seed_webhook(db_session)
        from lintpdf.webhooks.events import emit_event

        # 3 events for ep_a, 1 for ep_b
        emit_event(db_session, PLACEHOLDER_TENANT_ID, "verdict.changed", {"n": 1})
        emit_event(db_session, PLACEHOLDER_TENANT_ID, "annotation.created", {"n": 2})
        emit_event(db_session, PLACEHOLDER_TENANT_ID, "verdict.changed", {"n": 3})
        db_session.commit()

        # Plain list returns every delivery (6: 3 events × 2 subscribers)
        resp = client.get("/api/v1/webhooks/deliveries")
        assert resp.status_code == 200
        assert resp.json()["total"] == 6

        # Filter by webhook_id
        resp = client.get("/api/v1/webhooks/deliveries", params={"webhook_id": str(ep_a.id)})
        assert resp.status_code == 200
        assert resp.json()["total"] == 3

        # Filter by event
        resp = client.get("/api/v1/webhooks/deliveries", params={"event": "verdict.changed"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 4

    def test_invalid_webhook_id_uuid_422s(self, client: TestClient) -> None:
        resp = client.get("/api/v1/webhooks/deliveries", params={"webhook_id": "not-a-uuid"})
        assert resp.status_code == 422


class TestKnownEventsCatalog:
    def test_every_fire_helper_uses_a_known_event(self) -> None:
        """Guard against a typo silently firing an unlisted event name."""
        import inspect

        from lintpdf.webhooks import events as evt_mod

        # Just introspect the module docstring -- not a behavioural test,
        # but catches name drift quickly if someone adds a helper with a
        # typoed string literal.
        src = inspect.getsource(evt_mod)
        for ev in (
            "job.state_changed",
            "annotation.created",
            "annotation.deleted",
            "comment.created",
            "verdict.changed",
            "report.minted",
            "report.expired",
            "share_link.visited",
            "billing.file_quota.low",
            "billing.file_quota.exhausted",
            "billing.ai_credits.low",
            "billing.ai_credits.exhausted",
            "tenant.plan.changed",
        ):
            assert ev in src, f"Helper body should reference {ev!r} literal"
            assert ev in evt_mod.KNOWN_EVENTS, f"{ev} missing from KNOWN_EVENTS tuple"


class TestPerEndpointRetryConfig:
    def test_create_persists_and_echoes_new_fields(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://hooks.example.test/retry",
                "events": ["job.state_changed"],
                "max_retries": 5,
                "retry_base_delay_seconds": 2,
                "retry_max_delay_seconds": 30,
                "delivery_retention_days": 7,
                "retention_overrides": {"billing.*": 365},
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["max_retries"] == 5
        assert body["retry_base_delay_seconds"] == 2
        assert body["retry_max_delay_seconds"] == 30
        assert body["delivery_retention_days"] == 7
        assert body["retention_overrides"] == {"billing.*": 365}

    def test_patch_updates_retry_fields(self, client: TestClient, db_session: Session) -> None:
        ep = _seed_webhook(db_session)
        resp = client.patch(
            f"/api/v1/webhooks/{ep.id}",
            json={"max_retries": 1, "retry_base_delay_seconds": 10},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["max_retries"] == 1
        assert body["retry_base_delay_seconds"] == 10

    def test_max_retries_above_ceiling_422s(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://hooks.example.test/too-many",
                "events": [],
                "max_retries": 99,  # ceiling is 10
            },
        )
        assert resp.status_code == 422


class TestRetentionSweep:
    def test_default_retention_deletes_old_rows(
        self, client: TestClient, db_session: Session
    ) -> None:
        import datetime as _dt

        ep = _seed_webhook(db_session)
        ep.delivery_retention_days = 7
        db_session.commit()

        # One old row (outside window), one fresh (inside).
        old = WebhookDelivery(
            id=uuid.uuid4(),
            webhook_id=ep.id,
            tenant_id=ep.tenant_id,
            event="verdict.changed",
            payload={"x": 1},
            url=ep.url,
            attempt_count=1,
            final_status_code=200,
            success=True,
        )
        fresh = WebhookDelivery(
            id=uuid.uuid4(),
            webhook_id=ep.id,
            tenant_id=ep.tenant_id,
            event="verdict.changed",
            payload={"x": 2},
            url=ep.url,
            attempt_count=1,
            final_status_code=200,
            success=True,
        )
        db_session.add_all([old, fresh])
        db_session.commit()
        # Capture IDs up front — after the sweep expires the session we
        # can't compare via instance attribute.
        fresh_id = fresh.id
        old_id = old.id
        # Backdate the `old` row manually (server_default ignored on update).
        db_session.query(WebhookDelivery).filter(WebhookDelivery.id == old_id).update(
            {
                WebhookDelivery.created_at: _dt.datetime.now(_dt.timezone.utc)
                - _dt.timedelta(days=30)
            }
        )
        db_session.commit()

        # Run the sweep through an in-process session override so we
        # don't need a live Celery worker.
        # Patch the source module that sweep_webhook_deliveries imports
        # from so the task sees our in-memory test session.
        from lintpdf.api import database as _dbmod
        from lintpdf.queue import tasks as qt

        original_get = _dbmod.get_db_session
        _dbmod.get_db_session = lambda: db_session  # type: ignore[assignment]
        try:
            result = qt.sweep_webhook_deliveries()
        finally:
            _dbmod.get_db_session = original_get  # type: ignore[assignment]

        assert result["deleted"] == 1
        remaining_ids = [r.id for r in db_session.query(WebhookDelivery).all()]
        assert remaining_ids == [fresh_id]

    def test_per_event_override_keeps_matching_rows(
        self, client: TestClient, db_session: Session
    ) -> None:
        import datetime as _dt

        ep = _seed_webhook(db_session)
        ep.delivery_retention_days = 7
        ep.retention_overrides = {"billing.*": 365}
        db_session.commit()

        now = _dt.datetime.now(_dt.timezone.utc)
        old_billing = WebhookDelivery(
            id=uuid.uuid4(),
            webhook_id=ep.id,
            tenant_id=ep.tenant_id,
            event="billing.file_quota.low",
            payload={},
            url=ep.url,
            attempt_count=1,
            final_status_code=200,
            success=True,
        )
        old_annotation = WebhookDelivery(
            id=uuid.uuid4(),
            webhook_id=ep.id,
            tenant_id=ep.tenant_id,
            event="annotation.created",
            payload={},
            url=ep.url,
            attempt_count=1,
            final_status_code=200,
            success=True,
        )
        db_session.add_all([old_billing, old_annotation])
        db_session.commit()
        # Both backdated 30 days. Billing override = 365d (keeps),
        # annotation falls under default 7d (deletes).
        for row_id in (old_billing.id, old_annotation.id):
            db_session.query(WebhookDelivery).filter(WebhookDelivery.id == row_id).update(
                {WebhookDelivery.created_at: now - _dt.timedelta(days=30)}
            )
        db_session.commit()

        # Patch the source module that sweep_webhook_deliveries imports
        # from so the task sees our in-memory test session.
        from lintpdf.api import database as _dbmod
        from lintpdf.queue import tasks as qt

        original_get = _dbmod.get_db_session
        _dbmod.get_db_session = lambda: db_session  # type: ignore[assignment]
        try:
            result = qt.sweep_webhook_deliveries()
        finally:
            _dbmod.get_db_session = original_get  # type: ignore[assignment]

        assert result["deleted"] == 1
        remaining = db_session.query(WebhookDelivery).all()
        assert [r.event for r in remaining] == ["billing.file_quota.low"]


class TestTestPingAudit:
    def test_test_ping_writes_delivery_row_and_signs(
        self, client: TestClient, db_session: Session
    ) -> None:
        import httpx

        ep = _seed_webhook(db_session)

        # Patch httpx.post to capture the signed headers + return 200.
        captured: dict = {}

        class _Response:
            status_code = 200
            text = "ok"

            def raise_for_status(self) -> None:
                return None

        def fake_post(url: str, **kwargs):  # type: ignore[no-untyped-def]
            captured["url"] = url
            captured["headers"] = kwargs.get("headers") or {}
            captured["content"] = kwargs.get("content") or b""
            return _Response()

        original_post = httpx.post
        httpx.post = fake_post  # type: ignore[assignment]
        try:
            resp = client.post(f"/api/v1/webhooks/{ep.id}/test")
        finally:
            httpx.post = original_post  # type: ignore[assignment]

        assert resp.status_code == 200, resp.text
        # Signature header present
        headers = captured["headers"]
        assert headers.get("X-LintPDF-Event") == "test.ping"
        sig = headers.get("X-LintPDF-Signature", "")
        assert sig.startswith("sha256="), sig

        # A WebhookDelivery row was persisted
        rows = db_session.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == ep.id).all()
        assert len(rows) == 1
        assert rows[0].event == "test.ping"
        assert rows[0].success is True
        assert rows[0].final_status_code == 200
        assert rows[0].attempt_count == 1


@pytest.fixture(autouse=True)
def _seed_tenant_api_keys_tables_exist(db_session: Session) -> None:
    # No-op: just ensures the schema includes webhook_deliveries (the
    # migration adds it, and tests spin up the schema via Base.metadata
    # so we don't have to run alembic here).
    return None
