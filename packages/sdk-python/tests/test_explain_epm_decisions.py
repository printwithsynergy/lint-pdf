"""SDK contract tests for AI-Explain, EPM verdict, decisions, workflows,
and cost-cap methods (PR 9 of the v2 playbook).

Uses pytest-httpx to stub the engine. The engine's own behavior is
covered in the engine test suite; here we only verify the client shapes
each request correctly and maps responses into typed result objects.
"""

from __future__ import annotations

import pytest

from lintpdf import (
    CostCap,
    Decision,
    EpmVerdict,
    Explanation,
    LintPDF,
    LintPDFError,
    Workflow,
)


@pytest.fixture
def client() -> LintPDF:
    return LintPDF(api_key="lpdf_test", base_url="https://api.example.com")


# ---- explain_finding ----------------------------------------------------


def test_explain_finding_returns_typed_result(httpx_mock, client: LintPDF) -> None:
    httpx_mock.add_response(
        url="https://api.example.com/api/v1/jobs/job-1/findings/find-1/explain",
        method="POST",
        json={
            "finding_id": "find-1",
            "explanation": "Embed your fonts.",
            "model": "claude-haiku-4-5",
            "cached": False,
            "cost_cents": 0.05,
        },
    )
    result = client.explain_finding("job-1", "find-1")
    assert isinstance(result, Explanation)
    assert result.text == "Embed your fonts."
    assert result.model == "claude-haiku-4-5"
    assert result.cached is False


def test_explain_finding_402_raises(httpx_mock, client: LintPDF) -> None:
    """Cost-cap exceeded → HTTP 402 → SDK raises LintPDFError."""
    httpx_mock.add_response(
        url="https://api.example.com/api/v1/jobs/job-1/findings/find-1/explain",
        method="POST",
        status_code=402,
        text="cost cap exceeded",
    )
    with pytest.raises(LintPDFError, match="Cost cap exceeded"):
        client.explain_finding("job-1", "find-1")


# ---- get_epm_verdict ---------------------------------------------------


def test_get_epm_verdict_returns_typed_result(httpx_mock, client: LintPDF) -> None:
    httpx_mock.add_response(
        url="https://api.example.com/api/v1/jobs/job-1/epm",
        method="GET",
        json={
            "job_id": "job-1",
            "tier": "marginal",
            "rejection_drivers": ["LPDF_EPM_BLEED_REJECT"],
            "advisories": ["LPDF_EPM_TRAPPING_REJECT"],
            "recommends_indichrome": False,
            "legacy_codes_fired": [],
            "epm_findings_count": 2,
        },
    )
    verdict = client.get_epm_verdict("job-1")
    assert isinstance(verdict, EpmVerdict)
    assert verdict.tier == "marginal"
    assert "LPDF_EPM_BLEED_REJECT" in verdict.rejection_drivers
    assert verdict.epm_findings_count == 2


# ---- decisions ---------------------------------------------------------


def test_list_decisions_maps_rows(httpx_mock, client: LintPDF) -> None:
    httpx_mock.add_response(
        url="https://api.example.com/api/v1/jobs/job-1/decisions?include_revoked=false&limit=200",
        method="GET",
        json={
            "decisions": [
                {
                    "id": "d1",
                    "job_id": "job-1",
                    "finding_id": None,
                    "decision_type": "approve",
                    "decided_by_user_id": "u1",
                    "source": "dashboard",
                    "is_active": True,
                },
            ],
            "count": 1,
        },
    )
    rows = client.list_decisions("job-1")
    assert len(rows) == 1
    assert isinstance(rows[0], Decision)
    assert rows[0].decision_type == "approve"


def test_record_job_decision(httpx_mock, client: LintPDF) -> None:
    httpx_mock.add_response(
        url="https://api.example.com/api/v1/jobs/job-1/decisions",
        method="POST",
        json={
            "id": "d2",
            "job_id": "job-1",
            "decision_type": "waive",
            "decided_by_user_id": "u1",
            "source": "sdk",
            "is_active": True,
        },
        status_code=201,
    )
    decision = client.record_decision(
        "job-1", decision_type="waive", decided_by_user_id="u1"
    )
    assert isinstance(decision, Decision)
    assert decision.decision_type == "waive"


def test_record_finding_decision_uses_finding_path(
    httpx_mock, client: LintPDF
) -> None:
    httpx_mock.add_response(
        url="https://api.example.com/api/v1/jobs/job-1/findings/find-1/decisions",
        method="POST",
        json={
            "id": "d3",
            "job_id": "job-1",
            "finding_id": "find-1",
            "decision_type": "waive",
            "decided_by_user_id": "u1",
            "source": "sdk",
            "is_active": True,
        },
        status_code=201,
    )
    decision = client.record_decision(
        "job-1", decision_type="waive", decided_by_user_id="u1", finding_id="find-1"
    )
    assert decision.finding_id == "find-1"


def test_revoke_decision(httpx_mock, client: LintPDF) -> None:
    httpx_mock.add_response(
        url="https://api.example.com/api/v1/jobs/job-1/decisions/d2/revoke",
        method="POST",
        json={
            "id": "d2",
            "job_id": "job-1",
            "decision_type": "waive",
            "decided_by_user_id": "u1",
            "source": "sdk",
            "is_active": False,
            "revoked_by_user_id": "u2",
            "revoked_reason": "wrong call",
            "revoked_at": "2026-04-27T12:00:00Z",
        },
    )
    decision = client.revoke_decision(
        "job-1", "d2", revoked_by_user_id="u2", revoked_reason="wrong call"
    )
    assert decision.is_active is False
    assert decision.revoked_reason == "wrong call"


# ---- workflows ---------------------------------------------------------


def test_list_workflows(httpx_mock, client: LintPDF) -> None:
    httpx_mock.add_response(
        url="https://api.example.com/api/v1/workflows",
        method="GET",
        json={
            "workflows": [
                {"id": "w1", "name": "Coated stock", "profile_id": "lintpdf-default"},
            ]
        },
    )
    wfs = client.list_workflows()
    assert len(wfs) == 1
    assert isinstance(wfs[0], Workflow)
    assert wfs[0].name == "Coated stock"


def test_create_workflow(httpx_mock, client: LintPDF) -> None:
    httpx_mock.add_response(
        url="https://api.example.com/api/v1/workflows",
        method="POST",
        json={"id": "w2", "name": "Uncoated stock", "profile_id": "lintpdf-default"},
        status_code=201,
    )
    wf = client.create_workflow(name="Uncoated stock", profile_id="lintpdf-default")
    assert wf.name == "Uncoated stock"


# ---- cost-cap ----------------------------------------------------------


def test_get_cost_cap(httpx_mock, client: LintPDF) -> None:
    httpx_mock.add_response(
        url="https://api.example.com/api/v1/ai/cost-cap",
        method="GET",
        json={
            "enabled": True,
            "monthly_cap_cents": 10000,
            "alert_threshold_pct": 80,
            "used_cents": 1500,
        },
    )
    cap = client.get_cost_cap()
    assert isinstance(cap, CostCap)
    assert cap.enabled is True
    assert cap.monthly_cap_cents == 10000
    assert cap.used_cents == 1500


def test_set_cost_cap(httpx_mock, client: LintPDF) -> None:
    httpx_mock.add_response(
        url="https://api.example.com/api/v1/ai/cost-cap",
        method="POST",
        json={
            "enabled": False,
            "monthly_cap_cents": 0,
            "alert_threshold_pct": 80,
        },
    )
    cap = client.set_cost_cap(enabled=False)
    assert cap.enabled is False
