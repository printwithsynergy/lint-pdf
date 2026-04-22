"""Viewer endpoints — page tile rendering, dimensions, separation channels,
measurement tools, PDF layers, comparison, and verdict.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import logging
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any

import pikepdf
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    type: str  # "process" (CMYK) | "spot" | "rgb" (R/G/B) | "gray"


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


def _get_job_pdf_by_token(
    token: str,
    db: Session,
) -> tuple[Job, bytes]:
    """Resolve a job from a report token and return its PDF bytes.

    Used by public (unauthenticated) viewer endpoints. The token acts as
    both authentication and authorization — it proves the caller was given
    access to this specific job's report.
    """
    from lintpdf.api.models import ReportToken

    record = db.query(ReportToken).filter(ReportToken.token == token).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")

    if record.expires_at is not None and datetime.now(timezone.utc) > record.expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token expired")

    job = db.query(Job).filter(Job.id == record.job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != JobStatus.COMPLETE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is not complete",
        )
    storage = get_storage()
    try:
        pdf_bytes = storage.download_pdf(job.file_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve original PDF",
        ) from exc
    return job, pdf_bytes


def _get_job_pdf(
    job_id: str,
    tenant: Tenant,
    db: Session,
) -> tuple[Job, bytes]:
    """Fetch the job and its original PDF bytes from storage."""
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


def _expand_int_list(value: list[int] | list[str] | None) -> list[int] | None:
    """FastAPI parses ``?ocg_on=0,3`` as a single-element list
    ``["0,3"]`` when the caller uses comma-list form, and as
    ``[0, 3]`` when the caller uses repeated-query form. Normalise
    both to ``[0, 3]``. Empty / None → None.

    Raises HTTP 422 on non-numeric tokens so the user gets a clear
    error rather than an inscrutable 500.
    """
    if value is None:
        return None
    out: list[int] = []
    for item in value:
        if isinstance(item, int):
            out.append(item)
            continue
        s = str(item).strip()
        if not s:
            continue
        for tok in s.split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                out.append(int(tok))
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid OCG index '{tok}': must be an integer.",
                ) from exc
    return out or None


def _ocg_cache_suffix(ocg_on: list[int] | None, ocg_off: list[int] | None) -> str:
    """Deterministic cache-key suffix for an OCG override.

    Returns ``""`` when both inputs are absent/empty so tiles
    requested without OCG params keep using the legacy key — this
    preserves hits against the S3 cache warmed by
    ``warm_viewer_tiles`` (which only renders the default state).

    Non-empty inputs produce ``_ocg-<12-hex-of-sha256>`` from the
    sorted pair so any two requests with the same effective mask
    share a cache entry regardless of input ordering.
    """
    on = sorted(ocg_on or [])
    off = sorted(ocg_off or [])
    if not on and not off:
        return ""
    raw = f"on={','.join(map(str, on))};off={','.join(map(str, off))}".encode()
    return f"_ocg-{hashlib.sha256(raw).hexdigest()[:12]}"


def _tile_cache_key(
    tenant_id: str,
    job_id: str,
    page_num: int,
    dpi: int,
    ocg_on: list[int] | None = None,
    ocg_off: list[int] | None = None,
) -> str:
    """S3 key for a cached tile."""
    suffix = _ocg_cache_suffix(ocg_on, ocg_off)
    return f"{tenant_id}/{job_id}/tiles/p{page_num}_d{dpi}{suffix}.png"


def _channel_cache_key(
    tenant_id: str, job_id: str, page_num: int, dpi: int, channel_name: str
) -> str:
    """S3 key for a cached separation channel tile.

    Kept for backward compatibility with any call site that imports this
    name directly. The renderer module owns the canonical key format —
    see ``lintpdf.reports.separation_renderer.channel_cache_key``.
    """
    from lintpdf.reports.separation_renderer import channel_cache_key

    return channel_cache_key(tenant_id, job_id, page_num, dpi, channel_name)


def _tac_cache_key(tenant_id: str, job_id: str, page_num: int, dpi: int) -> str:
    """S3 key for a cached TAC heatmap PNG."""
    return f"{tenant_id}/{job_id}/tiles/p{page_num}_d{dpi}_tac.png"


def _tac_runs_cache_key(
    tenant_id: str, job_id: str, page_num: int, dpi: int, tac_limit: int
) -> str:
    """S3 key for cached TAC per-run metadata JSON."""
    from lintpdf.reports.separation_renderer import tac_runs_cache_key

    return tac_runs_cache_key(tenant_id, job_id, page_num, dpi, tac_limit)


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


# ---------------------------------------------------------------------------
# Optional Redis hot byte-cache for tiles (Phase 2 of the warming plan)
# ---------------------------------------------------------------------------
#
# When ``LINTPDF_TILE_HOT_CACHE_ENABLED=true`` we stash tile bytes in
# Redis for 15 min after any request. The next request for the same
# tile returns from RAM in ~1–3 ms instead of a ~100–200 ms S3 GET.
# Gated off by default because PNG tiles at 150 DPI average 50–500 KB
# and Redis memory is precious on smaller plans — the feature flag
# means ops can turn it on per-environment without a code change.


def _tile_hot_cache_key(
    tenant_id: str,
    job_id: str,
    page_num: int,
    dpi: int,
    ocg_on: list[int] | None = None,
    ocg_off: list[int] | None = None,
) -> str:
    suffix = _ocg_cache_suffix(ocg_on, ocg_off)
    return f"lintpdf:tile-hot:{tenant_id}:{job_id}:{page_num}:{dpi}{suffix}"


def _hot_cache_enabled() -> bool:
    import os as _os

    return _os.getenv("LINTPDF_TILE_HOT_CACHE_ENABLED", "false").lower() == "true"


_HOT_CACHE_TTL_S = 15 * 60  # 15 minutes — matches a typical review session


@router.get("/jobs/{job_id}/pages/{page_num}/tile")
async def get_page_tile(
    job_id: str,
    page_num: int,
    dpi: int = Query(
        default=150,
        ge=36,
        le=600,
        description="Render DPI. 36-600. Defaults to 150 (screen-friendly).",
    ),
    ocg_on: list[int] | None = Query(
        default=None,
        description=(
            "OCG (layer) indices to force **visible**, overriding the "
            "PDF's /D/OFF defaults. Indices match ``ocg_index`` from "
            "``GET /api/v1/viewer/jobs/{id}/layers``. Accepts a repeated "
            "query param (``ocg_on=0&ocg_on=3``) or a comma-list "
            "(``ocg_on=0,3``)."
        ),
    ),
    ocg_off: list[int] | None = Query(
        default=None,
        description=(
            "OCG (layer) indices to force **hidden**. Same index "
            "convention as ``ocg_on``. An index that appears in both "
            "``ocg_on`` and ``ocg_off`` is rejected with 422."
        ),
    ),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Response:
    """Render a single page as a PNG tile at the requested DPI.

    Tile read path (fastest first):
    1. Redis hot byte-cache (opt-in, ~1-3 ms).
    2. S3 tile cache (pre-warmed by ``warm_viewer_tiles`` after
       preflight completion - this is where the bytes live durably).
    3. Render on demand via ``render_page_to_image`` and populate
       both caches for the next reader.

    When ``ocg_on`` / ``ocg_off`` are omitted the response is
    byte-identical to the legacy default-state tile and shares its
    cache key, so S3 tiles warmed by ``warm_viewer_tiles`` still hit.
    """
    import contextlib as _contextlib

    from lintpdf.api.middleware import get_redis_client

    # Normalize comma-separated values that FastAPI delivered as a
    # single element (e.g. ``?ocg_on=0,3``). Repeated-param form
    # arrives already expanded.
    ocg_on = _expand_int_list(ocg_on)
    ocg_off = _expand_int_list(ocg_off)

    job, pdf_bytes = _get_job_pdf(job_id, tenant, db)
    _validate_page_num(pdf_bytes, page_num)
    storage = get_storage()
    cache_key = _tile_cache_key(str(tenant.id), str(job.id), page_num, dpi, ocg_on, ocg_off)

    hot_enabled = _hot_cache_enabled()
    redis = get_redis_client() if hot_enabled else None
    hot_key = (
        _tile_hot_cache_key(str(tenant.id), str(job.id), page_num, dpi, ocg_on, ocg_off)
        if redis is not None and dpi == 150
        else None
    )

    # 1. Redis hot byte-cache (only when the env flag is on and only
    #    for the default viewer DPI — high-DPI print tiles stay
    #    S3-only).
    if hot_key is not None and redis is not None:
        try:
            hot_bytes = redis.get(hot_key)
        except Exception:
            hot_bytes = None
        if hot_bytes:
            etag = hashlib.md5(hot_bytes[:1024]).hexdigest()
            return Response(
                content=hot_bytes,
                media_type="image/png",
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "ETag": etag,
                    "X-Tile-Source": "redis-hot",
                },
            )

    # 2. S3 tile cache
    try:
        cached = storage.download_raw(cache_key)
        if cached:
            etag = hashlib.md5(cached[:1024]).hexdigest()
            # Populate the hot cache opportunistically — the next
            # click on this page now skips S3 entirely.
            if hot_key is not None and redis is not None:
                with _contextlib.suppress(Exception):
                    redis.setex(hot_key, _HOT_CACHE_TTL_S, cached)
            return Response(
                content=cached,
                media_type="image/png",
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "ETag": etag,
                    "X-Tile-Source": "s3",
                },
            )
    except Exception:
        pass  # Cache miss — render on demand

    # 3. Render on demand
    from lintpdf.ai.rendering import OCGError, render_page_to_image

    try:
        tile_bytes = render_page_to_image(
            pdf_bytes,
            page_num,
            dpi=dpi,
            ocg_on=ocg_on,
            ocg_off=ocg_off,
        )
    except OCGError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    # Populate both caches (fire-and-forget).
    try:
        storage.upload_raw(
            cache_key,
            tile_bytes,
            content_type="image/png",
            cache_control="public, max-age=86400",
        )
    except Exception:
        logger.warning("Failed to cache tile to S3: %s", cache_key)
    if hot_key is not None and redis is not None:
        with _contextlib.suppress(Exception):
            redis.setex(hot_key, _HOT_CACHE_TTL_S, tile_bytes)

    etag = hashlib.md5(tile_bytes[:1024]).hexdigest()
    return Response(
        content=tile_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",
            "ETag": etag,
            "X-Tile-Source": "render",
        },
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
    dpi: int = Query(
        default=150,
        ge=36,
        le=600,
        description="Render DPI. 36-600. Defaults to 150 (screen-friendly).",
    ),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Response:
    """Render a single ink channel as a grayscale PNG."""
    from lintpdf.reports.separation_renderer import render_separation_channel

    # Ghostscript's tiffsep device only decomposes CMYK + spot colors.
    # For pure-RGB / pure-Gray PDFs, ``list_separations`` now correctly
    # reports those channels as ``type="rgb"`` / ``"gray"``, but the
    # separation renderer has no equivalent. Return 422 for now so the
    # viewer can surface "preview not available" instead of silently
    # producing a misleading CMYK-derived image.
    if channel_name in ("Red", "Green", "Blue", "Gray"):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Channel '{channel_name}' is a display channel, not a "
                "separation ink. LintPDF renders separations from CMYK "
                "and spot color spaces only; RGB/Gray previews are a "
                "roadmap item."
            ),
        )

    job, pdf_bytes = _get_job_pdf(job_id, tenant, db)
    _validate_page_num(pdf_bytes, page_num)
    storage = get_storage()

    # The renderer owns the S3 cache (direct hit for this channel; warm
    # all four CMYK siblings on miss) — we just surface the bytes.
    try:
        img_bytes = render_separation_channel(
            pdf_bytes,
            page_num,
            channel_name,
            dpi=dpi,
            tenant_id=str(tenant.id),
            job_id=str(job.id),
            storage=storage,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return Response(
        content=img_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


class TacRunResponse(BaseModel):
    """A text-run bbox with its mean TAC%.

    Coordinates are PDF points, origin **top-left** of the page (matching
    poppler's ``pdftotext -bbox`` output). The frontend overlay places
    SVG ``<rect>`` hit targets against the page viewport and shows a
    tooltip with ``mean_tac`` on hover.
    """

    x0: float
    y0: float
    x1: float
    y1: float
    mean_tac: float
    limit: float
    exceeds: bool


class TacRunsResponse(BaseModel):
    job_id: str
    page_num: int
    dpi: int
    tac_limit: float
    runs: list[TacRunResponse]


def _render_tac_with_runs(
    *,
    pdf_bytes: bytes,
    tenant_id: str,
    job_id: str,
    page_num: int,
    dpi: int,
    tac_limit: int,
) -> tuple[bytes, list[TacRunResponse]]:
    """Render the TAC heatmap + runs, populating both PNG and JSON caches.

    Single source of truth for the authenticated and public TAC
    endpoints so the two surfaces never drift.
    """
    import json as _json

    from lintpdf.reports.separation_renderer import render_tac_heatmap

    storage = get_storage()
    png_key = _tac_cache_key(tenant_id, job_id, page_num, dpi)
    runs_key = _tac_runs_cache_key(tenant_id, job_id, page_num, dpi, tac_limit)

    try:
        cached_png = storage.download_raw(png_key)
    except Exception:
        cached_png = None
    try:
        cached_runs_raw = storage.download_raw(runs_key)
    except Exception:
        cached_runs_raw = None

    if cached_png is not None and cached_runs_raw is not None:
        try:
            cached_runs = [TacRunResponse(**r) for r in _json.loads(cached_runs_raw)]
            return cached_png, cached_runs
        except Exception:
            # Corrupt JSON sidecar — fall through to re-render.
            logger.warning("TAC runs cache corrupt at %s; regenerating", runs_key)

    try:
        heatmap = render_tac_heatmap(
            pdf_bytes,
            page_num,
            dpi=dpi,
            tac_limit=tac_limit,
            tenant_id=tenant_id,
            job_id=job_id,
            storage=storage,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    png_bytes = heatmap["png"]
    runs = [TacRunResponse(**dict(r)) for r in heatmap["runs"]]

    try:
        storage.upload_raw(png_key, png_bytes, content_type="image/png")
    except Exception:
        logger.warning("Failed to cache TAC heatmap PNG at %s", png_key)
    try:
        storage.upload_raw(
            runs_key,
            _json.dumps([r.model_dump() for r in runs]).encode(),
            content_type="application/json",
        )
    except Exception:
        logger.warning("Failed to cache TAC runs JSON at %s", runs_key)

    return png_bytes, runs


@router.get("/jobs/{job_id}/pages/{page_num}/tac-heatmap")
async def get_tac_heatmap(
    job_id: str,
    page_num: int,
    dpi: int = Query(
        default=150,
        ge=36,
        le=600,
        description="Render DPI. 36-600. Defaults to 150 (screen-friendly).",
    ),
    tac_limit: int = Query(
        default=300,
        ge=100,
        le=500,
        description=(
            "Total area coverage threshold as a percentage (100-500). "
            "Pixels at or above this value are highlighted in the heatmap. "
            "Defaults to 300% (typical for sheetfed offset)."
        ),
    ),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Response:
    """Render a TAC heatmap overlay as an RGBA PNG."""
    job, pdf_bytes = _get_job_pdf(job_id, tenant, db)
    _validate_page_num(pdf_bytes, page_num)

    png_bytes, _runs = _render_tac_with_runs(
        pdf_bytes=pdf_bytes,
        tenant_id=str(tenant.id),
        job_id=str(job.id),
        page_num=page_num,
        dpi=dpi,
        tac_limit=tac_limit,
    )
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get(
    "/jobs/{job_id}/pages/{page_num}/tac-heatmap/runs",
    response_model=TacRunsResponse,
)
async def get_tac_runs(
    job_id: str,
    page_num: int,
    dpi: int = Query(
        default=150,
        ge=36,
        le=600,
        description="Render DPI. 36-600. Defaults to 150 (screen-friendly).",
    ),
    tac_limit: int = Query(
        default=300,
        ge=100,
        le=500,
        description="Total area coverage threshold in percent (100-500).",
    ),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> TacRunsResponse:
    """Return per-text-run mean TAC metadata for tooltip overlays.

    Coordinates are in PDF points with origin at the **top-left** of the
    page (matching poppler's ``pdftotext -bbox`` output). ``exceeds`` is
    pre-computed against ``tac_limit`` so the frontend can style the
    tooltip without re-comparing.
    """
    job, pdf_bytes = _get_job_pdf(job_id, tenant, db)
    _validate_page_num(pdf_bytes, page_num)
    _png, runs = _render_tac_with_runs(
        pdf_bytes=pdf_bytes,
        tenant_id=str(tenant.id),
        job_id=str(job.id),
        page_num=page_num,
        dpi=dpi,
        tac_limit=tac_limit,
    )
    return TacRunsResponse(
        job_id=str(job.id),
        page_num=page_num,
        dpi=dpi,
        tac_limit=float(tac_limit),
        runs=runs,
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
    # Resolved branding (stripped entirely when ``anonymous=True``)
    brand_name: str | None = "LintPDF"
    brand_logo_url: str | None = _LINTPDF_DEFAULT_LOGO
    brand_primary_color: str | None = "#1a3a7a"
    brand_accent_color: str | None = "#2563eb"
    # Surface metadata — clients use these to show or hide tenant chrome.
    anonymous: bool = False
    tenant_name: str | None = None
    support_email: str | None = None
    # How findings were produced for this job — drives the viewer's
    # "Load" affordances and empty-state copy.
    preflight_source: str = "engine"
    # Per-capability availability map. ``True`` means the tool is
    # backed by data; ``False`` means unavailable (the UI may offer a
    # one-click fill-in for supported capabilities).
    capabilities: dict[str, bool] = {}
    # Whether the tenant's plan allows on-demand capability fill-in.
    # When ``False`` the UI must hide Load buttons and render the
    # ``UpgradePrompt`` component instead.
    capability_fillin_enabled: bool = True
    # Whether the tenant's plan allows annotation tools in the viewer.
    annotations_enabled: bool = True
    # Whether the tenant's plan allows downloadable reports. When empty
    # the UI must disable PDF/JSON/XML download buttons.
    allowed_report_formats: list[str] = []
    tile_cdn_base: str | None = None


def _apply_branding_to_config(config: ViewerConfigResponse, branding: Any, tenant: Tenant) -> None:
    """Project a :class:`BrandingContext` onto a :class:`ViewerConfigResponse`.

    ``branding.anonymous`` wipes every identifying field so the viewer
    frame shows no broker OR LintPDF chrome.
    """
    if getattr(branding, "anonymous", False):
        config.anonymous = True
        config.brand_name = None
        config.brand_logo_url = None
        config.brand_primary_color = None
        config.brand_accent_color = None
        config.tenant_name = None
        config.support_email = None
        return

    config.anonymous = False
    config.brand_name = branding.name or "LintPDF"
    config.brand_logo_url = branding.logo_url
    config.brand_primary_color = branding.primary_color or config.brand_primary_color
    config.brand_accent_color = branding.accent_color or config.brand_accent_color
    config.tenant_name = tenant.name
    config.support_email = getattr(tenant, "contact_email", None)


def _build_viewer_config(
    *,
    job: Job,
    tenant: Tenant,
    db: Session,
    brand_param: str | None,
    overrides_dict: dict[str, Any] | None = None,
) -> ViewerConfigResponse:
    """Shared builder for authenticated + public viewer config endpoints.

    ``overrides_dict`` is the per-token or per-job override envelope
    (``lintpdf.overrides.OverridesEnvelope`` serialised to a dict). When
    present, its ``viewer`` section is applied last, overriding any
    value the brand-profile layer had set. This is how a single tenant
    can mint multiple tokens for the same job with different viewer UI
    shapes.
    """
    from lintpdf.reports.service import BrandingContext, resolve_branding

    caps = dict(job.data_capabilities or {})
    # ``tac_runs`` is derived on demand from the PDF's CMYK channels — it
    # does not have a dedicated analyzer, so it tracks ``tac``. If TAC
    # data is available, so is the per-run tooltip metadata. This keeps
    # the capability registry honest for the viewer frontend.
    if "tac" in caps:
        caps.setdefault("tac_runs", bool(caps.get("tac")))
    # ``tiles_warmed`` flips to true when the background warming task
    # has finished rendering every page tile into S3. The frontend uses
    # the flag to decide whether to kick the browser-side prefetch pass
    # (which shouldn't run against still-cold tiles). Resolved lazily
    # from Redis so no extra schema cost.
    caps["tiles_warmed"] = _is_warming_complete(str(job.id))

    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)

    config = ViewerConfigResponse(
        preflight_source=(
            job.preflight_source.value
            if hasattr(job.preflight_source, "value")
            else str(job.preflight_source or "engine")
        ),
        capabilities=caps,
        capability_fillin_enabled=entitlements.capability_fillin_enabled,
        annotations_enabled=entitlements.annotations_enabled,
        allowed_report_formats=list(entitlements.allowed_report_formats),
    )
    # When the plan forbids annotations, force the annotations toggle
    # off regardless of what the profile / brand / override layer says.
    # This is the immutable constraint — the frontend never sees an
    # annotate tool on a Viewer-tier tenant.
    if not entitlements.annotations_enabled:
        config.enable_annotations = False
    # Likewise for report downloads — the download button in the viewer
    # chrome uses ``enable_download`` to decide whether to render.
    if not entitlements.allowed_report_formats:
        config.enable_download = False

    def _lookup_profile(profile_id: str) -> BrandProfile | None:
        try:
            pid = uuid_mod.UUID(profile_id)
        except ValueError:
            return None
        return (
            db.query(BrandProfile)
            .filter(BrandProfile.id == pid, BrandProfile.tenant_id == tenant.id)
            .first()
        )

    branding = resolve_branding(
        tenant=tenant,
        job=job,
        brand_param=brand_param,
        default_lintpdf=BrandingContext(),
        lookup_profile=_lookup_profile,
    )
    _apply_branding_to_config(config, branding, tenant)

    # Merge the tenant's default brand profile viewer_config (toolbar
    # layout, zoom defaults, etc.) — but only when not anonymous.
    if not config.anonymous and tenant.default_brand_profile_id:
        profile = (
            db.query(BrandProfile)
            .filter(
                BrandProfile.id == tenant.default_brand_profile_id,
                BrandProfile.tenant_id == tenant.id,
            )
            .first()
        )
        if profile and profile.viewer_config:
            vc = profile.viewer_config
            for field_name in ViewerConfigResponse.model_fields:
                if field_name.startswith("brand_"):
                    continue
                if field_name in {
                    "anonymous",
                    "tenant_name",
                    "support_email",
                    "preflight_source",
                    "capabilities",
                }:
                    continue
                if field_name in vc:
                    setattr(config, field_name, vc[field_name])

    # Per-call override envelope wins over every other layer — the
    # caller explicitly asked for these viewer flags when they submitted
    # the job or minted the token. See ``lintpdf.overrides.envelope``
    # for the ``viewer`` schema. Unknown keys are ignored so a future
    # OverridesEnvelope field doesn't break older rows stored in the DB.
    if overrides_dict:
        viewer_override = overrides_dict.get("viewer") or {}
        protected = {
            "anonymous",
            "tenant_name",
            "support_email",
            "preflight_source",
            "capabilities",
        }
        for field_name, value in viewer_override.items():
            if value is None:
                continue
            if field_name in protected:
                continue
            if field_name in ViewerConfigResponse.model_fields:
                setattr(config, field_name, value)

    from lintpdf.api.config import get_settings as _cdn_settings

    _settings = _cdn_settings()
    if _settings.tile_cdn_base_url and caps.get("tiles_warmed"):
        cdn_base = _settings.tile_cdn_base_url.rstrip("/")
        config.tile_cdn_base = f"{cdn_base}/{tenant.id}/{job.id}/tiles/"

    return config


@router.get("/jobs/{job_id}/config", response_model=ViewerConfigResponse)
async def get_viewer_config(
    job_id: str,
    brand: str | None = Query(
        default=None,
        description=(
            "Branding override: 'anonymous' (strip all branding), "
            "'lintpdf' (LintPDF default), or a BrandProfile UUID."
        ),
    ),
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

    return _build_viewer_config(
        job=job,
        tenant=tenant,
        db=db,
        brand_param=brand,
        overrides_dict=job.overrides,
    )


# ---------------------------------------------------------------------------
# Tile warming status (Redis-backed progress)
# ---------------------------------------------------------------------------


class TileWarmingStatusResponse(BaseModel):
    """Warming progress for the per-job viewer tile pre-render task.

    The viewer polls this endpoint to show a "Preparing pages N/M..."
    badge so reviewers know when background pre-caching has finished.
    ``status`` values:

    - ``pending`` — job isn't COMPLETE yet (nothing to warm).
    - ``in_progress`` — worker is rendering tiles into S3.
    - ``complete`` — every page tile at the default DPI (and the
      thumbnail-DPI variants) is cached.
    - ``failed`` — the worker crashed; ``error`` carries a message.
    - ``disabled`` — warming is off (no Redis configured or the
      ``LINTPDF_TILE_WARMING_ENABLED`` env gate is false). The viewer
      can still render tiles on-demand; they just won't be pre-warmed.
    """

    job_id: str
    status: str
    rendered: int
    total: int
    dpi: int
    percent: int
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None


def _is_warming_complete(job_id: str) -> bool:
    """Cheap Redis probe: has ``warm_viewer_tiles`` finished for this job?

    Used by the viewer-config builder to surface a ``tiles_warmed``
    capability flag. Reads a single hash field (``HGET``) so it's a
    ~1 ms lookup; falls back to ``False`` on any error.
    """
    from lintpdf.api.middleware import get_redis_client
    from lintpdf.queue.tasks import _tile_warm_status_key

    redis = get_redis_client()
    if redis is None:
        return False
    try:
        value = redis.hget(_tile_warm_status_key(job_id), "status")
    except Exception:
        return False
    if value is None:
        return False
    decoded = value.decode() if isinstance(value, bytes) else str(value)
    return decoded == "complete"


def _load_tile_warming_status(
    *,
    job_id: str,
    page_count: int,
    job_created_at: datetime | None = None,
) -> TileWarmingStatusResponse:
    """Read the warming-status hash from Redis and shape it for the client.

    Shared by the authenticated and public surfaces so the two stay in
    sync. When Redis isn't configured or the key is missing, returns a
    synthetic ``disabled``/``pending`` response so the frontend can
    still render a sensible badge without special-casing the null.
    """
    from lintpdf.api.middleware import get_redis_client
    from lintpdf.queue.tasks import _tile_warm_status_key

    redis = get_redis_client()
    if redis is None:
        return TileWarmingStatusResponse(
            job_id=job_id,
            status="disabled",
            rendered=0,
            total=page_count,
            dpi=150,
            percent=100 if page_count == 0 else 0,
        )

    try:
        raw = redis.hgetall(_tile_warm_status_key(job_id))
    except Exception:
        logger.warning("tile-warming: Redis hgetall failed for %s", job_id)
        raw = None

    if not raw:
        stale_threshold = 300
        if job_created_at is not None:
            age = (datetime.now(timezone.utc) - job_created_at).total_seconds()
            if age > stale_threshold:
                return TileWarmingStatusResponse(
                    job_id=job_id,
                    status="disabled",
                    rendered=0,
                    total=page_count,
                    dpi=150,
                    percent=0,
                )
        return TileWarmingStatusResponse(
            job_id=job_id,
            status="pending",
            rendered=0,
            total=page_count,
            dpi=150,
            percent=0,
        )

    def _decode(value: Any) -> str:
        return value.decode() if isinstance(value, bytes) else str(value)

    decoded = {_decode(k): _decode(v) for k, v in raw.items()}

    try:
        rendered = int(decoded.get("rendered", "0"))
        total = int(decoded.get("total", page_count))
        dpi = int(decoded.get("dpi", 150))
    except ValueError:
        rendered, total, dpi = 0, page_count, 150

    status_value = decoded.get("status", "pending")
    percent = 100 if total == 0 else round((rendered / total) * 100)
    if status_value == "complete":
        percent = 100

    return TileWarmingStatusResponse(
        job_id=job_id,
        status=status_value,
        rendered=rendered,
        total=total,
        dpi=dpi,
        percent=percent,
        started_at=decoded.get("started_at"),
        completed_at=decoded.get("completed_at"),
        error=decoded.get("error"),
    )


@router.get(
    "/jobs/{job_id}/tile-warming",
    response_model=TileWarmingStatusResponse,
)
async def get_tile_warming_status(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> TileWarmingStatusResponse:
    """Report the current tile-warming progress for a job.

    Reads from the Redis hash written by the
    ``lintpdf.viewer.warm_tiles`` Celery task. The viewer polls this
    every 1.5 s until ``status`` settles into ``complete``, ``failed``,
    or ``disabled``.
    """
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    job = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return _load_tile_warming_status(
        job_id=job_id,
        page_count=int(job.page_count or 0),
        job_created_at=job.created_at,
    )


# ---------------------------------------------------------------------------
# Capability fill-in (on-demand analyzer runs for minimal / external jobs)
# ---------------------------------------------------------------------------


#: Capabilities the viewer can request on-demand. Keep in sync with
#: ``lintpdf.queue.tasks._CAPABILITY_ANALYZERS``.
_FILLABLE_CAPABILITIES: frozenset[str] = frozenset({"separations", "tac", "fonts", "images"})


class CapabilityFillResponse(BaseModel):
    job_id: str
    capability: str
    status: str  # "queued" | "already_filled"
    task_id: str | None = None


@router.post(
    "/jobs/{job_id}/capabilities/{capability}",
    response_model=CapabilityFillResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def fill_job_capability(
    job_id: str,
    capability: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CapabilityFillResponse:
    """Queue a one-off analyzer run to populate a missing viewer capability.

    Only applies to jobs whose ``data_capabilities[capability]`` is false —
    typically minimal or external-import jobs where the imported report
    didn't cover this tool.
    """
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    if capability not in _FILLABLE_CAPABILITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Capability {capability!r} cannot be filled on demand. "
                f"Supported: {sorted(_FILLABLE_CAPABILITIES)}"
            ),
        )

    from lintpdf.api.gates import plan_upgrade_required
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)
    if not entitlements.capability_fillin_enabled:
        raise plan_upgrade_required(
            gate="capability_fillin",
            current_plan=str(tenant.plan),
            required_plan="starter",
            message=(
                f"Your plan ({tenant.plan}) does not allow on-demand capability "
                f"fill-in. Upgrade to Starter to unlock findings, separations, "
                f"TAC, fonts, and images."
            ),
        )

    job = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    caps = dict(job.data_capabilities or {})
    if caps.get(capability) is True:
        return CapabilityFillResponse(job_id=job_id, capability=capability, status="already_filled")

    from lintpdf.queue.tasks import fill_capability

    task = fill_capability.apply_async(
        args=[str(uid), capability],
        queue="default",
    )
    return CapabilityFillResponse(
        job_id=job_id,
        capability=capability,
        status="queued",
        task_id=getattr(task, "id", None),
    )


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
    dpi: int = Query(
        default=300,
        ge=72,
        le=600,
        description=(
            "Render DPI at which the point was sampled. Higher values resolve "
            "finer geometry. 72-600, defaults to 300."
        ),
    ),
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


class DensitometerChannelResponse(BaseModel):
    name: str
    percent: float


class DensitometerResponse(BaseModel):
    x: float
    y: float
    dpi: int
    channels: list[DensitometerChannelResponse]
    tac: float
    tac_limit: float
    limit_exceeded: bool


async def _sample_densitometer(
    pdf_bytes: bytes,
    page_num: int,
    x: float,
    y: float,
    dpi: int,
    tac_limit: float,
    *,
    tenant_id: str | None = None,
    job_id: str | None = None,
) -> DensitometerResponse:
    """Shared helper: run ``sample_densitometer`` off-loop and box the result.

    Used by both the authenticated and the public token-scoped densitometer
    endpoints. Runs in a thread because Ghostscript shells out and we don't
    want to block the FastAPI event loop. When ``tenant_id``/``job_id`` are
    supplied, the CMYK S3 cache is consulted — second-click reads skip
    Ghostscript entirely.
    """
    from lintpdf.reports.separation_renderer import sample_densitometer

    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_num - 1]
        mb = page.get("/MediaBox")
        if mb is None:
            raise HTTPException(status_code=500, detail="Page has no MediaBox")
        mb_vals = [float(v) for v in mb]

    page_w = mb_vals[2] - mb_vals[0]
    page_h = mb_vals[3] - mb_vals[1]
    # Translate MediaBox-origin coordinate (bottom-left of the crop) into
    # a 0-origin sample — consistent with sample_color above.
    local_x = x - mb_vals[0]
    local_y = y - mb_vals[1]

    storage = get_storage() if (tenant_id and job_id) else None

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: sample_densitometer(
                pdf_bytes,
                page_num,
                x=local_x,
                y=local_y,
                page_w=page_w,
                page_h=page_h,
                dpi=dpi,
                tac_limit=tac_limit,
                tenant_id=tenant_id,
                job_id=job_id,
                storage=storage,
            ),
        )
    except RuntimeError as exc:
        # No CMYK channels (RGB-only PDF) or Ghostscript failure. Surface as
        # 422 so the UI can render a "no separations available" hint.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return DensitometerResponse(**result)  # type: ignore[arg-type]


@router.get("/jobs/{job_id}/pages/{page_num}/densitometer")
async def sample_densitometer_auth(
    job_id: str,
    page_num: int,
    x: float = Query(..., description="X coordinate in PDF points"),
    y: float = Query(..., description="Y coordinate in PDF points"),
    dpi: int = Query(default=300, ge=72, le=600),
    tac_limit: float = Query(default=300, ge=100, le=500),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> DensitometerResponse:
    """Sample per-channel ink coverage and TAC at a point on a PDF page.

    Runs Ghostscript ``tiffsep`` to decompose the page into CMYK + spot
    channel rasters, then reads a 3x3 patch around the sampled pixel on
    each channel. Returns ``{channels: [{name, percent}], tac,
    limit_exceeded}``. Every plan tier has access — this is a free QA
    tool, not a gated premium capability.
    """
    job, pdf_bytes = _get_job_pdf(job_id, tenant, db)
    _validate_page_num(pdf_bytes, page_num)
    return await _sample_densitometer(
        pdf_bytes,
        page_num,
        x,
        y,
        dpi,
        tac_limit,
        tenant_id=str(tenant.id),
        job_id=str(job.id),
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
                    ocg = (
                        ocg_ref.resolve()
                        if callable(getattr(ocg_ref, "resolve", None))
                        else ocg_ref
                    )
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

    previous_verdict = job.verdict
    job.verdict = body.verdict
    job.verdict_by = reviewer_email
    job.verdict_at = now
    job.verdict_notes = body.notes
    db.commit()

    if previous_verdict != body.verdict:
        from lintpdf.webhooks.events import fire_job_state_changed, fire_verdict_changed

        fire_verdict_changed(db, job, tenant.id, previous_verdict=previous_verdict)
        fire_job_state_changed(db, job, tenant.id, reason="verdict.changed")
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
            with contextlib.suppress(Exception):
                storage.upload_raw(diff_cache_key, diff_buf.getvalue(), content_type="image/png")

            page_summaries.append(
                ComparisonPageSummary(
                    page_num=pg,
                    ssim_score=round(score, 4),
                    diff_pixel_count=diff_count,
                    total_pixels=total,
                )
            )
        except Exception:
            logger.exception("Failed to compare page %d", pg)
            page_summaries.append(
                ComparisonPageSummary(
                    page_num=pg,
                    ssim_score=0.0,
                    diff_pixel_count=0,
                    total_pixels=0,
                )
            )

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


# ---------------------------------------------------------------------------
# Public token-based viewer endpoints (no tenant auth)
# ---------------------------------------------------------------------------


@router.get("/public/{token}/pages")
async def public_list_pages(token: str, db: Session = Depends(get_db)) -> PagesResponse:
    """Public: list pages via report token."""
    job, pdf_bytes = _get_job_pdf_by_token(token, db)
    pages: list[PageInfo] = []
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            media = _extract_box(page, "/MediaBox")
            if media is None:
                media = PageBox(x0=0, y0=0, x1=612, y1=792)
            pages.append(
                PageInfo(
                    page_num=i,
                    width_pts=media.x1 - media.x0,
                    height_pts=media.y1 - media.y0,
                    media_box=media,
                    crop_box=_extract_box(page, "/CropBox"),
                    trim_box=_extract_box(page, "/TrimBox"),
                    bleed_box=_extract_box(page, "/BleedBox"),
                    rotation=int(page.get("/Rotate", 0)),
                )
            )
    return PagesResponse(job_id=str(job.id), page_count=len(pages), pages=pages)


@router.get("/public/{token}/pages/{page_num}/tile")
async def public_get_tile(
    token: str,
    page_num: int,
    dpi: int = Query(default=150, ge=36, le=600),
    db: Session = Depends(get_db),
) -> Response:
    """Public: render a page tile as PNG."""
    _job, pdf_bytes = _get_job_pdf_by_token(token, db)
    _validate_page_num(pdf_bytes, page_num)
    from lintpdf.ai.rendering import render_page_to_image

    png = render_page_to_image(pdf_bytes, page_num, dpi=dpi)
    return Response(
        content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"}
    )


@router.get("/public/{token}/pages/{page_num}/info")
async def public_page_info(
    token: str,
    page_num: int,
    db: Session = Depends(get_db),
) -> dict:
    """Public: get page dimensions and box info."""
    _job, pdf_bytes = _get_job_pdf_by_token(token, db)
    _validate_page_num(pdf_bytes, page_num)
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_num - 1]
        media = _extract_box(page, "/MediaBox") or PageBox(x0=0, y0=0, x1=612, y1=792)
        return {
            "page_num": page_num,
            "width_pts": media.x1 - media.x0,
            "height_pts": media.y1 - media.y0,
            "media_box": media.model_dump(),
            "crop_box": (_extract_box(page, "/CropBox") or media).model_dump(),
            "trim_box": (b.model_dump() if (b := _extract_box(page, "/TrimBox")) else None),
            "bleed_box": (b2.model_dump() if (b2 := _extract_box(page, "/BleedBox")) else None),
        }


@router.get("/public/{token}/separations")
async def public_separations(token: str, db: Session = Depends(get_db)) -> dict:
    """Public: list ink separation channels."""
    job, pdf_bytes = _get_job_pdf_by_token(token, db)
    from lintpdf.reports.separation_renderer import list_separations

    channels = list_separations(pdf_bytes)
    return {"job_id": str(job.id), "channels": channels}


@router.get("/public/{token}/pages/{page_num}/channel/{channel_name}")
async def public_channel(
    token: str,
    page_num: int,
    channel_name: str,
    dpi: int = Query(
        default=150,
        ge=36,
        le=600,
        description="Render DPI. 36-600. Defaults to 150 (screen-friendly).",
    ),
    db: Session = Depends(get_db),
) -> Response:
    """Public: render a separation channel as grayscale PNG."""
    job, pdf_bytes = _get_job_pdf_by_token(token, db)
    _validate_page_num(pdf_bytes, page_num)
    from lintpdf.reports.separation_renderer import render_separation_channel

    storage = get_storage()
    try:
        png = render_separation_channel(
            pdf_bytes,
            page_num,
            channel_name,
            dpi=dpi,
            tenant_id=str(job.tenant_id),
            job_id=str(job.id),
            storage=storage,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"}
    )


@router.get("/public/{token}/pages/{page_num}/tac-heatmap")
async def public_tac_heatmap(
    token: str,
    page_num: int,
    dpi: int = Query(
        default=150,
        ge=36,
        le=600,
        description="Render DPI. 36-600. Defaults to 150 (screen-friendly).",
    ),
    tac_limit: int = Query(
        default=300,
        ge=100,
        le=500,
        description=(
            "Total area coverage threshold as a percentage (100-500). "
            "Pixels at or above this value are highlighted in the heatmap."
        ),
    ),
    db: Session = Depends(get_db),
) -> Response:
    """Public: render TAC heatmap overlay as RGBA PNG."""
    job, pdf_bytes = _get_job_pdf_by_token(token, db)
    _validate_page_num(pdf_bytes, page_num)

    png_bytes, _runs = _render_tac_with_runs(
        pdf_bytes=pdf_bytes,
        tenant_id=str(job.tenant_id),
        job_id=str(job.id),
        page_num=page_num,
        dpi=dpi,
        tac_limit=tac_limit,
    )
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get(
    "/public/{token}/pages/{page_num}/tac-heatmap/runs",
    response_model=TacRunsResponse,
)
async def public_tac_runs(
    token: str,
    page_num: int,
    dpi: int = Query(default=150, ge=36, le=600),
    tac_limit: int = Query(default=300, ge=100, le=500),
    db: Session = Depends(get_db),
) -> TacRunsResponse:
    """Public: per-text-run mean TAC metadata for tooltip overlays."""
    job, pdf_bytes = _get_job_pdf_by_token(token, db)
    _validate_page_num(pdf_bytes, page_num)
    _png, runs = _render_tac_with_runs(
        pdf_bytes=pdf_bytes,
        tenant_id=str(job.tenant_id),
        job_id=str(job.id),
        page_num=page_num,
        dpi=dpi,
        tac_limit=tac_limit,
    )
    return TacRunsResponse(
        job_id=str(job.id),
        page_num=page_num,
        dpi=dpi,
        tac_limit=float(tac_limit),
        runs=runs,
    )


@router.get(
    "/public/{token}/tile-warming",
    response_model=TileWarmingStatusResponse,
)
async def public_tile_warming_status(
    token: str, db: Session = Depends(get_db)
) -> TileWarmingStatusResponse:
    """Public: tile-warming progress for a share-link viewer."""
    job, _pdf = _get_job_pdf_by_token(token, db)
    return _load_tile_warming_status(
        job_id=str(job.id),
        page_count=int(job.page_count or 0),
        job_created_at=job.created_at,
    )


@router.get("/public/{token}/config")
async def public_config(token: str, db: Session = Depends(get_db)) -> dict:
    """Public: get viewer configuration for a share-link viewer.

    Branding is read from the :class:`ReportToken` snapshot captured at
    mint time — so the shared viewer keeps the brand the broker chose
    regardless of later tenant setting changes.
    """
    from lintpdf.api.models import ReportToken

    record = db.query(ReportToken).filter(ReportToken.token == token).first()
    if not record:
        raise HTTPException(status_code=404, detail="Token not found")

    job = db.query(Job).filter(Job.id == record.job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Token not found")

    tenant = db.query(Tenant).filter(Tenant.id == record.tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Token not found")

    # Translate the token's captured brand_mode into the same query-param
    # shape ``_build_viewer_config`` expects.
    brand_param: str | None = None
    if record.brand_mode == "anonymous":
        brand_param = "anonymous"
    elif record.brand_mode == "lintpdf":
        brand_param = "lintpdf"
    elif record.brand_mode == "profile" and record.brand_profile_id:
        brand_param = str(record.brand_profile_id)

    # Layer: per-token overrides (highest priority) fall back to per-job
    # overrides. The token snapshot is what the minter asked for at share
    # time; if it's absent, the job's own overrides still apply.
    overrides_for_config = record.overrides or job.overrides

    config = _build_viewer_config(
        job=job,
        tenant=tenant,
        db=db,
        brand_param=brand_param,
        overrides_dict=overrides_for_config,
    )
    # Surface the token's annotation permission on the public config so the
    # viewer UI can enable / disable the Mark Up toolbar accordingly. On the
    # authenticated viewer this is always implicitly true.
    payload = config.model_dump()
    payload["allow_annotations"] = bool(record.allow_annotations)
    return payload


@router.get("/public/{token}/pages/{page_num}/sample")
async def public_sample(
    token: str,
    page_num: int,
    x: float = Query(default=0, description="X coordinate in PDF points."),
    y: float = Query(default=0, description="Y coordinate in PDF points."),
    dpi: int = Query(
        default=300,
        ge=72,
        le=600,
        description=(
            "Render DPI at which the point was sampled. Higher values resolve "
            "finer geometry. 72-600, defaults to 300."
        ),
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Public: densitometer color sample."""
    _job, pdf_bytes = _get_job_pdf_by_token(token, db)
    _validate_page_num(pdf_bytes, page_num)
    from PIL import Image

    from lintpdf.ai.rendering import render_page_to_image

    png = render_page_to_image(pdf_bytes, page_num, dpi=dpi)
    img = Image.open(io.BytesIO(png)).convert("RGB")
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_num - 1]
        mb = _extract_box(page, "/MediaBox") or PageBox(x0=0, y0=0, x1=612, y1=792)
    pw, ph = mb.x1 - mb.x0, mb.y1 - mb.y0
    px = int((x - mb.x0) / pw * img.width) if pw > 0 else 0
    py = int((1 - (y - mb.y0) / ph) * img.height) if ph > 0 else 0
    px = max(0, min(px, img.width - 1))
    py = max(0, min(py, img.height - 1))
    r, g, b = img.getpixel((px, py))
    return {"x": x, "y": y, "rgb": [r, g, b], "hex": f"#{r:02x}{g:02x}{b:02x}", "tac": None}


@router.get("/public/{token}/pages/{page_num}/densitometer")
async def public_densitometer(
    token: str,
    page_num: int,
    x: float = Query(..., description="X coordinate in PDF points"),
    y: float = Query(..., description="Y coordinate in PDF points"),
    dpi: int = Query(default=300, ge=72, le=600),
    tac_limit: float = Query(default=300, ge=100, le=500),
    db: Session = Depends(get_db),
) -> DensitometerResponse:
    """Public: per-channel CMYK + spot ink densitometer reading."""
    job, pdf_bytes = _get_job_pdf_by_token(token, db)
    _validate_page_num(pdf_bytes, page_num)
    return await _sample_densitometer(
        pdf_bytes,
        page_num,
        x,
        y,
        dpi,
        tac_limit,
        tenant_id=str(job.tenant_id),
        job_id=str(job.id),
    )


@router.get("/public/{token}/layers")
async def public_layers(token: str, db: Session = Depends(get_db)) -> dict:
    """Public: list PDF layers (OCGs)."""
    _job, pdf_bytes = _get_job_pdf_by_token(token, db)
    layers = []
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        ocprops = pdf.Root.get("/OCProperties")
        if ocprops:
            ocgs = ocprops.get("/OCGs", [])
            for i, ocg in enumerate(ocgs):
                name = str(ocg.get("/Name", f"Layer {i + 1}"))
                layers.append({"name": name, "ocg_index": i, "default_on": True})
    return {"layers": layers}


@router.get("/public/{token}/verdict")
async def public_verdict(token: str, db: Session = Depends(get_db)) -> dict:
    """Public: get verdict (read-only)."""
    job, _ = _get_job_pdf_by_token(token, db)
    passed = True
    if job.result_json:
        passed = job.result_json.get("summary", {}).get("passed", True)
    return {
        "verdict": job.verdict,
        "auto_passed": passed,
        "verdict_by": job.verdict_by,
        "verdict_at": job.verdict_at.isoformat() if job.verdict_at else None,
        "notes": job.verdict_notes,
    }


@router.get("/public/{token}/state")
async def public_state(
    token: str, include: str | None = None, db: Session = Depends(get_db)
) -> dict:
    """Public share-link mirror of ``/api/v1/jobs/{id}/state``.

    Returns the same shape the tenant-authenticated digest does **minus**
    the ``reports`` section — listing every share-link token for the job
    from a single token would leak sibling shares that the current
    visitor wasn't handed. Everything else (preflight summary, verdict
    with notes, approval chain with per-step notes, annotations with
    comments embedded) is already exposed via the existing public
    endpoints; this endpoint just stitches them into one round trip.

    Accepted ``?include=`` keys: ``approval_chain``, ``verdict``,
    ``annotations`` (default = all three).
    """
    from lintpdf.api.models import (
        ApprovalChain,
        ApprovalStep,
        ViewerAnnotation,
        ViewerAnnotationComment,
    )

    allowed = {"approval_chain", "verdict", "annotations"}
    if include is None or not include.strip():
        wanted = set(allowed)
    else:
        wanted = set()
        for part in include.split(","):
            key = part.strip()
            if not key:
                continue
            if key not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Unknown include key {key!r}. Expected any of: "
                        f"{', '.join(sorted(allowed))}."
                    ),
                )
            wanted.add(key)

    job, _ = _get_job_pdf_by_token(token, db)

    # Core summary — always included so the caller knows WHICH job they got.
    out: dict[str, Any] = {
        "job": {
            "job_id": str(job.id),
            "status": job.status.value if hasattr(job.status, "value") else str(job.status),
            "profile_id": job.profile_id,
            "file_name": job.file_name,
            "page_count": job.page_count,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        },
    }
    if job.result_json:
        summary = job.result_json.get("summary") or {}
        out["summary"] = {
            "total_findings": summary.get("total_findings", 0),
            "error_count": summary.get("error_count", 0),
            "warning_count": summary.get("warning_count", 0),
            "advisory_count": summary.get("advisory_count", 0),
            "passed": summary.get("passed", True),
            "page_count": summary.get("page_count", 0),
            "file_size_bytes": summary.get("file_size_bytes", 0),
        }

    if "verdict" in wanted:
        auto_passed = None
        if job.result_json:
            auto_passed = (job.result_json.get("summary") or {}).get("passed")
        out["verdict"] = {
            "verdict": job.verdict,
            "auto_passed": auto_passed,
            "verdict_by": job.verdict_by,
            "verdict_at": job.verdict_at.isoformat() if job.verdict_at else None,
            "notes": job.verdict_notes,
        }

    if "approval_chain" in wanted:
        chain = db.query(ApprovalChain).filter(ApprovalChain.job_id == job.id).first()
        if chain is None:
            out["approval_chain"] = None
        else:
            steps = (
                db.query(ApprovalStep)
                .filter(ApprovalStep.chain_id == chain.id)
                .order_by(ApprovalStep.step_index, ApprovalStep.created_at)
                .all()
            )
            out["approval_chain"] = {
                "id": str(chain.id),
                "template_id": str(chain.template_id) if chain.template_id else None,
                "status": chain.status,
                "current_step": chain.current_step,
                "step_history": [
                    {
                        "step_index": s.step_index,
                        "step_name": s.step_name,
                        "approver_email": s.approver_email,
                        "decision": s.decision,
                        "notes": s.notes,
                        "decided_at": s.decided_at.isoformat() if s.decided_at else None,
                    }
                    for s in steps
                ],
                "created_at": chain.created_at.isoformat() if chain.created_at else None,
                "completed_at": chain.completed_at.isoformat() if chain.completed_at else None,
            }

    if "annotations" in wanted:
        ann_rows = (
            db.query(ViewerAnnotation)
            .filter(ViewerAnnotation.job_id == job.id)
            .order_by(ViewerAnnotation.created_at.asc())
            .all()
        )
        comments_by_ann: dict[str, list[dict]] = {}
        if ann_rows:
            comment_rows = (
                db.query(ViewerAnnotationComment)
                .filter(ViewerAnnotationComment.annotation_id.in_([r.id for r in ann_rows]))
                .order_by(ViewerAnnotationComment.created_at.asc())
                .all()
            )
            for c in comment_rows:
                comments_by_ann.setdefault(str(c.annotation_id), []).append(
                    {
                        "id": str(c.id),
                        "annotation_id": str(c.annotation_id),
                        "author_email": c.author_email,
                        "body": c.body,
                        "created_at": c.created_at.isoformat(),
                        "updated_at": c.updated_at.isoformat(),
                    }
                )
        by_page: dict[str, int] = {}
        items = []
        for r in ann_rows:
            by_page[str(r.page_num)] = by_page.get(str(r.page_num), 0) + 1
            items.append(
                {
                    "id": str(r.id),
                    "job_id": str(r.job_id),
                    "page_num": r.page_num,
                    "kind": r.kind,
                    "geometry": r.geometry_json,
                    "color": r.color,
                    "text": r.text,
                    "author_email": r.author_email,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat(),
                    "comments": comments_by_ann.get(str(r.id), []),
                }
            )
        out["annotations"] = {"total": len(ann_rows), "by_page": by_page, "items": items}

    return out


