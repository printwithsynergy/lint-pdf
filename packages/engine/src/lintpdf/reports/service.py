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


@dataclass
class BrandingContext:
    """White-label branding for report rendering."""

    name: str = "LintPDF"
    logo_url: str | None = None
    primary_color: str = "#1a3a7a"
    accent_color: str = "#2563eb"
    footer_text: str | None = "Powered by LintPDF"
    pdf_download_url: str | None = None
    report_url: str | None = None


@dataclass
class ReportResult:
    """Result of report generation."""

    reports: list[dict[str, Any]] = field(default_factory=list)


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

        # Fetch original PDF bytes for page screenshot rendering (lazy, once).
        # Executive reports skip screenshots entirely — no PDF fetch needed.
        pdf_bytes: bytes | None = None
        if detail_level != ReportDetailLevel.EXECUTIVE:
            pdf_bytes = self._fetch_original_pdf(result_json)

        for fmt in formats:
            content = self._generate_format(
                result_json, fmt, branding, pdf_bytes=pdf_bytes, detail_level=detail_level
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
        if not file_key:
            logger.debug("No file_key in result_json — reports will render without page screenshots")
            return None

        try:
            return self._storage.download_pdf(file_key)
        except Exception:
            logger.warning("Failed to download original PDF for report screenshots (file_key=%s)", file_key)
            return None

    def _generate_format(
        self,
        result_json: dict[str, Any],
        fmt: str,
        branding: BrandingContext,
        *,
        pdf_bytes: bytes | None = None,
        detail_level: str = "standard",
    ) -> bytes | None:
        """Generate report content in the requested format."""
        if fmt == "html":
            return self._generate_html(
                result_json, branding, pdf_bytes=pdf_bytes, detail_level=detail_level
            )
        if fmt == "pdf":
            return self._generate_pdf(
                result_json, branding, pdf_bytes=pdf_bytes, detail_level=detail_level
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
    ) -> bytes:
        """Generate branded HTML report from result JSON."""
        from jinja2 import Environment, FileSystemLoader

        from lintpdf.reports.html_report import _TEMPLATE_DIR

        env = Environment(  # nosemgrep: direct-use-of-jinja2
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=True,
        )
        template = env.get_template("report.html")

        summary = result_json.get("summary", {})
        metadata = result_json.get("metadata", {})
        findings = result_json.get("findings", [])

        # Build findings_by_page from flat findings list
        findings_by_page: dict[int, list[dict[str, Any]]] = {}
        for f in findings:
            page = f.get("page_num") or 0
            if page not in findings_by_page:
                findings_by_page[page] = []
            findings_by_page[page].append(f)

        # Generate annotated page screenshots (standard + comprehensive only)
        annotated_pages: dict[int, Any] = {}
        if pdf_bytes is not None and detail_level != ReportDetailLevel.EXECUTIVE:
            try:
                from lintpdf.reports.page_renderer import render_annotated_pages

                annotated_pages = render_annotated_pages(
                    pdf_bytes, findings_by_page, dpi=150
                )
            except Exception:
                logger.exception("Failed to render annotated pages for service report")

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
            "color_quality_score": metadata.get("color_quality_score"),
            "color_quality_grade": metadata.get("color_quality_grade"),
            "file_name": result_json.get("file_name", metadata.get("file_name", "")),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            # Detail level controls
            "detail_level": detail_level,
            "top_findings": top_findings,
            # Comprehensive-only data
            "ink_separations": ink_separations,
            "ink_tac_by_page": ink_tac_by_page,
            "ink_inventory": ink_inventory,
            "color_score_breakdown": color_score_breakdown,
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
    ) -> bytes:
        """Generate PDF from branded HTML."""
        from weasyprint import HTML

        html_bytes = self._generate_html(
            result_json, branding, pdf_bytes=pdf_bytes, detail_level=detail_level
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
