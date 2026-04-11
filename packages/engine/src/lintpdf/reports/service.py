"""Report generation, storage, and delivery service."""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import TYPE_CHECKING, Any


class ReportDetailLevel(StrEnum):
    """Report detail levels — controls how much data is included."""

    EXECUTIVE = "executive"  # 1-page summary: verdict, top findings, doc info
    STANDARD = "standard"  # Production report: screenshots, full findings
    COMPREHENSIVE = "comprehensive"  # Deep analysis: score breakdown, ink data, details

if TYPE_CHECKING:
    from lintpdf.api.config import Settings
    from lintpdf.api.models import BrandProfile, Tenant
    from lintpdf.tenants.entitlements import TenantEntitlements

logger = logging.getLogger(__name__)


def resolve_report_base_url(
    tenant: Tenant,
    brand_profile: BrandProfile | None,
    entitlements: TenantEntitlements,
    settings: Settings,
) -> str:
    """Pick the report base URL for a tenant + active brand profile.

    Resolution priority, highest wins:
      1. brand_profile.custom_domain (if whitelabel_enabled AND verified)
      2. tenant.brand_custom_domain   (if whitelabel_enabled AND verified)
      3. settings.report_base_url     (the global default)

    Unverified domains are ignored — the verified flag is the
    source of truth for "this CNAME is actually live in Railway".
    This prevents generating broken URLs during the onboarding
    window between "customer enters domain" and "ops/probe marks active".

    Tenants on plans without the whitelabel entitlement (FREE, STARTER,
    GROWTH) always get the global default no matter what's in the DB.
    """
    if entitlements.whitelabel_enabled:
        if (
            brand_profile is not None
            and brand_profile.custom_domain
            and brand_profile.custom_domain_verified
        ):
            return f"https://{brand_profile.custom_domain}"
        if tenant.brand_custom_domain and tenant.brand_custom_domain_verified:
            return f"https://{tenant.brand_custom_domain}"
    return settings.report_base_url


def resolve_viewer_base_url(
    tenant: Tenant,
    brand_profile: BrandProfile | None,
    entitlements: TenantEntitlements,
    settings: Settings,
) -> str:
    """Pick the viewer/app base URL for a tenant + active brand profile.

    Resolution priority, highest wins:
      1. brand_profile.app_custom_domain (if whitelabel_enabled AND verified)
      2. tenant.app_custom_domain        (if whitelabel_enabled AND verified)
      3. settings.app_base_url           (the global default)
    """
    if entitlements.whitelabel_enabled:
        if (
            brand_profile is not None
            and getattr(brand_profile, "app_custom_domain", None)
            and brand_profile.app_custom_domain_verified
        ):
            return f"https://{brand_profile.app_custom_domain}"
        if getattr(tenant, "app_custom_domain", None) and tenant.app_custom_domain_verified:
            return f"https://{tenant.app_custom_domain}"
    return settings.app_base_url


