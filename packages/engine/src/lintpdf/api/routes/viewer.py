"""Viewer endpoints — page tile rendering, dimensions, separation channels,
measurement tools, PDF layers, comparison, and verdict.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any

import pikepdf
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import BrandProfile, Job, JobStatus, Tenant
from lintpdf.api.storage import get_storage
from lintpdf.reports.service import _LINTPDF_DEFAULT_LOGO

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


# ---------------------------------------------------------------------------
# Viewer Configuration
# ---------------------------------------------------------------------------


class ViewerConfigResponse(BaseModel):
    enable_separations: bool = True
    enable_tac_heatmap: bool = True
    enable_annotations: bool = True
    enable_measurement: bool = True
    enable_comparison: bool = True
    enable_layers: bool = True
    enable_findings_panel: bool = True
    enable_page_thumbnails: bool = True
    enable_zoom: bool = True
    enable_download: bool = True
    enable_html_report_link: bool = True
    verdict_mode: str = "auto"
    default_zoom: int = 100
    default_dpi: int = 150
    default_tac_limit: float = 300.0
    viewer_logo_url: str | None = None
    viewer_accent_color: str | None = None
    toolbar_position: str = "top"
    dark_mode: bool = False
    # Resolved branding from brand profile (defaults to LintPDF branding)
    brand_name: str = "LintPDF"
    brand_logo_url: str | None = _LINTPDF_DEFAULT_LOGO
    brand_primary_color: str = "#1a3a7a"
    brand_accent_color: str = "#2563eb"


@router.get("/jobs/{job_id}/config", response_model=ViewerConfigResponse)
async def get_viewer_config(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> ViewerConfigResponse:
    """Return resolved viewer configuration for this job's tenant + brand profile."""
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    job = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Start with defaults — fall back to LintPDF branding when tenant has none
    config = ViewerConfigResponse(
        brand_name=tenant.brand_name or "LintPDF",
        brand_logo_url=tenant.brand_logo_url or _LINTPDF_DEFAULT_LOGO,
        brand_primary_color=tenant.brand_primary_color or "#1a3a7a",
        brand_accent_color=tenant.brand_accent_color or "#2563eb",
    )

    # Merge brand profile viewer_config if available
    if tenant.default_brand_profile_id:
        profile = (
            db.query(BrandProfile)
            .filter(
                BrandProfile.id == tenant.default_brand_profile_id,
                BrandProfile.tenant_id == tenant.id,
            )
            .first()
        )
        if profile:
            config.brand_name = profile.brand_name or config.brand_name
            config.brand_logo_url = profile.logo_url or config.brand_logo_url
            config.brand_primary_color = profile.primary_color or config.brand_primary_color
            config.brand_accent_color = profile.accent_color or config.brand_accent_color

            if profile.viewer_config:
                vc = profile.viewer_config
                for field_name in ViewerConfigResponse.model_fields:
                    if field_name.startswith("brand_"):
                        continue  # Don't overwrite resolved branding
                    if field_name in vc:
                        setattr(config, field_name, vc[field_name])

    return config


# ---------------------------------------------------------------------------
# Densitometer — Color Sampling
# ---------------------------------------------------------------------------


class ColorSampleResponse(BaseModel):
    x: float
    y: float
    rgb: list[int]
    hex: str
    tac: float | None = None


@router.get("/jobs/{job_id}/pages/{page_num}/sample")
async def sample_color(
    job_id: str,
    page_num: int,
    x: float = Query(..., description="X coordinate in PDF points"),
    y: float = Query(..., description="Y coordinate in PDF points"),
    dpi: int = Query(default=300, ge=72, le=600),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> ColorSampleResponse:
    """Sample the color at a point on a PDF page.

    Renders the page at the requested DPI and reads the pixel at the
    given PDF coordinate (origin lower-left, in points).
    """
    from PIL import Image

    from lintpdf.ai.rendering import render_page_to_image

    _job, pdf_bytes = _get_job_pdf(job_id, tenant, db)
    _validate_page_num(pdf_bytes, page_num)

    # Get page dimensions for coordinate conversion
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_num - 1]
        mb = page.get("/MediaBox")
        if mb is None:
            raise HTTPException(status_code=500, detail="Page has no MediaBox")
        mb_vals = [float(v) for v in mb]

    page_w = mb_vals[2] - mb_vals[0]
    page_h = mb_vals[3] - mb_vals[1]

    # Render page
    png_bytes = render_page_to_image(pdf_bytes, page_num, dpi=dpi)
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")

    # Convert PDF coords to pixel coords
    scale_x = img.width / page_w
    scale_y = img.height / page_h
    px_x = int((x - mb_vals[0]) * scale_x)
    px_y = int(img.height - (y - mb_vals[1]) * scale_y)  # Y-flip

    # Clamp to image bounds
    px_x = max(0, min(px_x, img.width - 1))
    px_y = max(0, min(px_y, img.height - 1))

    # Sample pixel (average 3x3 patch for stability)
    r_sum, g_sum, b_sum, count = 0, 0, 0, 0
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            sx = max(0, min(px_x + dx, img.width - 1))
            sy = max(0, min(px_y + dy, img.height - 1))
            pr, pg, pb = img.getpixel((sx, sy))
            r_sum += pr
            g_sum += pg
            b_sum += pb
            count += 1

    r_avg = r_sum // count
    g_avg = g_sum // count
    b_avg = b_sum // count
    hex_color = f"#{r_avg:02x}{g_avg:02x}{b_avg:02x}"

    return ColorSampleResponse(
        x=x,
        y=y,
        rgb=[r_avg, g_avg, b_avg],
        hex=hex_color,
    )


