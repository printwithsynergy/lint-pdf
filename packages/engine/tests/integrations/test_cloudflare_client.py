"""Unit tests for the Cloudflare DNS client used by the branded-alias layer."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from lintpdf.integrations.cloudflare import (
    CLOUDFLARE_API_BASE,
    CloudflareClient,
    CloudflareRecordResult,
)


def _make_client(
    token: str = "cf-test-token",
    zone_id: str = "zone-abc",
) -> CloudflareClient:
    return CloudflareClient(token=token, zone_id=zone_id)


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        json_body: dict[str, Any] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._json = json_body or {}
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("GET", "https://api.cloudflare.com/client/v4/"),
                response=httpx.Response(self.status_code, text=self.text),
            )

    def json(self) -> dict[str, Any]:
        return self._json


class TestDisabledFallback:
    """When the token is missing, every call should return disabled without network I/O."""

    @staticmethod
    def test_no_token_upsert_returns_disabled() -> None:
        client = CloudflareClient(token="", zone_id="z")
        with patch.object(client, "_client") as mock_http:
            result = client.upsert_cname("foo.custom.lintpdf.com", "target.example")
        assert result.status == "disabled"
        assert not mock_http.get.called
        assert not mock_http.post.called

    @staticmethod
    def test_no_token_delete_returns_disabled() -> None:
        client = CloudflareClient(token="", zone_id="z")
        with patch.object(client, "_client") as mock_http:
            result = client.delete_cname("foo.custom.lintpdf.com")
        assert result.status == "disabled"
        assert not mock_http.delete.called


class TestUpsertCname:
    """Creating / updating a CNAME. Happy paths + edge cases."""

    @staticmethod
    def test_creates_when_no_existing_record() -> None:
        client = _make_client()
        # _find_record => empty; then POST succeeds
        find_resp = _FakeResponse(200, {"success": True, "result": []})
        create_resp = _FakeResponse(
            200,
            {"success": True, "result": {"id": "rec-new", "name": "foo.custom.lintpdf.com"}},
        )
        with patch.object(client._client, "get", return_value=find_resp) as mock_get, patch.object(
            client._client, "post", return_value=create_resp
        ) as mock_post:
            result = client.upsert_cname("foo.custom.lintpdf.com", "9m9a8ps4.up.railway.app")
        assert result.status == "created"
        assert result.record_id == "rec-new"
        assert mock_get.call_count == 1
        assert mock_post.call_count == 1
        # POST body carries the right CNAME shape
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["type"] == "CNAME"
        assert kwargs["json"]["content"] == "9m9a8ps4.up.railway.app"
        assert kwargs["json"]["proxied"] is False

    @staticmethod
    def test_already_correct_short_circuits_no_write() -> None:
        """Don't spam CF with PUTs when the record is already in the desired state."""
        client = _make_client()
        find_resp = _FakeResponse(
            200,
            {
                "success": True,
                "result": [
                    {
                        "id": "rec-1",
                        "name": "foo.custom.lintpdf.com",
                        "type": "CNAME",
                        "content": "9m9a8ps4.up.railway.app",
                    }
                ],
            },
        )
        with patch.object(client._client, "get", return_value=find_resp), patch.object(
            client._client, "post"
        ) as mock_post, patch.object(client._client, "put") as mock_put:
            result = client.upsert_cname("foo.custom.lintpdf.com", "9m9a8ps4.up.railway.app")
        assert result.status == "already_correct"
        assert not mock_post.called
        assert not mock_put.called

    @staticmethod
    def test_already_correct_ignores_trailing_dots() -> None:
        """CF sometimes returns content with a trailing dot -- don't rewrite over a cosmetic diff."""
        client = _make_client()
        find_resp = _FakeResponse(
            200,
            {
                "success": True,
                "result": [
                    {
                        "id": "rec-1",
                        "content": "9m9a8ps4.up.railway.app.",
                    }
                ],
            },
        )
        with patch.object(client._client, "get", return_value=find_resp), patch.object(
            client._client, "put"
        ) as mock_put:
            result = client.upsert_cname("foo.custom.lintpdf.com", "9m9a8ps4.up.railway.app")
        assert result.status == "already_correct"
        assert not mock_put.called

    @staticmethod
    def test_updates_when_target_differs() -> None:
        """Existing record with a different target — PUT the correction."""
        client = _make_client()
        find_resp = _FakeResponse(
            200,
            {
                "success": True,
                "result": [
                    {"id": "rec-1", "content": "old-target.up.railway.app"},
                ],
            },
        )
        put_resp = _FakeResponse(200, {"success": True})
        with patch.object(client._client, "get", return_value=find_resp), patch.object(
            client._client, "put", return_value=put_resp
        ) as mock_put:
            result = client.upsert_cname("foo.custom.lintpdf.com", "new-target.up.railway.app")
        assert result.status == "updated"
        assert result.record_id == "rec-1"
        assert mock_put.call_count == 1
        _, kwargs = mock_put.call_args
        assert kwargs["json"]["content"] == "new-target.up.railway.app"

    @staticmethod
    def test_unauthorized_token_returns_explicit_status() -> None:
        """401/403 on the find call surfaces as ``unauthorized`` so ops know to rotate the token."""
        client = _make_client()
        find_resp = _FakeResponse(403, text="forbidden")
        with patch.object(client._client, "get", return_value=find_resp):
            result = client.upsert_cname("foo.custom.lintpdf.com", "target.example")
        assert result.status == "unauthorized"

    @staticmethod
    def test_transport_error_returns_error() -> None:
        """Network errors shouldn't crash the probe task -- just surface as error."""
        client = _make_client()
        with patch.object(
            client._client,
            "get",
            side_effect=httpx.ConnectError("dns down"),
        ):
            result = client.upsert_cname("foo.custom.lintpdf.com", "target.example")
        assert result.status == "error"
        assert "dns down" in (result.message or "")


