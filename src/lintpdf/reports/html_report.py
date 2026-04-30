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
    detail_level: str = "standard",
) -> dict[str, Any]:
    """Build template context from preflight result."""
    from lintpdf.reports.service import ReportDetailLevel

    # Group findings by page
    findings_by_page: dict[int, list[dict[str, Any]]] = {}
    all_finding_dicts: list[dict[str, Any]] = []

    # Load friendly check names
    try:
        from lintpdf.reports.check_names import get_check_info
    except ImportError:
        from dataclasses import dataclass as _dc

        @_dc(frozen=True)
        class _Fallback:
            name: str = ""
            description: str = ""

        def get_check_info(_id: str) -> _Fallback:  # type: ignore[misc]
            return _Fallback()

    for f in result.findings:
        page = f.page_num or 0
        info = get_check_info(f.inspection_id)
        finding_dict: dict[str, Any] = {
            "inspection_id": f.inspection_id,
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "message": f.message,
            "object_id": f.object_id,
            "object_type": f.object_type,
            "source": getattr(f, "source", "engine"),
            "category": getattr(f, "category", None),
            "bbox": f.bbox if hasattr(f, "bbox") else None,
            "page_num": f.page_num,
            "iso_clause": getattr(f, "iso_clause", ""),
            "details": f.details if hasattr(f, "details") else {},
            "friendly_name": info.name,
            "friendly_description": info.description,
            "thumbnail_base64": "",  # populated below
        }
        all_finding_dicts.append(finding_dict)
        if page not in findings_by_page:
            findings_by_page[page] = []
        findings_by_page[page].append(finding_dict)

    # Group findings by severity
    severity_groups: dict[str, list[dict[str, Any]]] = {
        "error": [],
        "warning": [],
        "advisory": [],
    }
    for fd in all_finding_dicts:
        sev = fd["severity"]
        if sev in severity_groups:
            severity_groups[sev].append(fd)

    # Top findings (sorted by severity: errors first)
    severity_order = {"error": 0, "warning": 1, "advisory": 2}
    top_findings = sorted(
        all_finding_dicts,
        key=lambda fd: severity_order.get(fd["severity"], 3),
    )[:10]

    # Generate annotated page screenshots (standard + comprehensive only)
    annotated_pages: dict[int, Any] = {}
    render_failed = False
    if pdf_bytes is not None and detail_level != ReportDetailLevel.EXECUTIVE:
        annotated_pages = _render_annotated_pages(pdf_bytes, findings_by_page, dpi=annotation_dpi)
        if not annotated_pages and findings_by_page:
            render_failed = True
            logger.error(
                "Page annotation rendering returned no images despite %d pages having findings. "
                "Check poppler-utils installation and PDF validity.",
                len(findings_by_page),
            )
    elif pdf_bytes is None and detail_level != ReportDetailLevel.EXECUTIVE:
        render_failed = True
        logger.error(
            "pdf_bytes is None — report will render in text-only mode (no page screenshots)"
        )

    # Generate per-finding cropped thumbnails (standard + comprehensive)
    if pdf_bytes is not None and detail_level != ReportDetailLevel.EXECUTIVE:
        try:
            from lintpdf.reports.page_renderer import render_finding_thumbnails

            render_finding_thumbnails(pdf_bytes, all_finding_dicts, dpi=120)
        except Exception:
            logger.exception("Failed to render per-finding thumbnails")

    # Build sorted flat list of all findings (errors first)
    all_findings_sorted = sorted(
        all_finding_dicts,
        key=lambda fd: (severity_order.get(fd["severity"], 3), fd.get("page_num") or 0),
    )

    # Extract comprehensive-only data
    ink_separations: list[dict[str, Any]] = []
    ink_tac_by_page: dict[int, dict[str, Any]] = {}
    ink_inventory: dict[str, Any] = {}
    color_score_breakdown: dict[str, Any] = {}

    if detail_level == ReportDetailLevel.COMPREHENSIVE:
        for fd in all_finding_dicts:
            iid = fd.get("inspection_id", "")
            details = fd.get("details") or {}
            if iid == "LPDF_INK_002":
                ink_separations.append(
                    {
                        "name": details.get("separation_name", ""),
                        "pages_used": details.get("pages_used", []),
                        "max_value": details.get("max_value", 0),
                        "event_count": details.get("event_count", 0),
                    }
                )
            elif iid == "LPDF_INK_001":
                page = fd.get("page_num", 0)
                if page and page > 0:
                    ink_tac_by_page[page] = {
                        "max_tac": details.get("max_tac", 0),
                        "tac_limit": details.get("tac_limit", 0),
                        "sample_count": details.get("sample_count", 0),
                    }
            elif iid == "LPDF_INK_003" and details.get("process_channels"):
                ink_inventory = details

        color_score_breakdown = result.metadata.get("color_score_breakdown", {})

    # EPM verdict — pure function of fired LPDF_EPM_* findings, cheap.
    # Computed inline so the standalone ``generate_html_report`` path
    # (used by tests + the orchestrator's preview render) shows the
    # candidacy header without requiring a DB session.
    try:
        from lintpdf.epm.scoring import score_epm_candidacy

        epm_codes = [
            f.inspection_id
            for f in result.findings
            if str(getattr(f, "inspection_id", "")).startswith("LPDF_EPM")
        ]
        verdict = score_epm_candidacy(epm_codes)
        epm_block = {
            "tier": verdict.tier.value if hasattr(verdict.tier, "value") else str(verdict.tier),
            "rejection_drivers": list(verdict.rejection_drivers),
            "advisories": list(verdict.advisories),
            "recommends_indichrome": verdict.recommends_indichrome,
            "legacy_codes_fired": list(verdict.legacy_codes_fired),
            "epm_findings_count": len(epm_codes),
        }
    except Exception:
        logger.exception("Failed to compute EPM verdict for HTML report")
        epm_block = None

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
        "render_failed": render_failed,
        "color_quality_score": result.metadata.get("color_quality_score"),
        "color_quality_grade": result.metadata.get("color_quality_grade"),
        "file_name": result.metadata.get("file_name", ""),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        # Detail level controls
        "detail_level": detail_level,
        "top_findings": top_findings,
        "all_findings_sorted": all_findings_sorted,
        # Comprehensive-only data
        "ink_separations": ink_separations,
        "ink_tac_by_page": ink_tac_by_page,
        "ink_inventory": ink_inventory,
        "color_score_breakdown": color_score_breakdown,
        # Substrate header
        "epm": epm_block,
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
    detail_level: str = "standard",
) -> bytes:
    """Generate an HTML report from preflight results.

    Args:
        result: Preflight result to render.
        branding: Optional white-label branding context.
        pdf_bytes: Original PDF bytes for page screenshot rendering.
            When provided, pages with findings are rendered to images
            with annotated bounding boxes and embedded in the report.
        annotation_dpi: DPI for page screenshot rendering.
        detail_level: Report detail ("executive", "standard", "comprehensive").

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
        detail_level=detail_level,
    )
    html = template.render(**context)  # nosemgrep: direct-use-of-jinja2
    return html.encode("utf-8")
