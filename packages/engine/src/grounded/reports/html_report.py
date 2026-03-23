"""HTML report generation using Jinja2 templates."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader

if TYPE_CHECKING:
    from grounded.profiles.orchestrator import PreflightResult

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _get_template_env() -> Environment:
    """Create Jinja2 environment with template directory."""
    return Environment(  # nosemgrep: direct-use-of-jinja2
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )


def _build_template_context(result: PreflightResult) -> dict[str, Any]:  # skipcq: PY-R1000
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

    return {
        "result": result,
        "summary": result.summary,
        "metadata": result.metadata,
        "findings_by_page": dict(sorted(findings_by_page.items())),
        "severity_groups": severity_groups,
        "pass_fail": "PASS" if result.summary.passed else "FAIL",
        "badge_color": "#22c55e" if result.summary.passed else "#ef4444",
    }


def generate_html_report(result: PreflightResult) -> bytes:
    """Generate an HTML report from preflight results.

    Args:
        result: Preflight result to render.

    Returns:
        UTF-8 encoded HTML bytes.
    """
    env = _get_template_env()
    template = env.get_template("report.html")
    context = _build_template_context(result)
    html = template.render(**context)  # nosemgrep: direct-use-of-jinja2
    return html.encode("utf-8")
