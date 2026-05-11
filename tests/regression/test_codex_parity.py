"""Behavior-locking parity snapshots for the codex unified-extraction seam.

These tests run the full ``PreflightOrchestrator`` on deterministic
synthetic documents with external services patched to no-ops, then
snapshot a stable summary of the result (sorted finding tuples +
selected metadata keys). The snapshots are checked into the repo at
``tests/regression/snapshots/codex_parity/``.

The seam this gates: subsequent commits introduce a ``CodexClient``
abstraction and feature-flag a new dispatch path through it for
text-region detection and veraPDF conformance. With all
``LINTPDF_CODEX_*`` flags off (the default), the orchestrator's
customer-facing output MUST remain bit-for-bit identical to today's
behaviour. These snapshots are the gate that proves it.

Use ``pytest --update-snapshots`` to regenerate after intentional
output changes; the harness is committed first so any future drift
shows up as a diff in CI.

Why synthetic docs instead of fixture PDFs? Production-fidelity
fixtures (``tests/fixtures/accuracy/*.pdf``) require a working codex
extraction subprocess, a GPU sidecar, and a veraPDF endpoint — none
of which are available in unit-test CI. The same dispatch path
runs in both cases, so locking it on synthetic docs gives a fast,
hermetic gate that catches the regressions this seam could
introduce (dropped findings, severity drift, metadata shape
changes). The handoff plan calls for production-fixture parity in
staging-side smoke after the consumer cutover; that lives outside
the pytest sandbox.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from lintpdf.profiles.orchestrator import PreflightOrchestrator
from lintpdf.profiles.schema import (
    AIFeatureConfig,
    CheckConfig,
    PreflightProfile,
    ThresholdConfig,
)
from lintpdf.semantic.model import (
    PdfBox,
    PdfFont,
    PdfImage,
    SemanticDocument,
    SemanticPage,
)

SNAPSHOT_DIR = Path(__file__).parent / "snapshots" / "codex_parity"


def _empty_doc() -> SemanticDocument:
    """Single blank page, no content. Exercises the empty-path branch
    through every analyzer."""
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


def _doc_with_unembedded_font() -> SemanticDocument:
    """Doc with an unembedded font — triggers ``LPDF_FONT_*`` findings via
    ``FontAnalyzer``. Locks the font-analyzer dispatch path."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        fonts={
            "F1": PdfFont(
                name="F1",
                base_font="Helvetica",
                font_type="Type1",
                embedded=False,
                subset=False,
            ),
        },
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


def _doc_with_low_dpi_image() -> SemanticDocument:
    """Doc with a sub-150 DPI image — triggers ``LPDF_IMG_*`` findings via
    ``ImageAnalyzer``. Locks the image-analyzer dispatch path."""
    img = PdfImage(
        name="Im1",
        width=72,  # at full page width that's 1 ppi
        height=72,
        bits_per_component=8,
        color_space=None,
        filters=("DCTDecode",),
        page_num=1,
    )
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        images=[img],
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


def _capture_finding_tuples(result: Any) -> list[dict[str, Any]]:
    """Reduce the orchestrator output to a deterministic, bytes-stable
    snapshot shape.

    Excludes volatile fields (job_id, duration_ms, bbox coordinates
    derived from CTM, full message text) so the snapshot tracks
    *structural* parity — the same set of findings firing with the
    same severities and ISO clauses — rather than getting tripped
    by cosmetic message tweaks. Future commits that intentionally
    rephrase a finding's message can leave this snapshot untouched.
    """
    tuples = sorted(
        [
            {
                "inspection_id": f.inspection_id,
                "severity": f.severity.value,
                "page_num": f.page_num,
                "source": f.source,
                "category": f.category,
                "iso_clause": f.iso_clause,
            }
            for f in result.findings
        ],
        key=lambda d: (d["inspection_id"], d["page_num"]),
    )
    return tuples


def _capture_metadata_shape(result: Any) -> dict[str, Any]:
    """Lock the metadata envelope shape (keys + JSON-able types).

    Volatile values are normalised. The point is to detect a
    structural drift (a key disappearing, a type flipping
    list↔dict) — not to assert a specific value.
    """
    metadata = result.metadata
    return {
        "pdf_version": metadata.get("pdf_version"),
        "page_count": metadata.get("page_count"),
        "is_encrypted": metadata.get("is_encrypted"),
        "conformance": metadata.get("conformance"),
        "workflow": metadata.get("workflow"),
        "ai_enabled": metadata.get("ai_enabled"),
        "ai_findings_count_type": type(metadata.get("ai_findings_count")).__name__,
        "verapdf_keys": sorted((metadata.get("verapdf") or {}).keys()),
        "has_structural_evidence": "structural_evidence" in metadata,
    }


def _run_orchestrator(
    document: SemanticDocument,
    *,
    profile: PreflightProfile,
) -> Any:
    """Run the orchestrator with all external services patched to no-ops
    so the test is hermetic and deterministic.

    Patched seams:
      - ``_parse_and_interpret``: skip the codex extraction subprocess
        and inject the synthetic SemanticDocument directly.
      - ``text_region_pass.run``: skip the GPU OCR call.
      - ``run_verapdf_checks``: skip the veraPDF REST round-trip.

    The flag-off CodexClient (added in a later commit) will route the
    same way; the snapshot must remain identical.
    """
    orch = PreflightOrchestrator(profile, profile_id="parity", pdf_bytes=b"x")

    with (
        patch.object(orch, "_parse_and_interpret", return_value=(document, [])),
        patch("lintpdf.ai.text_region_pass.run", return_value=None),
        patch(
            "lintpdf.conformance.verapdf_runner.run_verapdf_checks",
            return_value=[],
        ),
    ):
        return orch.run(b"x")


