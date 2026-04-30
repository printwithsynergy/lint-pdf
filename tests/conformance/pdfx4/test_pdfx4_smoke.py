"""Smoke test that runs the PDF/X-4 validator end-to-end on real PDF binaries.

Loads the generated fixtures under ``tests/fixtures/pdfx4/`` through the
real pikepdf adapter + SemanticModelBuilder + PdfX4Validator pipeline, then
asserts the expected findings are (or aren't) emitted.

Skipped when pikepdf isn't installed (the parser isn't available in
minimal CI environments).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from siftpdf.analyzers.finding import Finding, Severity
from siftpdf.conformance.pdfx4 import PdfX4Validator

pytest.importorskip("pikepdf")

from siftpdf.parser.pikepdf_adapter import PikePDFAdapter
from siftpdf.semantic.builder import SemanticModelBuilder

_FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "pdfx4"
_CONFORMING = _FIXTURES / "conforming"
_VIOLATING = _FIXTURES / "violating"


def _run(pdf_path: Path) -> list[Finding]:
    pdf_bytes = pdf_path.read_bytes()
    adapter = PikePDFAdapter()
    raw_doc = adapter.open(pdf_bytes)
    semantic_doc = SemanticModelBuilder(adapter).build(raw_doc)
    return PdfX4Validator().validate(semantic_doc, [])


def _ids(findings: list[Finding]) -> set[str]:
    return {f.inspection_id for f in findings}


def _errors(findings: list[Finding]) -> set[str]:
    return {f.inspection_id for f in findings if f.severity == Severity.ERROR}


class TestConformingFixtures:
    @staticmethod
    def test_minimal_no_errors() -> None:
        findings = _run(_CONFORMING / "minimal.pdf")
        # The minimal fixture is built to the smallest PDF/X-4 contract:
        # no ERROR-severity findings should be emitted.
        assert not _errors(findings), f"Conforming PDF emitted errors: {_errors(findings)}"


class TestViolatingFixtures:
    @staticmethod
    def test_no_output_intent_fires_016() -> None:
        assert "PDFX4-016" in _ids(_run(_VIOLATING / "no_output_intent.pdf"))

    @staticmethod
    def test_no_xmp_fires_005() -> None:
        assert "PDFX4-005" in _ids(_run(_VIOLATING / "no_xmp.pdf"))

    @staticmethod
    def test_pdf_1_4_fires_001() -> None:
        assert "PDFX4-001" in _ids(_run(_VIOLATING / "pdf_1_4.pdf"))

    @staticmethod
    @pytest.mark.xfail(
        reason=(
            "SemanticModelBuilder defaults missing TrimBox to CropBox per ISO "
            "32000-2 §14.11.2. PDFX4-050 (TrimBox/ArtBox required) therefore "
            "cannot fire on a parsed PDF — the builder hides the violation. "
            "Tracked as engine debt; unit test in test_pdfx4_validator.py "
            "covers the analyzer logic by setting trim_box/art_box to None "
            "directly on the SemanticPage."
        ),
        strict=True,
    )
    def test_no_trim_box_fires_050() -> None:
        assert "PDFX4-050" in _ids(_run(_VIOLATING / "no_trim_box.pdf"))
