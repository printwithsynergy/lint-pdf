"""Tests for the scalability-sprint additions.

Covers:

* Burst rate limiter (``check_burst_rate_limit``)
* ``/ready`` readiness probe
* Request-ID middleware
* Upload-size pre-check (streaming abort)
* Webhook dead-letter flag on retry exhaustion
* Redis-backed branding cache
* Celery ``result_expires`` config
* ``get_settings()`` singleton behaviour
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from lintpdf.api import cache, middleware
from lintpdf.api.config import Settings, get_settings
from lintpdf.api.upload_security import validate_upload
from lintpdf.queue.app import celery_app

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Burst rate limiter
# ---------------------------------------------------------------------------


class _FakeRedis:
    """In-memory stand-in just sufficient for the middleware under test."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    def eval(self, _script: str, _numkeys: int, key: str, _ttl: int) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def delete(self, *keys: str) -> None:
        for k in keys:
            self.store.pop(k, None)

    def get(self, key: str) -> int | None:
        return self.store.get(key)

    def setex(self, key: str, _ttl: int, value: object) -> None:
        self.store[key] = value  # type: ignore[assignment]

    def ping(self) -> bool:
        return True


class _Tenant:
    def __init__(self, tid: str = "11111111-1111-1111-1111-111111111111") -> None:
        self.id = tid


class TestBurstRateLimit:
    @staticmethod
    def test_returns_none_when_redis_unconfigured(monkeypatch) -> None:
        monkeypatch.setattr(middleware, "_redis_state", {"client": None})
        assert middleware.check_burst_rate_limit(_Tenant()) is None

    @staticmethod
    def test_allows_under_limit(monkeypatch) -> None:
        monkeypatch.setattr(middleware, "_redis_state", {"client": _FakeRedis()})
        result = middleware.check_burst_rate_limit(_Tenant(), limit_per_minute=10)
        assert result is not None
        assert result.used == 1
        assert result.remaining == 9

    @staticmethod
    def test_blocks_when_exceeded(monkeypatch) -> None:
        monkeypatch.setattr(middleware, "_redis_state", {"client": _FakeRedis()})
        # Burn through the budget
        for _ in range(3):
            middleware.check_burst_rate_limit(_Tenant(), limit_per_minute=3)
        with pytest.raises(HTTPException) as exc:
            middleware.check_burst_rate_limit(_Tenant(), limit_per_minute=3)
        assert exc.value.status_code == 429
        assert exc.value.detail["code"] == "burst_rate_limit"  # type: ignore[index]

    @staticmethod
    def test_disabled_when_limit_zero(monkeypatch) -> None:
        monkeypatch.setattr(middleware, "_redis_state", {"client": _FakeRedis()})
        assert middleware.check_burst_rate_limit(_Tenant(), limit_per_minute=0) is None


# ---------------------------------------------------------------------------
# /ready endpoint
# ---------------------------------------------------------------------------


