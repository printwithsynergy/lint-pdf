"""Wave V V-06 — emit_event + tenant-default secret integration."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from siftpdf.api.models import (
    Base,
    Tenant,
    TenantPlan,
    WebhookDelivery,
    WebhookEndpoint,
)
from siftpdf.webhooks.events import emit_event

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session


_TENANT_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):  # type: ignore[no-untyped-def]
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = factory()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def _seed_tenant(db: Session, *, default_secret: str | None = None) -> Tenant:
    t = Tenant(
        id=_TENANT_A,
        name="t",
        api_key_hash="hash",
        plan=TenantPlan.GROWTH,
        rate_limit_daily=1000,
        max_file_size_mb=10,
        webhook_signing_secret=default_secret,
    )
    db.add(t)
    db.commit()
    return t


def _add_endpoint(
    db: Session,
    *,
    secret: str | None,
    events: list[str] | None = None,
) -> WebhookEndpoint:
    ep = WebhookEndpoint(
        id=uuid.uuid4(),
        tenant_id=_TENANT_A,
        url="https://example.com/hook",
        secret=secret,
        events=events or [],
        is_active=True,
    )
    db.add(ep)
    db.commit()
    return ep


def _patch_dispatch(monkeypatch) -> MagicMock:
    """Replace ``dispatch_webhook.delay`` with a MagicMock so emit_event
    doesn't reach into Celery during the unit test."""
    mock = MagicMock()
    import siftpdf.queue.tasks as queue_tasks

    monkeypatch.setattr(queue_tasks.dispatch_webhook, "delay", mock)
    return mock


# ---- per-webhook secret wins ---------------------------------------------


def test_emit_event_uses_endpoint_secret_when_present(db: Session, monkeypatch):
    _seed_tenant(db, default_secret="tenant-default")
    _add_endpoint(db, secret="endpoint-specific")
    mock = _patch_dispatch(monkeypatch)

    emit_event(db, _TENANT_A, "job.completed", {"x": 1})

    assert mock.call_count == 1
    kwargs = mock.call_args.kwargs
    assert kwargs["webhook_secret"] == "endpoint-specific"


# ---- tenant default fills in ---------------------------------------------


def test_emit_event_falls_back_to_tenant_default(db: Session, monkeypatch):
    _seed_tenant(db, default_secret="tenant-default")
    _add_endpoint(db, secret=None)
    mock = _patch_dispatch(monkeypatch)

    emit_event(db, _TENANT_A, "job.completed", {"x": 1})

    assert mock.call_count == 1
    assert mock.call_args.kwargs["webhook_secret"] == "tenant-default"


def test_emit_event_falls_back_when_endpoint_secret_empty(db: Session, monkeypatch):
    _seed_tenant(db, default_secret="tenant-default")
    _add_endpoint(db, secret="")
    mock = _patch_dispatch(monkeypatch)

    emit_event(db, _TENANT_A, "job.completed", {"x": 1})

    assert mock.call_count == 1
    assert mock.call_args.kwargs["webhook_secret"] == "tenant-default"


# ---- both missing → skip dispatch + log -----------------------------------


def test_emit_event_skips_when_neither_secret_set(db: Session, monkeypatch, caplog):
    _seed_tenant(db, default_secret=None)
    _add_endpoint(db, secret=None)
    mock = _patch_dispatch(monkeypatch)

    import logging

    with caplog.at_level(logging.ERROR, logger="siftpdf.webhooks.events"):
        emit_event(db, _TENANT_A, "job.completed", {"x": 1})

    assert mock.call_count == 0
    assert "neither per-webhook nor tenant-default" in caplog.text
    # Audit row also not created — emission abandoned before persisting.
    rows = db.query(WebhookDelivery).all()
    assert rows == []


# ---- multiple endpoints share the tenant default ------------------------


def test_emit_event_resolves_per_endpoint_independently(db: Session, monkeypatch):
    _seed_tenant(db, default_secret="tenant-default")
    _add_endpoint(db, secret="endpoint-a-specific")
    _add_endpoint(db, secret=None)  # falls back to tenant default
    _add_endpoint(db, secret="endpoint-c-specific")
    mock = _patch_dispatch(monkeypatch)

    emit_event(db, _TENANT_A, "job.completed", {"x": 1})

    assert mock.call_count == 3
    used_secrets = sorted(call.kwargs["webhook_secret"] for call in mock.call_args_list)
    assert used_secrets == [
        "endpoint-a-specific",
        "endpoint-c-specific",
        "tenant-default",
    ]


def test_emit_event_persists_delivery_row_with_resolved_dispatch(db: Session, monkeypatch):
    """Audit row + dispatch are created together when secret resolves."""
    _seed_tenant(db, default_secret="tenant-default")
    _add_endpoint(db, secret=None)
    _patch_dispatch(monkeypatch)

    emit_event(db, _TENANT_A, "job.completed", {"x": 1})

    rows = db.query(WebhookDelivery).all()
    assert len(rows) == 1
    assert rows[0].event == "job.completed"
    assert rows[0].tenant_id == _TENANT_A


# ---- subscription filter still applies after secret resolution -----------


def test_emit_event_skips_unsubscribed_event_before_resolving(db: Session, monkeypatch):
    _seed_tenant(db, default_secret="tenant-default")
    # Endpoint subscribes only to "approval.chain.completed"
    _add_endpoint(db, secret="endpoint-a", events=["approval.chain.completed"])
    mock = _patch_dispatch(monkeypatch)

    emit_event(db, _TENANT_A, "job.completed", {"x": 1})
    assert mock.call_count == 0