# ---------------------------------------------------------------------------
# PDF Layers (OCG / Optional Content Groups)
# ---------------------------------------------------------------------------


class LayerInfo(BaseModel):
    name: str
    ocg_index: int
    default_on: bool = True


class LayersResponse(BaseModel):
    job_id: str
    layers: list[LayerInfo]


@router.get("/jobs/{job_id}/layers", response_model=LayersResponse)
async def list_layers(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> LayersResponse:
    """List PDF Optional Content Groups (layers)."""
    _job, pdf_bytes = _get_job_pdf(job_id, tenant, db)

    layers: list[LayerInfo] = []
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        catalog = pdf.Root
        oc_props = catalog.get("/OCProperties")
        if oc_props is None:
            return LayersResponse(job_id=job_id, layers=[])

        ocgs = oc_props.get("/OCGs")
        if ocgs is None:
            return LayersResponse(job_id=job_id, layers=[])

        # Get default ON/OFF state
        default_config = oc_props.get("/D", {})
        off_list = default_config.get("/OFF", [])
        off_set: set[int] = set()
        try:
            for ref in off_list:
                off_set.add(id(ref))
        except Exception:
            pass

        for idx, ocg_ref in enumerate(ocgs):
            try:
                ocg = ocg_ref
                if hasattr(ocg, "resolve"):
                    ocg = ocg_ref.resolve() if callable(getattr(ocg_ref, "resolve", None)) else ocg_ref
                name = str(ocg.get("/Name", f"Layer {idx + 1}"))
                default_on = id(ocg_ref) not in off_set
                layers.append(LayerInfo(name=name, ocg_index=idx, default_on=default_on))
            except Exception:
                layers.append(LayerInfo(name=f"Layer {idx + 1}", ocg_index=idx))

    return LayersResponse(job_id=job_id, layers=layers)


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


class VerdictRequest(BaseModel):
    verdict: str  # "pass" or "fail"
    notes: str | None = None


class VerdictResponse(BaseModel):
    verdict: str | None = None
    auto_passed: bool | None = None
    verdict_by: str | None = None
    verdict_at: str | None = None
    notes: str | None = None


@router.get("/jobs/{job_id}/verdict", response_model=VerdictResponse)
async def get_verdict(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> VerdictResponse:
    """Get the current verdict for a job."""
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    job = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    auto_passed = None
    if job.result_json:
        summary = job.result_json.get("summary", {})
        auto_passed = summary.get("passed")

    return VerdictResponse(
        verdict=job.verdict,
        auto_passed=auto_passed,
        verdict_by=job.verdict_by,
        verdict_at=job.verdict_at.isoformat() if job.verdict_at else None,
        notes=job.verdict_notes,
    )


@router.post("/jobs/{job_id}/verdict", response_model=VerdictResponse)
async def set_verdict(
    job_id: str,
    body: VerdictRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> VerdictResponse:
    """Set a manual verdict (pass/fail) on a job."""
    if body.verdict not in ("pass", "fail"):
        raise HTTPException(status_code=422, detail="verdict must be 'pass' or 'fail'")

    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    job = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETE:
        raise HTTPException(status_code=409, detail="Job is not complete")

    # If fail, require notes or annotations
    if body.verdict == "fail" and not body.notes:
        raise HTTPException(
            status_code=422,
            detail="Fail verdict requires notes or annotations.",
        )

    reviewer_email = getattr(tenant, "owner_email", None) or "reviewer"
    now = datetime.now(timezone.utc)

    job.verdict = body.verdict
    job.verdict_by = reviewer_email
    job.verdict_at = now
    job.verdict_notes = body.notes
    db.commit()

    return VerdictResponse(
        verdict=job.verdict,
        auto_passed=job.result_json.get("summary", {}).get("passed") if job.result_json else None,
        verdict_by=job.verdict_by,
        verdict_at=job.verdict_at.isoformat() if job.verdict_at else None,
        notes=job.verdict_notes,
    )


# ---------------------------------------------------------------------------
# File Comparison
# ---------------------------------------------------------------------------


class ComparisonRequest(BaseModel):
    job_a: str
    job_b: str
    dpi: int = 150


class ComparisonPageSummary(BaseModel):
    page_num: int
    ssim_score: float
    diff_pixel_count: int
    total_pixels: int


class ComparisonResponse(BaseModel):
    comparison_id: str
    page_count_a: int
    page_count_b: int
    pages: list[ComparisonPageSummary]


@router.post("/compare", response_model=ComparisonResponse)
async def create_comparison(
    body: ComparisonRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> ComparisonResponse:
    """Compare two jobs' PDFs and return per-page similarity scores."""
    import asyncio

    import numpy as np
    from PIL import Image

    from lintpdf.ai.rendering import render_page_to_image

    # Validate both jobs belong to this tenant
    try:
        uid_a = uuid_mod.UUID(body.job_a)
        uid_b = uuid_mod.UUID(body.job_b)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid job ID") from exc

    job_a = db.query(Job).filter(Job.id == uid_a, Job.tenant_id == tenant.id).first()
    job_b = db.query(Job).filter(Job.id == uid_b, Job.tenant_id == tenant.id).first()
    if not job_a or not job_b:
        raise HTTPException(status_code=404, detail="One or both jobs not found")
    if job_a.status != JobStatus.COMPLETE or job_b.status != JobStatus.COMPLETE:
        raise HTTPException(status_code=409, detail="Both jobs must be complete")

    storage = get_storage()
    pdf_a = storage.download_pdf(job_a.file_key)
    pdf_b = storage.download_pdf(job_b.file_key)

    # Get page counts
    with pikepdf.open(io.BytesIO(pdf_a)) as pa:
        pages_a = len(pa.pages)
    with pikepdf.open(io.BytesIO(pdf_b)) as pb:
        pages_b = len(pb.pages)

    comparison_id = str(uuid_mod.uuid4())
    max_pages = min(pages_a, pages_b, 50)
    page_summaries: list[ComparisonPageSummary] = []

    loop = asyncio.get_running_loop()

    for pg in range(1, max_pages + 1):
        try:
            img_a_bytes = await loop.run_in_executor(
                None, lambda p=pg: render_page_to_image(pdf_a, p, dpi=body.dpi)
            )
            img_b_bytes = await loop.run_in_executor(
                None, lambda p=pg: render_page_to_image(pdf_b, p, dpi=body.dpi)
            )

            arr_a = np.array(Image.open(io.BytesIO(img_a_bytes)).convert("L"))
            arr_b = np.array(Image.open(io.BytesIO(img_b_bytes)).convert("L"))

            # Resize to match if different dimensions
            min_h = min(arr_a.shape[0], arr_b.shape[0])
            min_w = min(arr_a.shape[1], arr_b.shape[1])
            arr_a = arr_a[:min_h, :min_w]
            arr_b = arr_b[:min_h, :min_w]

            # SSIM
            try:
                from skimage.metrics import structural_similarity as ssim

                score = float(ssim(arr_a, arr_b))
            except ImportError:
                # Fallback: simple pixel comparison
                diff = np.abs(arr_a.astype(int) - arr_b.astype(int))
                score = 1.0 - (float(np.mean(diff)) / 255.0)

            # Diff pixel count (threshold: delta > 10)
            diff_arr = np.abs(arr_a.astype(int) - arr_b.astype(int))
            diff_count = int(np.sum(diff_arr > 10))
            total = int(arr_a.shape[0] * arr_a.shape[1])

            # Generate and cache diff image
            diff_img = Image.new("RGBA", (min_w, min_h), (0, 0, 0, 0))
            diff_pixels = diff_img.load()
            for row in range(min_h):
                for col in range(min_w):
                    delta = int(diff_arr[row, col])
                    if delta > 10:
                        alpha = min(255, delta * 3)
                        diff_pixels[col, row] = (255, 0, 80, alpha)

            diff_buf = io.BytesIO()
            diff_img.save(diff_buf, format="PNG")
            diff_cache_key = f"comparisons/{comparison_id}/p{pg}_diff.png"
            try:
                storage.upload_raw(diff_cache_key, diff_buf.getvalue(), content_type="image/png")
            except Exception:
                pass

            page_summaries.append(ComparisonPageSummary(
                page_num=pg,
                ssim_score=round(score, 4),
                diff_pixel_count=diff_count,
                total_pixels=total,
            ))
        except Exception:
            logger.exception("Failed to compare page %d", pg)
            page_summaries.append(ComparisonPageSummary(
                page_num=pg, ssim_score=0.0, diff_pixel_count=0, total_pixels=0,
            ))

    return ComparisonResponse(
        comparison_id=comparison_id,
        page_count_a=pages_a,
        page_count_b=pages_b,
        pages=page_summaries,
    )


@router.get("/compare/{comparison_id}/pages/{page_num}/diff")
async def get_comparison_diff(
    comparison_id: str,
    page_num: int,
) -> Response:
    """Serve a cached comparison diff image (red highlights where pixels differ)."""
    storage = get_storage()
    cache_key = f"comparisons/{comparison_id}/p{page_num}_diff.png"

    try:
        content = storage.download_raw(cache_key)
        if content:
            return Response(
                content=content,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=3600"},
            )
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="Diff image not found")
