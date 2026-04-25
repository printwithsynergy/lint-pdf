"""Tests for Batch 10a — Tier-2 deferred + T4-A10.

Covers:
  - LPDF_PSTEP_POSITIONS (T2-ISO02)
  - LPDF_PSTEP_WHITE_SUBTYPE (T2-ISO03)
  - LPDF_SPOT_DEPRECATED_PANTONE (T2-SPT03)
  - LPDF_TRANS_BLEND_CS_MISMATCH (T2-TRN04)
  - LPDF_TRANS_ON_SPOT (T2-TRN05)
  - LPDF_TEXT_REVERSE_THIN (T2-RB02)
  - LPDF_XMP_GWG_TRAIL (T2-XMP01)
  - LPDF_VIEWER_DISPLAY_TITLE (T4-A10)
"""

from __future__ import annotations

import io

import pikepdf

from lintpdf.analyzers.metadata import MetadataAnalyzer
from lintpdf.analyzers.spot_name_normaliser import (
    check_deprecated_pantone_names,
    check_white_subtype_specificity,
    suggest_position_tagging,
)
from lintpdf.analyzers.transparency import TransparencyAnalyzer
from lintpdf.semantic.events import OpacityChangedEvent
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import (
    PdfBox,
    SemanticDocument,
    SemanticPage,
)


def _pdf_with_separation_spots(spot_names: list[str]) -> bytes:
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    page = pdf.pages[0]
    cs_dict = pikepdf.Dictionary()
    for idx, name in enumerate(spot_names, start=1):
        cs_dict[f"/CS{idx}"] = pikepdf.Array(
            [
                pikepdf.Name("/Separation"),
                pikepdf.Name(f"/{name}"),
                pikepdf.Name("/DeviceCMYK"),
                pikepdf.Dictionary(
                    {
                        "/FunctionType": 2,
                        "/Domain": [0.0, 1.0],
                        "/Range": [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0],
                        "/N": 1,
                        "/C0": [0.0, 0.0, 0.0, 0.0],
                        "/C1": [0.0, 0.0, 0.0, 1.0],
                    }
                ),
            ]
        )
    page.obj["/Resources"] = pikepdf.Dictionary({"/ColorSpace": cs_dict})
    out = io.BytesIO()
    pdf.save(out)
    return out.getvalue()


