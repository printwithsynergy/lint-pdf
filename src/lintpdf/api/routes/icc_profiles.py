"""ICC profile upload — substrate-aware EPM gamut path (PR-followup).

Single-active-slot per tenant. The uploaded ICC profile bytes get
stashed in object storage at a deterministic key:

    icc-profiles/{tenant_id}/active.icc

The orchestrator's EPM-A1 path (PR 24 + the orchestrator wiring PR)
downloads those bytes to a temp file when constructing
``EpmTierAAnalyzer`` and forwards the path to ``load_profile``.

Endpoints:

* ``POST   /api/v1/icc-profiles/active`` — upload (multipart/form-data,
  field ``file``). Validates the ICC magic bytes (``acsp`` at offset 36).
* ``GET    /api/v1/icc-profiles/active`` — returns metadata (size in
  bytes, uploaded_at, optional description from the profile header) or
  ``null`` when no profile is set.
* ``DELETE /api/v1/icc-profiles/active`` — clear the active slot.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from lintpdf.api.models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/icc-profiles", tags=["icc-profiles"])

# Storage key — single-active-slot per tenant.
_ACTIVE_KEY_TEMPLATE = "icc-profiles/{tenant_id}/active.icc"

# ICC magic bytes — every valid profile carries 'acsp' at offset 36
# per ICC.1:2010 §7.2. Used to reject obviously-not-ICC uploads
# before we waste storage on garbage.
_ICC_MAGIC = b"acsp"
_ICC_MAGIC_OFFSET = 36

# 16 MB cap — most printer profiles are 200 KB - 5 MB; anything
# bigger is almost certainly a wrong file. Cheap to enforce, hard
# to exceed accidentally.
_MAX_ICC_SIZE_BYTES = 16 * 1024 * 1024


# ---- response models -----------------------------------------------------


class IccProfileResponse(BaseModel):
    """Metadata for the tenant's active ICC profile (no bytes)."""

    storage_key: str = Field(description="Storage key (icc-profiles/{tenant_id}/active.icc).")
    size_bytes: int = Field(description="Profile size in bytes.")
    uploaded_at: datetime = Field(description="Upload timestamp (UTC).")
    description: str | None = Field(
        default=None,
        description="Profile description string from the ICC tag table, when readable.",
    )


# ---- helpers -------------------------------------------------------------


def _key_for(tenant_id: object) -> str:
    return _ACTIVE_KEY_TEMPLATE.format(tenant_id=str(tenant_id))


def _is_icc_bytes(content: bytes) -> bool:
    """Return True iff the bytes look like an ICC profile."""
    if len(content) < _ICC_MAGIC_OFFSET + len(_ICC_MAGIC):
        return False
    return content[_ICC_MAGIC_OFFSET : _ICC_MAGIC_OFFSET + len(_ICC_MAGIC)] == _ICC_MAGIC


def _profile_description(content: bytes) -> str | None:
    """Best-effort: pull the 'desc' tag value from the ICC profile.

    Walks the tag table (count at offset 128, entries at 132+). Each
    entry is 12 bytes: signature(4), offset(4), size(4). If we find
    the 'desc' tag, decode the ASCII portion of its data block.
    Returns None on any parse failure — never raises.
    """
    try:
        if len(content) < 132 + 12:
            return None
        tag_count = int.from_bytes(content[128:132], "big")
        for i in range(tag_count):
            entry = 132 + i * 12
            sig = content[entry : entry + 4]
            if sig != b"desc":
                continue
            offset = int.from_bytes(content[entry + 4 : entry + 8], "big")
            size = int.from_bytes(content[entry + 8 : entry + 12], "big")
            if offset + size > len(content):
                return None
            data = content[offset : offset + size]
            # ICC v2 'desc' tag: type(4)='desc', reserved(4),
            # ascii_count(4), ascii(N).
            if len(data) >= 16 and data[:4] == b"desc":
                ascii_count = int.from_bytes(data[8:12], "big")
                ascii_bytes = data[12 : 12 + ascii_count]
                return ascii_bytes.rstrip(b"\x00").decode("latin-1", errors="replace")
            # ICC v4 'mluc' under desc: type='mluc' header. Skip.
            return None
    except Exception:
        return None
    return None


# ---- routes --------------------------------------------------------------


@router.post(
    "/active",
    response_model=IccProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def set_active_profile(
    file: UploadFile = File(..., description="ICC profile file (.icc / .icm)."),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> IccProfileResponse:
    """Upload + activate a substrate ICC profile for the tenant."""
    from lintpdf.api.storage import get_storage

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="ICC profile is empty.",
        )
    if len(content) > _MAX_ICC_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(f"ICC profile exceeds the {_MAX_ICC_SIZE_BYTES // (1024 * 1024)} MB cap."),
        )
    if not _is_icc_bytes(content):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "File does not look like an ICC profile (missing 'acsp' magic bytes at offset 36)."
            ),
        )

    storage = get_storage()
    key = _key_for(tenant.id)
    storage.upload_raw(key, content, content_type="application/vnd.iccprofile")
    logger.info("ICC profile uploaded for tenant %s (%d bytes)", tenant.id, len(content))

    return IccProfileResponse(
        storage_key=key,
        size_bytes=len(content),
        uploaded_at=datetime.now(tz=timezone.utc),
        description=_profile_description(content),
    )


@router.get("/active", response_model=IccProfileResponse | None)
async def get_active_profile(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> IccProfileResponse | None:
    """Return metadata for the tenant's active ICC profile, or null."""
    from lintpdf.api.storage import get_storage

    storage = get_storage()
    key = _key_for(tenant.id)
    try:
        content = storage.download_raw(key)
    except Exception:
        return None
    if not content:
        return None
    return IccProfileResponse(
        storage_key=key,
        size_bytes=len(content),
        uploaded_at=datetime.now(tz=timezone.utc),
        description=_profile_description(content),
    )


@router.delete("/active", status_code=status.HTTP_204_NO_CONTENT)
async def delete_active_profile(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> None:
    """Clear the tenant's active ICC profile."""
    from lintpdf.api.storage import get_storage

    storage = get_storage()
    key = _key_for(tenant.id)
    import contextlib

    with contextlib.suppress(Exception):
        # Idempotent — already gone is fine.
        storage.delete_file(key)


__all__ = ["router"]
