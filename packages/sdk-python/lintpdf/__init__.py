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
        # Q-C4/C5 AI-Explain cache + Wave V V-05 effective_decision —
        # surfaced on FindingResponse since PR 2 of the v2 playbook.
        self.ai_explanation: str | None = data.get("ai_explanation")
        self.ai_explanation_model: str | None = data.get("ai_explanation_model")
        self.ai_explanation_at: str | None = data.get("ai_explanation_at")
        self.effective_decision: dict | None = data.get("effective_decision")

    def __repr__(self) -> str:
        return f"Finding({self.inspection_id}, {self.severity}, {self.message!r})"


class Explanation:
    """Result of POST /api/v1/jobs/{job_id}/findings/{finding_id}/explain."""

    def __init__(self, data: dict):
        self.finding_id: str = data.get("finding_id", "")
        self.text: str = data.get("explanation") or data.get("text", "")
        self.model: str | None = data.get("model")
        self.cached: bool = bool(data.get("cached", False))
        self.cost_cents: float | None = data.get("cost_cents")

    def __repr__(self) -> str:
        return f"Explanation({self.finding_id}, model={self.model!r}, cached={self.cached})"


class EpmVerdict:
    """Result of GET /api/v1/jobs/{job_id}/epm."""

    def __init__(self, data: dict):
        self.job_id: str = data.get("job_id", "")
        self.tier: str = data.get("tier", "")
        self.rejection_drivers: list[str] = list(data.get("rejection_drivers", []))
        self.advisories: list[str] = list(data.get("advisories", []))
        self.recommends_indichrome: bool = bool(data.get("recommends_indichrome", False))
        self.legacy_codes_fired: list[str] = list(data.get("legacy_codes_fired", []))
        self.epm_findings_count: int = int(data.get("epm_findings_count", 0))

    def __repr__(self) -> str:
        return (
            f"EpmVerdict(tier={self.tier!r}, drivers={len(self.rejection_drivers)}, "
            f"advisories={len(self.advisories)})"
        )


class Decision:
    """A single decision row (V-05 audit table)."""

    def __init__(self, data: dict):
        self.id: str = data.get("id", "")
        self.job_id: str = data.get("job_id", "")
        self.finding_id: str | None = data.get("finding_id")
        self.decision_type: str = data.get("decision_type", "")
        self.decision_value: str | None = data.get("decision_value")
        self.notes: str | None = data.get("notes")
        self.decided_by_user_id: str = data.get("decided_by_user_id", "")
        self.decided_by_email: str | None = data.get("decided_by_email")
        self.decided_at: str | None = data.get("decided_at")
        self.source: str = data.get("source", "")
        self.is_active: bool = bool(data.get("is_active", True))
        self.revoked_at: str | None = data.get("revoked_at")
        self.revoked_by_user_id: str | None = data.get("revoked_by_user_id")
        self.revoked_reason: str | None = data.get("revoked_reason")

    def __repr__(self) -> str:
        return f"Decision({self.id}, type={self.decision_type!r}, active={self.is_active})"


class Workflow:
    """A workflow row (Phase 0.7 unified-config substrate)."""

    def __init__(self, data: dict):
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.profile_id: str = data.get("profile_id", "")
        self.brand_spec_id: str | None = data.get("brand_spec_id")
        self.created_at: str | None = data.get("created_at")
        self.updated_at: str | None = data.get("updated_at")

    def __repr__(self) -> str:
        return f"Workflow({self.id}, name={self.name!r}, profile={self.profile_id!r})"


class CostCap:
    """LLM cost-cap snapshot for the tenant."""

    def __init__(self, data: dict):
        self.enabled: bool = bool(data.get("enabled", False))
        self.monthly_cap_cents: int = int(data.get("monthly_cap_cents", 0))
        self.alert_threshold_pct: int = int(data.get("alert_threshold_pct", 80))
        self.used_cents: int | None = data.get("used_cents")

    def __repr__(self) -> str:
        return (
            f"CostCap(enabled={self.enabled}, cap={self.monthly_cap_cents}c, "
            f"used={self.used_cents}c)"
        )