def _doc(catalog: dict | None = None, **kwargs) -> SemanticDocument:
    return SemanticDocument(
        version=kwargs.get("version", "1.7"),
        page_count=1,
        is_encrypted=False,
        info_dict=kwargs.get("info_dict", {}),
        catalog=catalog or {},
        output_intents=kwargs.get("output_intents", []),
        metadata_stream=kwargs.get("metadata_stream"),
        trailer={},
        pages=kwargs.get(
            "pages",
            [SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        ),
    )


# ─────────────────────────────────────────────────────────────────────
# T2-ISO02 — Positions taxonomy
# ─────────────────────────────────────────────────────────────────────


class TestPositionsSuggestion:
    @staticmethod
    def test_registration_spot_fires() -> None:
        out = suggest_position_tagging(_pdf_with_separation_spots(["Registration"]))
        ids = [f.inspection_id for f in out]
        assert "LPDF_PSTEP_POSITIONS" in ids
        assert out[0].details["iso_group"] == "Positions"

    @staticmethod
    def test_trim_mark_spot_fires() -> None:
        out = suggest_position_tagging(_pdf_with_separation_spots(["TrimMark"]))
        assert any(f.inspection_id == "LPDF_PSTEP_POSITIONS" for f in out)

    @staticmethod
    def test_normal_spot_silent() -> None:
        assert suggest_position_tagging(_pdf_with_separation_spots(["PMS_185_C"])) == []


# ─────────────────────────────────────────────────────────────────────
# T2-ISO03 — White subtypes
# ─────────────────────────────────────────────────────────────────────


class TestWhiteSubtype:
    @staticmethod
    def test_white_underprint_suggests_underprint() -> None:
        out = check_white_subtype_specificity(_pdf_with_separation_spots(["WhiteUnderprint"]))
        assert any(f.inspection_id == "LPDF_PSTEP_WHITE_SUBTYPE" for f in out)
        f = next(f for f in out if f.inspection_id == "LPDF_PSTEP_WHITE_SUBTYPE")
        assert f.details["suggested_subtype"] == "WhiteUnderprint"

    @staticmethod
    def test_plain_white_silent() -> None:
        out = check_white_subtype_specificity(_pdf_with_separation_spots(["White"]))
        assert out == []

    @staticmethod
    def test_non_white_spot_silent() -> None:
        out = check_white_subtype_specificity(_pdf_with_separation_spots(["CutContour"]))
        assert out == []


# ─────────────────────────────────────────────────────────────────────
# T2-SPT03 — Deprecated Pantone names
# ─────────────────────────────────────────────────────────────────────


class TestDeprecatedPantone:
    @staticmethod
    def test_cvc_suffix_fires() -> None:
        out = check_deprecated_pantone_names(_pdf_with_separation_spots(["PANTONE 185 CVC"]))
        ids = [f.inspection_id for f in out]
        assert "LPDF_SPOT_DEPRECATED_PANTONE" in ids

    @staticmethod
    def test_modern_c_suffix_silent() -> None:
        out = check_deprecated_pantone_names(_pdf_with_separation_spots(["PANTONE 185 C"]))
        assert out == []


# ─────────────────────────────────────────────────────────────────────
# T2-TRN04 — Blending CS vs OutputIntent
# ─────────────────────────────────────────────────────────────────────


class TestTransBlendCSMismatch:
    @staticmethod
    def test_mismatch_fires() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            transparency_group={"/CS": "/DeviceRGB"},
        )
        doc = _doc(
            output_intents=[
                {"/S": "/GTS_PDFX", "/DestOutputProfile": {"/N": 4}},
            ],
            pages=[page],
        )
        out = TransparencyAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in out]
        assert "LPDF_TRANS_BLEND_CS_MISMATCH" in ids

    @staticmethod
    def test_no_output_intent_silent() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            transparency_group={"/CS": "/DeviceRGB"},
        )
        doc = _doc(pages=[page])
        out = TransparencyAnalyzer().analyze(doc, [])
        assert all(f.inspection_id != "LPDF_TRANS_BLEND_CS_MISMATCH" for f in out)


# ─────────────────────────────────────────────────────────────────────
# T2-TRN05 — Transparency on spot page
# ─────────────────────────────────────────────────────────────────────


class TestTransparencyOnSpot:
    @staticmethod
    def test_alpha_on_spot_page_fires() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={
                "/ColorSpace": {
                    "/CS1": ["/Separation", "/PMS185", "/DeviceCMYK", {}],
                }
            },
        )
        doc = _doc(pages=[page])
        events = [
            OpacityChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=0,
                stroking_alpha=None,
                non_stroking_alpha=0.6,
                blend_mode="Normal",
            )
        ]
        out = TransparencyAnalyzer().analyze(doc, events)
        assert any(f.inspection_id == "LPDF_TRANS_ON_SPOT" for f in out)

    @staticmethod
    def test_no_transparency_on_spot_page_silent() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={
                "/ColorSpace": {
                    "/CS1": ["/Separation", "/PMS185", "/DeviceCMYK", {}],
                }
            },
        )
        doc = _doc(pages=[page])
        out = TransparencyAnalyzer().analyze(doc, [])
        assert all(f.inspection_id != "LPDF_TRANS_ON_SPOT" for f in out)


# ─────────────────────────────────────────────────────────────────────
# T2-RB02 — Reverse text minimum stroke
# ─────────────────────────────────────────────────────────────────────


