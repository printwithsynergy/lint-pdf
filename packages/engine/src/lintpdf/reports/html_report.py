"""HTML report generation using Jinja2 templates."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader

if TYPE_CHECKING:
    from lintpdf.profiles.orchestrator import PreflightResult
    from lintpdf.reports.service import BrandingContext

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _get_template_env() -> Environment:
    """Create Jinja2 environment with template directory."""
    return Environment(  # nosemgrep: direct-use-of-jinja2
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )


def _build_template_context(  # skipcq: PY-R1000
    result: PreflightResult,
    *,
    branding: BrandingContext | None = None,
    pdf_bytes: bytes | None = None,
    annotation_dpi: int = 150,
) -> dict[str, Any]:
    """Build template context from preflight result."""
    # Group findings by page
    findings_by_page: dict[int, list[dict[str, Any]]] = {}
    for f in result.findings:
        page = f.page_num or 0
        if page not in findings_by_page:
            findings_by_page[page] = []
        findings_by_page[page].append(
            {
                "inspection_id": f.inspection_id,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "message": f.message,
                "object_id": f.object_id,
                "object_type": f.object_type,
                "source": getattr(f, "source", "engine"),
                "category": getattr(f, "category", None),
                "bbox": f.bbox if hasattr(f, "bbox") else None,
            }
        )

    # Group findings by severity
    severity_groups: dict[str, list[dict[str, Any]]] = {
        "error": [],
        "warning": [],
        "advisory": [],
    }
    for f in result.findings:
        sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
        if sev in severity_groups:
            severity_groups[sev].append(
                {
                    "inspection_id": f.inspection_id,
                    "message": f.message,
                    "page_num": f.page_num,
                }
            )

    # Generate annotated page screenshots if PDF bytes available
    annotated_pages: dict[int, Any] = {}
    if pdf_bytes is not None:
        annotated_pages = _render_annotated_pages(
            pdf_bytes, findings_by_page, dpi=annotation_dpi
        )

    context: dict[str, Any] = {
        "result": result,
        "summary": result.summary,
        "metadata": result.metadata,
        "findings_by_page": dict(sorted(findings_by_page.items())),
        "severity_groups": severity_groups,
        "pass_fail": "PASS" if result.summary.passed else "FAIL",
        "badge_color": "#22c55e" if result.summary.passed else "#ef4444",
        "brand": branding,
        "annotated_pages": annotated_pages,
        "color_quality_score": result.metadata.get("color_quality_score"),
        "color_quality_grade": result.metadata.get("color_quality_grade"),
        "file_name": result.metadata.get("file_name", ""),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    return context


def _render_annotated_pages(
    pdf_bytes: bytes,
    findings_by_page: dict[int, list[dict[str, Any]]],
    *,
    dpi: int = 150,
) -> dict[int, Any]:
    """Render annotated page screenshots for pages that have findings."""
    try:
        from lintpdf.reports.page_renderer import render_annotated_pages

        return render_annotated_pages(pdf_bytes, findings_by_page, dpi=dpi)
    except Exception:
        logger.exception("Failed to render annotated pages for report")
        return {}


def generate_html_report(
    result: PreflightResult,
    *,
    branding: BrandingContext | None = None,
    pdf_bytes: bytes | None = None,
    annotation_dpi: int = 150,
) -> bytes:
    """Generate an HTML report from preflight results.

    Args:
        result: Preflight result to render.
        branding: Optional white-label branding context.
        pdf_bytes: Original PDF bytes for page screenshot rendering.
            When provided, pages with findings are rendered to images
            with annotated bounding boxes and embedded in the report.
        annotation_dpi: DPI for page screenshot rendering.

    Returns:
        UTF-8 encoded HTML bytes.
    """
    env = _get_template_env()
    template = env.get_template("report.html")
    context = _build_template_context(
        result,
        branding=branding,
        pdf_bytes=pdf_bytes,
        annotation_dpi=annotation_dpi,
    )
    html = template.render(**context)  # nosemgrep: direct-use-of-jinja2
    return html.encode("utf-8")
