"""Q-C4 / Q-C5 — AI-Explain service.

Produces a 2-3 sentence plain-language explanation for a single
preflight finding, suitable for the viewer's "Explain" button.
Every explanation is cached on the parent ``JobFinding`` row so a
second view of the same finding doesn't pay for a fresh Claude call.

Cost-cap aware: every dispatch goes through
:func:`lintpdf.ai.cost_cap.check_cap_or_raise` so a tenant who has
opted into the per-tenant LLM cost cap can never overspend by
clicking Explain repeatedly. When the cap is exceeded the call
raises :class:`lintpdf.ai.cost_cap.CostCapExceededError` and the
caller's HTTP handler renders a 402.

Model: ``claude-haiku-4-5`` per Q-C4; overridable via
``LINTPDF_EXPLAIN_MODEL`` for staging experiments. Token budget:
~400 input + 200 output, well under the cap-relevant numbers
exercised by audit / OCR.

Side-effect ordering inside the service:

1. Cache hit on ``finding.ai_explanation`` → return immediately, no spend.
2. Cap check (``check_cap_or_raise``) → may raise CostCapExceededError.
3. Claude Haiku call.
4. ``record_usage`` — best-effort, never raises.
5. Cache write back to ``finding.ai_explanation`` /
   ``ai_explanation_model`` / ``ai_explanation_at``; commit.

Defensive: if the Claude call fails for any reason the service
returns ``None`` and leaves the cache row untouched so the next
attempt can retry. The HTTP handler renders a 503-style payload.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from lintpdf.ai.cost_cap import CostCapExceededError, check_cap_or_raise

if TYPE_CHECKING:
    import uuid as uuid_mod

    from sqlalchemy.orm import Session

    from lintpdf.api.models import JobFinding


logger = logging.getLogger(__name__)


_DEFAULT_MODEL = os.environ.get("LINTPDF_EXPLAIN_MODEL", "claude-haiku-4-5")
_MAX_TOKENS = 256
_SYSTEM_PROMPT = (
    "You are a senior prepress operator explaining a PDF preflight"
    " finding to a designer who is not a print expert. Your job is to:"
    "\n  1. Translate the technical message into plain language."
    "\n  2. Explain in one sentence why the issue matters at print time."
    "\n  3. Suggest a concrete fix the designer can apply in their"
    " authoring tool (Illustrator / InDesign / Photoshop)."
    "\nAlways write 2-3 sentences total. Never invent details that the"
    " input did not state. If the input is ambiguous, lead with what"
    " is verified and flag the unknown part briefly."
)


def explain_finding(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    finding: JobFinding,
    model: str | None = None,
    skip_cache: bool = False,
) -> str | None:
    """Return a cached or freshly-computed explanation for ``finding``.

    Returns ``None`` when:
    * The Claude client is not configured (no ANTHROPIC_API_KEY).
    * The Claude call raised — caller can retry on a future request.

    Raises :class:`CostCapExceededError` when the tenant has the cost
    cap enabled and the next call would push past the cap. The caller
    surfaces this as a 402.
    """
    if not skip_cache and finding.ai_explanation:
        return finding.ai_explanation

    resolved_model = model or _DEFAULT_MODEL

    # Cap check before paying for tokens. ``check_cap_or_raise`` is a
    # no-op when the cap is disabled (the default).
    check_cap_or_raise(db, tenant_id)

    try:
        import anthropic
    except ImportError:  # pragma: no cover — anthropic is a runtime dep
        logger.warning("explain_finding: anthropic package missing; cannot dispatch")
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning(
            "explain_finding: ANTHROPIC_API_KEY unset; returning None for finding %s",
            finding.id,
        )
        return None

    user_prompt = _build_user_prompt(finding)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(  # type: ignore[call-overload]
            model=resolved_model,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception:
        logger.exception(
            "explain_finding: Claude call failed for finding %s tenant %s",
            finding.id,
            tenant_id,
        )
        return None

    text = _extract_text(response)
    if not text:
        logger.warning(
            "explain_finding: Claude returned empty response for finding %s",
            finding.id,
        )
        return None

    # Best-effort metering write into the caller's session (so we don't
    # spin up a second SessionLocal in test/Celery contexts that haven't
    # initialized one). Never raises.
    _record_usage_inline(
        db,
        tenant_id=tenant_id,
        job_id=getattr(finding, "job_id", None),
        model=resolved_model,
        usage=getattr(response, "usage", None),
    )

    # Cache + commit. The caller already holds the session; the commit
    # here keeps the cache write atomic with the AIUsageLog row.
    finding.ai_explanation = text
    finding.ai_explanation_model = resolved_model
    finding.ai_explanation_at = datetime.now(tz=timezone.utc)
    db.commit()
    return text


def _build_user_prompt(finding: JobFinding) -> str:
    """Assemble the per-finding context for Claude.

    Kept compact: the system prompt carries the bulk of the
    instruction; the user message just states the facts.
    """
    parts: list[str] = []
    parts.append(f"Inspection ID: {finding.inspection_id}")
    parts.append(f"Severity: {finding.severity}")
    parts.append(f"Message: {finding.message}")
    if finding.page_num is not None:
        parts.append(f"Page: {finding.page_num}")
    if finding.category:
        parts.append(f"Category: {finding.category}")
    if finding.object_type:
        parts.append(f"Object type: {finding.object_type}")
    if finding.object_id:
        parts.append(f"Object id: {finding.object_id}")
    parts.append("\nWrite 2-3 sentences explaining what this finding means and how to fix it.")
    return "\n".join(parts)


def _extract_text(response: object) -> str | None:
    """Pull the text out of the Anthropic Messages response.

    Defensive against future SDK reshuffles: walks the ``content``
    blocks and concatenates ``type='text'`` parts, returning None on
    any unexpected structure.
    """
    content = getattr(response, "content", None)
    if not content:
        return None
    chunks: list[str] = []
    for block in content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text = getattr(block, "text", None)
            if isinstance(text, str):
                chunks.append(text)
    joined = "\n".join(c.strip() for c in chunks if c).strip()
    return joined or None


def _record_usage_inline(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    job_id: uuid_mod.UUID | None,
    model: str,
    usage: object,
) -> None:
    """Best-effort cost-cents bookkeeping written into the caller's session.

    Mirrors :func:`lintpdf.audit.metering.record_usage` but reuses the
    request-scoped session instead of opening a fresh ``SessionLocal``,
    which lets the explain hot path stay snappy in unit tests that
    haven't called ``init_db``.
    """
    try:
        from lintpdf.api.models import AIUsageLog
        from lintpdf.audit.metering import compute_cost_cents

        cost = compute_cost_cents(
            model=model,
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            cache_read_tokens=int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            cache_write_tokens=int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
        )
        db.add(
            AIUsageLog(
                tenant_id=tenant_id,
                job_id=job_id,
                category="explain",
                feature="explain",
                credits_consumed=cost,
                cost=cost / 100.0,
                processing_time_ms=0,
                result_summary=None,
                model=model,
                input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
                cache_read_tokens=int(getattr(usage, "cache_read_input_tokens", 0) or 0),
                cache_write_tokens=int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
                cost_cents=cost,
            )
        )
        db.flush()
    except Exception:
        logger.warning(
            "explain_finding: metering write failed (cap math will be slightly off)",
            exc_info=True,
        )


__all__ = ["CostCapExceededError", "explain_finding"]