class TestReverseThinText:
    @staticmethod
    def test_white_small_fill_only_fires() -> None:
        from lintpdf.analyzers.hairline import HairlineAnalyzer
        from lintpdf.semantic.events import TextRenderedEvent

        events = [
            TextRenderedEvent(
                operator="Tj",
                page_num=1,
                operator_index=0,
                font_name="Helvetica",
                font_size=8.0,
                ctm=TransformationMatrix(1, 0, 0, 1, 0, 0),
                text_matrix=TransformationMatrix(1, 0, 0, 1, 0, 0),
                color_space="DeviceCMYK",
                color_values=(0.0, 0.0, 0.0, 0.0),
                rendering_mode=0,
            )
        ]
        doc = _doc()
        out = HairlineAnalyzer().analyze(doc, events)
        ids = [f.inspection_id for f in out]
        assert "LPDF_TEXT_REVERSE_THIN" in ids

    @staticmethod
    def test_white_large_text_silent() -> None:
        from lintpdf.analyzers.hairline import HairlineAnalyzer
        from lintpdf.semantic.events import TextRenderedEvent

        events = [
            TextRenderedEvent(
                operator="Tj",
                page_num=1,
                operator_index=0,
                font_name="Helvetica",
                font_size=18.0,
                ctm=TransformationMatrix(1, 0, 0, 1, 0, 0),
                text_matrix=TransformationMatrix(1, 0, 0, 1, 0, 0),
                color_space="DeviceCMYK",
                color_values=(0.0, 0.0, 0.0, 0.0),
                rendering_mode=0,
            )
        ]
        doc = _doc()
        out = HairlineAnalyzer().analyze(doc, events)
        assert all(f.inspection_id != "LPDF_TEXT_REVERSE_THIN" for f in out)


# ─────────────────────────────────────────────────────────────────────
# T2-XMP01 — GWG audit-trail namespace
# ─────────────────────────────────────────────────────────────────────


class TestGwgXmpTrail:
    @staticmethod
    def test_xmp_without_gwg_namespace_fires() -> None:
        xmp = (
            b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
            b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            b'<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/">'
            b"<dc:title>Test</dc:title></rdf:Description></rdf:RDF></x:xmpmeta>"
            b'<?xpacket end="r"?>'
        )
        doc = _doc(metadata_stream=xmp)
        out = MetadataAnalyzer().analyze(doc, [])
        assert any(f.inspection_id == "LPDF_XMP_GWG_TRAIL" for f in out)

    @staticmethod
    def test_xmp_with_gwg_namespace_silent() -> None:
        xmp = (
            b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
            b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            b'<rdf:Description xmlns:gwg="http://www.gwg.org/ns/2022/">'
            b"<gwg:auditTrail>preflight-pass</gwg:auditTrail>"
            b"</rdf:Description></rdf:RDF></x:xmpmeta>"
            b'<?xpacket end="r"?>'
        )
        doc = _doc(metadata_stream=xmp)
        out = MetadataAnalyzer().analyze(doc, [])
        assert all(f.inspection_id != "LPDF_XMP_GWG_TRAIL" for f in out)


# ─────────────────────────────────────────────────────────────────────
# T4-A10 — DisplayDocTitle
# ─────────────────────────────────────────────────────────────────────


class TestDisplayDocTitle:
    @staticmethod
    def test_missing_viewer_prefs_fires() -> None:
        doc = _doc(catalog={})
        out = MetadataAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in out]
        assert "LPDF_VIEWER_DISPLAY_TITLE" in ids

    @staticmethod
    def test_display_title_false_fires() -> None:
        doc = _doc(catalog={"/ViewerPreferences": {"/DisplayDocTitle": False}})
        out = MetadataAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in out]
        assert "LPDF_VIEWER_DISPLAY_TITLE" in ids

    @staticmethod
    def test_display_title_true_silent() -> None:
        doc = _doc(catalog={"/ViewerPreferences": {"/DisplayDocTitle": True}})
        out = MetadataAnalyzer().analyze(doc, [])
        assert all(f.inspection_id != "LPDF_VIEWER_DISPLAY_TITLE" for f in out)
