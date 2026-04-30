"""Q-C4 / Q-C5 — AI-Explain service + HTTP route tests."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from siftpdf.ai.cost_cap import CAP_TOGGLE_ID, CostCapExceededError
from siftpdf.ai.explain import explain_finding
from siftpdf.tenants.toggle_models import (
    ToggleOverride,
    ToggleScope,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


def _make_finding(db, *, tenant_id, job_id=None):
    from siftpdf.api.models import Job, JobFinding, JobStatus

    if job_id is None:
        job = Job(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            status=JobStatus.PENDING,
            profile_id="lintpdf-default",
            file_key=f"{tenant_id}/x.pdf",
            file_name="x.pdf",
            file_size=1,
        )
        db.add(job)
        db.commit()
        job_id = job.id

    finding = JobFinding(
        id=uuid.uuid4(),
        job_id=job_id,
        inspection_id="LPDF_F-22",
        severity="warning",
        message="Image below 300 dpi",
        page_num=2,
        category="resolution",
    )
    db.add(finding)
    db.commit()
    return finding


def _enable_cap(db, tenant_id, *, monthly_cap_cents):
    db.add(
        ToggleOverride(
            id=secrets.token_urlsafe(8),
            toggle_id=CAP_TOGGLE_ID,
            scope=ToggleScope.TENANT,
            scope_id=str(tenant_id),
            value={
                "enabled": True,
                "monthly_cap_cents": monthly_cap_cents,
                "alert_threshold_pct": 80,
            },
            locked=False,
            set_by="test",
            surface="test",
        )
    )
    db.commit()


def _add_usage(db, tenant_id, cost_cents):
    from siftpdf.api.models import AIUsageLog

    db.add(
        AIUsageLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            job_id=None,
            category="explain",
            feature="explain",
            credits_consumed=cost_cents,
            cost=cost_cents / 100.0,
            processing_time_ms=0,
            cost_cents=cost_cents,
        )
    )
    db.commit()


# ---- service-level: cache hit doesn't call Claude ------------------------


def test_explain_returns_cache_when_present(db_session: Session, monkeypatch):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)
    finding.ai_explanation = "Pre-cached explanation."
    finding.ai_explanation_model = "claude-haiku-4-5"
    finding.ai_explanation_at = datetime.now(tz=timezone.utc)
    db_session.commit()

    # Ensure a Claude call would error out — proving we never reach it.
    import siftpdf.ai.explain as explain_mod

    monkeypatch.setattr(
        explain_mod,
        "check_cap_or_raise",
        MagicMock(side_effect=AssertionError("cap check should not run")),
    )

    text = explain_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID, finding=finding)
    assert text == "Pre-cached explanation."


# ---- cost-cap-exceeded → raise ------------------------------------------


def test_explain_raises_when_cost_cap_exceeded(db_session: Session, monkeypatch):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)
    _enable_cap(db_session, PLACEHOLDER_TENANT_ID, monthly_cap_cents=100)
    _add_usage(db_session, PLACEHOLDER_TENANT_ID, cost_cents=100)

    # Even if anthropic is missing/configured, the cap check fires first.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(CostCapExceededError):
        explain_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID, finding=finding)


# ---- happy path: mocks Claude, caches result ----------------------------


def test_explain_calls_claude_and_caches(db_session: Session, monkeypatch):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    # Stub anthropic.Anthropic so the test never hits the network.
    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text=" Resolution issue. ")]
    fake_response.usage = MagicMock(
        input_tokens=120,
        output_tokens=80,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    fake_anthropic = MagicMock()
    fake_anthropic.Anthropic = MagicMock(return_value=fake_client)

    import sys

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    text = explain_finding(
        db_session,
        tenant_id=PLACEHOLDER_TENANT_ID,
        finding=finding,
    )

    assert text == "Resolution issue."
    db_session.refresh(finding)
    assert finding.ai_explanation == "Resolution issue."
    assert finding.ai_explanation_model == "claude-haiku-4-5"
    assert finding.ai_explanation_at is not None

    # Calling again should NOT hit the (expensive) mock again.
    fake_client.messages.create.reset_mock()
    text2 = explain_finding(
        db_session,
        tenant_id=PLACEHOLDER_TENANT_ID,
        finding=finding,
    )
    assert text2 == "Resolution issue."
    fake_client.messages.create.assert_not_called()


def test_explain_returns_none_when_anthropic_key_missing(db_session: Session, monkeypatch):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    text = explain_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID, finding=finding)
    assert text is None
    db_session.refresh(finding)
    assert finding.ai_explanation is None


def test_explain_returns_none_when_claude_call_raises(db_session: Session, monkeypatch):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RuntimeError("transient")
    fake_anthropic = MagicMock()
    fake_anthropic.Anthropic = MagicMock(return_value=fake_client)
    import sys

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    text = explain_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID, finding=finding)
    assert text is None
    db_session.refresh(finding)
    # Cache stays NULL so a future call retries.
    assert finding.ai_explanation is None


def test_explain_returns_none_when_response_text_empty(db_session: Session, monkeypatch):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    fake_response = MagicMock()
    fake_response.content = []  # empty payload
    fake_response.usage = MagicMock(
        input_tokens=0,
        output_tokens=0,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    fake_anthropic = MagicMock()
    fake_anthropic.Anthropic = MagicMock(return_value=fake_client)
    import sys

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    text = explain_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID, finding=finding)
    assert text is None


def test_explain_skip_cache_recomputes(db_session: Session, monkeypatch):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)
    finding.ai_explanation = "stale"
    db_session.commit()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text="fresh")]
    fake_response.usage = MagicMock(
        input_tokens=10,
        output_tokens=5,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    fake_anthropic = MagicMock()
    fake_anthropic.Anthropic = MagicMock(return_value=fake_client)
    import sys

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    text = explain_finding(
        db_session,
        tenant_id=PLACEHOLDER_TENANT_ID,
        finding=finding,
        skip_cache=True,
    )
    assert text == "fresh"


# ---- HTTP route ----------------------------------------------------------


def test_route_returns_cached_explanation(client: TestClient, db_session: Session):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)
    finding.ai_explanation = "Already done."
    finding.ai_explanation_model = "claude-haiku-4-5"
    finding.ai_explanation_at = datetime.now(tz=timezone.utc)
    db_session.commit()

    resp = client.post(f"/api/v1/jobs/{finding.job_id}/findings/{finding.id}/explain")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["explanation"] == "Already done."
    assert body["cached"] is True
    assert body["model"] == "claude-haiku-4-5"


def test_route_404_for_unknown_finding(client: TestClient, db_session: Session):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)
    resp = client.post(f"/api/v1/jobs/{finding.job_id}/findings/{uuid.uuid4()}/explain")
    assert resp.status_code == 404


def test_route_404_for_invalid_uuid(client: TestClient):
    resp = client.post("/api/v1/jobs/not-a-uuid/findings/also-not-a-uuid/explain")
    assert resp.status_code == 404


def test_route_404_when_finding_belongs_to_other_tenant(client: TestClient, db_session: Session):
    """Cross-tenant: a finding owned by another tenant must 404 for us."""
    from siftpdf.api.models import Tenant, TenantPlan

    foreign_id = uuid.uuid4()
    db_session.add(
        Tenant(
            id=foreign_id,
            name="other",
            api_key_hash="other-hash",
            plan=TenantPlan.GROWTH,
            rate_limit_daily=1000,
            max_file_size_mb=10,
        )
    )
    db_session.commit()

    finding = _make_finding(db_session, tenant_id=foreign_id)
    finding.ai_explanation = "Foreign secret."
    db_session.commit()

    # Auth fixture impersonates PLACEHOLDER_TENANT_ID, so this is a
    # cross-tenant lookup
    resp = client.post(f"/api/v1/jobs/{finding.job_id}/findings/{finding.id}/explain")
    assert resp.status_code == 404


def test_route_402_when_cost_cap_exceeded(client: TestClient, db_session: Session, monkeypatch):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)
    _enable_cap(db_session, PLACEHOLDER_TENANT_ID, monthly_cap_cents=100)
    _add_usage(db_session, PLACEHOLDER_TENANT_ID, cost_cents=100)

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resp = client.post(f"/api/v1/jobs/{finding.job_id}/findings/{finding.id}/explain")
    assert resp.status_code == 402, resp.text
    body = resp.json()["detail"]
    assert body["code"] == "cost_cap_exceeded"
    assert body["cap_cents"] == 100
    assert body["used_cents"] == 100


def test_route_503_when_claude_unconfigured(client: TestClient, db_session: Session, monkeypatch):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    resp = client.post(f"/api/v1/jobs/{finding.job_id}/findings/{finding.id}/explain")
    assert resp.status_code == 503


def test_route_calls_claude_when_no_cache_present(
    client: TestClient, db_session: Session, monkeypatch
):
    from tests.api.conftest import PLACEHOLDER_TENANT_ID

    finding = _make_finding(db_session, tenant_id=PLACEHOLDER_TENANT_ID)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text="Image is too low-res for printing.")]
    fake_response.usage = MagicMock(
        input_tokens=120,
        output_tokens=40,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    fake_anthropic = MagicMock()
    fake_anthropic.Anthropic = MagicMock(return_value=fake_client)
    import sys

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    resp = client.post(f"/api/v1/jobs/{finding.job_id}/findings/{finding.id}/explain")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["explanation"] == "Image is too low-res for printing."
    assert body["cached"] is False
    fake_client.messages.create.assert_called_once()