class PreflightResult:
    """Result of a preflight check."""

    def __init__(self, data: dict):
        self.job_id: str = data.get("job_id", "")
        self.profile_id: str = data.get("profile_id", "")
        self.passed: bool = data.get("summary", {}).get("passed", True)
        self.findings: list[Finding] = [Finding(f) for f in data.get("findings", [])]
        self.summary: dict = data.get("summary", {})
        self.duration_ms: int = data.get("duration_ms", 0)
        # Inline EPM verdict surfaced on the single-job endpoint (PR 2).
        epm_dict = data.get("epm_verdict")
        self.epm_verdict: EpmVerdict | None = (
            EpmVerdict({**epm_dict, "job_id": self.job_id})
            if isinstance(epm_dict, dict)
            else None
        )
        self.decisions_count: int | None = data.get("decisions_count")

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

    # ---- AI-Explain ---------------------------------------------------

    def explain_finding(self, job_id: str, finding_id: str) -> Explanation:
        """Request an AI explanation for a finding.

        Wraps ``POST /api/v1/jobs/{job_id}/findings/{finding_id}/explain``.
        Cost-cap exceeded → 402 → raised as :class:`LintPDFError`.
        """
        return Explanation(
            self._post(f"/api/v1/jobs/{job_id}/findings/{finding_id}/explain", body={})
        )

    # ---- EPM verdict --------------------------------------------------

    def get_epm_verdict(self, job_id: str) -> EpmVerdict:
        """Fetch the EPM candidacy verdict for a job.

        Wraps ``GET /api/v1/jobs/{job_id}/epm``.
        """
        return EpmVerdict(self._get(f"/api/v1/jobs/{job_id}/epm"))

    # ---- Decisions audit (Wave V V-05) -------------------------------

    def list_decisions(
        self, job_id: str, *, include_revoked: bool = False, limit: int = 200
    ) -> list[Decision]:
        """List decisions on a job (newest first)."""
        payload = self._get(
            f"/api/v1/jobs/{job_id}/decisions",
            params={"include_revoked": str(include_revoked).lower(), "limit": limit},
        )
        return [Decision(d) for d in payload.get("decisions", [])]

    def record_decision(
        self,
        job_id: str,
        *,
        decision_type: str,
        decided_by_user_id: str,
        source: str = "sdk",
        finding_id: str | None = None,
        decision_value: str | None = None,
        notes: str | None = None,
        decided_by_email: str | None = None,
        decision_metadata: dict | None = None,
    ) -> Decision:
        """Record a job- or finding-level decision (append-only)."""
        body: dict = {
            "decision_type": decision_type,
            "decided_by_user_id": decided_by_user_id,
            "source": source,
        }
        if decision_value is not None:
            body["decision_value"] = decision_value
        if notes is not None:
            body["notes"] = notes
        if decided_by_email is not None:
            body["decided_by_email"] = decided_by_email
        if decision_metadata is not None:
            body["decision_metadata"] = decision_metadata
        if finding_id:
            path = f"/api/v1/jobs/{job_id}/findings/{finding_id}/decisions"
        else:
            path = f"/api/v1/jobs/{job_id}/decisions"
        return Decision(self._post(path, body=body))

    def revoke_decision(
        self,
        job_id: str,
        decision_id: str,
        *,
        revoked_by_user_id: str,
        revoked_reason: str | None = None,
    ) -> Decision:
        """Soft-revoke a decision (Q-2). Idempotent."""
        body: dict = {"revoked_by_user_id": revoked_by_user_id}
        if revoked_reason is not None:
            body["revoked_reason"] = revoked_reason
        return Decision(
            self._post(
                f"/api/v1/jobs/{job_id}/decisions/{decision_id}/revoke",
                body=body,
            )
        )

    # ---- Workflows (Phase 0.7 unified-config substrate) --------------

    def list_workflows(self) -> list[Workflow]:
        payload = self._get("/api/v1/workflows")
        return [Workflow(w) for w in payload.get("workflows", payload if isinstance(payload, list) else [])]

    def create_workflow(
        self, *, name: str, profile_id: str, brand_spec_id: str | None = None
    ) -> Workflow:
        body: dict = {"name": name, "profile_id": profile_id}
        if brand_spec_id is not None:
            body["brand_spec_id"] = brand_spec_id
        return Workflow(self._post("/api/v1/workflows", body=body))

    def update_workflow(self, workflow_id: str, **fields) -> Workflow:
        return Workflow(self._patch(f"/api/v1/workflows/{workflow_id}", body=fields))

    def delete_workflow(self, workflow_id: str) -> None:
        self._delete(f"/api/v1/workflows/{workflow_id}")

    # ---- LLM cost-cap (Q-C5) -----------------------------------------

    def get_cost_cap(self) -> CostCap:
        """Read the tenant's current cost-cap configuration + usage."""
        return CostCap(self._get("/api/v1/ai/cost-cap"))

    def set_cost_cap(
        self,
        *,
        enabled: bool,
        monthly_cap_cents: int | None = None,
        alert_threshold_pct: int | None = None,
    ) -> CostCap:
        """Update the tenant's cost-cap configuration. Tenant-scope only."""
        body: dict = {"enabled": enabled}
        if monthly_cap_cents is not None:
            body["monthly_cap_cents"] = monthly_cap_cents
        if alert_threshold_pct is not None:
            body["alert_threshold_pct"] = alert_threshold_pct
        return CostCap(self._post("/api/v1/ai/cost-cap", body=body))

    # ---- internal HTTP helpers ---------------------------------------

    def _headers(self, *, body: bool = False) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self.api_key}"}
        if body:
            h["Content-Type"] = "application/json"
        return h

    def _raise_for(self, response) -> None:
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        if response.status_code == 402:
            raise LintPDFError(
                f"Cost cap exceeded (HTTP 402): {response.text}"
            )
        if response.status_code == 429:
            raise RateLimitError(int(response.headers.get("Retry-After", 60)))
        response.raise_for_status()

    def _get(self, path: str, *, params: dict | None = None) -> dict:
        import httpx

        response = httpx.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        self._raise_for(response)
        return response.json()

    def _post(self, path: str, *, body: dict) -> dict:
        import httpx

        response = httpx.post(
            f"{self.base_url}{path}",
            headers=self._headers(body=True),
            json=body,
            timeout=self.timeout,
        )
        self._raise_for(response)
        return response.json()

    def _patch(self, path: str, *, body: dict) -> dict:
        import httpx

        response = httpx.patch(
            f"{self.base_url}{path}",
            headers=self._headers(body=True),
            json=body,
            timeout=self.timeout,
        )
        self._raise_for(response)
        return response.json()

    def _delete(self, path: str) -> None:
        import httpx

        response = httpx.delete(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        self._raise_for(response)


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
