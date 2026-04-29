"""Tests for the structural-only auditor short-circuit added when
the post-merge audit revealed 39.5% of findings sat in
``needs_context`` purely because vision can't verify what the engine
already read deterministically from the PDF object graph.
"""

from __future__ import annotations

from dataclasses import dataclass

from lintpdf.audit.internal import _is_operational_advisory, _is_structural_only


def test_pdfx_conformance_ids_are_structural() -> None:
    for cid in ("PDFX4-001", "PDFX4-005", "PDFX1A-016", "PDFA-014"):
        assert _is_structural_only(cid), cid


def test_accessibility_metadata_ids_are_structural() -> None:
    for cid in ("LPDF_ACCESS_001", "LPDF_ACCESS_004", "LPDF_META_001", "LPDF_DOC_003"):
        assert _is_structural_only(cid), cid


def test_font_inventory_ids_are_structural() -> None:
    for cid in ("LPDF_FONT_001", "LPDF_FONT_005", "LPDF_FONT_NONE_DECLARED"):
        assert _is_structural_only(cid), cid


def test_print_standard_ids_are_structural() -> None:
    for cid in ("LPDF_STD_001", "LPDF_STD_002", "LPDF_INK_003", "LPDF_LANG_001"):
        assert _is_structural_only(cid), cid


def test_explicit_color_metadata_ids_are_structural() -> None:
    """The exact-set entries — checks where the engine reads metadata
    Opus would otherwise mark needs_context."""
    for cid in (
        "LPDF_COLOR_006",
        "LPDF_COLOR_003",
        "LPDF_COLOR_014",
        "LPDF_SPOT_001",
        "LPDF_SPOT_006",
        "LPDF_SPOT_008",
        "LPDF_STROKE_003",
        "LPDF_IMG_018",
    ):
        assert _is_structural_only(cid), cid


def test_visual_ids_are_not_structural() -> None:
    """Checks that genuinely need pixel-level verification stay in
    the audit pipeline."""
    for cid in (
        "LPDF_BARCODE_NOMINAL_SIZE_LOW",
        "LPDF_BOX_BG_NO_BLEED",
        "LPDF_BOX_PRESS_MARKS_MISSING",
        "LPDF_DIE_PERF_INDICATOR_NO_STEP",
        "LPDF_TEXT_OUTLINED_SMALL",
        "LPDF_PLACEHOLDER_001",
        "LPDF_HAIRLINE_001",
    ):
        assert not _is_structural_only(cid), cid


def test_unknown_check_id_treated_as_visual() -> None:
    """When in doubt, audit it. New check IDs default to vision-
    verifiable so we don't silently mark them confirmed."""
    assert _is_structural_only("LPDF_NEW_CHECK_001") is False


# ── Operational-advisory filter ────────────────────────────────────


@dataclass
class _OpFakeFinding:
    inspection_id: str = "AI_SIM_001"
    severity: str = "advisory"
    message: str = ""
    details: dict | None = None


def test_gpu_unavailable_finding_is_operational() -> None:
    f = _OpFakeFinding(
        inspection_id="AI_SIM_001",
        message="GPU inference service unavailable for image similarity embedding.",
        details={"reason": "gpu_unavailable"},
    )
    assert _is_operational_advisory(f) is True


def test_circuit_breaker_message_is_operational() -> None:
    f = _OpFakeFinding(
        inspection_id="AI_PSTEP_001",
        message="GPU inference service circuit breaker is open. Service will be retried automatically.",
    )
    assert _is_operational_advisory(f) is True


def test_no_target_languages_is_operational() -> None:
    f = _OpFakeFinding(
        inspection_id="AI_LANG_001",
        message="No target languages configured.",
        details={"reason": "no_target_languages"},
    )
    assert _is_operational_advisory(f) is True


def test_real_finding_is_not_operational() -> None:
    f = _OpFakeFinding(
        inspection_id="LPDF_BARCODE_NOMINAL_SIZE_LOW",
        message="Barcode is below GS1 80% magnification minimum.",
        details={"long_axis_mm": 22.0},
    )
    assert _is_operational_advisory(f) is False