class TestReadyEndpoint:
    @staticmethod
    def test_ready_ok_when_deps_available(client: TestClient) -> None:
        mock_engine = MagicMock()
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        with (
            patch("lintpdf.api.database.get_engine", return_value=mock_engine),
            patch("lintpdf.api.middleware.get_redis_client", return_value=mock_redis),
        ):
            resp = client.get("/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["database"] == "connected"
        assert body["redis"] == "connected"

    @staticmethod
    def test_ready_503_when_database_errors(client: TestClient) -> None:
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("boom")
        with patch("lintpdf.api.database.get_engine", return_value=mock_engine):
            resp = client.get("/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "unavailable"


# ---------------------------------------------------------------------------
# Request-ID middleware
# ---------------------------------------------------------------------------


class TestRequestIdMiddleware:
    @staticmethod
    def test_generates_id_when_missing(client: TestClient) -> None:
        resp = client.get("/health")
        assert "x-request-id" in {k.lower() for k in resp.headers}
        assert len(resp.headers["x-request-id"]) >= 16

    @staticmethod
    def test_propagates_inbound_id(client: TestClient) -> None:
        supplied = "req-abc123"
        resp = client.get("/health", headers={"X-Request-ID": supplied})
        assert resp.headers["x-request-id"] == supplied


# ---------------------------------------------------------------------------
# Upload streaming pre-check
# ---------------------------------------------------------------------------


def _upload(
    content: bytes, filename: str = "x.pdf", declared_size: int | None = None
) -> UploadFile:
    f = UploadFile(filename=filename, file=io.BytesIO(content))
    # Starlette populates size from headers; override for the test.
    if declared_size is not None:
        f.size = declared_size  # type: ignore[assignment]
    return f


class TestUploadStreaming:
    @staticmethod
    @pytest.mark.asyncio
    async def test_rejects_declared_size_over_limit() -> None:
        from lintpdf.api.upload_security import PDF_TYPES

        f = _upload(b"%PDF-1.4\n...", declared_size=10 * 1024 * 1024)
        with pytest.raises(HTTPException) as exc:
            await validate_upload(f, allowed_types=PDF_TYPES, max_size_bytes=1024)
        assert exc.value.status_code == 413

    @staticmethod
    @pytest.mark.asyncio
    async def test_rejects_mid_stream_when_content_length_lied() -> None:
        from lintpdf.api.upload_security import PDF_TYPES

        # Build a body that claims to be tiny but is actually large.
        payload = b"%PDF-1.4\n" + b"A" * (5 * 1024 * 1024)
        f = _upload(payload, declared_size=None)
        with pytest.raises(HTTPException) as exc:
            await validate_upload(f, allowed_types=PDF_TYPES, max_size_bytes=1024)
        assert exc.value.status_code == 413


# ---------------------------------------------------------------------------
# Webhook dead-letter flagging
# ---------------------------------------------------------------------------


class TestWebhookDeadLetter:
    @staticmethod
    def test_is_dead_default_false(db_session) -> None:
        import uuid

        from lintpdf.api.models import (
            Tenant,
            WebhookDelivery,
            WebhookEndpoint,
        )

        tenant = db_session.query(Tenant).first()
        endpoint = WebhookEndpoint(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            url="https://example.invalid/hook",
            secret="s",
            is_active=True,
            events=["job.completed"],
        )
        db_session.add(endpoint)
        db_session.flush()

        row = WebhookDelivery(
            id=uuid.uuid4(),
            webhook_id=endpoint.id,
            tenant_id=tenant.id,
            event="job.completed",
            payload={},
            url=endpoint.url,
            attempt_count=1,
            final_status_code=500,
            success=False,
        )
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)
        assert row.is_dead is False
        assert row.replay_count == 0


# ---------------------------------------------------------------------------
# Branding cache
# ---------------------------------------------------------------------------


class TestBrandingCache:
    @staticmethod
    def test_roundtrip(monkeypatch) -> None:
        fake = _FakeRedis()
        monkeypatch.setattr(middleware, "_redis_state", {"client": fake})
        key = cache.brand_profile_key("t", "p")
        cache.set_json(key, {"a": 1})
        assert cache.get_json(key) == {"a": 1}
        cache.invalidate(key)
        assert cache.get_json(key) is None

    @staticmethod
    def test_miss_on_unconfigured_redis(monkeypatch) -> None:
        monkeypatch.setattr(middleware, "_redis_state", {"client": None})
        assert cache.get_json("nope") is None
        # Should not raise
        cache.set_json("nope", {"a": 1})


# ---------------------------------------------------------------------------
# Celery config + settings singleton
# ---------------------------------------------------------------------------


class TestCeleryAndSettings:
    @staticmethod
    def test_result_expires_configured() -> None:
        assert celery_app.conf.result_expires == 3600

    @staticmethod
    def test_get_settings_is_cached_in_production(monkeypatch) -> None:
        # Under pytest we deliberately bypass the cache so
        # monkeypatch.setenv works; verify the cache is still wired up
        # for production by pretending we're not under pytest.
        import os

        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        from lintpdf.api.config import _cached_settings

        _cached_settings.cache_clear()
        a = get_settings()
        b = get_settings()
        assert a is b
        assert isinstance(a, Settings)
        # Restore env for subsequent tests
        os.environ["PYTEST_CURRENT_TEST"] = "restored"
