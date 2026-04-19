"""Railway GraphQL client for white-label custom domain automation.

Used by the DNS verification probe task to register a customer's
CNAME as a Railway custom domain on the API service once DNS is live.
All calls go through the project-scoped token set in ``RAILWAY_API_TOKEN``;
if that token is unset, the client is disabled and the probe falls back
to the manual ops runbook (admin clicks "Mark Active" in the dashboard
after adding the domain by hand).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RAILWAY_GRAPHQL_URL = "https://backboard.railway.app/graphql/v2"


@dataclass(frozen=True)
class RailwayDomainResult:
    """Outcome of attempting to register a custom domain with Railway."""

    status: str
    """One of: 'created', 'already_exists', 'disabled', 'unauthorized', 'error'."""
    message: str | None = None
    required_cname: str | None = None
    """The unique Railway backend hostname the customer must CNAME to.

    Railway's new Envoy-based routing assigns a DIFFERENT target per
    custom domain (e.g. ``zaprv9d7.up.railway.app``), not the shared
    service hostname (``app.lintpdf.com`` / ``bwfl38nz.up.railway.app``).
    Returned from ``customDomainCreate.status.dnsRecords[0].requiredValue``
    so the admin UI can show the customer exactly what to CNAME to.

    None if the mutation didn't return a dnsRecords entry (e.g., already
    exists, error, or pre-Envoy Railway project)."""


class RailwayClient:
    """Thin client for the minimum Railway GraphQL operations we need.

    This is deliberately NOT a general-purpose Railway SDK — it only
    exposes the mutations the probe task uses. Keeping the surface
    area small keeps the blast radius of a leaked project token small.
    """

    def __init__(
        self,
        token: str | None = None,
        project_id: str | None = None,
        environment_id: str | None = None,
        service_id: str | None = None,
        *,
        timeout: float = 10.0,
    ) -> None:
        # Env vars are read at construction so tests can inject explicit
        # values and production reads from Railway-provided service env.
        self.token = token or os.environ.get("RAILWAY_API_TOKEN") or ""
        self.project_id = project_id or os.environ.get("RAILWAY_PROJECT_ID") or ""
        self.environment_id = environment_id or os.environ.get("RAILWAY_ENVIRONMENT_ID") or ""
        self.service_id = service_id or os.environ.get("RAILWAY_API_SERVICE_ID") or ""
        self.app_service_id = os.environ.get("RAILWAY_APP_SERVICE_ID") or ""
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        """True when all required config is present.

        When False, ``add_custom_domain`` short-circuits to a 'disabled'
        result and the probe task falls through to the manual ops path.
        """
        return bool(self.token and self.project_id and self.environment_id and self.service_id)

    def _post(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Project-Access-Token": self.token,
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                RAILWAY_GRAPHQL_URL,
                headers=headers,
                json={"query": query, "variables": variables},
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            return payload

    def add_custom_domain(
        self, domain: str, *, service_id: str | None = None
    ) -> RailwayDomainResult:
        """Register a custom domain on the configured service.

        Args:
            domain: Customer's hostname to register.
            service_id: Override the default API service ID (e.g., pass
                ``self.app_service_id`` for viewer/app domains).

        Returns a :class:`RailwayDomainResult` describing the outcome.
        """
        if not self.enabled:
            return RailwayDomainResult(
                status="disabled",
                message="Railway client not configured (missing env vars)",
            )

        # Railway's ``customDomainCreate`` used to return ``status`` as a
        # scalar enum. It's now a ``CustomDomainStatus!`` complex type —
        # selecting it as a scalar gets rejected by their GraphQL
        # validator with a 400. We only care about whether Railway
        # accepted the registration at this stage (the verified flag is
        # driven by DNS + TLS issuance in the background), so select a
        # minimal subfield set. ``dnsRecords`` / ``verificationToken`` are
        # available for richer diagnostics in a future patch.
        # ``dnsRecords[].requiredValue`` is the per-domain unique Railway
        # backend hostname the customer must CNAME to (e.g.
        # ``zaprv9d7.up.railway.app``, NOT the shared ``app.lintpdf.com``
        # hostname). Railway's new Envoy-based routing needs each custom
        # domain to point at its own generated target -- CNAMEing to the
        # shared service hostname leaves the cert stuck in
        # ``VALIDATING_OWNERSHIP`` forever. We thread this value back to
        # the caller so the admin UI can show the customer exactly what
        # to CNAME to, instead of the stale "reports.lintpdf.com" /
        # "app.lintpdf.com" targets in the old docs.
        query = """
        mutation CustomDomainCreate($input: CustomDomainCreateInput!) {
          customDomainCreate(input: $input) {
            id
            domain
            status {
              verified
              certificateStatus
              dnsRecords {
                hostlabel
                recordType
                requiredValue
                purpose
              }
            }
          }
        }
        """
        variables = {
            "input": {
                "projectId": self.project_id,
                "environmentId": self.environment_id,
                "serviceId": service_id or self.service_id,
                "domain": domain,
                "targetPort": 443,
            }
        }

        try:
            payload = self._post(query, variables)
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code in (401, 403):
                return RailwayDomainResult(
                    status="unauthorized",
                    message=(
                        "Railway project token lacks permission to create "
                        "custom domains — admin must add the domain manually."
                    ),
                )
            logger.warning("Railway HTTP error for domain %s: %s", domain, code)
            return RailwayDomainResult(
                status="error",
                message=f"Railway HTTP {code}",
            )
        except httpx.HTTPError as exc:
            logger.warning("Railway transport error for domain %s: %s", domain, exc)
            return RailwayDomainResult(status="error", message=str(exc))

        errors = payload.get("errors") or []
        if errors:
            first = errors[0]
            msg = first.get("message", "").lower()
            # Railway returns a generic error when the domain already
            # exists; treat that as success for our probe.
            if "already" in msg and "exist" in msg:
                return RailwayDomainResult(
                    status="already_exists",
                    message=first.get("message"),
                )
            if "unauthorized" in msg or "permission" in msg:
                return RailwayDomainResult(
                    status="unauthorized",
                    message=first.get("message"),
                )
            logger.warning("Railway GraphQL error for domain %s: %s", domain, first.get("message"))
            return RailwayDomainResult(status="error", message=first.get("message"))

        data = (payload.get("data") or {}).get("customDomainCreate") or {}
        if not data:
            return RailwayDomainResult(status="error", message="Empty response from Railway")

        # ``status`` used to be a scalar enum we surfaced as the message;
        # it's now a dict of verified + certificateStatus + dnsRecords so
        # pull out the bits we care about.
        st = data.get("status") or {}
        message = f"verified={st.get('verified')}  cert={st.get('certificateStatus')}"

        # Partition the returned DNS records by type. Today Railway's new
        # Envoy-based flow returns exactly one CNAME (TRAFFIC_ROUTE) per
        # domain and no TXT — the LE ownership challenge is TLS-ALPN-01
        # via the custom-hostname listener, so no ownership TXT is
        # needed. Legacy ``_railway-verify.*`` TXT records on older
        # Railway projects were from a pre-ACME ownership token flow
        # that's no longer used for new domains. BUT: if Railway ever
        # adds a required TXT back (verification, DMARC-style ownership,
        # etc.), we don't want to silently miss it. Capture ALL records
        # with a non-empty ``requiredValue`` so probe logs surface them
        # for any customer that hasn't satisfied one.
        required_cname: str | None = None
        extra_required: list[str] = []  # "TXT _acme-challenge.foo = bar"
        for rec in st.get("dnsRecords") or []:
            req = rec.get("requiredValue")
            if not req:
                continue
            rtype = (rec.get("recordType") or "").replace("DNS_RECORD_TYPE_", "")
            purpose = (rec.get("purpose") or "").replace("DNS_RECORD_PURPOSE_", "")
            if rtype == "CNAME" and purpose == "TRAFFIC_ROUTE":
                required_cname = req
            elif rtype == "CNAME" and required_cname is None:
                # Fallback: some future Railway response shape where
                # purpose isn't set but a single CNAME is returned.
                required_cname = req
            else:
                # Any other required record (TXT, DMARC-style TXT, etc.).
                # Surface in the message so the probe WARNING contains
                # enough context for ops to act.
                extra_required.append(
                    f"{rtype} {rec.get('fqdn') or rec.get('hostlabel')} = {req}"
                )

        if extra_required:
            message += "  extra_required=[" + "; ".join(extra_required) + "]"

        return RailwayDomainResult(
            status="created",
            message=message,
            required_cname=required_cname,
        )