# Default LintPDF logo as an embedded base64 data URI so reports always have
# branding even when no tenant/brand override is configured.
_LINTPDF_DEFAULT_LOGO = (
    "data:image/svg+xml;base64,"
    "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyB3aWR0aD0iMTAy"
    "NCIgaGVpZ2h0PSIxMDI0IiB2aWV3Qm94PSIwIDAgMTAyNCAxMDI0IiBmaWxsPSJub25lIiB4"
    "bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgogIDx0aXRsZT5MaW50UERGLXN0"
    "eWxlIGJyYWNrZXQgbG9nbzwvdGl0bGU+CiAgPGRlc2M+VmVjdG9yIHJlY3JlYXRpb24gb2Yg"
    "dGhlIHVwbG9hZGVkIGZsYXQgYnJhY2tldCBsb2dvLjwvZGVzYz4KICA8IS0tIEJhY2tncm91"
    "bmQgLS0+CiAgPHJlY3QgeD0iMTgiIHk9IjE4IiB3aWR0aD0iOTg4IiBoZWlnaHQ9Ijk4OCIg"
    "cng9IjE2NSIgZmlsbD0iIzQwODdGNyIvPgogIDwhLS0gQ2VudGVyIGNvbnRlbnQgYXJlYSAt"
    "LT4KICA8IS0tIEJyYWNrZXRzIC0tPgogIDxwYXRoIGQ9Ik0yMTAgMjcwCiAgICAgICAgICAg"
    "QzIxMCAyMzYgMjM2IDIxMCAyNzAgMjEwCiAgICAgICAgICAgSDM1OAogICAgICAgICAgIEMz"
    "ODAgMjEwIDM5OCAyMjggMzk4IDI1MAogICAgICAgICAgIEMzOTggMjcyIDM4MCAyOTAgMzU4"
    "IDI5MAogICAgICAgICAgIEgyNjYKICAgICAgICAgICBWNzM0CiAgICAgICAgICAgSDM1OAogICAg"
    "ICAgICAgIEMzODAgNzM0IDM5OCA3NTIgMzk4IDc3NAogICAgICAgICAgIEMzOTggNzk2IDM4"
    "MCA4MTQgMzU4IDgxNAogICAgICAgICAgIEgyNzAKICAgICAgICAgICBDMjM2IDgxNCAyMTAg"
    "Nzg4IDIxMCA3NTQKICAgICAgICAgICBWMjcwWiIKICAgICAgICBmaWxsPSIjRjJGMkYyIi8+"
    "CiAgPHBhdGggZD0iTTgxNCAyNzAKICAgICAgICAgICBDODE0IDIzNiA3ODggMjEwIDc1NCAy"
    "MTAKICAgICAgICAgICBINjY2CiAgICAgICAgICAgQzY0NCAyMTAgNjI2IDIyOCA2MjYgMjUw"
    "CiAgICAgICAgICAgQzYyNiAyNzIgNjQ0IDI5MCA2NjYgMjkwCiAgICAgICAgICAgSDc1OAog"
    "ICAgICAgICAgIFY3MzQKICAgICAgICAgICBINjY2CiAgICAgICAgICAgQzY0NCA3MzQgNjI2"
    "IDc1MiA2MjYgNzc0CiAgICAgICAgICAgQzYyNiA3OTYgNjQ0IDgxNCA2NjYgODE0CiAgICAg"
    "ICAgICAgSDc1NAogICAgICAgICAgIEM3ODggODE0IDgxNCA3ODggODE0IDc1NAogICAgICAg"
    "ICAgIFYyNzBaIgogICAgICAgIGZpbGw9IiNGMkYyRjIiLz4KICA8IS0tIFRleHQgbGluZXMg"
    "LS0+CiAgPHJlY3QgeD0iMzQ3IiB5PSIzNTYiIHdpZHRoPSIzMzAiIGhlaWdodD0iMzYiIHJ4"
    "PSIxOCIgZmlsbD0iIzkzQzVGRCIvPgogIDxyZWN0IHg9IjM5MiIgeT0iNDU1IiB3aWR0aD0i"
    "MjQwIiBoZWlnaHQ9IjM2IiByeD0iMTgiIGZpbGw9IiM5M0M1RkQiLz4KICA8cmVjdCB4PSIz"
    "NjYiIHk9IjU1NCIgd2lkdGg9IjI5NCIgaGVpZ2h0PSIzNiIgcng9IjE4IiBmaWxsPSIjOTND"
    "NUZEIi8+Cjwvc3ZnPgo="
)


@dataclass
class BrandingContext:
    """White-label branding for report rendering."""

    name: str = "LintPDF"
    logo_url: str | None = _LINTPDF_DEFAULT_LOGO
    primary_color: str = "#1a3a7a"
    accent_color: str = "#2563eb"
    footer_text: str | None = "Powered by LintPDF"
    pdf_download_url: str | None = None
    report_url: str | None = None
    viewer_url: str | None = None


@dataclass
class ReportResult:
    """Result of report generation."""

    reports: list[dict[str, Any]] = field(default_factory=list)


