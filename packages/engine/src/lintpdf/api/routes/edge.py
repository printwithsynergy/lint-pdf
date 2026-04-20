"""Internal endpoints called by the LintPDF edge infrastructure.

Today this is just the on-demand-TLS ask endpoint that Caddy (running
on Fly.io as ``packages/edge-caddy``) hits before issuing a Let's
Encrypt cert for a customer hostname. The guard prevents internet
randos from pointing ``evil.com`` at our edge to force us to burn
LE rate-limit budget on hostnames we don't know about.

See packages/edge-caddy/Caddyfile for the ``ask`` directive that
calls this endpoint. The shared secret must match
``LINTPDF_EDGE_SHARED_SECRET`` in the Caddy app's env.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from lintpdf.api.database import get_db
from lintpdf.api.models import BrandProfile, Tenant

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_edge_secret(request: Request) -> None:
    """Caddy sends ``X-Edge-Shared-Secret`` on every ask call. Reject
    any request without the right secret -- stops probes from random
    traffic + stops customers from enumerating which hostnames we
    know about.
    """
    expected = os.environ.get("LINTPDF_EDGE_SHARED_SECRET") or ""
    got = request.headers.get("x-edge-shared-secret") or ""
    # Use constant-time comparison to avoid timing leaks.
    if not expected:
        logger.warning(
            "LINTPDF_EDGE_SHARED_SECRET not set -- all on-demand-tls-check "
            "calls will be rejected. Set the secret on both API + Caddy."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Edge ask endpoint not configured.",
        )
    import hmac

    if not hmac.compare_digest(got, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bad edge secret.",
        )


@router.get(
    "/api/v1/internal/on-demand-tls-check",
    include_in_schema=False,  # internal; keep out of the public OpenAPI
)
def on_demand_tls_check(
    request: Request,
    domain: str = "",
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Caddy's ``on_demand_tls.ask`` hits this before issuing a cert.

    Returns 200 iff ``domain`` is registered as a tenant-level or
    brand-profile-level custom domain. Any other response (including
    200-missing-body) tells Caddy to refuse cert issuance.

    Also unconditionally accepts anything under our own zone
    (``*.lintpdf.com`` + ``lintpdf.com``) so a stray internal hostname
    doesn't burn an LE order.
    """
    _verify_edge_secret(request)

    canonical = (domain or "").strip().lower().rstrip(".")
    if not canonical:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="domain query param required",
        )

    # Defense-in-depth: anything under our own zone is trivially ours.
    if canonical.endswith(".lintpdf.com") or canonical == "lintpdf.com":
        return {"ok": "true", "reason": "lintpdf-owned", "domain": canonical}

    # Primary check: tenant-level or profile-level registered domain.
    tenant_hit = (
        db.query(Tenant)
        .filter(
            (Tenant.brand_custom_domain == canonical)
            | (Tenant.app_custom_domain == canonical),
        )
        .first()
    )
    if tenant_hit is not None:
        return {"ok": "true", "reason": "tenant", "domain": canonical}

    profile_hit = (
        db.query(BrandProfile)
        .filter(
            (BrandProfile.custom_domain == canonical)
            | (BrandProfile.app_custom_domain == canonical),
        )
        .first()
    )
    if profile_hit is not None:
        return {"ok": "true", "reason": "brand_profile", "domain": canonical}

    logger.info(
        "on-demand-tls-check REJECTED unknown domain: %s",
        canonical,
    )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"domain '{canonical}' not registered on any tenant / brand profile",
    )