def _default_profile() -> PreflightProfile:
    return PreflightProfile(
        name="codex-parity",
        thresholds=ThresholdConfig(),
        ai=AIFeatureConfig(enabled=False),
        checks=CheckConfig(enabled=["LPDF_*"]),
    )


def _load_snapshot(name: str) -> dict[str, Any] | None:
    path = SNAPSHOT_DIR / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _write_snapshot(name: str, payload: dict[str, Any]) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _assert_or_update(request: pytest.FixtureRequest, name: str, payload: dict[str, Any]) -> None:
    if request.config.getoption("--update-snapshots"):
        _write_snapshot(name, payload)
        return
    expected = _load_snapshot(name)
    if expected is None:
        _write_snapshot(name, payload)
        pytest.skip(f"created initial snapshot {name}; re-run to assert")
    assert payload == expected, (
        f"Codex parity snapshot {name} drifted. If intentional, re-run with "
        "--update-snapshots; otherwise investigate the orchestrator dispatch "
        "path (CodexClient seam introduced regression?)."
    )


@pytest.fixture()
def parity_profile() -> PreflightProfile:
    return _default_profile()


class TestCodexParitySnapshots:
    """The orchestrator's customer-facing output on a fixed input must
    not drift when the CodexClient seam lands with all feature flags
    off. Each test snapshots a (findings, metadata) reduction and
    fails on diff."""

    @staticmethod
    def test_empty_doc_parity(
        parity_profile: PreflightProfile,
        request: pytest.FixtureRequest,
    ) -> None:
        result = _run_orchestrator(_empty_doc(), profile=parity_profile)
        payload = {
            "findings": _capture_finding_tuples(result),
            "metadata": _capture_metadata_shape(result),
            "summary": {
                "total_findings": result.summary.total_findings,
                "error_count": result.summary.error_count,
                "warning_count": result.summary.warning_count,
                "advisory_count": result.summary.advisory_count,
                "passed": result.summary.passed,
                "page_count": result.summary.page_count,
            },
        }
        _assert_or_update(request, "empty_doc", payload)

    @staticmethod
    def test_unembedded_font_parity(
        parity_profile: PreflightProfile,
        request: pytest.FixtureRequest,
    ) -> None:
        result = _run_orchestrator(_doc_with_unembedded_font(), profile=parity_profile)
        payload = {
            "findings": _capture_finding_tuples(result),
            "metadata": _capture_metadata_shape(result),
            "summary": {
                "total_findings": result.summary.total_findings,
                "error_count": result.summary.error_count,
                "warning_count": result.summary.warning_count,
                "advisory_count": result.summary.advisory_count,
                "passed": result.summary.passed,
                "page_count": result.summary.page_count,
            },
        }
        _assert_or_update(request, "unembedded_font", payload)

    @staticmethod
    def test_low_dpi_image_parity(
        parity_profile: PreflightProfile,
        request: pytest.FixtureRequest,
    ) -> None:
        result = _run_orchestrator(_doc_with_low_dpi_image(), profile=parity_profile)
        payload = {
            "findings": _capture_finding_tuples(result),
            "metadata": _capture_metadata_shape(result),
            "summary": {
                "total_findings": result.summary.total_findings,
                "error_count": result.summary.error_count,
                "warning_count": result.summary.warning_count,
                "advisory_count": result.summary.advisory_count,
                "passed": result.summary.passed,
                "page_count": result.summary.page_count,
            },
        }
        _assert_or_update(request, "low_dpi_image", payload)

    @staticmethod
    def test_stage_durations_populated(
        parity_profile: PreflightProfile,
    ) -> None:
        """Each canonical orchestrator stage records a non-negative
        duration. Locks the shape — drift here would mean a stage
        timing was dropped during refactor.
        """
        result = _run_orchestrator(_empty_doc(), profile=parity_profile)
        assert result.stage_durations_ms is not None
        expected_stages = {
            "extract",
            "analyzers",
            "conformance",
            "text_regions",
            "ai_analyzers",
            "filter",
            "color_score",
            "bbox_enrich",
        }
        assert expected_stages.issubset(result.stage_durations_ms.keys())
        for stage in expected_stages:
            value = result.stage_durations_ms[stage]
            assert isinstance(value, int)
            assert value >= 0

    @staticmethod
    def test_pdfx4_conformance_dispatch_parity(
        request: pytest.FixtureRequest,
    ) -> None:
        """Conformance pipeline dispatch parity — even when veraPDF
        returns no findings (patched), the orchestrator must run
        through the PDF/X-4 validator path without drift. Locks the
        ``conformance == 'pdfx4'`` dispatch that commit 6 swaps to
        codex."""
        profile = PreflightProfile(
            name="codex-parity-pdfx4",
            thresholds=ThresholdConfig(),
            ai=AIFeatureConfig(enabled=False),
            checks=CheckConfig(enabled=["LPDF_*"]),
            conformance="pdfx4",
        )
        result = _run_orchestrator(_empty_doc(), profile=profile)
        payload = {
            "findings": _capture_finding_tuples(result),
            "metadata": _capture_metadata_shape(result),
        }
        _assert_or_update(request, "pdfx4_dispatch", payload)


# Suppress unused-import lint on ``asdict`` — kept for forward
# compatibility when snapshots need richer Finding shapes.
_ = asdict
