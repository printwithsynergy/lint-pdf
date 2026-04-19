"""Cloudflare DNS client for the branded-alias layer.

Used by ``probe_pending_custom_domains`` to provision LintPDF-branded
CNAME records in the ``lintpdf.com`` zone so customers never see
Railway-generated hostnames (``9m9a8ps4.up.railway.app``) in their DNS
records. Instead they CNAME to ``{tenant-slug}-reports.custom.lintpdf.com``
and we CNAME that to the Railway target in turn.

Token resolution mirrors ``railway.py``: reads ``CLOUDFLARE_API_TOKEN``
(scoped, ``Zone:DNS:Write`` on ``lintpdf.com``). Zone ID read from
``CLOUDFLARE_ZONE_ID_LINTPDF`` or auto-discovered on first call via
``GET /zones?name=lintpdf.com``.

If the token is absent or invalid, the client stays "disabled" and
every operation returns ``status="disabled"`` so the probe task falls
back to returning the raw Railway target (existing behavior, no hard
failure).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"


@dataclass(frozen=True)
class CloudflareRecordResult:
    """Outcome of attempting to create / update / delete a CNAME record."""

    status: str
    """One of: 'created', 'updated', 'already_correct', 'deleted',
    'not_found', 'disabled', 'unauthorized', 'error'."""
    message: str | None = None
    record_id: str | None = None
    """The Cloudflare DNS record ID — useful for callers that want to
    delete by ID later without a lookup round-trip."""


class CloudflareClient:
    """Thin client for the minimum Cloudflare DNS operations we need.

    Deliberately NOT a general-purpose Cloudflare SDK — only exposes
    the CNAME CRUD the probe task uses. Keeping the surface small
    keeps the blast radius of a leaked scoped token small.
    """

    def __init__(
        self,
        token: str | None = None,
        zone_id: str | None = None,
        zone_name: str = "lintpdf.com",
        *,
        timeout: float = 10.0,
    ) -> None:
        self.token = token or os.environ.get("CLOUDFLARE_API_TOKEN") or ""
        self.zone_id = zone_id or os.environ.get("CLOUDFLARE_ZONE_ID_LINTPDF") or ""
        self.zone_name = zone_name
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    @property
    def enabled(self) -> bool:
        """Client is enabled iff a token is set. Zone ID is lazy-resolved."""
        return bool(self.token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _ensure_zone_id(self) -> str | None:
        """Resolve the zone ID from the zone name on first call, cache it.

        Returns None if the lookup fails — the caller should treat that
        as a disabled state (same as missing token).
        """
        if self.zone_id:
            return self.zone_id
        try:
            resp = self._client.get(
                f"{CLOUDFLARE_API_BASE}/zones",
                params={"name": self.zone_name},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Cloudflare zone lookup failed for %s: %s", self.zone_name, exc)
            return None
        if not data.get("success"):
            logger.warning(
                "Cloudflare zone lookup rejected for %s: %s",
                self.zone_name,
                data.get("errors"),
            )
            return None
        result = data.get("result") or []
        if not result:
            logger.warning("Cloudflare returned no zones matching %s", self.zone_name)
            return None
        self.zone_id = result[0]["id"]
        return self.zone_id

    def _find_record(self, fqdn: str) -> dict | None:
        """Return the existing DNS record for ``fqdn`` in our zone, or None."""
        zone_id = self._ensure_zone_id()
        if not zone_id:
            return None
        resp = self._client.get(
            f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records",
            params={"name": fqdn, "type": "CNAME"},
            headers=self._headers(),
        )
        resp.raise_for_status()
        records = resp.json().get("result") or []
        return records[0] if records else None

    def upsert_cname(
        self,
        fqdn: str,
        target: str,
        ttl: int = 300,
    ) -> CloudflareRecordResult:
        """Create or update a CNAME ``fqdn`` → ``target`` in our zone.

        If a matching record already exists with the exact target, no
        write is performed -- returns ``status='already_correct'``.
        If target differs, PUTs the update. If no record exists, POSTs
        a new one.

        Cloudflare normalises trailing dots; we strip them here so the
        ``already_correct`` equality check doesn't spuriously miss.
        """
        if not self.enabled:
            return CloudflareRecordResult(
                status="disabled",
                message="CLOUDFLARE_API_TOKEN not set — alias provisioning skipped",
            )

        target_normalized = target.rstrip(".").lower()

        try:
            existing = self._find_record(fqdn)
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code in (401, 403):
                return CloudflareRecordResult(
                    status="unauthorized",
                    message=(
                        "Cloudflare rejected the API token (HTTP "
                        f"{code}) — ops must issue a new scoped token"
                    ),
                )
            logger.warning("Cloudflare HTTP error for %s: %s", fqdn, code)
            return CloudflareRecordResult(status="error", message=f"Cloudflare HTTP {code}")
        except httpx.HTTPError as exc:
            logger.warning("Cloudflare transport error for %s: %s", fqdn, exc)
            return CloudflareRecordResult(status="error", message=str(exc))

        zone_id = self.zone_id  # populated by _ensure_zone_id in _find_record

        if existing is not None:
            current = (existing.get("content") or "").rstrip(".").lower()
            if current == target_normalized:
                return CloudflareRecordResult(
                    status="already_correct",
                    message=f"CNAME {fqdn} -> {target} already set",
                    record_id=existing.get("id"),
                )
            try:
                resp = self._client.put(
                    f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records/{existing['id']}",
                    headers=self._headers(),
                    json={
                        "type": "CNAME",
                        "name": fqdn,
                        "content": target,
                        "ttl": ttl,
                        "proxied": False,
                    },
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                return CloudflareRecordResult(status="error", message=str(exc))
            return CloudflareRecordResult(
                status="updated",
                message=f"CNAME {fqdn} retargeted to {target}",
                record_id=existing.get("id"),
            )

        # Create new
        try:
            resp = self._client.post(
                f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records",
                headers=self._headers(),
                json={
                    "type": "CNAME",
                    "name": fqdn,
                    "content": target,
                    "ttl": ttl,
                    "proxied": False,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            body = exc.response.text[:200]
            return CloudflareRecordResult(status="error", message=f"HTTP {code}: {body}")
        except httpx.HTTPError as exc:
            return CloudflareRecordResult(status="error", message=str(exc))

        result = resp.json().get("result") or {}
        return CloudflareRecordResult(
            status="created",
            message=f"CNAME {fqdn} -> {target}",
            record_id=result.get("id"),
        )

    def delete_cname(self, fqdn: str) -> CloudflareRecordResult:
        """Remove the CNAME record for ``fqdn`` in our zone.

        Called when a tenant clears their custom domain -- we don't
        want orphan aliases in the zone. Idempotent: returns
        ``status='not_found'`` if the record was already gone.
        """
        if not self.enabled:
            return CloudflareRecordResult(
                status="disabled",
                message="CLOUDFLARE_API_TOKEN not set — alias cleanup skipped",
            )

        try:
            existing = self._find_record(fqdn)
        except httpx.HTTPError as exc:
            return CloudflareRecordResult(status="error", message=str(exc))

        if existing is None:
            return CloudflareRecordResult(
                status="not_found",
                message=f"No CNAME {fqdn} in zone",
            )

        try:
            resp = self._client.delete(
                f"{CLOUDFLARE_API_BASE}/zones/{self.zone_id}/dns_records/{existing['id']}",
                headers=self._headers(),
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            return CloudflareRecordResult(status="error", message=str(exc))

        return CloudflareRecordResult(
            status="deleted",
            message=f"CNAME {fqdn} removed",
            record_id=existing.get("id"),
        )
