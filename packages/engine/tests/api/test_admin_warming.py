"""Tests for the super-admin tile-warming observability endpoints.

Covers:
* `/api/v1/admin/tile-warming/events` — recent events, tenant filter, limit.
* `/api/v1/admin/tile-warming/summary` — aggregates, p95 math, window filter.
* `/api/v1/admin/tile-warming/jobs/{job_id}` — status hash + filtered events.
* `_record_tile_warm_event` — the Redis sink used by ``warm_viewer_tiles``.

A small FakeRedis shim adds ``lpush`` / ``ltrim`` / ``lrange`` on top of the
string + hash commands the warming shim already supports.
"""

from __future__ import annotations

import datetime as _dt
import json
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from lintpdf.api.app import create_app
from lintpdf.queue.tasks import (
    _record_tile_warm_event,
    _tile_warm_events_all_key,
    _tile_warm_events_key,
    _tile_warm_status_key,
)

if TYPE_CHECKING:
    from collections.abc import Generator

ADMIN_KEY = "test-admin-key-warming"


class FakeRedis:
    """In-memory Redis shim covering the commands the admin-warming router uses."""

    def __init__(self) -> None:
        self._lists: dict[str, list[Any]] = {}
        self._hashes: dict[str, dict[str, str]] = {}

    # List ops ------------------------------------------------------
    def lpush(self, key: str, value: Any) -> int:
        self._lists.setdefault(key, []).insert(0, value)
        return len(self._lists[key])

    def ltrim(self, key: str, start: int, stop: int) -> bool:
        lst = self._lists.get(key, [])
        # Redis LTRIM is inclusive on both ends; stop=-1 means "end".
        if stop == -1:
            self._lists[key] = lst[start:]
        else:
            self._lists[key] = lst[start : stop + 1]
        return True

    def lrange(self, key: str, start: int, stop: int) -> list[Any]:
        lst = self._lists.get(key, [])
        if stop == -1:
            return list(lst[start:])
        return list(lst[start : stop + 1])

    def expire(self, key: str, ttl: int) -> bool:
        _ = (key, ttl)
        return True

    # Hash ops ------------------------------------------------------
    def hset(
        self,
        key: str,
        *,
        mapping: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> int:
        payload = dict(mapping or {})
        payload.update(kwargs)
        self._hashes.setdefault(key, {}).update(payload)
        return len(payload)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))


@pytest.fixture(autouse=True)
def _admin_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINTPDF_ADMIN_API_KEY", ADMIN_KEY)


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    redis = FakeRedis()
    import lintpdf.api.middleware as mw
    import lintpdf.api.routes.admin_warming as aw

    monkeypatch.setattr(mw, "get_redis_client", lambda: redis)
    monkeypatch.setattr(aw, "get_redis_client", lambda: redis)
    return redis


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app = create_app()
    with TestClient(app) as tc:
        yield tc


def _headers() -> dict[str, str]:
    return {"X-Admin-Key": ADMIN_KEY}


def _push_event(
    redis: FakeRedis,
    tenant_id: str | None,
    *,
    event: str = "tile_warm.complete",
    job_id: str = "job-1",
    duration_s: float | None = 1.0,
    page_count: int | None = 10,
    error: str | None = None,
    recorded_at: _dt.datetime | None = None,
) -> dict[str, Any]:
    payload = {
        "event": event,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "page_count": page_count,
        "dpi": 150,
        "thumbnails": True,
        "duration_s": duration_s,
        "error": error,
        "recorded_at": (recorded_at or _dt.datetime.now(_dt.UTC)).isoformat(),
    }
    _record_tile_warm_event(redis, tenant_id, payload)
    return payload


# ── Auth ─────────────────────────────────────────────────────────────


class TestAdminWarmingAuth:
    @staticmethod
    def test_events_requires_admin_key(client: TestClient) -> None:
        resp = client.get("/api/v1/admin/tile-warming/events")
        assert resp.status_code == 401

    @staticmethod
    def test_summary_wrong_key_is_401(client: TestClient) -> None:
        resp = client.get(
            "/api/v1/admin/tile-warming/summary",
            headers={"X-Admin-Key": "nope"},
        )
        assert resp.status_code == 401

    @staticmethod
    def test_job_detail_non_admin_is_401(client: TestClient) -> None:
        resp = client.get("/api/v1/admin/tile-warming/jobs/abc")
        assert resp.status_code == 401


# ── No-Redis graceful path ───────────────────────────────────────────


