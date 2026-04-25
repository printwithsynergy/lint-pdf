"""Tests for text primitives (Tier-0 Batch 07)."""

from __future__ import annotations

import math

from lintpdf.primitives import REGISTRY
from lintpdf.primitives import text as text_p


def test_registry_contains_fourteen_primitives():
    expected = {
        "font_name",
        "font_subtype",
        "font_is_embedded",
        "font_is_subset",
        "font_has_to_unicode",
        "font_to_unicode_complete",
        "font_widths_consistent",
        "glyph_uses_notdef",
        "is_artificial_bold",
        "is_artificial_italic",
        "is_artificial_outline",
        "rendering_mode",
        "size_pt",
        "effective_size_pt",
    }
    assert REGISTRY.get("text", {}).keys() == expected


# ---- font_name / subtype / embedded / subset --------------------------


def test_font_name_from_attribute():
    class Ev:
        font_name = "AAAAAA+Helvetica"

    assert text_p.font_name(Ev()) == "AAAAAA+Helvetica"


def test_font_name_from_mapping():
    assert text_p.font_name({"font_name": "Times-Roman"}) == "Times-Roman"


def test_font_name_basefont_alias():
    assert text_p.font_name({"BaseFont": "Helvetica"}) == "Helvetica"


def test_font_name_returns_none_when_absent():
    assert text_p.font_name({}) is None
    assert text_p.font_name(None) is None


def test_font_subtype():
    assert text_p.font_subtype({"font_subtype": "TrueType"}) == "TrueType"
    assert text_p.font_subtype({"Subtype": "Type1"}) == "Type1"
    assert text_p.font_subtype({}) is None


def test_font_is_embedded():
    assert text_p.font_is_embedded({"font_is_embedded": True}) is True
    assert text_p.font_is_embedded({"embedded": True}) is True
    assert text_p.font_is_embedded({}) is False


def test_font_is_subset_true_for_six_letter_prefix():
    assert text_p.font_is_subset({"font_name": "ABCDEF+Helvetica"}) is True
    assert text_p.font_is_subset({"font_name": "ZZZZZZ+Times"}) is True


def test_font_is_subset_false_for_lowercase_prefix():
    assert text_p.font_is_subset({"font_name": "abcdef+Helvetica"}) is False


def test_font_is_subset_false_for_short_prefix():
    assert text_p.font_is_subset({"font_name": "AAA+Helvetica"}) is False


def test_font_is_subset_false_when_no_plus():
    assert text_p.font_is_subset({"font_name": "Helvetica"}) is False


# ---- ToUnicode ---------------------------------------------------------


def test_font_has_to_unicode():
    assert text_p.font_has_to_unicode({"has_to_unicode": True}) is True
    assert text_p.font_has_to_unicode({"to_unicode": True}) is True
    assert text_p.font_has_to_unicode({}) is False


def test_font_to_unicode_complete():
    assert text_p.font_to_unicode_complete({"to_unicode_complete": True}) is True
    assert text_p.font_to_unicode_complete({}) is False


def test_font_widths_consistent_default_true():
    assert text_p.font_widths_consistent({}) is True


def test_font_widths_consistent_explicit_false():
    assert text_p.font_widths_consistent({"font_widths_consistent": False}) is False


def test_glyph_uses_notdef():
    assert text_p.glyph_uses_notdef({"glyph_uses_notdef": True}) is True
    assert text_p.glyph_uses_notdef({"uses_notdef": True}) is True
    assert text_p.glyph_uses_notdef({}) is False


# ---- artificial bold / italic / outline -------------------------------


def test_is_artificial_bold_true_when_tr2_and_stroke():
    assert text_p.is_artificial_bold({"rendering_mode": 2, "line_width": 0.3}) is True


def test_is_artificial_bold_false_when_tr0():
    assert text_p.is_artificial_bold({"rendering_mode": 0, "line_width": 0.3}) is False


def test_is_artificial_bold_false_when_no_stroke_width():
    assert text_p.is_artificial_bold({"rendering_mode": 2, "line_width": 0.0}) is False


def test_is_artificial_italic_true_when_text_matrix_has_shear():
    # Text matrix with c=0.3 (significant shear)
    assert (
        text_p.is_artificial_italic({"text_matrix": [1, 0, 0.3, 1, 0, 0]}) is True
    )


def test_is_artificial_italic_false_when_no_shear():
    assert text_p.is_artificial_italic({"text_matrix": [1, 0, 0, 1, 0, 0]}) is False


def test_is_artificial_italic_false_when_no_text_matrix():
    assert text_p.is_artificial_italic({}) is False


def test_is_artificial_outline_when_tr1():
    assert text_p.is_artificial_outline({"rendering_mode": 1}) is True
    assert text_p.is_artificial_outline({"rendering_mode": 0}) is False


# ---- rendering_mode ----------------------------------------------------


def test_rendering_mode_default_zero():
    assert text_p.rendering_mode({}) == 0


def test_rendering_mode_returns_int():
    for i in range(8):
        assert text_p.rendering_mode({"rendering_mode": i}) == i


def test_rendering_mode_via_tr_alias():
    assert text_p.rendering_mode({"Tr": 3}) == 3


# ---- size_pt + effective_size_pt --------------------------------------


def test_size_pt_from_font_size():
    assert text_p.size_pt({"font_size": 12.0}) == 12.0


def test_size_pt_default_zero():
    assert text_p.size_pt({}) == 0.0


def test_effective_size_pt_no_matrices():
    assert text_p.effective_size_pt({"font_size": 12.0}) == 12.0


def test_effective_size_pt_with_uniform_text_matrix_scale():
    """Text matrix at 2x = effective size doubles."""
    ev = {"font_size": 6.0, "text_matrix": [2, 0, 0, 2, 0, 0]}
    assert text_p.effective_size_pt(ev) == 12.0


def test_effective_size_pt_with_ctm_scale():
    """CTM at 0.5x halves rendered size."""
    ev = {"font_size": 12.0}
    ctm = (0.5, 0, 0, 0.5, 0, 0)
    assert text_p.effective_size_pt(ev, ctm) == 6.0


def test_effective_size_pt_combined_text_matrix_and_ctm():
    """Text matrix 2x and CTM 0.5x cancel out → unchanged."""
    ev = {"font_size": 10.0, "text_matrix": [2, 0, 0, 2, 0, 0]}
    ctm = (0.5, 0, 0, 0.5, 0, 0)
    assert text_p.effective_size_pt(ev, ctm) == 10.0


def test_effective_size_pt_zero_when_no_size():
    assert text_p.effective_size_pt({"font_size": 0.0}) == 0.0


def test_effective_size_pt_with_rotation():
    """Pure rotation preserves scale."""
    angle = math.radians(45)
    tm = [math.cos(angle), math.sin(angle), -math.sin(angle), math.cos(angle), 0, 0]
    assert text_p.effective_size_pt({"font_size": 10.0, "text_matrix": tm}) == 10.0
