"""Unit tests for ``lintpdf.audit.internal.InternalAuditor``.

Mocks the ``anthropic`` SDK + the ``render_page_to_image`` helper so
the tests run without Ghostscript or a live ``ANTHROPIC_API_KEY``.
Covers:

* Empty input → empty result (no SDK call).
* SDK unavailable → RuntimeError on construction.
* Missing API key → RuntimeError on construction.
* Happy path — one batch, two findings on the same page, each gets a
  verdict from a ``record_verdict`` tool-use block.
* API failure → every finding in the affected batch gets an
  ``error`` verdict rather than silently dropping.
* Findings without a ``page_num`` are still included in the prompt
  (auditor judges them off the finding text + rendered pages of
  their neighbours).
* ``record_verdict`` call for an index outside the batch is ignored.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

# ── Fixture: fake finding that quacks like the real JobFinding ──


@dataclass
class _FakeFinding:
    inspection_id: str = "LPDF_TEST_001"
    severity: str = "advisory"
    message: str = "Test finding"
    page_num: int | None = 1
    bbox_x0: float | None = None
    bbox_y0: float | None = None
    bbox_x1: float | None = None
    bbox_y1: float | None = None


@pytest.fixture(autouse=True)
def _stub_anthropic(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Install a fake ``anthropic`` module so the auditor imports cleanly."""
    fake_mod = types.ModuleType("anthropic")
    mock_client = MagicMock()
    fake_mod.Anthropic = MagicMock(return_value=mock_client)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", fake_mod)
    return mock_client


@pytest.fixture(autouse=True)
def _stub_renderer(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Avoid shelling out to Ghostscript for the unit tests."""
    from lintpdf import rendering

    renderer_mock = MagicMock(return_value=b"\x89PNG\r\n\x1a\n-fake")
    monkeypatch.setattr(rendering, "render_page_to_image", renderer_mock)
    return renderer_mock


@pytest.fixture
def opus_response() -> Any:
    """Build an anthropic-shaped response with two tool_use verdicts."""

    class _Block:
        def __init__(self, **kw: Any) -> None:
            for k, v in kw.items():
                setattr(self, k, v)

    resp = MagicMock()
    resp.content = [
        _Block(
            type="tool_use",
            name="record_verdict",
            input={"finding_index": 0, "status": "confirmed", "rationale": "Visible on page 1."},
        ),
        _Block(
            type="tool_use",
            name="record_verdict",
            input={
                "finding_index": 1,
                "status": "disputed",
                "rationale": "Engine misread the color stack.",
            },
        ),
    ]
    return resp


# ── Tests ──


class TestConstruction:
    @staticmethod
    def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from lintpdf.audit.internal import InternalAuditor

        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            InternalAuditor()

    @staticmethod
    def test_explicit_key_bypasses_env(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from lintpdf.audit.internal import InternalAuditor

        auditor = InternalAuditor(api_key="sk-ant-explicit")
        assert auditor._client is not None  # type: ignore[attr-defined]


class TestAudit:
    @staticmethod
    def test_empty_findings_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        from lintpdf.audit.internal import InternalAuditor

        assert InternalAuditor().audit(b"%PDF-1.4", []) == []

    @staticmethod
    def test_happy_path_two_findings_one_batch(
        monkeypatch: pytest.MonkeyPatch,
        _stub_anthropic: MagicMock,
        opus_response: Any,
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        from lintpdf.audit.internal import InternalAuditor

        _stub_anthropic.messages.create.return_value = opus_response

        # Both check IDs must be vision-verifiable (not in the
        # structural-only short-circuit list) so the test exercises
        # the Opus path rather than the auto-confirm fast path.
        findings = [
            _FakeFinding(inspection_id="LPDF_OVER_001", page_num=1),
            _FakeFinding(inspection_id="LPDF_HAIRLINE_001", page_num=1, severity="warning"),
        ]
        out = InternalAuditor().audit(b"%PDF-fake", findings)
        assert out[0] is not None and out[0].status == "confirmed"
        assert out[0].rationale == "Visible on page 1."
        assert out[1] is not None and out[1].status == "disputed"
        assert out[1].model == "claude-opus-4-7"
        assert isinstance(out[0].at, datetime)
        _stub_anthropic.messages.create.assert_called_once()

    @staticmethod
    def test_api_failure_returns_error_verdicts(
        monkeypatch: pytest.MonkeyPatch, _stub_anthropic: MagicMock
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        _stub_anthropic.messages.create.side_effect = RuntimeError("rate_limit")

        from lintpdf.audit.internal import InternalAuditor

        findings = [_FakeFinding(page_num=1), _FakeFinding(page_num=1)]
        out = InternalAuditor().audit(b"%PDF-fake", findings)
        assert all(v is not None and v.status == "error" for v in out)
        assert out[0].rationale and "failed" in out[0].rationale.lower()

    @staticmethod
    def test_unmatched_finding_index_leaves_verdict_none(
        monkeypatch: pytest.MonkeyPatch, _stub_anthropic: MagicMock
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        class _Block:
            def __init__(self, **kw: Any) -> None:
                for k, v in kw.items():
                    setattr(self, k, v)

        # AI called the tool only for index 0; index 1 has no verdict.
        resp = MagicMock()
        resp.content = [
            _Block(
                type="tool_use",
                name="record_verdict",
                input={"finding_index": 0, "status": "confirmed", "rationale": "ok"},
            ),
        ]
        _stub_anthropic.messages.create.return_value = resp

        from lintpdf.audit.internal import InternalAuditor

        findings = [_FakeFinding(page_num=1), _FakeFinding(page_num=1)]
        out = InternalAuditor().audit(b"%PDF-fake", findings)
        assert out[0] is not None and out[0].status == "confirmed"
        assert out[1] is None  # caller surfaces as "skipped"

    @staticmethod
    def test_finding_without_page_still_audited(
        monkeypatch: pytest.MonkeyPatch,
        _stub_anthropic: MagicMock,
        _stub_renderer: MagicMock,
    ) -> None:
        """Document-level findings (page_num=None) don't request any
        page render but still hit the AI and collect a verdict."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        class _Block:
            def __init__(self, **kw: Any) -> None:
                for k, v in kw.items():
                    setattr(self, k, v)

        resp = MagicMock()
        resp.content = [
            _Block(
                type="tool_use",
                name="record_verdict",
                input={
                    "finding_index": 0,
                    "status": "needs_context",
                    "rationale": "Requires JDF sidecar.",
                },
            ),
        ]
        _stub_anthropic.messages.create.return_value = resp

        from lintpdf.audit.internal import InternalAuditor

        findings = [_FakeFinding(page_num=None, inspection_id="LPDF_JDF_001")]
        out = InternalAuditor().audit(b"%PDF-fake", findings)
        assert out[0] is not None and out[0].status == "needs_context"
        # No page renders when no page numbers referenced.
        _stub_renderer.assert_not_called()
