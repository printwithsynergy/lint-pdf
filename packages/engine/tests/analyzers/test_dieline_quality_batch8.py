"""Tests for Batch 8 dieline-quality findings (T3-D06, T3-D07, T3-D14)."""

from __future__ import annotations

import io

import pikepdf

from lintpdf.analyzers.dieline_quality import check_dieline_quality
from lintpdf.analyzers.finding import Severity


def _make_sep_cs(spot_name: str, pdf: pikepdf.Pdf) -> pikepdf.Array:
    tint = pdf.make_indirect(
        pikepdf.Dictionary(
            FunctionType=2,
            Domain=pikepdf.Array([0, 1]),
            Range=pikepdf.Array([0, 1, 0, 1, 0, 1, 0, 1]),
            C0=pikepdf.Array([0, 0, 0, 0]),
            C1=pikepdf.Array([0, 0, 0, 1]),
            N=1,
        )
    )
    return pikepdf.Array(
        [
            pikepdf.Name("/Separation"),
            pikepdf.Name("/" + spot_name),
            pikepdf.Name("/DeviceCMYK"),
            tint,
        ]
    )


def _build_pdf(content: bytes, *, spots: dict[str, str] | None = None) -> bytes:
    pdf = pikepdf.new()
    resources = pikepdf.Dictionary()
    if spots:
        cs_dict = pikepdf.Dictionary()
        for res_name, spot in spots.items():
            cs_dict[pikepdf.Name("/" + res_name)] = _make_sep_cs(spot, pdf)
        resources["/ColorSpace"] = cs_dict
    page = pdf.add_blank_page(page_size=(612, 792))
    page.Resources = resources
    page.Contents = pdf.make_stream(content)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


# ────────────────────────────────────────────────────────────────────
# T3-D07 — text near fold
# ────────────────────────────────────────────────────────────────────


class TestTextNearFold:
    @staticmethod
    def test_text_near_fold_fires() -> None:
        """Crease line at y=300; text painted at y=295 (just 5pt = 1.7mm
        away — under the 3mm default threshold)."""
        content = (
            # Stroke crease line at y=300
            b"/CS_FOLD CS\n"
            b"1 SCN\n"
            b"100 300 m\n"
            b"500 300 l\n"
            b"S\n"
            # Place text at y=295
            b"BT\n"
            b"/F1 12 Tf\n"
            b"100 295 Td\n"
            b"(Hello World) Tj\n"
            b"ET\n"
        )
        pdf_bytes = _build_pdf(content, spots={"CS_FOLD": "FoldLine"})
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name=None,
            source="missing",
            text_to_fold_distance_mm=3.0,
        )
        text = [f for f in findings if f.inspection_id == "LPDF_TEXT_NEAR_FOLD"]
        assert len(text) == 1
        assert text[0].severity == Severity.WARNING
        assert text[0].details["text_count"] >= 1
        assert text[0].details["min_distance_mm"] < 3.0

    @staticmethod
    def test_text_far_from_fold_silent() -> None:
        """Text 100pt = 35mm away from fold — well past 3mm threshold."""
        content = (
            b"/CS_FOLD CS\n"
            b"1 SCN\n"
            b"100 300 m\n"
            b"500 300 l\n"
            b"S\n"
            b"BT\n"
            b"/F1 12 Tf\n"
            b"100 100 Td\n"
            b"(Far away) Tj\n"
            b"ET\n"
        )
        pdf_bytes = _build_pdf(content, spots={"CS_FOLD": "FoldLine"})
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name=None,
            source="missing",
        )
        text = [f for f in findings if f.inspection_id == "LPDF_TEXT_NEAR_FOLD"]
        assert text == []

    @staticmethod
    def test_no_fold_silent() -> None:
        """No fold/crease spot → silent regardless of text placement."""
        content = b"BT\n/F1 12 Tf\n100 100 Td\n(Some text) Tj\nET\n"
        pdf_bytes = _build_pdf(content)
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name=None,
            source="missing",
        )
        text = [f for f in findings if f.inspection_id == "LPDF_TEXT_NEAR_FOLD"]
        assert text == []

    @staticmethod
    def test_threshold_zero_disables() -> None:
        content = (
            b"/CS_FOLD CS\n1 SCN\n100 300 m\n500 300 l\nS\nBT\n/F1 12 Tf\n100 295 Td\n(Hi) Tj\nET\n"
        )
        pdf_bytes = _build_pdf(content, spots={"CS_FOLD": "FoldLine"})
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name=None,
            source="missing",
            text_to_fold_distance_mm=0.0,
        )
        text = [f for f in findings if f.inspection_id == "LPDF_TEXT_NEAR_FOLD"]
        assert text == []


# ────────────────────────────────────────────────────────────────────
# T3-D14 — Braille zone integrity
# ────────────────────────────────────────────────────────────────────


