"""Viewer endpoints — page tile rendering, dimensions, and separation channels."""

from __future__ import annotations

import hashlib
import io
import logging
import re
import uuid as uuid_mod
from typing import Any

import pikepdf
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import Job, JobStatus, Tenant
from lintpdf.api.storage import get_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/viewer", tags=["viewer"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SeparationChannel(BaseModel):
    name: str
    type: str  # "process" or "spot"


class SeparationsResponse(BaseModel):
    job_id: str
    channels: list[SeparationChannel]


class PageBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class PageInfo(BaseModel):
    page_num: int
    width_pts: float
    height_pts: float
    media_box: PageBox
    crop_box: PageBox | None = None
    trim_box: PageBox | None = None
    bleed_box: PageBox | None = None
    rotation: int = 0


class PagesResponse(BaseModel):
    job_id: str
    page_count: int
    pages: list[PageInfo]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_job_pdf(
    job_id: str,
    tenant: Tenant,
    db: Session,
) -> tuple[Job, bytes]:
    """Fetch the job and its original PDF bytes from storage."""
    # Job.id is a UUID column — pre-validate the parameter so a malformed
    # path like ``/jobs/nonexistent-job-id-000/...`` returns 404 instead of
    # bubbling up an SQLAlchemy cast error as a 500.
    try:
        job_uuid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        ) from exc

    job = db.query(Job).filter(Job.id == job_uuid, Job.tenant_id == tenant.id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != JobStatus.COMPLETE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is not complete — viewer requires a finished preflight",
        )
    storage = get_storage()
    try:
        pdf_bytes = storage.download_pdf(job.file_key)
    except Exception as exc:
        logger.error("Failed to download PDF for viewer: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve original PDF from storage",
        ) from exc
    return job, pdf_bytes


def _validate_page_num(pdf_bytes: bytes, page_num: int) -> None:
    """Raise 404 if ``page_num`` is out of range for this PDF.

    Done before calling renderers so an out-of-range page returns a clean
    404 rather than a 503 from the rendering backend's "Failed to render
    page" RuntimeError.
    """
    try:
        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not read PDF",
        ) from exc
    if page_num < 1 or page_num > page_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_num} not found (PDF has {page_count} pages)",
        )


def _extract_box(page: Any, name: str) -> PageBox | None:
    """Extract a named box from a pikepdf page, returning None if absent."""
    raw = page.get(name)
    if raw is None:
        return None
    coords = [float(c) for c in raw]
    return PageBox(x0=coords[0], y0=coords[1], x1=coords[2], y1=coords[3])


def _tile_cache_key(tenant_id: str, job_id: str, page_num: int, dpi: int) -> str:
    """S3 key for a cached tile."""
    return f"{tenant_id}/{job_id}/tiles/p{page_num}_d{dpi}.png"


def _channel_cache_key(
    tenant_id: str, job_id: str, page_num: int, dpi: int, channel_name: str
) -> str:
    """S3 key for a cached separation channel tile."""
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", channel_name)
    return f"{tenant_id}/{job_id}/tiles/p{page_num}_d{dpi}_ch_{safe_name}.png"


def _tac_cache_key(tenant_id: str, job_id: str, page_num: int, dpi: int) -> str:
    """S3 key for a cached TAC heatmap."""
    return f"{tenant_id}/{job_id}/tiles/p{page_num}_d{dpi}_tac.png"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/pages", response_model=PagesResponse)
