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
        self.environment_id = (
            environment_id or os.environ.get("RAILWAY_ENVIRONMENT_ID") or ""
        )
        self.service_id = service_id or os.environ.get("RAILWAY_API_SERVICE_ID") or ""
        self.app_service_id = os.environ.get("RAILWAY_APP_SERVICE_ID") or ""
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        """True when all required config is present.

        When False, ``add_custom_domain`` short-circuits to a 'disabled'
        result and the probe task falls through to the manual ops path.
        """
        return bool(
            self.token
            and self.project_id
            and self.environment_id
            and self.service_id
        )

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
            return response.json()

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

        query = """
        mutation CustomDomainCreate($input: CustomDomainCreateInput!) {
          customDomainCreate(input: $input) {
            id
            domain
            status
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
            logger.warning(
                "Railway GraphQL error for domain %s: %s", domain, first.get("message")
            )
            return RailwayDomainResult(
                status="error", message=first.get("message")
            )

        data = (payload.get("data") or {}).get("customDomainCreate") or {}
        if not data:
            return RailwayDomainResult(
                status="error", message="Empty response from Railway"
            )

        return RailwayDomainResult(status="created", message=data.get("status"))
