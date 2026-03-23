"""Natural language report interpretation endpoint."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  # noqa: TC002

from grounded.api.ai_schemas import NLInterpretResponse
from grounded.api.auth import get_current_tenant
from grounded.api.database import get_db
from grounded.api.models import Job, JobFinding, JobStatus, Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/captains-log", tags=["ai-interpret"])

_INTERPRET_SYSTEM_PROMPT = """You are a prepress expert explaining PDF preflight findings in plain language.

For each finding, provide:
1. A clear, non-technical explanation of what was found
2. Why it matters for print production
3. A practical suggestion for how to fix it

Use simple language. Avoid jargon. The reader may not be a print professional.

Respond as a JSON array where each element has:
- "inspection_id": the original ID
- "explanation": plain language explanation
- "why_it_matters": why this is important
- "suggestion": how to fix it

Wrap the array in {"interpretations": [...], "summary": "overall summary"}"""


@router.get("/{job_id}/interpret", response_model=NLInterpretResponse)
async def interpret_captains_log(
    job_id: str,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> NLInterpretResponse:
    """Generate plain language interpretation of Captain's Log findings."""
    import uuid as uuid_mod

    from grounded.ai.access import check_ai_access

    check_ai_access(tenant, db)

    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid job ID format.",
        ) from exc

    job = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if job.status != JobStatus.COMPLETE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is not yet complete.",
        )

    findings = db.query(JobFinding).filter(JobFinding.job_id == uid).all()
    if not findings:
        return NLInterpretResponse(
            summary="No findings to interpret. The file passed all checks.",
            interpretations=[],
        )

    # Build findings text for LLM
    findings_text = []
    for f in findings:
        findings_text.append(
            f"- [{f.severity}] {f.inspection_id}: {f.message} (page {f.page_num or 'N/A'})"
        )
    findings_str = "\n".join(findings_text)

    try:
        result = _interpret_with_llm(findings_str)
    except Exception:
        logger.exception("LLM interpretation failed")
        result = _interpret_rule_based(findings)

    return NLInterpretResponse(
        summary=result.get("summary", ""),
        interpretations=result.get("interpretations", []),
    )


def _interpret_with_llm(findings_text: str) -> dict[str, Any]:
    """Interpret findings using an LLM."""
    import json

    try:
        import anthropic

        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            system=_INTERPRET_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Please interpret these preflight findings:\n\n{findings_text}",
                }
            ],
        )
        result: dict[str, Any] = json.loads(message.content[0].text)
        return result
    except ImportError:
        raise RuntimeError("anthropic package not installed") from None


def _interpret_rule_based(findings: list[JobFinding]) -> dict[str, Any]:
    """Fallback rule-based interpretation."""
    severity_counts = {"error": 0, "warning": 0, "advisory": 0}
    interpretations = []

    for f in findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        interpretations.append(
            {
                "inspection_id": f.inspection_id,
                "explanation": f.message,
                "why_it_matters": _severity_explanation(f.severity),
                "suggestion": "Review this finding and correct the issue in your source file.",
            }
        )

    errors = severity_counts.get("error", 0)
    warnings = severity_counts.get("warning", 0)
    advisory = severity_counts.get("advisory", 0)

    if errors > 0:
        summary = f"This file has {errors} critical issue(s) that must be fixed before printing."
    elif warnings > 0:
        summary = f"This file has {warnings} warning(s) that should be reviewed."
    else:
        summary = f"This file has {advisory} informational note(s). No critical issues found."

    return {"summary": summary, "interpretations": interpretations}


def _severity_explanation(severity: str) -> str:
    """Get a plain language explanation for a severity level."""
    return {
        "error": "This is a critical issue that will likely cause problems in print production.",
        "warning": "This is a warning that could affect print quality and should be reviewed.",
        "advisory": "This is informational and may not require action.",
    }.get(severity, "Review this finding.")
