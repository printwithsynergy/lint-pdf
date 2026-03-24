"""Dev-only authentication endpoints for testing.

Gated by LINTPDF_DEV_AUTH_ENABLED=true.  Requires admin API key.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import generate_api_key, hash_api_key
from lintpdf.api.auth import verify_admin_key as _verify_admin_key
from lintpdf.api.database import get_db
from lintpdf.api.models import ApiKey, Tenant
from lintpdf.tenants.models import TenantPlan

router = APIRouter(prefix="/api/v1/dev", tags=["dev"])


class ImpersonateRequest(BaseModel):
    tenant_id: str


class ImpersonateResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    plan: str
    api_key: str


@router.post("/impersonate", response_model=ImpersonateResponse)
async def impersonate_tenant(
    body: ImpersonateRequest,
    db: Session = Depends(get_db),  # noqa: B008
    _key: str = Depends(_verify_admin_key),
) -> ImpersonateResponse:
    """Generate a temporary API key for a tenant (dev/test use only)."""
    try:
        uid = uuid.UUID(body.tenant_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid UUID.",
        ) from exc

    tenant = db.query(Tenant).filter(Tenant.id == uid).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    # Update tenant's primary key hash for direct auth
    tenant.api_key_hash = key_hash

    # Also store in api_keys table
    api_key_record = ApiKey(
        tenant_id=uid,
        key_hash=key_hash,
        label="dev-impersonate",
        key_prefix=raw_key[:12],
    )
    db.add(api_key_record)
    db.commit()

    return ImpersonateResponse(
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        plan=tenant.plan,
        api_key=raw_key,
    )


class SeedResponse(BaseModel):
    tenants: dict[str, dict[str, str]]


@router.post("/seed")
async def seed_test_data(
    db: Session = Depends(get_db),  # noqa: B008
    _key: str = Depends(_verify_admin_key),
) -> dict[str, Any]:
    """Seed test tenants (dev/test use only)."""
    try:
        return _do_seed(db)
    except Exception as exc:
        db.rollback()
        logger.exception("Seed test data failed")
        raise HTTPException(status_code=500, detail="Internal error during seeding") from exc


def _do_seed(db: Session) -> dict[str, Any]:
    plan_limits = {
        "free": {"rate_limit_daily": 50, "max_file_size_mb": 25},
        "starter": {"rate_limit_daily": 500, "max_file_size_mb": 250},
        "growth": {"rate_limit_daily": 5000, "max_file_size_mb": 500},
        "scale": {"rate_limit_daily": 25000, "max_file_size_mb": 1024},
        "enterprise": {"rate_limit_daily": 100000, "max_file_size_mb": 2048},
    }

    result: dict[str, dict[str, str]] = {}

    for plan in TenantPlan:
        name = f"Test {plan.value.capitalize()} Tenant"
        existing = db.query(Tenant).filter(Tenant.name == name).first()

        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        limits = plan_limits.get(plan.value, {})

        if existing:
            existing.api_key_hash = key_hash
            db.flush()
            result[plan.value] = {
                "id": str(existing.id),
                "name": name,
                "api_key": raw_key,
            }
            continue

        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            name=name,
            api_key_hash=key_hash,
            plan=plan,
            rate_limit_daily=limits.get("rate_limit_daily", 10),
            max_file_size_mb=limits.get("max_file_size_mb", 25),
            contact_email=f"test-{plan.value}@lintpdf.com",
            is_active=True,
        )
        db.add(tenant)
        db.flush()  # Ensure tenant exists before FK reference

        api_key_record = ApiKey(
            tenant_id=tenant_id,
            key_hash=key_hash,
            label="seed-key",
            key_prefix=raw_key[:12],
        )
        db.add(api_key_record)
        db.flush()

        result[plan.value] = {
            "id": str(tenant_id),
            "name": name,
            "api_key": raw_key,
        }

    db.commit()
    return {"tenants": result}
