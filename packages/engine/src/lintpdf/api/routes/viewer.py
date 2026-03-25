"""Viewer endpoints — page tile rendering, dimensions, and separation channels."""

from __future__ import annotations

import hashlib
import io
import logging
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
    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.tenant_id == tenant.id)
        .first()
    )
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
    storage = get_storage()
    cache_key = _tile_cache_key(str(tenant.id), str(job.id), page_num, dpi)

    # Try serving from S3 cache
    try:
        cached = storage.download_raw(cache_key)
        if cached:
            etag = hashlib.md5(cached[:1024]).hexdigest()  # noqa: S324
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

    etag = hashlib.md5(tile_bytes[:1024]).hexdigest()  # noqa: S324
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
