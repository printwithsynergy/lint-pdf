"""Unit tests for the Railway GraphQL client used by the DNS probe task."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx

from lintpdf.integrations.railway import RailwayClient, RailwayDomainResult


def _make_client(**env: str) -> RailwayClient:
    return RailwayClient(
        token=env.get("token", "test-token"),
        project_id=env.get("project_id", "proj-1"),
        environment_id=env.get("environment_id", "env-1"),
        service_id=env.get("service_id", "svc-1"),
    )


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._json = json_body or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("POST", "https://backboard.railway.app/graphql/v2"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict[str, Any]:
        return self._json


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def post(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> _FakeResponse:
        return self._response


def _patch_httpx(response: _FakeResponse) -> Any:
    return patch("httpx.Client", lambda timeout: _FakeClient(response))


class TestEnabled:
    @staticmethod
    def test_enabled_with_all_config() -> None:
        client = _make_client()
        assert client.enabled is True

    @staticmethod
    def test_disabled_when_token_missing() -> None:
        client = _make_client(token="")
        assert client.enabled is False

    @staticmethod
    def test_disabled_when_service_id_missing() -> None:
        client = _make_client(service_id="")
        assert client.enabled is False


class TestAddCustomDomain:
    @staticmethod
    def test_disabled_returns_disabled_result() -> None:
        client = _make_client(token="")
        result = client.add_custom_domain("reports.acme.example")
        assert isinstance(result, RailwayDomainResult)
        assert result.status == "disabled"

    @staticmethod
    def test_successful_create() -> None:
        # New Railway schema: ``status`` is a CustomDomainStatus object,
        # not a scalar. Matches the actual mutation shape post-Envoy.
        response = _FakeResponse(
            200,
            {
                "data": {
                    "customDomainCreate": {
                        "id": "cd-1",
                        "domain": "reports.acme.example",
                        "status": {
                            "verified": False,
                            "certificateStatus": "CERTIFICATE_STATUS_TYPE_VALIDATING_OWNERSHIP",
                            "dnsRecords": [
                                {
                                    "hostlabel": "reports",
                                    "recordType": "DNS_RECORD_TYPE_CNAME",
                                    "requiredValue": "xyz123.up.railway.app",
                                    "purpose": "DNS_RECORD_PURPOSE_TRAFFIC_ROUTE",
                                }
                            ],
                        },
                    }
                }
            },
        )
        with _patch_httpx(response):
            result = _make_client().add_custom_domain("reports.acme.example")
        assert result.status == "created"
        # The per-domain target is threaded back for the admin UI.
        assert result.required_cname == "xyz123.up.railway.app"

    @staticmethod
    def test_txt_ownership_record_surfaced_in_message() -> None:
        """Future-proofing: if Railway ever returns a TXT ownership record,
        the probe's WARNING log should include it so ops can update DNS.
        Today (post-Envoy) only CNAME is returned; this locks in that
        we don't silently drop non-CNAME records."""
        response = _FakeResponse(
            200,
            {
                "data": {
                    "customDomainCreate": {
                        "id": "cd-1",
                        "domain": "reports.acme.example",
                        "status": {
                            "verified": False,
                            "certificateStatus": "CERTIFICATE_STATUS_TYPE_VALIDATING_OWNERSHIP",
                            "dnsRecords": [
                                {
                                    "hostlabel": "reports",
                                    "recordType": "DNS_RECORD_TYPE_CNAME",
                                    "requiredValue": "xyz123.up.railway.app",
                                    "purpose": "DNS_RECORD_PURPOSE_TRAFFIC_ROUTE",
                                    "fqdn": "reports.acme.example",
                                },
                                {
                                    "hostlabel": "_acme-challenge.reports",
                                    "recordType": "DNS_RECORD_TYPE_TXT",
                                    "requiredValue": "deadbeef-ownership-token",
                                    "purpose": "DNS_RECORD_PURPOSE_OWNERSHIP_VERIFICATION",
                                    "fqdn": "_acme-challenge.reports.acme.example",
                                },
                            ],
                        },
                    }
                }
            },
        )
        with _patch_httpx(response):
            result = _make_client().add_custom_domain("reports.acme.example")
        assert result.status == "created"
        assert result.required_cname == "xyz123.up.railway.app"
        assert "TXT _acme-challenge.reports.acme.example = deadbeef-ownership-token" in (
            result.message or ""
        )

    @staticmethod
    def test_already_exists_detected_from_graphql_error() -> None:
        response = _FakeResponse(
            200,
            {"errors": [{"message": "Custom domain already exists on this service"}]},
        )
        with _patch_httpx(response):
            result = _make_client().add_custom_domain("reports.acme.example")
        assert result.status == "already_exists"

    @staticmethod
    def test_unauthorized_from_http_401() -> None:
        response = _FakeResponse(401)
        with _patch_httpx(response):
            result = _make_client().add_custom_domain("reports.acme.example")
        assert result.status == "unauthorized"

    @staticmethod
    def test_unauthorized_from_http_403() -> None:
        response = _FakeResponse(403)
        with _patch_httpx(response):
            result = _make_client().add_custom_domain("reports.acme.example")
        assert result.status == "unauthorized"

    @staticmethod
    def test_unauthorized_from_graphql_permission_error() -> None:
        response = _FakeResponse(
            200,
            {"errors": [{"message": "Unauthorized: missing permission for custom_domains"}]},
        )
        with _patch_httpx(response):
            result = _make_client().add_custom_domain("reports.acme.example")
        assert result.status == "unauthorized"

    @staticmethod
    def test_generic_graphql_error_becomes_error() -> None:
        response = _FakeResponse(200, {"errors": [{"message": "something broke"}]})
        with _patch_httpx(response):
            result = _make_client().add_custom_domain("reports.acme.example")
        assert result.status == "error"

    @staticmethod
    def test_http_500_becomes_error() -> None:
        response = _FakeResponse(500)
        with _patch_httpx(response):
            result = _make_client().add_custom_domain("reports.acme.example")
        assert result.status == "error"
