"""LintPDF Python SDK.

A Python client library for the LintPDF preflight API.

Usage:
    from lintpdf import LintPDF

    client = LintPDF(api_key="lpdf_...")
    result = client.preflight("document.pdf", profile="lintpdf-default")

    if result.passed:
        print("PDF passed preflight!")
    else:
        for finding in result.findings:
            print(f"[{finding.severity}] {finding.message}")
"""

__version__ = "0.1.0"


class LintPDFError(Exception):
    """Base exception for LintPDF SDK errors."""


class AuthenticationError(LintPDFError):
    """API key is invalid or missing."""


class RateLimitError(LintPDFError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after}s")


class Finding:
    """A single preflight finding."""

    def __init__(self, data: dict):
        self.inspection_id: str = data.get("inspection_id", "")
        self.severity: str = data.get("severity", "")
        self.message: str = data.get("message", "")
        self.page_num: int = data.get("page_num", 0)
        self.details: dict = data.get("details", {})
        self.iso_clause: str = data.get("iso_clause", "")
        self.bbox: tuple | None = tuple(data["bbox"]) if data.get("bbox") else None

    def __repr__(self) -> str:
        return f"Finding({self.inspection_id}, {self.severity}, {self.message!r})"


class PreflightResult:
    """Result of a preflight check."""

    def __init__(self, data: dict):
        self.job_id: str = data.get("job_id", "")
        self.profile_id: str = data.get("profile_id", "")
        self.passed: bool = data.get("summary", {}).get("passed", True)
        self.findings: list[Finding] = [Finding(f) for f in data.get("findings", [])]
        self.summary: dict = data.get("summary", {})
        self.duration_ms: int = data.get("duration_ms", 0)

    @property
    def error_count(self) -> int:
        return self.summary.get("error_count", 0)

    @property
    def warning_count(self) -> int:
        return self.summary.get("warning_count", 0)

    @property
    def advisory_count(self) -> int:
        return self.summary.get("advisory_count", 0)