class TestBrailleIntegrity:
    @staticmethod
    def test_braille_only_advisory() -> None:
        """Braille fill with no other ink touching → advisory presence note."""
        content = b"/CS_BRAILLE cs\n1 scn\n100 100 50 50 re\nf\n"
        pdf_bytes = _build_pdf(content, spots={"CS_BRAILLE": "Braille"})
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name=None,
            source="missing",
        )
        bra = [f for f in findings if f.inspection_id == "LPDF_BRAILLE_INTEGRITY"]
        assert len(bra) == 1
        assert bra[0].severity == Severity.ADVISORY
        assert bra[0].details["has_clearance_violation"] is False
        assert bra[0].details["braille_spot"] == "Braille"

    @staticmethod
    def test_clearance_violation_warning() -> None:
        """Braille zone painted, then a non-Braille rectangle painted
        inside the Braille bbox → clearance violation."""
        content = (
            # Braille zone covers (100,100)-(200,200)
            b"/CS_BRAILLE cs\n"
            b"1 scn\n"
            b"100 100 100 100 re\n"
            b"f\n"
            # Black rectangle painted inside the zone
            b"/DeviceCMYK cs\n"
            b"0 0 0 1 scn\n"
            b"120 120 30 30 re\n"
            b"f\n"
        )
        pdf_bytes = _build_pdf(content, spots={"CS_BRAILLE": "Braille"})
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name=None,
            source="missing",
        )
        bra = [f for f in findings if f.inspection_id == "LPDF_BRAILLE_INTEGRITY"]
        assert len(bra) == 1
        assert bra[0].severity == Severity.WARNING
        assert bra[0].details["has_clearance_violation"] is True
        assert bra[0].details["violation_count"] >= 1

    @staticmethod
    def test_no_braille_silent() -> None:
        """Plain artwork without Braille → no LPDF_BRAILLE_INTEGRITY."""
        content = b"/DeviceCMYK cs\n0 0 0 1 scn\n100 100 50 50 re\nf\n"
        pdf_bytes = _build_pdf(content)
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name=None,
            source="missing",
        )
        bra = [f for f in findings if f.inspection_id == "LPDF_BRAILLE_INTEGRITY"]
        assert bra == []


# ────────────────────────────────────────────────────────────────────
# T3-D06 — barcode quiet zone vs dieline / fold
# ────────────────────────────────────────────────────────────────────


def _build_pdf_with_image_xobject(
    content: bytes,
    *,
    spots: dict[str, str] | None = None,
) -> bytes:
    """Build a PDF that includes a 1x1 grayscale Image XObject named
    /Im1 so a `Do /Im1` operation in the content stream resolves
    cleanly."""
    pdf = pikepdf.new()
    resources = pikepdf.Dictionary()
    if spots:
        cs_dict = pikepdf.Dictionary()
        for res_name, spot in spots.items():
            cs_dict[pikepdf.Name("/" + res_name)] = _make_sep_cs(spot, pdf)
        resources["/ColorSpace"] = cs_dict
    image_dict = pikepdf.Dictionary(
        Type=pikepdf.Name("/XObject"),
        Subtype=pikepdf.Name("/Image"),
        Width=1,
        Height=1,
        ColorSpace=pikepdf.Name("/DeviceGray"),
        BitsPerComponent=8,
    )
    image_stream = pdf.make_stream(b"\x00", image_dict)
    resources["/XObject"] = pikepdf.Dictionary(Im1=image_stream)
    page = pdf.add_blank_page(page_size=(612, 792))
    page.Resources = resources
    page.Contents = pdf.make_stream(content)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


class TestBarcodeQuietZone:
    @staticmethod
    def test_image_near_dieline_fires() -> None:
        """Image painted at (200,300) 100x100, dieline stroked at
        (200,250)-(400,250) — image edge at y=300, dieline at y=250
        → 50pt = ~17.6mm gap. Below 2.5mm? No. So tighten the test
        with a closer placement: image at y=252, dieline at y=250."""
        content = (
            # Stroke dieline at y=250
            b"/CS_DIE CS\n"
            b"1 SCN\n"
            b"200 250 m\n"
            b"400 250 l\n"
            b"S\n"
            # Place image at y=252 (2pt = 0.7mm above the dieline —
            # well within 2.5mm threshold).
            b"q\n"
            b"100 0 0 50 200 252 cm\n"
            b"/Im1 Do\n"
            b"Q\n"
        )
        pdf_bytes = _build_pdf_with_image_xobject(content, spots={"CS_DIE": "Dieline"})
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
            barcode_quiet_zone_mm=2.5,
        )
        bq = [f for f in findings if f.inspection_id == "LPDF_BARCODE_QUIET_ZONE"]
        assert len(bq) == 1
        assert bq[0].severity == Severity.ADVISORY
        assert bq[0].details["image_count"] >= 1
        assert bq[0].details["min_distance_mm"] < 2.5

    @staticmethod
    def test_image_far_from_dieline_silent() -> None:
        """Image well clear of any dieline → silent."""
        content = (
            b"/CS_DIE CS\n"
            b"1 SCN\n"
            b"200 250 m\n"
            b"400 250 l\n"
            b"S\n"
            # Image at y=500 — far above the dieline.
            b"q\n"
            b"100 0 0 50 200 500 cm\n"
            b"/Im1 Do\n"
            b"Q\n"
        )
        pdf_bytes = _build_pdf_with_image_xobject(content, spots={"CS_DIE": "Dieline"})
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name="Dieline",
            source="name",
        )
        bq = [f for f in findings if f.inspection_id == "LPDF_BARCODE_QUIET_ZONE"]
        assert bq == []

    @staticmethod
    def test_no_dieline_silent() -> None:
        """Image but no dieline / crease line → silent."""
        content = b"q\n100 0 0 50 200 252 cm\n/Im1 Do\nQ\n"
        pdf_bytes = _build_pdf_with_image_xobject(content)
        findings = check_dieline_quality(
            pdf_bytes,
            spot_name=None,
            source="missing",
        )
        bq = [f for f in findings if f.inspection_id == "LPDF_BARCODE_QUIET_ZONE"]
        assert bq == []
