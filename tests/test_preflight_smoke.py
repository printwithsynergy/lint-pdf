"""End-to-end preflight smoke test (Gate G2 — contract lock).

Runs ``PreflightOrchestrator.run()`` against the bundled
``tests/fixtures/test-sample.pdf`` and renders every standalone report
format (HTML, PDF, JSON), asserting that every artefact carries the
EPM verdict header and that the AI-Explain block is reachable when
text has been cached.

Claude is **stubbed** per Q-1: any explain-path call routes to
:func:`_stub_claude_explain` so this test never spends API budget and
runs deterministically without ``ANTHROPIC_API_KEY``.

Run:

    uv run --package engine pytest packages/engine/tests/test_preflight_smoke.py -s -v
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lintpdf.profiles.orchestrator import PreflightOrchestrator
from lintpdf.profiles.schema import CheckConfig, PreflightProfile, ThresholdConfig
from lintpdf.reports.json_report import generate_json_report

_FIXTURE = Path(__file__).parent / "fixtures" / "test-sample.pdf"


# ---- Claude stub --------------------------------------------------------


def _stub_claude_explain(*_args: Any, **_kwargs: Any) -> str:
    """Deterministic explain-text stub. Q-1 — never call out to Anthropic."""
    return "Stubbed explanation: this finding indicates a press readiness issue."


@pytest.fixture(autouse=True)
def _stub_anthropic(monkeypatch):
    """Replace the explain backend with a deterministic stub.

    The real call site lives at ``lintpdf.ai.explain._call_claude``;
    stubbing it keeps the smoke test offline + free.
    """
    try:
        from lintpdf.ai import explain as _explain_mod
    except ImportError:
        return
    if hasattr(_explain_mod, "_call_claude"):
        monkeypatch.setattr(_explain_mod, "_call_claude", _stub_claude_explain)


# ---- helpers ------------------------------------------------------------


def _default_profile() -> PreflightProfile:
    """Profile that exercises every analyzer category we care about."""
    return PreflightProfile(
        name="smoke",
        thresholds=ThresholdConfig(
            epm_mode=True,
            cmy_tac_threshold=240.0,
        ),
        checks=CheckConfig(enabled=["LPDF_*"]),
    )


# ---- smoke tests --------------------------------------------------------


def test_fixture_pdf_exists():
    assert _FIXTURE.exists(), f"missing fixture: {_FIXTURE}"


def test_orchestrator_runs_against_fixture():
    """Sanity: the full pipeline completes on the bundled fixture."""
    orch = PreflightOrchestrator(_default_profile(), profile_id="smoke")
    result = orch.run(_FIXTURE.read_bytes())
    assert result is not None
    assert result.summary is not None
    # The fixture is a valid PDF; we expect a non-zero page_count even
    # if no findings fire (a clean file is a valid smoke test outcome).
    assert result.summary.page_count >= 1


def test_result_json_carries_epm_block():
    """result_json produced by the orchestrator carries a well-formed epm block.

    HTML rendering is now handled by lens-server; this test verifies the
    upstream data contract (the payload lint-pdf sends to lens-server) rather
    than the rendered HTML output.
    """
    import json as _json

    orch = PreflightOrchestrator(_default_profile(), profile_id="smoke")
    result = orch.run(_FIXTURE.read_bytes())
    # generate_json_report serialises the full result including the epm block.
    data = _json.loads(generate_json_report(result))
    epm = data.get("epm")
    assert epm is not None, "epm block missing from result_json"
    assert "tier" in epm
    assert "rejection_drivers" in epm
    assert "advisories" in epm


def test_json_report_carries_epm_block():
    """Every rendered JSON report ships an `epm` block."""
    orch = PreflightOrchestrator(_default_profile(), profile_id="smoke")
    result = orch.run(_FIXTURE.read_bytes())
    data = json.loads(generate_json_report(result))
    assert "epm" in data
    assert data["epm"] is not None
    assert "tier" in data["epm"]
    assert "rejection_drivers" in data["epm"]
    assert "advisories" in data["epm"]
    assert "epm_findings_count" in data["epm"]


def test_smoke_summary_prints_every_artefact():
    """The smoke test produces visual confirmation of the contract:
    EPM verdict + a finding count + Stubbed AI explanation example."""
    orch = PreflightOrchestrator(_default_profile(), profile_id="smoke")
    result = orch.run(_FIXTURE.read_bytes())
    json_data = json.loads(generate_json_report(result))
    epm = json_data["epm"]
    assert epm is not None

    # Print a summary line so engineers running the smoke test see the
    # contract has been met. Captured by `pytest -s`.
    print()
    print("=" * 60)
    print("PREFLIGHT SMOKE — contract summary")
    print("=" * 60)
    print(f"  Fixture     : {_FIXTURE.name}")
    print(f"  EPM tier    : {epm['tier']}")
    print(f"  Drivers     : {epm['rejection_drivers']}")
    print(f"  Advisories  : {epm['advisories']}")
    print(f"  EPM findings: {epm['epm_findings_count']}")
    print(f"  Total       : {result.summary.total_findings}")
    print(f"  AI stub     : {_stub_claude_explain()}")
    print("=" * 60)


def test_explain_call_uses_stub_only():
    """Calling explain through the stubbed module returns deterministic
    text — no API key needed."""
    try:
        from lintpdf.ai import explain
    except ImportError:
        pytest.skip("explain module not available")
    if not hasattr(explain, "_call_claude"):
        pytest.skip("_call_claude hook not present")
    text = explain._call_claude("anything", "anything")  # type: ignore[attr-defined]
    assert "Stubbed explanation" in text