class TestNoRedis:
    @staticmethod
    def test_events_returns_no_redis(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        import lintpdf.api.routes.admin_warming as aw

        monkeypatch.setattr(aw, "get_redis_client", lambda: None)

        resp = client.get("/api/v1/admin/tile-warming/events", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["events"] == []
        assert body["status"] == "no_redis"

    @staticmethod
    def test_summary_returns_no_redis(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        import lintpdf.api.routes.admin_warming as aw

        monkeypatch.setattr(aw, "get_redis_client", lambda: None)

        resp = client.get("/api/v1/admin/tile-warming/summary", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "no_redis"
        assert body["total_events"] == 0

    @staticmethod
    def test_job_detail_returns_no_redis(
        client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import lintpdf.api.routes.admin_warming as aw

        monkeypatch.setattr(aw, "get_redis_client", lambda: None)

        resp = client.get(
            "/api/v1/admin/tile-warming/jobs/xyz",
            headers=_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "no_redis"
        assert body["recent_events"] == []


# ── /events ──────────────────────────────────────────────────────────


class TestListEvents:
    @staticmethod
    def test_returns_events_newest_first(client: TestClient, fake_redis: FakeRedis) -> None:
        _push_event(fake_redis, "tenant-a", job_id="j1")
        _push_event(fake_redis, "tenant-a", job_id="j2")
        _push_event(fake_redis, "tenant-a", job_id="j3")

        resp = client.get("/api/v1/admin/tile-warming/events", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        ids = [ev["job_id"] for ev in body["events"]]
        # LPUSH puts newest at index 0 → j3 first.
        assert ids == ["j3", "j2", "j1"]

    @staticmethod
    def test_limit_caps_response(client: TestClient, fake_redis: FakeRedis) -> None:
        for i in range(10):
            _push_event(fake_redis, "tenant-a", job_id=f"job-{i}")

        resp = client.get("/api/v1/admin/tile-warming/events?limit=3", headers=_headers())
        assert resp.status_code == 200
        assert len(resp.json()["events"]) == 3

    @staticmethod
    def test_tenant_filter_scopes_to_tenant(client: TestClient, fake_redis: FakeRedis) -> None:
        _push_event(fake_redis, "tenant-a", job_id="a1")
        _push_event(fake_redis, "tenant-b", job_id="b1")
        _push_event(fake_redis, "tenant-a", job_id="a2")

        resp = client.get(
            "/api/v1/admin/tile-warming/events?tenant_id=tenant-a",
            headers=_headers(),
        )
        assert resp.status_code == 200
        ids = {ev["job_id"] for ev in resp.json()["events"]}
        assert ids == {"a1", "a2"}

    @staticmethod
    def test_malformed_entry_is_dropped(client: TestClient, fake_redis: FakeRedis) -> None:
        # One good, one garbage JSON blob at position 0.
        _push_event(fake_redis, "tenant-a", job_id="good")
        fake_redis.lpush(_tile_warm_events_all_key(), "{not json")

        resp = client.get("/api/v1/admin/tile-warming/events", headers=_headers())
        assert resp.status_code == 200
        ids = [ev["job_id"] for ev in resp.json()["events"]]
        assert ids == ["good"]


# ── /summary ─────────────────────────────────────────────────────────


class TestSummary:
    @staticmethod
    def test_p50_and_p95_math(client: TestClient, fake_redis: FakeRedis) -> None:
        # 20 complete events with durations 1..20 → p50≈10, p95≈19.
        for i in range(1, 21):
            _push_event(
                fake_redis,
                "tenant-a",
                job_id=f"job-{i}",
                duration_s=float(i),
            )

        resp = client.get("/api/v1/admin/tile-warming/summary", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_completes"] == 20
        assert body["total_failures"] == 0
        # Nearest-rank with round(): p50 → index 10 → value 11.
        assert body["p50_duration_s"] in (10.0, 11.0)
        assert body["p95_duration_s"] in (19.0, 20.0)

    @staticmethod
    def test_window_filters_out_old_events(client: TestClient, fake_redis: FakeRedis) -> None:
        old = _dt.datetime.now(_dt.UTC) - _dt.timedelta(hours=48)
        _push_event(fake_redis, "tenant-a", job_id="old", recorded_at=old)
        _push_event(fake_redis, "tenant-a", job_id="new")

        resp = client.get(
            "/api/v1/admin/tile-warming/summary?since_hours=24",
            headers=_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        # Only the fresh event is in-window.
        assert body["total_events"] == 1
        assert body["total_completes"] == 1

    @staticmethod
    def test_failures_and_top_errors(client: TestClient, fake_redis: FakeRedis) -> None:
        _push_event(fake_redis, "tenant-a")
        _push_event(
            fake_redis,
            "tenant-a",
            event="tile_warm.failure",
            duration_s=None,
            page_count=None,
            error="S3 timeout",
        )
        _push_event(
            fake_redis,
            "tenant-a",
            event="tile_warm.failure",
            duration_s=None,
            page_count=None,
            error="S3 timeout",
        )
        _push_event(
            fake_redis,
            "tenant-b",
            event="tile_warm.failure",
            duration_s=None,
            page_count=None,
            error="render crash",
        )

        resp = client.get("/api/v1/admin/tile-warming/summary", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_completes"] == 1
        assert body["total_failures"] == 3
        # Top error is the repeated S3 timeout.
        assert body["top_errors"][0] == {"error": "S3 timeout", "count": 2}
        # Both tenants are represented.
        tenant_ids = {t["tenant_id"] for t in body["per_tenant"]}
        assert tenant_ids == {"tenant-a", "tenant-b"}

    @staticmethod
    def test_top_tenants_is_sorted_by_volume(client: TestClient, fake_redis: FakeRedis) -> None:
        for i in range(5):
            _push_event(fake_redis, "tenant-heavy", job_id=f"h-{i}")
        _push_event(fake_redis, "tenant-light", job_id="l-0")

        resp = client.get("/api/v1/admin/tile-warming/summary", headers=_headers())
        body = resp.json()
        assert body["top_tenants"][0]["tenant_id"] == "tenant-heavy"
        assert body["top_tenants"][0]["completes"] == 5
        assert len(body["top_tenants"]) == 2


# ── /jobs/{job_id} ───────────────────────────────────────────────────


class TestJobDetail:
    @staticmethod
    def test_returns_status_hash_and_matching_events(
        client: TestClient, fake_redis: FakeRedis
    ) -> None:
        job_id = "abc-123"
        fake_redis.hset(
            _tile_warm_status_key(job_id),
            mapping={"status": "complete", "rendered": "4", "total": "4"},
        )
        _push_event(fake_redis, "tenant-a", job_id=job_id)
        _push_event(fake_redis, "tenant-a", job_id="other-job")

        resp = client.get(f"/api/v1/admin/tile-warming/jobs/{job_id}", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["status_hash"] is not None
        assert body["status_hash"]["status"] == "complete"
        assert len(body["recent_events"]) == 1
        assert body["recent_events"][0]["job_id"] == job_id

    @staticmethod
    def test_unknown_job_returns_empty(client: TestClient, fake_redis: FakeRedis) -> None:
        resp = client.get("/api/v1/admin/tile-warming/jobs/ghost", headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["status_hash"] is None
        assert body["recent_events"] == []


# ── _record_tile_warm_event sink ─────────────────────────────────────


class TestRecordEvent:
    @staticmethod
    def test_pushes_to_tenant_and_all_lists() -> None:
        redis = FakeRedis()
        payload = {
            "event": "tile_warm.complete",
            "job_id": "j-1",
            "tenant_id": "t-1",
            "page_count": 3,
            "dpi": 150,
            "thumbnails": True,
            "duration_s": 2.5,
            "error": None,
            "recorded_at": _dt.datetime.now(_dt.UTC).isoformat(),
        }
        _record_tile_warm_event(redis, "t-1", payload)

        all_items = redis.lrange(_tile_warm_events_all_key(), 0, -1)
        tenant_items = redis.lrange(_tile_warm_events_key("t-1"), 0, -1)
        assert len(all_items) == 1
        assert len(tenant_items) == 1
        assert json.loads(all_items[0])["job_id"] == "j-1"

    @staticmethod
    def test_none_tenant_only_writes_to_all() -> None:
        redis = FakeRedis()
        payload = {
            "event": "tile_warm.failure",
            "job_id": "j-x",
            "tenant_id": None,
            "error": "early",
            "recorded_at": _dt.datetime.now(_dt.UTC).isoformat(),
        }
        _record_tile_warm_event(redis, None, payload)
        assert len(redis.lrange(_tile_warm_events_all_key(), 0, -1)) == 1

    @staticmethod
    def test_none_redis_is_noop() -> None:
        # Must not raise.
        _record_tile_warm_event(None, "t", {"event": "x"})

    @staticmethod
    def test_cap_trims_to_500_entries() -> None:
        redis = FakeRedis()
        for i in range(510):
            _record_tile_warm_event(
                redis,
                "t",
                {
                    "event": "tile_warm.complete",
                    "job_id": f"j-{i}",
                    "tenant_id": "t",
                    "recorded_at": _dt.datetime.now(_dt.UTC).isoformat(),
                },
            )
        assert len(redis.lrange(_tile_warm_events_all_key(), 0, -1)) == 500
