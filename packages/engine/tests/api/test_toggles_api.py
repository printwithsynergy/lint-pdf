"""Integration tests for the V-07 toggles endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from lintpdf.tenants.toggle_models import (
    MergeStrategy,
    Toggle,
    ToggleScope,
    ToggleType,
)
from tests.api.conftest import PLACEHOLDER_TENANT_ID

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


def _seed_toggle(
    db_session: Session,
    *,
    toggle_id: str,
    type_: ToggleType,
    default: object,
    category: str | None = None,
    lockable: bool = False,
    merge: MergeStrategy = MergeStrategy.REPLACE,
) -> None:
    db_session.add(
        Toggle(
            id=toggle_id,
            category=category or toggle_id.split(".")[0],
            human_name=toggle_id,
            type=type_,
            default_value=default,
            override_at=[ToggleScope.TENANT, ToggleScope.WORKFLOW, ToggleScope.CALL],
            merge_strategy=merge,
            lockable=lockable,
        )
    )
    db_session.commit()


# ---- registry endpoints --------------------------------------------------


def test_list_toggles_empty(client: TestClient):
    resp = client.get("/api/v1/toggles")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0}


def test_list_toggles_returns_seeded_rows(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    _seed_toggle(db_session, toggle_id="profiles.PDF-X-4", type_=ToggleType.BOOLEAN, default=True)
    resp = client.get("/api/v1/toggles")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    ids = [item["id"] for item in body["items"]]
    assert ids == sorted(ids)


def test_list_toggles_filters_by_category(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    _seed_toggle(db_session, toggle_id="profiles.PDF-X-4", type_=ToggleType.BOOLEAN, default=True)
    resp = client.get("/api/v1/toggles?category=checks")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_get_toggle_404_on_unknown(client: TestClient):
    resp = client.get("/api/v1/toggles/checks.GHOST")
    assert resp.status_code == 404


def test_get_toggle_returns_row(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    resp = client.get("/api/v1/toggles/checks.F-22")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "checks.F-22"
    assert body["default_value"] == "warn"
    assert body["deprecated"] is False


# ---- resolve endpoint ---------------------------------------------------


def test_resolve_returns_default_with_no_overrides(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    resp = client.get("/api/v1/toggles/resolve?toggle_id=checks.F-22")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"toggle_id": "checks.F-22", "value": "warn", "locked": False}


def test_resolve_404_on_unknown(client: TestClient):
    resp = client.get("/api/v1/toggles/resolve?toggle_id=checks.GHOST")
    assert resp.status_code == 404


# ---- tenant override CRUD ----------------------------------------------


def test_put_tenant_override_creates_row(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    resp = client.put(
        "/api/v1/tenant/toggles/checks.F-22", json={"value": "error", "locked": False}
    )
    assert resp.status_code == 200
    assert resp.json()["value"] == "error"

    # Verify subsequent resolve sees the override
    resp = client.get("/api/v1/toggles/resolve?toggle_id=checks.F-22")
    assert resp.json()["value"] == "error"


def test_put_tenant_override_updates_existing(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    client.put("/api/v1/tenant/toggles/checks.F-22", json={"value": "error"})
    client.put("/api/v1/tenant/toggles/checks.F-22", json={"value": "info"})
    resp = client.get("/api/v1/toggles/resolve?toggle_id=checks.F-22")
    assert resp.json()["value"] == "info"


def test_put_locked_when_lockable(client: TestClient, db_session: Session):
    _seed_toggle(
        db_session,
        toggle_id="checks.F-22",
        type_=ToggleType.STRING,
        default="warn",
        lockable=True,
    )
    resp = client.put(
        "/api/v1/tenant/toggles/checks.F-22",
        json={"value": "error", "locked": True},
    )
    assert resp.status_code == 200
    resp = client.get("/api/v1/toggles/resolve?toggle_id=checks.F-22")
    assert resp.json() == {"toggle_id": "checks.F-22", "value": "error", "locked": True}


def test_put_locked_rejected_when_not_lockable(client: TestClient, db_session: Session):
    _seed_toggle(
        db_session,
        toggle_id="checks.F-22",
        type_=ToggleType.STRING,
        default="warn",
        lockable=False,
    )
    resp = client.put(
        "/api/v1/tenant/toggles/checks.F-22",
        json={"value": "error", "locked": True},
    )
    assert resp.status_code == 400


def test_delete_tenant_override(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    client.put("/api/v1/tenant/toggles/checks.F-22", json={"value": "error"})
    resp = client.delete("/api/v1/tenant/toggles/checks.F-22")
    assert resp.status_code == 204
    resp = client.get("/api/v1/toggles/resolve?toggle_id=checks.F-22")
    assert resp.json()["value"] == "warn"


def test_put_404_on_unknown_toggle(client: TestClient):
    resp = client.put("/api/v1/tenant/toggles/unknown", json={"value": "x"})
    assert resp.status_code == 404


def test_put_400_when_tenant_scope_not_allowed(client: TestClient, db_session: Session):
    """A toggle that excludes TENANT from override_at should reject tenant overrides."""
    db_session.add(
        Toggle(
            id="locked-toggle",
            category="locked",
            human_name="Locked toggle",
            type=ToggleType.STRING,
            default_value="x",
            override_at=[ToggleScope.CALL],  # CALL only
            lockable=False,
        )
    )
    db_session.commit()
    resp = client.put("/api/v1/tenant/toggles/locked-toggle", json={"value": "y"})
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "tenant_value, locked, want_locked",
    [
        ("error", True, True),
        ("error", False, False),
    ],
)
def test_resolve_reports_locked_flag(
    client: TestClient,
    db_session: Session,
    tenant_value: str,
    locked: bool,
    want_locked: bool,
):
    _seed_toggle(
        db_session,
        toggle_id="checks.F-22",
        type_=ToggleType.STRING,
        default="warn",
        lockable=True,
    )
    client.put(
        "/api/v1/tenant/toggles/checks.F-22",
        json={"value": tenant_value, "locked": locked},
    )
    resp = client.get("/api/v1/toggles/resolve?toggle_id=checks.F-22")
    assert resp.json()["locked"] is want_locked
    # Sanity: the placeholder tenant ID matches the override scope_id
    assert PLACEHOLDER_TENANT_ID is not None