async def list_pages(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> PagesResponse:
    """Return page count and dimensions for all pages in a job's PDF."""
    _job, pdf_bytes = _get_job_pdf(job_id, tenant, db)

    pages: list[PageInfo] = []
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            media = _extract_box(page, "/MediaBox")
            if not media:
                continue
            crop = _extract_box(page, "/CropBox")
            trim = _extract_box(page, "/TrimBox")
            bleed = _extract_box(page, "/BleedBox")
            rotation = int(page.get("/Rotate", 0))
            pages.append(
                PageInfo(
                    page_num=i,
                    width_pts=media.x1 - media.x0,
                    height_pts=media.y1 - media.y0,
                    media_box=media,
                    crop_box=crop,
                    trim_box=trim,
                    bleed_box=bleed,
                    rotation=rotation,
                )
            )

    return PagesResponse(job_id=job_id, page_count=len(pages), pages=pages)


@router.get("/jobs/{job_id}/pages/{page_num}/tile")
async def get_page_tile(
    job_id: str,
    page_num: int,
    dpi: int = Query(default=150, ge=36, le=600),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Response:
    """Render a single page as a PNG tile at the requested DPI.

    Tiles are cached in S3 — subsequent requests serve the cached version.
    """
    job, pdf_bytes = _get_job_pdf(job_id, tenant, db)
    _validate_page_num(pdf_bytes, page_num)
    storage = get_storage()
    cache_key = _tile_cache_key(str(tenant.id), str(job.id), page_num, dpi)

    # Try serving from S3 cache
    try:
        cached = storage.download_raw(cache_key)
        if cached:
            etag = hashlib.md5(cached[:1024]).hexdigest()
            return Response(
                content=cached,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=86400", "ETag": etag},
            )
    except Exception:
        pass  # Cache miss — render on demand

    # Render the tile
    from lintpdf.ai.rendering import render_page_to_image

    try:
        tile_bytes = render_page_to_image(pdf_bytes, page_num, dpi=dpi)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    # Cache to S3 (fire-and-forget)
    try:
        storage.upload_raw(cache_key, tile_bytes, content_type="image/png")
    except Exception:
        logger.warning("Failed to cache tile to S3: %s", cache_key)

    etag = hashlib.md5(tile_bytes[:1024]).hexdigest()
    return Response(
        content=tile_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400", "ETag": etag},
    )


@router.get("/jobs/{job_id}/pages/{page_num}/info", response_model=PageInfo)
async def get_page_info(
    job_id: str,
    page_num: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> PageInfo:
    """Return dimensions and box info for a single page."""
    _job, pdf_bytes = _get_job_pdf(job_id, tenant, db)

    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        if page_num < 1 or page_num > len(pdf.pages):
            raise HTTPException(status_code=404, detail=f"Page {page_num} not found")
        page = pdf.pages[page_num - 1]
        media = _extract_box(page, "/MediaBox")
        if not media:
            raise HTTPException(status_code=500, detail="Page has no MediaBox")
        return PageInfo(
            page_num=page_num,
            width_pts=media.x1 - media.x0,
            height_pts=media.y1 - media.y0,
            media_box=media,
            crop_box=_extract_box(page, "/CropBox"),
            trim_box=_extract_box(page, "/TrimBox"),
            bleed_box=_extract_box(page, "/BleedBox"),
            rotation=int(page.get("/Rotate", 0)),
        )


@router.get("/jobs/{job_id}/separations", response_model=SeparationsResponse)
async def get_separations(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> SeparationsResponse:
    """List all ink channels (CMYK + spot colors) in the job's PDF."""
    from lintpdf.reports.separation_renderer import list_separations

    _job, pdf_bytes = _get_job_pdf(job_id, tenant, db)
    channels_raw = list_separations(pdf_bytes)
    channels = [SeparationChannel(name=c["name"], type=c["type"]) for c in channels_raw]
    return SeparationsResponse(job_id=job_id, channels=channels)


@router.get("/jobs/{job_id}/pages/{page_num}/channel/{channel_name}")
async def get_separation_channel(
    job_id: str,
    page_num: int,
    channel_name: str,
    dpi: int = Query(default=150, ge=36, le=600),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Response:
    """Render a single ink channel as a grayscale PNG."""
    from lintpdf.reports.separation_renderer import render_separation_channel

    job, pdf_bytes = _get_job_pdf(job_id, tenant, db)
    _validate_page_num(pdf_bytes, page_num)
    storage = get_storage()
    cache_key = _channel_cache_key(str(tenant.id), str(job.id), page_num, dpi, channel_name)

    # Try S3 cache
    try:
        cached = storage.download_raw(cache_key)
        if cached:
            return Response(
                content=cached,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception:
        pass

    try:
        img_bytes = render_separation_channel(pdf_bytes, page_num, channel_name, dpi=dpi)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Cache to S3
    try:
        storage.upload_raw(cache_key, img_bytes, content_type="image/png")
    except Exception:
        logger.warning("Failed to cache channel tile: %s", cache_key)

    return Response(
        content=img_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/jobs/{job_id}/pages/{page_num}/tac-heatmap")
async def get_tac_heatmap(
    job_id: str,
    page_num: int,
    dpi: int = Query(default=150, ge=36, le=600),
    tac_limit: int = Query(default=300, ge=100, le=500),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Response:
    """Render a TAC heatmap overlay as an RGBA PNG."""
    from lintpdf.reports.separation_renderer import render_tac_heatmap

    job, pdf_bytes = _get_job_pdf(job_id, tenant, db)
    _validate_page_num(pdf_bytes, page_num)
    storage = get_storage()
    cache_key = _tac_cache_key(str(tenant.id), str(job.id), page_num, dpi)

    # Try S3 cache
    try:
        cached = storage.download_raw(cache_key)
        if cached:
            return Response(
                content=cached,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception:
        pass

    try:
        heatmap_bytes = render_tac_heatmap(pdf_bytes, page_num, dpi=dpi, tac_limit=tac_limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Cache to S3
    try:
        storage.upload_raw(cache_key, heatmap_bytes, content_type="image/png")
    except Exception:
        logger.warning("Failed to cache TAC heatmap: %s", cache_key)

    return Response(
        content=heatmap_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
