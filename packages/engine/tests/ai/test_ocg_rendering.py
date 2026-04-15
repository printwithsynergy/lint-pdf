"""Unit tests for OCG (Optional Content Group) override handling in
``render_page_to_image`` + the cache-key suffix helper in the viewer
route module.

These tests exercise the pure helpers only (``_apply_ocg_overrides``
and ``_ocg_cache_suffix``) — the full route-level tests live in
``tests/api/test_viewer_warming_and_annotations.py`` and would pull
in the whole FastAPI + DB stack. Keeping the OCG smoke tests pure
unit-level makes them fast and focussed.
"""

from __future__ import annotations

import io

import pikepdf
import pytest

from lintpdf.ai.rendering import OCGError, _apply_ocg_overrides
from lintpdf.api.routes.viewer import _ocg_cache_suffix


# ── Fixtures ─────────────────────────────────────────────────


def _make_layered_pdf(
    layer_names: list[str],
    off_indices: list[int] | None = None,
) -> bytes:
    """Build a minimal one-page PDF with ``layer_names`` OCGs. Layers
    whose indices are in ``off_indices`` go into ``/OCProperties/D/OFF``.

    The page itself has no content — we only need the structure, not
    pretty rasters. Every test in this module inspects bytes or
    errors, not image pixels.
    """
    off_indices = off_indices or []
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))

    ocg_refs = []
    for name in layer_names:
        ocg = pdf.make_indirect(
            pikepdf.Dictionary(
                {
                    "/Type": pikepdf.Name("/OCG"),
                    "/Name": pikepdf.String(name),
                }
            )
        )
        ocg_refs.append(ocg)

    off_refs = [ocg_refs[i] for i in off_indices]
    oc_props = pikepdf.Dictionary(
        {
            "/OCGs": pikepdf.Array(ocg_refs),
            "/D": pikepdf.Dictionary(
                {
                    "/Order": pikepdf.Array(ocg_refs),
                    "/OFF": pikepdf.Array(off_refs),
                }
            ),
        }
    )
    pdf.Root["/OCProperties"] = oc_props

    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


def _make_non_layered_pdf() -> bytes:
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


def _read_off_indices(pdf_bytes: bytes) -> list[int]:
    """Read the /OFF list back out of a rewritten PDF and return the
    sorted list of OCG indices (positions in /OCProperties/OCGs)."""
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        oc_props = pdf.Root["/OCProperties"]
        ocgs = oc_props["/OCGs"]
        d = oc_props.get("/D")
        if d is None:
            return []
        off = d.get("/OFF")
        if off is None:
            return []
        ocg_objs = [ocgs[i] for i in range(len(ocgs))]
        indices: list[int] = []
        for ref in off:
            for i, ocg in enumerate(ocg_objs):
                if ref.objgen == ocg.objgen:
                    indices.append(i)
                    break
        return sorted(indices)


# ── _apply_ocg_overrides ─────────────────────────────────────


def test_empty_overrides_returns_input_unchanged():
    pdf = _make_layered_pdf(["Dieline", "Artwork", "Spot"])
    assert _apply_ocg_overrides(pdf, None, None) is pdf
    assert _apply_ocg_overrides(pdf, [], []) is pdf


def test_ocg_off_adds_to_existing_off_list():
    # Start with layer 0 off by default. Force layer 2 off too.
    pdf = _make_layered_pdf(["A", "B", "C"], off_indices=[0])
    out = _apply_ocg_overrides(pdf, None, [2])
    assert _read_off_indices(out) == [0, 2]


def test_ocg_on_removes_from_default_off_list():
    # Layer 1 is off by default. ocg_on=[1] should re-show it.
    pdf = _make_layered_pdf(["A", "B", "C"], off_indices=[1])
    out = _apply_ocg_overrides(pdf, [1], None)
    assert _read_off_indices(out) == []


def test_ocg_on_and_off_together_merge_correctly():
    pdf = _make_layered_pdf(["A", "B", "C", "D"], off_indices=[0])
    # Re-show 0 (was off), hide 2 and 3.
    out = _apply_ocg_overrides(pdf, [0], [2, 3])
    assert _read_off_indices(out) == [2, 3]


def test_conflict_between_ocg_on_and_ocg_off_raises():
    pdf = _make_layered_pdf(["A", "B"])
    with pytest.raises(OCGError, match="conflict"):
        _apply_ocg_overrides(pdf, [1], [1])


def test_out_of_range_index_raises():
    pdf = _make_layered_pdf(["A", "B"])
    with pytest.raises(OCGError, match="out of range"):
        _apply_ocg_overrides(pdf, None, [5])
    with pytest.raises(OCGError, match="out of range"):
        _apply_ocg_overrides(pdf, [-1], None)


def test_non_layered_pdf_raises():
    pdf = _make_non_layered_pdf()
    with pytest.raises(OCGError, match="no /OCProperties"):
        _apply_ocg_overrides(pdf, [0], None)


# ── _ocg_cache_suffix ────────────────────────────────────────


def test_cache_suffix_empty_for_default_state():
    assert _ocg_cache_suffix(None, None) == ""
    assert _ocg_cache_suffix([], []) == ""
    assert _ocg_cache_suffix(None, []) == ""


def test_cache_suffix_non_empty_for_overrides():
    s = _ocg_cache_suffix([0, 3], [2])
    assert s.startswith("_ocg-")
    assert len(s) == len("_ocg-") + 12  # 12-hex prefix


def test_cache_suffix_is_order_independent():
    a = _ocg_cache_suffix([3, 1], [2])
    b = _ocg_cache_suffix([1, 3], [2])
    assert a == b


def test_cache_suffix_differs_when_masks_differ():
    a = _ocg_cache_suffix([0], [])
    b = _ocg_cache_suffix([], [0])
    assert a != b

    c = _ocg_cache_suffix([0, 1], [])
    d = _ocg_cache_suffix([0, 2], [])
    assert c != d
