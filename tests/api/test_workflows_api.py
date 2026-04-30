"""Phase 0.7 PR-A — workflow CRUD + workflow-scoped override endpoint tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.tenants.toggle_models import (
    MergeStrategy,
    Toggle,
    ToggleOverride,
    ToggleScope,
    ToggleType,
    Workflow,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


def _seed_toggle(
    db_session: Session,
    *,
    toggle_id: str,
    type_: ToggleType = ToggleType.STRING,
    default: object = "warn",
    override_at: list[ToggleScope] | None = None,
    lockable: bool = False,
    merge: MergeStrategy = MergeStrategy.REPLACE,
) -> None:
    db_session.add(
        Toggle(
            id=toggle_id,
            category=toggle_id.split(".")[0],
            human_name=toggle_id,
            type=type_,
            default_value=default,
            override_at=override_at or [ToggleScope.TENANT, ToggleScope.WORKFLOW, ToggleScope.CALL],
            merge_strategy=merge,
            lockable=lockable,
        )
    )
    db_session.commit()


# ---- workflow CRUD -------------------------------------------------------


def test_list_workflows_empty(client: TestClient):
    resp = client.get("/api/v1/workflows")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0}


def test_create_workflow(client: TestClient):
    resp = client.post(
        "/api/v1/workflows",
        json={
            "slug": "packaging-fc",
            "human_name": "Packaging — Folding Carton",
            "description": "Standard FC pipeline",
            "is_default": False,
            "response_mode": "async",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "packaging-fc"
    assert body["human_name"] == "Packaging — Folding Carton"
    assert body["is_active"] is True
    assert body["is_default"] is False
    assert body["response_mode"] == "async"
    assert body["server_revision"] == 1
    assert isinstance(body["id"], str) and len(body["id"]) > 0


def test_create_workflow_rejects_duplicate_slug(client: TestClient):
    body = {
        "slug": "dup",
        "human_name": "Dup",
        "response_mode": "async",
    }
    assert client.post("/api/v1/workflows", json=body).status_code == 201
    resp = client.post("/api/v1/workflows", json=body)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


def test_create_workflow_rejects_invalid_response_mode(client: TestClient):
    resp = client.post(
        "/api/v1/workflows",
        json={"slug": "x", "human_name": "x", "response_mode": "bogus"},
    )
    assert resp.status_code == 422


def test_get_workflow(client: TestClient):
    create = client.post(
        "/api/v1/workflows",
        json={"slug": "wf1", "human_name": "Workflow 1"},
    ).json()
    resp = client.get(f"/api/v1/workflows/{create['id']}")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "wf1"


def test_get_workflow_404_on_unknown(client: TestClient):
    resp = client.get("/api/v1/workflows/does-not-exist")
    assert resp.status_code == 404


def test_patch_workflow_updates_fields_and_bumps_revision(client: TestClient):
    wf = client.post(
        "/api/v1/workflows",
        json={"slug": "wf1", "human_name": "Workflow 1"},
    ).json()
    initial_rev = wf["server_revision"]
    resp = client.patch(
        f"/api/v1/workflows/{wf['id']}",
        json={"human_name": "Renamed", "description": "now with description"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["human_name"] == "Renamed"
    assert body["description"] == "now with description"
    assert body["server_revision"] == initial_rev + 1


def test_patch_workflow_setting_default_clears_other_defaults(
    client: TestClient,
    db_session: Session,
):
    a = client.post(
        "/api/v1/workflows",
        json={"slug": "a", "human_name": "A", "is_default": True},
    ).json()
    b = client.post(
        "/api/v1/workflows",
        json={"slug": "b", "human_name": "B", "is_default": False},
    ).json()
    # Now flip B to default
    resp = client.patch(f"/api/v1/workflows/{b['id']}", json={"is_default": True})
    assert resp.status_code == 200
    assert resp.json()["is_default"] is True
    # A is no longer default
    db_session.expire_all()
    a_row = db_session.get(Workflow, a["id"])
    assert a_row is not None
    assert a_row.is_default is False


def test_delete_workflow_soft_deletes(client: TestClient, db_session: Session):
    wf = client.post(
        "/api/v1/workflows",
        json={"slug": "wf1", "human_name": "Workflow 1"},
    ).json()
    resp = client.delete(f"/api/v1/workflows/{wf['id']}")
    assert resp.status_code == 204
    # Row still exists, but is_active=False
    db_session.expire_all()
    row = db_session.get(Workflow, wf["id"])
    assert row is not None
    assert row.is_active is False
    # default list excludes it
    listed = client.get("/api/v1/workflows").json()
    assert listed["total"] == 0
    # include_inactive surfaces it again
    listed_all = client.get("/api/v1/workflows?include_inactive=true").json()
    assert listed_all["total"] == 1


# ---- workflow-scoped overrides ------------------------------------------


def test_set_workflow_override_creates_row(
    client: TestClient,
    db_session: Session,
):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    wf = client.post(
        "/api/v1/workflows",
        json={"slug": "wf1", "human_name": "Workflow 1"},
    ).json()
    resp = client.put(
        f"/api/v1/workflows/{wf['id']}/toggles/checks.F-22",
        json={"value": "error"},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "workflow_id": wf["id"],
        "toggle_id": "checks.F-22",
        "value": "error",
    }
    rows = (
        db_session.query(ToggleOverride)
        .filter(
            ToggleOverride.toggle_id == "checks.F-22",
            ToggleOverride.scope == ToggleScope.WORKFLOW,
            ToggleOverride.scope_id == wf["id"],
        )
        .all()
    )
    assert len(rows) == 1
    assert rows[0].value == "error"


def test_set_workflow_override_404_on_unknown_toggle(client: TestClient):
    wf = client.post(
        "/api/v1/workflows",
        json={"slug": "wf1", "human_name": "Workflow 1"},
    ).json()
    resp = client.put(
        f"/api/v1/workflows/{wf['id']}/toggles/checks.GHOST",
        json={"value": "error"},
    )
    assert resp.status_code == 404


def test_set_workflow_override_rejects_non_workflow_scope(
    client: TestClient,
    db_session: Session,
):
    _seed_toggle(
        db_session,
        toggle_id="checks.F-22",
        override_at=[ToggleScope.TENANT],  # WORKFLOW excluded
    )
    wf = client.post(
        "/api/v1/workflows",
        json={"slug": "wf1", "human_name": "Workflow 1"},
    ).json()
    resp = client.put(
        f"/api/v1/workflows/{wf['id']}/toggles/checks.F-22",
        json={"value": "error"},
    )
    assert resp.status_code == 400
    assert "WORKFLOW" in resp.json()["detail"]


def test_set_workflow_override_bumps_server_revision(
    client: TestClient,
    db_session: Session,
):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    wf = client.post(
        "/api/v1/workflows",
        json={"slug": "wf1", "human_name": "Workflow 1"},
    ).json()
    initial_rev = wf["server_revision"]
    client.put(
        f"/api/v1/workflows/{wf['id']}/toggles/checks.F-22",
        json={"value": "error"},
    )
    db_session.expire_all()
    row = db_session.get(Workflow, wf["id"])
    assert row is not None
    assert row.server_revision == initial_rev + 1


def test_list_workflow_overrides_returns_set_values(
    client: TestClient,
    db_session: Session,
):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    _seed_toggle(db_session, toggle_id="checks.F-23")
    wf = client.post(
        "/api/v1/workflows",
        json={"slug": "wf1", "human_name": "Workflow 1"},
    ).json()
    client.put(
        f"/api/v1/workflows/{wf['id']}/toggles/checks.F-22",
        json={"value": "error"},
    )
    client.put(
        f"/api/v1/workflows/{wf['id']}/toggles/checks.F-23",
        json={"value": "advisory"},
    )
    resp = client.get(f"/api/v1/workflows/{wf['id']}/toggles")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    found = {item["toggle_id"]: item["value"] for item in body["items"]}
    assert found == {"checks.F-22": "error", "checks.F-23": "advisory"}


def test_delete_workflow_override(client: TestClient, db_session: Session):
    _seed_toggle(db_session, toggle_id="checks.F-22")
    wf = client.post(
        "/api/v1/workflows",
        json={"slug": "wf1", "human_name": "Workflow 1"},
    ).json()
    client.put(
        f"/api/v1/workflows/{wf['id']}/toggles/checks.F-22",
        json={"value": "error"},
    )
    resp = client.delete(f"/api/v1/workflows/{wf['id']}/toggles/checks.F-22")
    assert resp.status_code == 204
    rows = db_session.query(ToggleOverride).filter(ToggleOverride.toggle_id == "checks.F-22").all()
    assert rows == []


def test_workflow_override_resolve_overrides_tenant_value(
    client: TestClient,
    db_session: Session,
):
    """End-to-end: workflow scope wins over tenant scope at resolve time."""
    _seed_toggle(db_session, toggle_id="checks.F-22", default="default")
    wf = client.post(
        "/api/v1/workflows",
        json={"slug": "wf1", "human_name": "Workflow 1"},
    ).json()
    # Tenant says "warn"
    client.put("/api/v1/tenant/toggles/checks.F-22", json={"value": "warn"})
    # Workflow says "error"
    client.put(
        f"/api/v1/workflows/{wf['id']}/toggles/checks.F-22",
        json={"value": "error"},
    )

    # Resolve without workflow_id → tenant value
    resp1 = client.get("/api/v1/toggles/resolve?toggle_id=checks.F-22")
    assert resp1.json()["value"] == "warn"

    # Resolve WITH workflow_id → workflow value wins
    resp2 = client.get(f"/api/v1/toggles/resolve?toggle_id=checks.F-22&workflow_id={wf['id']}")
    assert resp2.json()["value"] == "error"


def test_locked_tenant_override_short_circuits_workflow(
    client: TestClient,
    db_session: Session,
):
    """Locked tenant override cannot be overridden by workflow scope."""
    _seed_toggle(
        db_session,
        toggle_id="checks.F-22",
        default="default",
        lockable=True,
    )
    wf = client.post(
        "/api/v1/workflows",
        json={"slug": "wf1", "human_name": "Workflow 1"},
    ).json()
    # Tenant locks at "warn"
    client.put(
        "/api/v1/tenant/toggles/checks.F-22",
        json={"value": "warn", "locked": True},
    )
    # Workflow tries to escalate
    client.put(
        f"/api/v1/workflows/{wf['id']}/toggles/checks.F-22",
        json={"value": "error"},
    )
    # Resolver short-circuits to the locked tenant value
    resp = client.get(f"/api/v1/toggles/resolve?toggle_id=checks.F-22&workflow_id={wf['id']}")
    assert resp.json()["value"] == "warn"
    assert resp.json()["locked"] is True