class TestDeleteCname:
    @staticmethod
    def test_deletes_existing() -> None:
        client = _make_client()
        find_resp = _FakeResponse(
            200,
            {"success": True, "result": [{"id": "rec-1", "content": "x.example"}]},
        )
        del_resp = _FakeResponse(200, {"success": True})
        with patch.object(client._client, "get", return_value=find_resp), patch.object(
            client._client, "delete", return_value=del_resp
        ) as mock_del:
            result = client.delete_cname("foo.custom.lintpdf.com")
        assert result.status == "deleted"
        assert result.record_id == "rec-1"
        assert mock_del.call_count == 1

    @staticmethod
    def test_not_found_returns_explicit_status() -> None:
        """Idempotent: deleting a record that's already gone is not an error."""
        client = _make_client()
        find_resp = _FakeResponse(200, {"success": True, "result": []})
        with patch.object(client._client, "get", return_value=find_resp), patch.object(
            client._client, "delete"
        ) as mock_del:
            result = client.delete_cname("foo.custom.lintpdf.com")
        assert result.status == "not_found"
        assert not mock_del.called


class TestZoneIdResolution:
    """Zone ID is lazy-resolved on first call if not explicitly passed."""

    @staticmethod
    def test_auto_discovers_zone_id_when_missing() -> None:
        client = CloudflareClient(token="tok", zone_id="", zone_name="lintpdf.com")
        zones_resp = _FakeResponse(
            200,
            {"success": True, "result": [{"id": "zone-auto-discovered"}]},
        )
        find_resp = _FakeResponse(200, {"success": True, "result": []})
        create_resp = _FakeResponse(
            200,
            {"success": True, "result": {"id": "rec-new"}},
        )
        # Two GETs expected: first for /zones?name=, second for dns_records
        with patch.object(
            client._client, "get", side_effect=[zones_resp, find_resp]
        ) as mock_get, patch.object(client._client, "post", return_value=create_resp):
            result = client.upsert_cname("foo.custom.lintpdf.com", "target.example")
        assert result.status == "created"
        assert client.zone_id == "zone-auto-discovered"
        # First call is the zone lookup
        first_call = mock_get.call_args_list[0]
        assert "/zones" in first_call.args[0]
        assert first_call.kwargs["params"] == {"name": "lintpdf.com"}
