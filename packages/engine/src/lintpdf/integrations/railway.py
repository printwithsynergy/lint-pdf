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

    def _lookup_existing_required_cname(
        self, domain: str, service_id: str
    ) -> str | None:
        """Fetch the required CNAME target for an already-registered domain.

        Called on ``already_exists`` to recover the per-domain Railway
        backend hostname so the probe task can provision a matching
        Cloudflare alias for tenants that were registered before the
        alias layer shipped. Returns None on any error -- caller
        treats that as "no alias possible this cycle".
        """
        query = """
        query Domains($projectId: String!, $environmentId: String!, $serviceId: String!) {
          domains(projectId: $projectId, environmentId: $environmentId, serviceId: $serviceId) {
            customDomains {
              domain
              status {
                dnsRecords {
                  recordType
                  requiredValue
                  purpose
                }
              }
            }
          }
        }
        """
        try:
            payload = self._post(
                query,
                {
                    "projectId": self.project_id,
                    "environmentId": self.environment_id,
                    "serviceId": service_id,
                },
            )
        except Exception:  # noqa: BLE001 -- never fail the outer call on this
            logger.exception("Railway domains() re-query failed for %s", domain)
            return None

        cds = (
            (payload.get("data") or {}).get("domains", {}).get("customDomains") or []
        )
        for cd in cds:
            if (cd.get("domain") or "").lower() != domain.lower():
                continue
            records = (cd.get("status") or {}).get("dnsRecords") or []
            for rec in records:
                if (
                    rec.get("recordType") == "DNS_RECORD_TYPE_CNAME"
                    and rec.get("requiredValue")
                    and rec.get("purpose") == "DNS_RECORD_PURPOSE_TRAFFIC_ROUTE"
                ):
                    return rec["requiredValue"]
            # Fallback: first CNAME with a requiredValue
            for rec in records:
                if (
                    rec.get("recordType") == "DNS_RECORD_TYPE_CNAME"
                    and rec.get("requiredValue")
                ):
                    return rec["requiredValue"]
        return None

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
            if "unauthorized" in msg or "permission" in msg:
                return RailwayDomainResult(
                    status="unauthorized",
                    message=first.get("message"),
                )
            # Any other mutation error is AMBIGUOUS:
            #
            #   * "domain already exists on another service" -- this was
            #     the historical message (code still checks for it).
            #   * "Failed to create custom domain, please try again" --
            #     Railway's current generic error for duplicates (Envoy
            #     rewrite). Same meaning, less helpful wording. See
            #     Worker logs from 2026-04-19 for evidence.
            #   * Real transient failures (rate-limit, partial outage).
            #
            # Distinguishing them from the error message alone is
            # unreliable. So we probe with a domains() re-query: if the
            # domain is already attached to this service we get its
            # required_cname back and treat this as "already_exists"
            # (downstream probe task persists the alias column from the
            # required_cname it receives). If the re-query returns
            # nothing, the domain genuinely didn't register -- surface
            # as error.
            req = self._lookup_existing_required_cname(
                domain, service_id or self.service_id
            )
            if req is not None:
                return RailwayDomainResult(
                    status="already_exists",
                    message=first.get("message"),
                    required_cname=req,
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
