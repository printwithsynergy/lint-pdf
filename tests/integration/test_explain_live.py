"""Live-AI verification (Gate G5 PR 20).

Opt-in test that hits the **real** Claude Haiku 4.5 API via
:func:`lintpdf.ai.explain.explain_finding`. Exercises the full path:

* No-cache (skip_cache=True) → real API call.
* Cache write back to the JobFinding row.
* AIUsageLog row written via the inline metering shim.

Cost: ~$0.01 per run (one Haiku call with ~400 input + 200 output
tokens). Runs only when the ``live_ai`` pytest marker is selected,
so default ``pytest`` invocations skip it. Also requires
``ANTHROPIC_API_KEY`` to be set; otherwise the test is skipped.

Usage:

    uv run --package engine pytest -m live_ai
    # or via the make target shipped in the engine Makefile:
    make smoke-live-ai

Failure modes:

* Missing key → ``pytest.skip``.
* Real call succeeds → asserts text is non-empty + cached on the row.
* Real call fails (Anthropic outage, rate-limit) → test fails so
  release engineers see the regression *before* tagging.
"""

from __future__ import annotations

import os
import uuid

import pytest

pytestmark = pytest.mark.live_ai


@pytest.fixture(scope="module")
def _has_api_key() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set — live-AI verification is opt-in")
    return True


def test_real_claude_explain_round_trip(_has_api_key, db_session, tmp_path) -> None:
    """Hit real Claude — assert cache write + non-empty explanation."""
    from lintpdf.ai.explain import explain_finding
    from lintpdf.api.models import Job, JobFinding, JobStatus
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    job = Job(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        status=JobStatus.COMPLETE,
        profile_id="lintpdf-default",
        file_key="live-ai/x.pdf",
        file_name="x.pdf",
        file_size=1,
    )
    db_session.add(job)
    db_session.commit()

    finding = JobFinding(
        id=uuid.uuid4(),
        job_id=job.id,
        inspection_id="LPDF_FONT_001",
        severity="error",
        message=(
            "Helvetica-Bold is referenced on page 3 but the embedded font "
            "stream is missing. Output device will substitute a fallback "
            "font, changing layout metrics."
        ),
        page_num=3,
        category="fonts",
    )
    db_session.add(finding)
    db_session.commit()

    text = explain_finding(
        db_session,
        tenant_id=PLACEHOLDER_TENANT_ID,
        finding=finding,
        skip_cache=True,
    )

    assert text is not None, "Claude returned None — see log for failure mode"
    assert len(text.strip()) > 20, "explanation too short — possibly an error"

    # Cache write must have landed.
    db_session.refresh(finding)
    assert finding.ai_explanation == text
    assert finding.ai_explanation_model is not None
    assert finding.ai_explanation_at is not None


def test_real_claude_explain_caches_second_call(_has_api_key, db_session) -> None:
    """Second call should hit the cache; no new API spend."""
    from lintpdf.ai.explain import explain_finding
    from lintpdf.api.models import Job, JobFinding, JobStatus
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    job = Job(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        status=JobStatus.COMPLETE,
        profile_id="lintpdf-default",
        file_key="live-ai/y.pdf",
        file_name="y.pdf",
        file_size=1,
    )
    db_session.add(job)
    db_session.commit()

    finding = JobFinding(
        id=uuid.uuid4(),
        job_id=job.id,
        inspection_id="LPDF_IMG_001",
        severity="warning",
        message="Image Im4 placed at 96 DPI is below the 300 DPI minimum.",
        page_num=1,
        category="images",
        ai_explanation="Pre-cached: image is below the resolution threshold.",
        ai_explanation_model="claude-haiku-4-5",
    )
    db_session.add(finding)
    db_session.commit()

    text = explain_finding(
        db_session,
        tenant_id=PLACEHOLDER_TENANT_ID,
        finding=finding,
        skip_cache=False,
    )
    assert text == finding.ai_explanation, "second call ignored the cache — would be paying twice"
