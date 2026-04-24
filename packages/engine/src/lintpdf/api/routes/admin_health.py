"""Admin health toolbox — ops-only tools surfaced on /dashboard/admin/health.

Four tools, zero customer-path impact:

* ``POST /admin/health/opus-audit`` — runs the Opus internal auditor
  on a specific job id. Manual only; never wired into the preflight
  critical path. Useful for red-teaming a Claude Haiku pass.
* ``POST /admin/health/corpus-benchmark`` — kicks off the golden-PDF
  harness. Shells out to ``scripts/audit_preflight_accuracy.py``.
* ``GET /admin/health/claude-probe`` — one synthetic Haiku ping;
  surfaces latency + status for the probe badge.
* ``POST /admin/health/outage-override`` — force-sets the
  reactive outage flag on/off. Lets ops test the banner without
  waiting for the real sliding-window detector to flip.

All endpoints gated by ``_verify_admin_key`` (shared admin secret).
"""

from __future__ import annotations

import logging
import os
import time
import uuid as uuid_mod
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from lintpdf.api.database import get_db

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/health", tags=["admin-health"])


# Deferred import trick: the admin key verifier lives inside
# ``routes/admin.py`` and depends on a lot of state — we pull it
# via module attribute access at request time to avoid a circular
# import at module load.
def _verify_admin_key_dep():
    from lintpdf.api.routes import admin as _admin

    return Depends(_admin._verify_admin_key)


class OpusAuditRequest(BaseModel):
    job_id: str = Field(..., description="Target job id (UUID).")


class OpusAuditResponse(BaseModel):
    job_id: str
    findings_audited: int
    model: str


@router.post("/opus-audit", response_model=OpusAuditResponse)
async def run_opus_audit(
    body: OpusAuditRequest,
    db: Session = Depends(get_db),
    _admin: str = _verify_admin_key_dep(),
) -> OpusAuditResponse:
    """Run the internal Opus auditor against a specific job, admin only.

    Never touches the customer request path. Writes verdicts with
    ``audit_model`` set to the Opus model name so subsequent
    Haiku runs can tell them apart.
    """
    try:
        uid = uuid_mod.UUID(body.job_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="job_id must be UUID") from exc

    from lintpdf.api.models import Job, JobFinding
    from lintpdf.api.storage import get_storage
    from lintpdf.audit.internal import InternalAuditor

    job = db.query(Job).filter(Job.id == uid).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    findings = db.query(JobFinding).filter(JobFinding.job_id == job.id).all()
    if not findings:
        return OpusAuditResponse(job_id=str(uid), findings_audited=0, model="claude-opus-4-7")

    storage = get_storage()
    pdf_bytes = storage.download_pdf(job.file_key)

    auditor = InternalAuditor()
    verdicts = auditor.audit(pdf_bytes, findings)
    written = 0
    for f, v in zip(findings, verdicts, strict=False):
        if v is None:
            continue
        f.audit_status = v.status
        f.audit_rationale = v.rationale
        f.audit_model = v.model
        f.audit_at = v.at
        written += 1
    if written:
        db.commit()
    return OpusAuditResponse(
        job_id=str(uid),
        findings_audited=written,
        model=os.environ.get("LINTPDF_OPUS_MODEL", "claude-opus-4-7"),
    )


class CorpusBenchmarkResponse(BaseModel):
    started: bool
    last_run_at: str | None = None
    pass_rate: float | None = None
    message: str


@router.post("/corpus-benchmark", response_model=CorpusBenchmarkResponse)
async def run_corpus_benchmark(
    _admin: str = _verify_admin_key_dep(),
) -> CorpusBenchmarkResponse:
    """Kick off the golden-corpus benchmark harness in a subprocess.

    The harness itself writes its report to
    ``tests/fixtures/accuracy/_runs/`` — this endpoint just fires
    it and returns "started". Poll the spend dashboard or the
    reports directory for completion.
    """
    import subprocess

    script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "..",
        "..",
        "scripts",
        "audit_preflight_accuracy.py",
    )
    script = os.path.abspath(script)
    if not os.path.isfile(script):
        return CorpusBenchmarkResponse(
            started=False,
            message=f"Harness script not found at {script}",
        )
    try:
        # Fire-and-forget. The harness script is idempotent and
        # writes its own run artifacts; we just need it to start.
        subprocess.Popen(
            ["python", script, "--coverage-only"],
            cwd=os.path.dirname(script),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return CorpusBenchmarkResponse(
            started=True,
            message="Benchmark started; check tests/fixtures/accuracy/_runs/",
        )
    except Exception as exc:
        return CorpusBenchmarkResponse(started=False, message=f"Failed to start: {exc!s}")


class ClaudeProbeResponse(BaseModel):
    status: str
    latency_ms: int | None = None
    error: str | None = None


@router.get("/claude-probe", response_model=ClaudeProbeResponse)
async def claude_probe(
    _admin: str = _verify_admin_key_dep(),
) -> ClaudeProbeResponse:
    """Fire one synthetic Haiku call and return status + latency."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return ClaudeProbeResponse(status="unconfigured", error="ANTHROPIC_API_KEY is not set")
    try:
        import anthropic

        client = anthropic.Anthropic()
        t0 = time.monotonic()
        client.messages.create(
            model=os.environ.get("LINTPDF_AUDIT_MODEL", "claude-haiku-4-5"),
            max_tokens=8,
            messages=[{"role": "user", "content": "ping"}],
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        return ClaudeProbeResponse(status="ok", latency_ms=latency_ms)
    except Exception as exc:
        return ClaudeProbeResponse(status="error", error=str(exc))


class OutageOverrideRequest(BaseModel):
    state: bool | None = Field(
        ...,
        description="True = force outage banner on. False = clear. null = no-op.",
    )


@router.post("/outage-override")
async def outage_override(
    body: OutageOverrideRequest,
    _admin: str = _verify_admin_key_dep(),
) -> dict[str, Any]:
    """Force the AI outage flag on/off for manual banner testing."""
    from lintpdf.audit.outage import override

    override(body.state)
    return {"state": body.state}
