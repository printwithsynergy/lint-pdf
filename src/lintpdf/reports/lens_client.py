"""HTTP client for delegating report rendering to lens-server."""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_LENS_SERVER_URL = os.environ.get("LENS_SERVER_URL", "http://localhost:3001").rstrip("/")
_RENDER_TIMEOUT = int(os.environ.get("LENS_RENDER_TIMEOUT", "120"))


def _get_session():
    """Return a requests.Session (lazy import to avoid import-time cost)."""
    import requests
    s = requests.Session()
    s.headers["User-Agent"] = "lintpdf-render-client/1.0"
    return s


def render_html(
    result_json: dict[str, Any],
    *,
    branding: dict[str, Any] | None = None,
    detail_level: str = "standard",
    summary_page: str = "prepend",
    pdf_bytes: bytes | None = None,
    job_id: str | None = None,
) -> bytes:
    """Call lens-server POST /render and return HTML bytes."""
    return _render(
        fmt="html",
        result_json=result_json,
        branding=branding,
        detail_level=detail_level,
        summary_page=summary_page,
        pdf_bytes=pdf_bytes,
        job_id=job_id,
    )


def render_pdf(
    result_json: dict[str, Any],
    *,
    branding: dict[str, Any] | None = None,
    detail_level: str = "standard",
    summary_page: str = "prepend",
    pdf_bytes: bytes | None = None,
    job_id: str | None = None,
) -> bytes:
    """Call lens-server POST /render and return PDF bytes."""
    return _render(
        fmt="pdf",
        result_json=result_json,
        branding=branding,
        detail_level=detail_level,
        summary_page=summary_page,
        pdf_bytes=pdf_bytes,
        job_id=job_id,
    )


def render_annotated_pdf(
    result_json: dict[str, Any],
    pdf_bytes: bytes,
    *,
    branding_name: str = "LintPDF",
) -> bytes:
    """Call lens-server POST /render and return annotated PDF bytes."""
    return _render(
        fmt="annotated_pdf",
        result_json=result_json,
        branding={"name": branding_name},
        pdf_bytes=pdf_bytes,
    )


def render_markup_pdf(
    pdf_bytes: bytes,
    annotations: list[dict[str, Any]],
    comments_by_annotation: dict[str, list[dict[str, Any]]],
    *,
    branding_name: str = "LintPDF",
) -> bytes:
    """Call lens-server POST /render and return markup PDF bytes."""
    import json as _json

    context: dict[str, Any] = {
        "format": "markup_pdf",
        "result_json": {"summary": {}, "metadata": {}, "findings": []},
        "branding": {"name": branding_name},
        "annotations": annotations,
        "comments_by_annotation": comments_by_annotation,
    }
    session = _get_session()
    files: dict[str, Any] = {
        "context": (None, _json.dumps(context), "application/json"),
        "pdf": ("source.pdf", pdf_bytes, "application/pdf"),
    }
    try:
        resp = session.post(
            f"{_LENS_SERVER_URL}/render",
            files=files,
            timeout=_RENDER_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.content
    except Exception:
        logger.exception("lens-server markup_pdf render failed")
        raise


def _render(
    fmt: str,
    result_json: dict[str, Any],
    *,
    branding: dict[str, Any] | None = None,
    detail_level: str = "standard",
    summary_page: str = "prepend",
    pdf_bytes: bytes | None = None,
    job_id: str | None = None,
) -> bytes:
    import json as _json

    context: dict[str, Any] = {
        "format": fmt,
        "result_json": result_json,
        "branding": branding or {},
        "detail_level": detail_level,
        "summary_page": summary_page,
    }
    if job_id:
        context["job_id"] = job_id

    session = _get_session()
    files: dict[str, Any] = {
        "context": (None, _json.dumps(context), "application/json"),
    }
    if pdf_bytes is not None:
        files["pdf"] = ("source.pdf", pdf_bytes, "application/pdf")

    try:
        resp = session.post(
            f"{_LENS_SERVER_URL}/render",
            files=files,
            timeout=_RENDER_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.content
    except Exception:
        logger.exception("lens-server %s render failed", fmt)
        raise