class ShareRequest(BaseModel):
    emails: list[str]
    from_name: str | None = None
    from_email: str | None = None
    message: str | None = None


@router.post("/public/{token}/share")
async def public_share(
    token: str,
    body: ShareRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Public: email the interactive viewer link to one or more recipients.

    Anyone with the token can forward the report. Rate-limited implicitly
    by the viewer page's email gate.
    """
    import re as _re

    from lintpdf.api.config import get_settings
    from lintpdf.api.models import BrandProfile, Tenant
    from lintpdf.email.service import send_report

    # Validate emails
    email_re = _re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    emails = [e.strip() for e in body.emails if e and e.strip()]
    emails = [e for e in emails if email_re.match(e)]
    if not emails:
        raise HTTPException(status_code=400, detail="At least one valid email required.")
    if len(emails) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 recipients per share.")

    job, _ = _get_job_pdf_by_token(token, db)

    # Resolve branding
    tenant = db.query(Tenant).filter(Tenant.id == job.tenant_id).first()
    profile = None
    if tenant and tenant.default_brand_profile_id:
        profile = (
            db.query(BrandProfile)
            .filter(BrandProfile.id == tenant.default_brand_profile_id)
            .first()
        )

    settings = get_settings()
    app_base = settings.app_base_url.rstrip("/")
    if tenant and getattr(tenant, "app_custom_domain", None) and tenant.app_custom_domain_verified:
        app_base = f"https://{tenant.app_custom_domain}"

    viewer_url = f"{app_base}/view/{token}"
    brand_name = (
        (profile.brand_name if profile else None)
        or (tenant.brand_name if tenant else None)
        or "LintPDF"
    )
    brand_color = (
        (profile.primary_color if profile else None)
        or (tenant.brand_primary_color if tenant else None)
        or "#1e3a8a"
    )

    summary = (job.result_json or {}).get("summary", {})
    finding_count = summary.get("total_findings", 0)
    passed = summary.get("passed", True)

    sent = 0
    errors = []
    for email in emails:
        try:
            res = send_report(
                to=email,
                tenant_name=tenant.name if tenant else brand_name,
                job_id=str(job.id),
                report_url=viewer_url,
                finding_count=finding_count,
                passed=passed,
                brand_name=brand_name,
                brand_primary_color=brand_color,
            )
            if res.success:
                sent += 1
            else:
                errors.append(f"{email}: {res.error or 'failed'}")
        except Exception as e:
            errors.append(f"{email}: {e}")

    return {"sent": sent, "total": len(emails), "errors": errors}
