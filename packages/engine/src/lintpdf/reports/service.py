"""Report generation, storage, and delivery service."""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


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

        for fmt in formats:
            content = self._generate_format(result_json, fmt, branding)
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

    def _generate_format(
        self,
        result_json: dict[str, Any],
        fmt: str,
        branding: BrandingContext,
    ) -> bytes | None:
        """Generate report content in the requested format."""
        if fmt == "html":
            return self._generate_html(result_json, branding)
        if fmt == "pdf":
            return self._generate_pdf(result_json, branding)
        if fmt == "annotated_pdf":
            return self._generate_annotated_pdf(result_json, branding)
        return None

    @staticmethod
    def _generate_html(
        result_json: dict[str, Any],
        branding: BrandingContext,
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
        }

        html = template.render(**context)  # nosemgrep: direct-use-of-jinja2
        return html.encode("utf-8")

    def _generate_pdf(
        self,
        result_json: dict[str, Any],
        branding: BrandingContext,
    ) -> bytes:
        """Generate PDF from branded HTML."""
        from weasyprint import HTML

        html_bytes = self._generate_html(result_json, branding)
        pdf_bytes: bytes = HTML(string=html_bytes.decode("utf-8")).write_pdf()
        return pdf_bytes

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
