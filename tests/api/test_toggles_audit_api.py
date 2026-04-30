"""Tests for V-08 audit log helper + endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from siftpdf.tenants import toggle_audit
from siftpdf.tenants.toggle_models import (
    Toggle,
    ToggleAuditLog,
    ToggleOverride,
    ToggleScope,
    ToggleType,
)
from tests.api.conftest import PLACEHOLDER_TENANT_ID

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


def _seed_toggle(session: Session, *, toggle_id: str, lockable: bool = False) -> None:
    session.add(
        Toggle(
            id=toggle_id,
            category=toggle_id.split(".")[0],
            human_name=toggle_id,
            type=ToggleType.STRING,
            default_value="warn",
            override_at=[ToggleScope.TENANT, ToggleScope.WORKFLOW, ToggleScope.CALL],
            lockable=lockable,
        )
    )
    session.commit()


# ---- audit helper unit tests ----------------------------------------


def test_record_create_writes_row(db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    toggle_audit.record(
        db_session,
        tenant_id=PLACEHOLDER_TENANT_ID,
        toggle_id="checks.F-22",
        scope=ToggleScope.TENANT,
        scope_id=str(PLACEHOLDER_TENANT_ID),
        action=toggle_audit.CREATE,
        before=None,
        after_value="error",
        after_locked=False,
        actor="api_test",
        surface="api",
    )
    db_session.commit()
    row = db_session.execute(select(ToggleAuditLog)).scalar_one()
    assert row.action == "CREATE"
    assert row.before_value is None
    assert row.after_value == "error"
    assert row.before_locked is None
    assert row.after_locked is False
    assert row.actor == "api_test"


def test_record_update_captures_before_and_after(db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    existing = ToggleOverride(
        id="ov_existing",
        toggle_id="checks.F-22",
        scope=ToggleScope.TENANT,
        scope_id=str(PLACEHOLDER_TENANT_ID),
        value="error",
        locked=False,
        set_by="seed",
        surface="api",
    )
    db_session.add(existing)
    db_session.commit()

    toggle_audit.record(
        db_session,
        tenant_id=PLACEHOLDER_TENANT_ID,
        toggle_id="checks.F-22",
        scope=ToggleScope.TENANT,
        scope_id=str(PLACEHOLDER_TENANT_ID),
        action=toggle_audit.UPDATE,
        before=existing,
        after_value="info",
        after_locked=True,
        actor="user_42",
        surface="api",
    )
    db_session.commit()
    row = db_session.execute(select(ToggleAuditLog)).scalar_one()
    assert row.action == "UPDATE"
    assert row.before_value == "error"
    assert row.after_value == "info"
    assert row.before_locked is False
    assert row.after_locked is True


def test_record_delete_clears_after(db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    existing = ToggleOverride(
        id="ov_existing",
        toggle_id="checks.F-22",
        scope=ToggleScope.TENANT,
        scope_id=str(PLACEHOLDER_TENANT_ID),
        value="error",
        locked=False,
        set_by="seed",
        surface="api",
    )
    db_session.add(existing)
    db_session.commit()

    toggle_audit.record(
        db_session,
        tenant_id=PLACEHOLDER_TENANT_ID,
        toggle_id="checks.F-22",
        scope=ToggleScope.TENANT,
        scope_id=str(PLACEHOLDER_TENANT_ID),
        action=toggle_audit.DELETE,
        before=existing,
        after_value=None,
        after_locked=None,
        actor="api",
        surface="api",
    )
    db_session.commit()
    row = db_session.execute(select(ToggleAuditLog)).scalar_one()
    assert row.action == "DELETE"
    assert row.before_value == "error"
    assert row.after_value is None
    assert row.after_locked is None


def test_record_rejects_unknown_action(db_session: Session):
    import pytest

    with pytest.raises(ValueError, match="unknown action"):
        toggle_audit.record(
            db_session,
            tenant_id=PLACEHOLDER_TENANT_ID,
            toggle_id="x",
            scope=ToggleScope.TENANT,
            scope_id="x",
            action="NUKE",
            before=None,
            actor="api",
            surface="api",
        )


# ---- endpoint integration -------------------------------------------


def test_put_writes_create_audit(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    client.put("/api/v1/tenant/toggles/checks.F-22", json={"value": "error"})

    rows = db_session.execute(select(ToggleAuditLog)).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "CREATE"
    assert rows[0].after_value == "error"


def test_put_then_put_writes_update_audit(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    client.put("/api/v1/tenant/toggles/checks.F-22", json={"value": "error"})
    client.put("/api/v1/tenant/toggles/checks.F-22", json={"value": "info"})

    rows = (
        db_session.execute(select(ToggleAuditLog).order_by(ToggleAuditLog.created_at))
        .scalars()
        .all()
    )
    assert [r.action for r in rows] == ["CREATE", "UPDATE"]
    assert rows[1].before_value == "error"
    assert rows[1].after_value == "info"


def test_delete_writes_delete_audit(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    client.put("/api/v1/tenant/toggles/checks.F-22", json={"value": "error"})
    client.delete("/api/v1/tenant/toggles/checks.F-22")

    rows = (
        db_session.execute(select(ToggleAuditLog).order_by(ToggleAuditLog.created_at))
        .scalars()
        .all()
    )
    assert [r.action for r in rows] == ["CREATE", "DELETE"]
    assert rows[1].before_value == "error"
    assert rows[1].after_value is None


def test_audit_list_endpoint_returns_recent_first(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    _seed_toggle(db_session, toggle_id="checks.F-23")
    client.put("/api/v1/tenant/toggles/checks.F-22", json={"value": "error"})
    client.put("/api/v1/tenant/toggles/checks.F-23", json={"value": "off"})

    resp = client.get("/api/v1/tenant/toggles/audit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    # newest first
    assert body["items"][0]["toggle_id"] == "checks.F-23"
    assert body["items"][1]["toggle_id"] == "checks.F-22"


def test_audit_list_filters_by_toggle(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    _seed_toggle(db_session, toggle_id="checks.F-23")
    client.put("/api/v1/tenant/toggles/checks.F-22", json={"value": "error"})
    client.put("/api/v1/tenant/toggles/checks.F-23", json={"value": "off"})

    resp = client.get("/api/v1/tenant/toggles/audit?toggle_id=checks.F-22")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["toggle_id"] == "checks.F-22"


def test_audit_list_filters_by_action(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    client.put("/api/v1/tenant/toggles/checks.F-22", json={"value": "error"})
    client.delete("/api/v1/tenant/toggles/checks.F-22")

    resp = client.get("/api/v1/tenant/toggles/audit?action=DELETE")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["action"] == "DELETE"