def compute_health_score(summary: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute an overall preflight health score (0-100) with letter grade."""
    errors = summary.get("error_count", 0)
    warnings = summary.get("warning_count", 0)
    advisory = summary.get("advisory_count", 0)

    score = max(0, min(100, round(100 - errors * 10 - warnings * 3 - advisory * 0.5)))
    if score >= 90:
        grade, color = "A", "#22c55e"
    elif score >= 80:
        grade, color = "B", "#22c55e"
    elif score >= 70:
        grade, color = "C", "#f59e0b"
    elif score >= 60:
        grade, color = "D", "#ef4444"
    else:
        grade, color = "F", "#ef4444"

    return {"score": score, "grade": grade, "color": color}


class ReportService:
    """Generates, stores, and serves branded preflight reports."""

    def __init__(self, storage: Any, db: Any) -> None:
        self._storage = storage
        self._db = db

    def generate_and_store(  # skipcq: PY-R1000
        self,
        job_id: str,
        tenant_id: str,
        result_json: dict[str, Any],
        *,
        formats: list[str] | None = None,
        expiry_days: int | None = None,
        branding: BrandingContext | None = None,
        report_base_url: str = "https://reports.lintpdf.com",
        detail_level: str = "standard",
        summary_page: str = "prepend",
    ) -> ReportResult:
        """Generate reports, upload to storage, and create access tokens.

        Args:
            job_id: UUID of the completed job.
            tenant_id: UUID of the tenant.
            result_json: The job's result_json dict (summary + metadata).
            formats: Report formats to generate (default: ["html", "pdf"]).
            expiry_days: Days until report tokens expire (None = no expiry).
            branding: White-label branding context.
            report_base_url: Base URL for hosted report links.
            detail_level: Report detail level ("executive", "standard", "comprehensive").

        Returns:
            ReportResult with generated report URLs and tokens.
        """
        import uuid as uuid_mod

        from lintpdf.api.models import ReportToken

        if formats is None:
            formats = ["html", "pdf"]
        if branding is None:
            branding = BrandingContext()

        expires_at = None
        if expiry_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)

        report_result = ReportResult()

        # Generate tokens first so we can cross-link HTML <-> PDF
        tokens: dict[str, str] = {}
        for fmt in formats:
            tokens[fmt] = secrets.token_urlsafe(32)

        # Set cross-links in branding
        if "pdf" in tokens:
            branding.pdf_download_url = f"{report_base_url}/r/{tokens['pdf']}.pdf"
        if "html" in tokens:
            branding.report_url = f"{report_base_url}/r/{tokens['html']}"
            # Link to the interactive viewer (served by the Next.js app)
            from lintpdf.api.config import get_settings as _get_settings

            app_base = _get_settings().app_base_url.rstrip("/")
            branding.viewer_url = f"{app_base}/view/{tokens['html']}"

        # Fetch original PDF bytes for page screenshot rendering (lazy, once).
        # Executive reports skip screenshots entirely — no PDF fetch needed.
        pdf_bytes: bytes | None = None
        if detail_level != ReportDetailLevel.EXECUTIVE:
            pdf_bytes = self._fetch_original_pdf(result_json)

        for fmt in formats:
            content = self._generate_format(
                result_json, fmt, branding, pdf_bytes=pdf_bytes,
                detail_level=detail_level, summary_page=summary_page,
            )
            if content is None:
                continue

            # Upload to storage
            self._storage.upload_report(tenant_id, job_id, fmt, content)

            # Create token record
            token_record = ReportToken(
                id=uuid_mod.uuid4(),
                job_id=uuid_mod.UUID(job_id),
                tenant_id=uuid_mod.UUID(tenant_id),
                token=tokens[fmt],
                format=fmt,
                expires_at=expires_at,
            )
            self._db.add(token_record)

            # Build URL
            suffix = ".pdf" if fmt == "pdf" else ""
            url = f"{report_base_url}/r/{tokens[fmt]}{suffix}"

            report_result.reports.append(
                {
                    "format": fmt,
                    "url": url,
                    "token": tokens[fmt],
                    "expires_at": expires_at.isoformat() if expires_at else None,
                }
            )

        self._db.commit()
        return report_result

    def get_report(self, token: str) -> tuple[bytes, str] | None:
        """Fetch report content by token.

        Args:
            token: URL-safe report access token.

        Returns:
            Tuple of (content_bytes, format) or None if not found/expired.
        """
        from lintpdf.api.models import ReportToken

        record: ReportToken | None = (
            self._db.query(ReportToken).filter(ReportToken.token == token).first()
        )
        if record is None:
            return None

        # Check expiry
        if record.expires_at is not None and datetime.now(timezone.utc) > record.expires_at:
            return None

        # Increment access count
        record.accessed_count += 1
        record.last_accessed_at = datetime.now(timezone.utc)
        self._db.commit()

        # Download from storage
        content = self._storage.download_report(
            str(record.tenant_id), str(record.job_id), record.format
        )
        return content, record.format

    def cleanup_expired(self) -> int:
        """Delete expired report tokens and their storage files.

        Returns:
            Number of tokens cleaned up.
        """
        from lintpdf.api.models import ReportToken

        now = datetime.now(timezone.utc)
        expired = (
            self._db.query(ReportToken)
            .filter(ReportToken.expires_at.isnot(None), ReportToken.expires_at < now)
            .all()
        )

        count = 0
        for record in expired:
            try:
                file_key = f"reports/{record.tenant_id}/{record.job_id}/report.{record.format}"
                self._storage.delete_file(file_key)
            except Exception:
                logger.debug(  # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
                    "Failed to delete report file for token %s", record.token
                )

            self._db.delete(record)
            count += 1

        if count > 0:
            self._db.commit()

        return count

    def _fetch_original_pdf(self, result_json: dict[str, Any]) -> bytes | None:
        """Attempt to retrieve original PDF bytes from storage.

        Best-effort: returns None if unavailable, so reports degrade
        gracefully to text-only mode without page screenshots.
        """
        file_key = result_json.get("metadata", {}).get("file_key", "")
        job_id = result_json.get("job_id", "unknown")
        if not file_key:
            logger.error(
                "No file_key in result_json for job %s — "
                "report will render without page screenshots",
                job_id,
            )
            return None

        try:
            return self._storage.download_pdf(file_key)
        except Exception:
            logger.error(
                "Failed to download original PDF for report screenshots "
                "(job_id=%s, file_key=%s)",
                job_id,
                file_key,
                exc_info=True,
            )
            return None

    def _generate_format(
        self,
        result_json: dict[str, Any],
        fmt: str,
        branding: BrandingContext,
        *,
        pdf_bytes: bytes | None = None,
        detail_level: str = "standard",
        summary_page: str = "prepend",
    ) -> bytes | None:
        """Generate report content in the requested format."""
        if fmt == "html":
            return self._generate_html(
                result_json, branding, pdf_bytes=pdf_bytes,
                detail_level=detail_level, summary_page=summary_page,
            )
        if fmt == "pdf":
            return self._generate_pdf(
                result_json, branding, pdf_bytes=pdf_bytes,
                detail_level=detail_level, summary_page=summary_page,
            )
        if fmt == "annotated_pdf":
            return self._generate_annotated_pdf(result_json, branding)
        return None

    @staticmethod
    def _generate_html(  # skipcq: PY-R1000
        result_json: dict[str, Any],
        branding: BrandingContext,
        *,
        pdf_bytes: bytes | None = None,
        detail_level: str = "standard",
        summary_page: str = "prepend",
    ) -> bytes:
        """Generate branded HTML report from result JSON."""
        from jinja2 import Environment, FileSystemLoader

        from lintpdf.reports.html_report import _TEMPLATE_DIR

        env = Environment(  # nosemgrep: direct-use-of-jinja2
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=True,
        )

        def _decode_svg_data_uri(data_uri: str) -> str:
            """Decode a base64 SVG data URI to inline <svg> markup for WeasyPrint."""
            import base64
            from markupsafe import Markup

            try:
                # Strip the data:image/svg+xml;base64, prefix
                b64 = data_uri.split(",", 1)[1]
                svg = base64.b64decode(b64).decode("utf-8")
                # Add class for sizing
                svg = svg.replace("<svg ", '<svg class="header-logo" ', 1)
                return Markup(svg)
            except Exception:
                return Markup("")

        env.filters["decode_svg_data_uri"] = _decode_svg_data_uri

        template = env.get_template("report.html")

        summary = result_json.get("summary", {})
        metadata = result_json.get("metadata", {})
        findings = result_json.get("findings", [])

        # Enrich findings with friendly names
        try:
            from lintpdf.reports.check_names import get_check_info

            for f in findings:
                info = get_check_info(f.get("inspection_id", ""))
                f.setdefault("friendly_name", info.name)
                f.setdefault("friendly_description", info.description)
                f.setdefault("thumbnail_base64", "")
        except Exception:
            pass

        # Build findings_by_page from flat findings list
        findings_by_page: dict[int, list[dict[str, Any]]] = {}
        for f in findings:
            page = f.get("page_num") or 0
            if page not in findings_by_page:
                findings_by_page[page] = []
            findings_by_page[page].append(f)

        # Generate annotated page screenshots (standard + comprehensive only)
        annotated_pages: dict[int, Any] = {}
        render_failed = False
        if pdf_bytes is not None and detail_level != ReportDetailLevel.EXECUTIVE:
            try:
                from lintpdf.reports.page_renderer import render_annotated_pages

                annotated_pages = render_annotated_pages(
                    pdf_bytes, findings_by_page, dpi=150
                )
            except Exception:
                logger.exception("Failed to render annotated pages for service report")

            # Generate per-finding cropped thumbnails
            try:
                from lintpdf.reports.page_renderer import render_finding_thumbnails

                render_finding_thumbnails(pdf_bytes, findings, dpi=120)
            except Exception:
                logger.exception("Failed to render per-finding thumbnails")

            if not annotated_pages and findings_by_page:
                render_failed = True
        elif pdf_bytes is None and detail_level != ReportDetailLevel.EXECUTIVE:
            render_failed = True

        # Build top findings for executive summary (sorted by severity priority)
        severity_order = {"error": 0, "warning": 1, "advisory": 2}
        sorted_findings = sorted(
            findings,
            key=lambda f: severity_order.get(f.get("severity", "advisory"), 3),
        )
        top_findings = sorted_findings[:10]

        # Extract ink coverage data for comprehensive reports
        ink_separations: list[dict[str, Any]] = []
        ink_tac_by_page: dict[int, dict[str, Any]] = {}
        ink_inventory: dict[str, Any] = {}
        color_score_breakdown: dict[str, Any] = {}

        if detail_level == ReportDetailLevel.COMPREHENSIVE:
            for f in findings:
                iid = f.get("inspection_id", "")
                details = f.get("details") or {}
                if iid == "LPDF_INK_002":
                    ink_separations.append({
                        "name": details.get("separation_name", ""),
                        "pages_used": details.get("pages_used", []),
                        "max_value": details.get("max_value", 0),
                        "event_count": details.get("event_count", 0),
                    })
                elif iid == "LPDF_INK_001":
                    page = f.get("page_num", 0)
                    if page > 0:
                        ink_tac_by_page[page] = {
                            "max_tac": details.get("max_tac", 0),
                            "tac_limit": details.get("tac_limit", 0),
                            "sample_count": details.get("sample_count", 0),
                        }
                elif iid == "LPDF_INK_003" and details.get("process_channels"):
                    ink_inventory = details

            color_score_breakdown = metadata.get("color_score_breakdown", {})

        # Build sorted flat list (errors first, then warnings, advisory)
        all_findings_sorted = sorted(
            findings,
            key=lambda f: (severity_order.get(f.get("severity", "advisory"), 3), f.get("page_num") or 0),
        )

        # Summary page data (thumbnails + health score)
        page_thumbnails: list[str] = []
        health = compute_health_score(summary, findings)
        if summary_page != "off" and pdf_bytes is not None:
            try:
                from lintpdf.reports.page_renderer import render_page_thumbnail_grid
                page_thumbnails = render_page_thumbnail_grid(pdf_bytes, max_pages=12, dpi=72)
            except Exception:
                logger.exception("Failed to render page thumbnails for summary page")

        # Extract color info for summary page
        color_spaces_used = set()
        spot_colors: list[str] = []
        max_tac = 0.0
        for f in findings:
            iid = f.get("inspection_id", "")
            details = f.get("details") or {}
            if iid == "LPDF_INK_002":
                name = details.get("separation_name", "")
                if name and name not in ("Cyan", "Magenta", "Yellow", "Black"):
                    spot_colors.append(name)
            if iid == "LPDF_INK_001":
                mt = details.get("max_tac", 0)
                if mt > max_tac:
                    max_tac = mt
            if iid == "LPDF_COLOR_014":
                cs = details.get("color_spaces", [])
                color_spaces_used.update(cs if isinstance(cs, list) else [])

        summary_color_info = {
            "color_spaces": sorted(color_spaces_used) or ["DeviceCMYK"],
            "spot_colors": spot_colors[:6],
            "max_tac": round(max_tac, 1),
        }

        passed = summary.get("passed", True)
        context = {
            "result": type(
                "R",
                (),
                {
                    "job_id": result_json.get("job_id", ""),
                    "profile_id": result_json.get("profile_id", ""),
                    "findings": findings,
                    "duration_ms": result_json.get("duration_ms", 0),
                },
            )(),
            "summary": type("S", (), summary)(),
            "metadata": metadata,
            "findings_by_page": dict(sorted(findings_by_page.items())),
            "severity_groups": {},
            "pass_fail": "PASS" if passed else "FAIL",
            "badge_color": "#22c55e" if passed else "#ef4444",
            "brand": branding,
            "annotated_pages": annotated_pages,
            "render_failed": render_failed,
            "color_quality_score": metadata.get("color_quality_score"),
            "color_quality_grade": metadata.get("color_quality_grade"),
            "file_name": result_json.get("file_name", metadata.get("file_name", "")),
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
            # Summary page
            "summary_page": summary_page,
            "page_thumbnails": page_thumbnails,
            "health": health,
            "summary_color_info": summary_color_info,
        }

        html = template.render(**context)  # nosemgrep: direct-use-of-jinja2
        return html.encode("utf-8")

    def _generate_pdf(
        self,
        result_json: dict[str, Any],
        branding: BrandingContext,
        *,
        pdf_bytes: bytes | None = None,
        detail_level: str = "standard",
        summary_page: str = "prepend",
    ) -> bytes:
        """Generate PDF from branded HTML."""
        from weasyprint import HTML

        html_bytes = self._generate_html(
            result_json, branding, pdf_bytes=pdf_bytes,
            detail_level=detail_level, summary_page=summary_page,
        )
        pdf_bytes_out: bytes = HTML(string=html_bytes.decode("utf-8")).write_pdf()
        return pdf_bytes_out

    def _generate_annotated_pdf(
        self,
        result_json: dict[str, Any],
        branding: BrandingContext,
    ) -> bytes | None:
        """Generate annotated PDF with finding overlays on original pages.

        Requires the original PDF bytes to be available in storage.
        Falls back to None if the original PDF cannot be retrieved.
        """
        from lintpdf.reports.annotated_pdf_report import generate_annotated_pdf

        # Get original PDF from storage
        file_key = result_json.get("metadata", {}).get("file_key", "")
        if not file_key:
            logger.warning("Cannot generate annotated PDF: no file_key in result_json")
            return None

        try:
            pdf_bytes = self._storage.download_pdf(file_key)
        except Exception:
            logger.warning("Cannot generate annotated PDF: failed to download original PDF")
            return None

        findings = result_json.get("findings", [])
        return generate_annotated_pdf(
            pdf_bytes,
            findings,
            branding_name=branding.name,
        )
