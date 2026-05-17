"""Corpus run execution logic.

The runner is invoked from the ``execute_corpus_run`` Celery task.
It runs the preflight orchestrator directly (no Job rows created) so
corpus runs never pollute the tenant's job history or consume preflight
quota.

Finding identity key: ``(inspection_id, severity, page_num)``
This is stable across minor engine changes but sensitive to new/removed
rules and severity promotions — the right signal for profile regression.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _identity_key(finding: dict[str, Any]) -> tuple[str, str, int | None]:
    return (
        finding.get("inspection_id") or "",
        finding.get("severity") or "",
        finding.get("page_num"),
    )


def _findings_to_identity_set(findings: list[dict[str, Any]]) -> set[tuple[str, str, int | None]]:
    return {_identity_key(f) for f in findings}


def _diff_findings(
    expected: list[dict[str, Any]],
    actual: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare expected vs actual findings and return a structured diff."""
    exp_keys = _findings_to_identity_set(expected)
    act_keys = _findings_to_identity_set(actual)

    missing = sorted(
        [{"inspection_id": k[0], "severity": k[1], "page_num": k[2]} for k in exp_keys - act_keys],
        key=lambda x: (x["inspection_id"], x["severity"] or "", x["page_num"] or 0),
    )
    new = sorted(
        [{"inspection_id": k[0], "severity": k[1], "page_num": k[2]} for k in act_keys - exp_keys],
        key=lambda x: (x["inspection_id"], x["severity"] or "", x["page_num"] or 0),
    )
    return {
        "missing": missing,
        "new": new,
        "actual_count": len(actual),
        "expected_count": len(expected),
    }


def _run_orchestrator(
    pdf_bytes: bytes,
    profile: Any,
    profile_id: str,
) -> list[dict[str, Any]]:
    """Run the preflight orchestrator and return serialised findings."""
    from lintpdf.profiles.orchestrator import PreflightOrchestrator

    orchestrator = PreflightOrchestrator(
        profile,
        profile_id=profile_id,
        ai_config={},
        pdf_bytes=pdf_bytes,
    )
    result = orchestrator.run(pdf_bytes)
    return [
        {
            "inspection_id": f.inspection_id,
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "page_num": f.page_num,
        }
        for f in result.findings
    ]


def execute_run(run_id: str, db: Session) -> None:
    """Execute all assays in a corpus run and persist results.

    Called synchronously from the ``execute_corpus_run`` Celery task.
    Mutates the ``CorpusRun`` and ``CorpusRunAssay`` rows in-place.
    """
    from lintpdf.api.config import get_settings
    from lintpdf.api.models import CorpusAssayStatus, CorpusRun, CorpusRunAssay, CorpusRunStatus
    from lintpdf.api.storage import get_storage
    from lintpdf.corpus.certificate import compute_corpus_hash, sign_certificate
    from lintpdf.profiles.registry import ProfileNotFoundError, ProfileRegistry

    run = db.get(CorpusRun, uuid.UUID(run_id))
    if run is None:
        logger.error("execute_run: corpus run %s not found", run_id)
        return

    run.status = CorpusRunStatus.PROCESSING
    db.commit()

    storage = get_storage()
    settings = get_settings()

    run_assays: list[CorpusRunAssay] = (
        db.query(CorpusRunAssay).filter(CorpusRunAssay.run_id == run.id).all()
    )

    # Resolve profile once — shared across all assays.
    try:
        registry = ProfileRegistry()
        profile = registry.get(run.profile_id)
    except ProfileNotFoundError:
        logger.exception("execute_run: could not resolve profile %s", run.profile_id)
        run.status = CorpusRunStatus.ERROR
        run.error_message = f"Profile '{run.profile_id}' not found."
        run.completed_at = datetime.now(UTC)
        db.commit()
        return

    pass_count = 0
    fail_count = 0
    assay_pdf_hashes: list[str] = []

    for run_assay in run_assays:
        assay = run_assay.assay
        try:
            pdf_bytes = storage.download_pdf(assay.pdf_storage_key)
        except Exception:
            logger.exception("execute_run: could not download PDF for assay %s", assay.id)
            run_assay.status = CorpusAssayStatus.ERROR
            run_assay.error_message = "PDF download failed."
            fail_count += 1
            db.commit()
            continue

        try:
            actual_findings = _run_orchestrator(pdf_bytes, profile, run.profile_id)
        except Exception:
            logger.exception("execute_run: orchestrator failed for assay %s", assay.id)
            run_assay.status = CorpusAssayStatus.ERROR
            run_assay.error_message = "Orchestrator raised an exception."
            fail_count += 1
            db.commit()
            continue

        expected = assay.expected_findings_json

        if expected is None:
            # Bootstrap: write engine output as the baseline.
            assay.expected_findings_json = actual_findings
            assay.updated_at = datetime.now(UTC)
            run_assay.status = CorpusAssayStatus.PASSED
            run_assay.bootstrapped = True
            run_assay.diff_json = {
                "missing": [],
                "new": [],
                "actual_count": len(actual_findings),
                "expected_count": len(actual_findings),
            }
            pass_count += 1
        else:
            diff = _diff_findings(expected, actual_findings)
            run_assay.diff_json = diff
            if diff["missing"] or diff["new"]:
                run_assay.status = CorpusAssayStatus.FAILED
                fail_count += 1
            else:
                run_assay.status = CorpusAssayStatus.PASSED
                pass_count += 1

        assay_pdf_hashes.append(assay.pdf_hash)
        db.commit()

    # Finalize run.
    run.pass_count = pass_count
    run.fail_count = fail_count
    run.completed_at = datetime.now(UTC)

    if fail_count == 0:
        run.status = CorpusRunStatus.PASSED
        if settings.corpus_signing_key and assay_pdf_hashes:
            corpus_hash = compute_corpus_hash(assay_pdf_hashes)
            run.certificate_json = sign_certificate(
                run_id=run.id,
                tenant_id=run.tenant_id,
                profile_id=run.profile_id,
                assay_count=run.assay_count,
                pass_count=pass_count,
                corpus_hash=corpus_hash,
                signing_key=settings.corpus_signing_key,
            )
    else:
        run.status = CorpusRunStatus.FAILED

    db.commit()
