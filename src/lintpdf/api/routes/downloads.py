"""Desktop app download distribution endpoints.

Serves signed R2 URLs for the LintPDF desktop app (Tauri bundles) to
tenants who have the ``desktop_app_enabled`` entitlement flipped on.

Storage layout in R2 (under the existing ``lintpdf-uploads`` bucket):

    desktop-releases/
      latest.json                     # { "version": "x.y.z", "manifest_key": "desktop-releases/x.y.z/manifest.json" }
      <version>/
        manifest.json                 # full manifest of artifacts for this version
        macos/<installer>.dmg
        windows/<installer>.msi
        linux/<installer>.AppImage
        linux/<installer>.deb

Entitlement gating happens here; the admin-only endpoints are used by
the release script + app admin UI.
"""

from __future__ import annotations

import json
import logging
import uuid as uuid_mod

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import verify_admin_key
from lintpdf.api.database import get_db
from lintpdf.api.models import Tenant
from lintpdf.api.storage import get_storage
from lintpdf.services.entitlements import EntitlementsService, get_entitlements_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["downloads"])

_LATEST_KEY = "desktop-releases/latest.json"
_PRESIGN_EXPIRES_SECONDS = 900  # 15 min


class PlatformArtifact(BaseModel):
    filename: str
    size: int
    sha256: str
    key: str
    download_url: str | None = None  # populated in responses


class DesktopManifest(BaseModel):
    version: str
    released_at: str | None = None
    notes_url: str | None = None
    platforms: dict[str, PlatformArtifact]


class DesktopManifestResponse(BaseModel):
    version: str
    released_at: str | None = None
    notes_url: str | None = None
    platforms: dict[str, PlatformArtifact]


class PromoteRequest(BaseModel):
    version: str


class PromoteResponse(BaseModel):
    version: str
    manifest_key: str
    promoted: bool


def _load_manifest_for_version(version: str) -> dict:
    """Fetch and parse ``desktop-releases/<version>/manifest.json`` from R2."""
    storage = get_storage()
    manifest_key = f"desktop-releases/{version}/manifest.json"
    raw = storage.download_raw(manifest_key)
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manifest not found for version {version!r}.",
        )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.exception("Malformed desktop manifest at %s", manifest_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Desktop manifest is malformed.",
        ) from exc


def _load_latest_pointer() -> dict:
    """Fetch and parse ``desktop-releases/latest.json`` from R2."""
    storage = get_storage()
    raw = storage.download_raw(_LATEST_KEY)
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No desktop release has been published yet.",
        )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.exception("Malformed desktop latest pointer at %s", _LATEST_KEY)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Desktop latest pointer is malformed.",
        ) from exc


def _build_manifest_response(manifest: dict) -> DesktopManifestResponse:
    """Convert a raw manifest dict into a response with freshly-presigned URLs."""
    storage = get_storage()
    platforms_raw = manifest.get("platforms") or {}
    platforms: dict[str, PlatformArtifact] = {}
    for name, info in platforms_raw.items():
        key = info.get("key")
        if not key:
            continue
        try:
            url = storage.generate_presigned_url(
                key,
                expires_in=_PRESIGN_EXPIRES_SECONDS,
            )
        except Exception:
            logger.exception("Failed to presign desktop artifact %s", key)
            url = None
        platforms[name] = PlatformArtifact(
            filename=info.get("filename", ""),
            size=int(info.get("size", 0)),
            sha256=info.get("sha256", ""),
            key=key,
            download_url=url,
        )
    return DesktopManifestResponse(
        version=manifest.get("version", ""),
        released_at=manifest.get("released_at"),
        notes_url=manifest.get("notes_url"),
        platforms=platforms,
    )


def _parse_tenant_uuid(value: str) -> uuid_mod.UUID:
    try:
        return uuid_mod.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid tenant id.",
        ) from exc


# ── Tenant-gated download (called by the app on behalf of a user) ────────


@router.get(
    "/api/v1/admin/downloads/desktop/tenants/{tenant_id}/manifest",
    response_model=DesktopManifestResponse,
)
async def get_desktop_manifest_for_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(verify_admin_key),
    entitlements_service: EntitlementsService = Depends(get_entitlements_service),
) -> DesktopManifestResponse:
    """Return the latest desktop manifest with presigned URLs for ``tenant_id``.

    Called by the LintPDF app's ``/api/lintpdf/downloads/desktop`` proxy,
    which itself authenticates the user via their dashboard session and
    resolves ``tenantId`` from the session. Authentication here is the
    engine admin key (server-to-server).

    Returns 403 ``desktop_app_disabled`` if the tenant's resolved
    entitlements do not have ``desktop_app_enabled`` set to true.
    """
    uid = _parse_tenant_uuid(tenant_id)
    tenant: Tenant | None = db.query(Tenant).filter(Tenant.id == uid).first()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    entitlements = entitlements_service.resolve(tenant)
    if not entitlements.desktop_app_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="desktop_app_disabled",
        )

    pointer = _load_latest_pointer()
    version = pointer.get("version")
    if not version:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Desktop latest pointer missing 'version'.",
        )
    manifest = _load_manifest_for_version(version)
    return _build_manifest_response(manifest)


# ── Admin-only endpoints (release tooling) ───────────────────────────────


@router.get(
    "/api/v1/admin/downloads/desktop/manifest",
    response_model=DesktopManifestResponse,
)
async def get_desktop_manifest_admin(
    version: str | None = None,
    _key: str = Depends(verify_admin_key),
) -> DesktopManifestResponse:
    """Return a desktop manifest with presigned URLs (admin-only).

    Useful for smoke-testing a new release or a prior version.
    ``version`` defaults to whatever ``latest.json`` points at.
    """
    if version is None:
        pointer = _load_latest_pointer()
        version = pointer.get("version")
        if not version:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Desktop latest pointer missing 'version'.",
            )
    manifest = _load_manifest_for_version(version)
    return _build_manifest_response(manifest)


@router.post(
    "/api/v1/admin/downloads/desktop/promote",
    response_model=PromoteResponse,
)
async def promote_desktop_version(
    body: PromoteRequest,
    _key: str = Depends(verify_admin_key),
) -> PromoteResponse:
    """Overwrite ``desktop-releases/latest.json`` to point at ``body.version``.

    Use for rollback or for promoting a pre-staged version without
    re-uploading the binary artifacts.
    """
    # Validate that the target version's manifest exists before promoting.
    manifest = _load_manifest_for_version(body.version)
    if manifest.get("version") != body.version:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Manifest at desktop-releases/{body.version}/manifest.json "
                f"has version {manifest.get('version')!r}, refusing to promote."
            ),
        )

    manifest_key = f"desktop-releases/{body.version}/manifest.json"
    pointer = {
        "version": body.version,
        "manifest_key": manifest_key,
    }
    storage = get_storage()
    storage.upload_raw(
        _LATEST_KEY,
        json.dumps(pointer, indent=2).encode("utf-8"),
        content_type="application/json",
    )
    return PromoteResponse(
        version=body.version,
        manifest_key=manifest_key,
        promoted=True,
    )