class LintPDF:
    """LintPDF API client.

    Args:
        api_key: Your LintPDF API key (starts with lpdf_).
        base_url: API base URL (default: https://api.lintpdf.com).
        timeout: Request timeout in seconds (default: 300).
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.lintpdf.com",
        timeout: int = 300,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def preflight(
        self,
        pdf_path: str,
        *,
        profile: str = "lintpdf-default",
        jdf_path: str | None = None,
        wait: bool = True,
        timeout: int | None = None,
    ) -> PreflightResult:
        """Submit a PDF for preflight and optionally wait for results.

        Args:
            pdf_path: Path to the PDF file.
            profile: Preflight Profile ID.
            jdf_path: Optional path to a JDF/XJDF sidecar file.
            wait: If True, poll until job completes.
            timeout: Override timeout for this request.

        Returns:
            PreflightResult with findings and summary.

        Raises:
            AuthenticationError: If API key is invalid.
            RateLimitError: If rate limit exceeded.
            LintPDFError: For other API errors.
        """
        import httpx

        headers = {"Authorization": f"Bearer {self.api_key}"}
        t = timeout or self.timeout

        # Upload and submit
        with open(pdf_path, "rb") as f:
            files = {"file": f}
            if jdf_path is not None:
                jdf_fh = open(jdf_path, "rb")
                files["jdf_file"] = jdf_fh
            else:
                jdf_fh = None

            try:
                response = httpx.post(
                    f"{self.base_url}/api/v1/jobs",
                    headers=headers,
                    files=files,
                    data={"profile_id": profile},
                    timeout=t,
                )
            finally:
                if jdf_fh is not None:
                    jdf_fh.close()

        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        if response.status_code == 429:
            raise RateLimitError(int(response.headers.get("Retry-After", 60)))
        response.raise_for_status()

        job_data = response.json()
        job_id = job_data["id"]

        if not wait:
            return PreflightResult(job_data)

        # Poll for completion
        import time

        for _ in range(t):
            response = httpx.get(
                f"{self.base_url}/api/v1/jobs/{job_id}",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") in ("complete", "failed"):
                return PreflightResult(data)
            time.sleep(1)

        raise LintPDFError(f"Job {job_id} did not complete within {t}s")

    def list_profiles(self) -> list[dict]:
        """List available Preflight Profiles."""
        import httpx

        response = httpx.get(
            f"{self.base_url}/api/v1/profiles",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def reports(
        self,
        job_id: str,
        formats: list,
        *,
        idempotency_key: str | None = None,
        branding: dict | None = None,
        expiry_days: int | None = None,
        detail_level: str | None = None,
        summary_page: str | None = None,
    ) -> "ReportsResult":
        """Generate hosted and/or inline reports for a completed job.

        Wraps ``POST /api/v1/jobs/{job_id}/reports``.

        Args:
            job_id: UUID of the completed job.
            formats: Mixed list of bare format strings (back-compat —
                ``["html", "pdf"]``) or per-format specs
                (``[{"format": "json", "return": "inline"}]``). ``return``
                may be ``"url"`` (default), ``"inline"`` (text formats
                only: ``json``/``xml``), or ``"both"``.
            idempotency_key: Optional client-supplied key. Repeated
                calls with the same key converge on the same token and
                reuse the stored artifact instead of regenerating it.
            branding: Optional ``{"name", "logo_url", "primary_color",
                "accent_color", "hide_footer"}`` override. Ignored
                unless the tenant has the white-label entitlement.
            expiry_days: Override token TTL.
            detail_level: ``"executive"`` | ``"standard"`` (default) |
                ``"comprehensive"``.
            summary_page: ``"prepend"`` (default) | ``"only"`` | ``"off"``.

        Returns:
            ``ReportsResult`` whose ``reports`` list exposes both the
            hosted URL (when applicable) and the inline ``data`` /
            ``content_type`` (when applicable) for each requested
            format.
        """
        import httpx

        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        body: dict = {"formats": formats}
        if branding is not None:
            body["branding"] = branding
        if expiry_days is not None:
            body["expiry_days"] = expiry_days
        if detail_level is not None:
            body["detail_level"] = detail_level
        if summary_page is not None:
            body["summary_page"] = summary_page

        response = httpx.post(
            f"{self.base_url}/api/v1/jobs/{job_id}/reports",
            headers=headers,
            json=body,
            timeout=self.timeout,
        )
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        if response.status_code == 429:
            raise RateLimitError(int(response.headers.get("Retry-After", 60)))
        response.raise_for_status()
        return ReportsResult(response.json())


class ReportArtifact:
    """One row from ``POST /reports``.

    Either ``url`` is populated (default / ``return="url"``), ``data``
    is populated (``return="inline"`` — text formats only), or both
    (``return="both"``). ``token`` and ``expires_at`` mirror ``url``:
    populated when the engine minted a share link, ``None`` otherwise.
    """

    def __init__(self, data: dict):
        self.format: str = data.get("format", "")
        self.url: str | None = data.get("url")
        self.token: str | None = data.get("token")
        self.expires_at: str | None = data.get("expires_at")
        self.data = data.get("data")
        self.content_type: str | None = data.get("content_type")

    def __repr__(self) -> str:
        return (
            f"ReportArtifact({self.format}, url={self.url!r}, "
            f"token={self.token!r}, inline={'yes' if self.data is not None else 'no'})"
        )


class ReportsResult:
    """Envelope returned by :py:meth:`LintPDF.reports`."""

    def __init__(self, payload: dict):
        self.reports: list[ReportArtifact] = [
            ReportArtifact(r) for r in payload.get("reports", [])
        ]

    def by_format(self, fmt: str) -> ReportArtifact | None:
        """Return the first artifact matching ``fmt`` (or None)."""
        for r in self.reports:
            if r.format == fmt:
                return r
        return None

    def __iter__(self):
        return iter(self.reports)

    def __len__(self) -> int:
        return len(self.reports)
