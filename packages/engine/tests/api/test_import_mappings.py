"""Tests for the tenant import-mappings CRUD + preview endpoints."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from lintpdf.api.models import Tenant, TenantImportMapping

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

from tests.api.conftest import PLACEHOLDER_TENANT_ID

BASE = "/api/v1/tenant/import-mappings"


_SAMPLE_XML = (
    '<?xml version="1.0"?>'
    "<PreflightLog><Issues>"
    '<Issue level="HIGH" page="2" ruleId="IMG_DPI">'
    "<Description>Image below 300 dpi</Description>"
    "</Issue>"
    '<Issue level="LOW" page="1"><Description>Font not embedded</Description></Issue>'
    "</Issues></PreflightLog>"
)

_SAMPLE_JSON = (
    '{"results":[{"issues":[{"sev":"blocker","text":"Bleed box missing","loc":{"page":2}}]}]}'
)


def _xml_payload() -> dict:
    return {
        "name": "Acme PitStop-lite",
        "description": "In-house XML preflight",
        "format": "xml",
        "config": {
            "format": "xml",
            "item_selector": "Issues/Issue",
            "fields": {
                "severity": {"selector": "@level"},
                "message": {"selector": "Description"},
                "page": {"selector": "@page"},
                "check_id": {"selector": "@ruleId"},
            },
            "severity_map": {"high": "error", "low": "advisory"},
        },
        "sample_payload": _SAMPLE_XML,
        "sample_mime": "application/xml",
        "is_active": True,
    }


def _json_payload() -> dict:
    return {
        "name": "Acme callas-lite",
        "description": "Proprietary JSON preflight",
        "format": "json",
        "config": {
            "format": "json",
            "item_selector": "results[*].issues[*]",
            "fields": {
                "severity": "sev",
                "message": "text",
                "page": "loc.page",
            },
            "severity_map": {"blocker": "error"},
        },
        "sample_payload": _SAMPLE_JSON,
        "sample_mime": "application/json",
        "is_active": True,
    }


# ----------------------------------------------------------------------
# Create / list / get
# ----------------------------------------------------------------------


class TestCreate:
    @staticmethod
    def test_create_xml_mapping_round_trips(client: TestClient, db_session: Session) -> None:
        resp = client.post(BASE, json=_xml_payload())
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == "Acme PitStop-lite"
        assert body["format"] == "xml"
        assert body["is_active"] is True
        assert body["config"]["item_selector"] == "Issues/Issue"
        assert uuid.UUID(body["id"])

        row = (
            db_session.query(TenantImportMapping)
            .filter(TenantImportMapping.id == uuid.UUID(body["id"]))
            .first()
        )
        assert row is not None
        assert row.tenant_id == PLACEHOLDER_TENANT_ID

    @staticmethod
    def test_create_rejects_bad_config(client: TestClient) -> None:
        bad = _xml_payload()
        bad["config"] = {"format": "xml"}  # missing item_selector
        resp = client.post(BASE, json=bad)
        assert resp.status_code == 422
        assert "item_selector" in resp.json()["detail"]

    @staticmethod
    def test_create_defaults_config_format_from_top_level(
        client: TestClient,
    ) -> None:
        payload = _json_payload()
        # Strip format from the nested config — the route should fill it.
        payload["config"].pop("format", None)
        resp = client.post(BASE, json=payload)
        assert resp.status_code == 201, resp.text
        assert resp.json()["config"]["format"] == "json"


class TestList:
    @staticmethod
    def test_list_returns_tenant_mappings_only(client: TestClient, db_session: Session) -> None:
        # Tenant's own mapping.
        client.post(BASE, json=_xml_payload())

        # Foreign mapping — directly inserted, different tenant.
        foreign_tenant_id = uuid.uuid4()
        foreign_tenant = Tenant(
            id=foreign_tenant_id,
            name="Other",
            api_key_hash="foreign-hash",
        )
        db_session.add(foreign_tenant)
        db_session.add(
            TenantImportMapping(
                id=uuid.uuid4(),
                tenant_id=foreign_tenant_id,
                name="Foreign",
                format="xml",
                config={"format": "xml", "item_selector": "x", "fields": {"message": "m"}},
            )
        )
        db_session.commit()

        resp = client.get(BASE)
        assert resp.status_code == 200
        names = [m["name"] for m in resp.json()["mappings"]]
        assert names == ["Acme PitStop-lite"]


class TestGet:
    @staticmethod
    def test_get_returns_mapping(client: TestClient) -> None:
        created = client.post(BASE, json=_xml_payload()).json()
        resp = client.get(f"{BASE}/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    @staticmethod
    def test_get_bad_uuid_is_422(client: TestClient) -> None:
        resp = client.get(f"{BASE}/not-a-uuid")
        assert resp.status_code == 422

    @staticmethod
    def test_get_unknown_is_404(client: TestClient) -> None:
        resp = client.get(f"{BASE}/{uuid.uuid4()}")
        assert resp.status_code == 404


# ----------------------------------------------------------------------
# Update / delete
# ----------------------------------------------------------------------


class TestUpdate:
    @staticmethod
    def test_put_updates_name_and_config(client: TestClient) -> None:
        created = client.post(BASE, json=_xml_payload()).json()
        upd = _xml_payload()
        upd["name"] = "Renamed"
        upd["config"]["severity_map"]["high"] = "warning"
        resp = client.put(f"{BASE}/{created['id']}", json=upd)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["name"] == "Renamed"
        assert body["config"]["severity_map"]["high"] == "warning"

    @staticmethod
    def test_put_bad_config_is_422(client: TestClient) -> None:
        created = client.post(BASE, json=_xml_payload()).json()
        upd = _xml_payload()
        upd["config"]["format"] = "yaml"
        resp = client.put(f"{BASE}/{created['id']}", json=upd)
        assert resp.status_code == 422


class TestDelete:
    @staticmethod
    def test_delete_soft_deletes(client: TestClient, db_session: Session) -> None:
        created = client.post(BASE, json=_xml_payload()).json()
        resp = client.delete(f"{BASE}/{created['id']}")
        assert resp.status_code == 204

        db_session.expire_all()
        row = (
            db_session.query(TenantImportMapping)
            .filter(TenantImportMapping.id == uuid.UUID(created["id"]))
            .first()
        )
        assert row is not None
        assert row.is_active is False


# ----------------------------------------------------------------------
# Preview
# ----------------------------------------------------------------------


class TestPreview:
    @staticmethod
    def test_preview_with_saved_payload(client: TestClient) -> None:
        created = client.post(BASE, json=_xml_payload()).json()
        resp = client.post(f"{BASE}/{created['id']}/preview", json={})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["findings_count"] == 2
        assert len(body["sample_findings"]) == 2
        first = body["sample_findings"][0]
        assert first["severity"] == "error"
        assert "300 dpi" in first["message"]

    @staticmethod
    def test_preview_with_override_payload_and_config(client: TestClient) -> None:
        created = client.post(BASE, json=_xml_payload()).json()
        override = {
            "config": _xml_payload()["config"],
            "sample_payload": (
                "<PreflightLog><Issues>"
                '<Issue level="HIGH"><Description>Only one</Description></Issue>'
                "</Issues></PreflightLog>"
            ),
        }
        resp = client.post(f"{BASE}/{created['id']}/preview", json=override)
        assert resp.status_code == 200
        assert resp.json()["findings_count"] == 1

    @staticmethod
    def test_preview_without_payload_returns_error(client: TestClient) -> None:
        payload = _xml_payload()
        payload["sample_payload"] = None
        created = client.post(BASE, json=payload).json()
        resp = client.post(f"{BASE}/{created['id']}/preview", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert "sample payload" in body["error"].lower()

    @staticmethod
    def test_preview_bad_payload_returns_error(client: TestClient) -> None:
        created = client.post(BASE, json=_xml_payload()).json()
        resp = client.post(
            f"{BASE}/{created['id']}/preview",
            json={"sample_payload": "<not-closed>"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["error"]

    @staticmethod
    def test_preview_json_mapping(client: TestClient) -> None:
        created = client.post(BASE, json=_json_payload()).json()
        resp = client.post(f"{BASE}/{created['id']}/preview", json={})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["findings_count"] == 1
        assert body["sample_findings"][0]["message"] == "Bleed box missing"
