"""Regression — separations scanner must recurse into nested Form XObjects.

Context: the 2026-04-22 Amalgam_Catalyst wine label declares nine
spot colors (`/All`, `/BUFF`, `/Dark Biege`, `/Faint Beige`,
`/Splatter`, `/Foil 425`, `/Cutting`, `/Lt Beige`, `/Med Beige`)
but the viewer's Separations Panel showed zero channels. Root
cause: ``_scan_page_colorspaces`` only looked one level deep
into Form XObjects, so spots declared inside nested Illustrator
Forms were invisible to ``list_separations``. The ``SpotColorAnalyzer``
path sees them because it runs off ``SemanticDocument`` which
walks the full page tree.

This file builds a synthetic PDF with the same nesting pattern
(page → Form A → Form B → Separation cs) and asserts the scanner
now surfaces the spot.
"""

from __future__ import annotations

import io

import pikepdf

from siftpdf.reports.separation_renderer import list_separations


def _make_nested_spot_pdf(spot_names: list[str]) -> bytes:
    """Build a minimal single-page PDF where a spot colorspace is
    only declared inside a doubly-nested Form XObject.

    Shape:
        page.Resources.XObject /FormA    → Form
        FormA.Resources.XObject /FormB   → Form
        FormB.Resources.ColorSpace       → { CSn: [/Separation /<name> /DeviceCMYK <tint>] }

    No content stream actually paints with the spot; we only care
    that the scanner walks the tree and finds the declaration.
    """
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    page = pdf.pages[0]

    # Build the innermost Form (Form B) whose Resources hold the
    # Separation colorspace declarations.
    inner_cs = pikepdf.Dictionary()
    for i, name in enumerate(spot_names):
        inner_cs[f"/CS{i}"] = pikepdf.Array(
            [
                pikepdf.Name("/Separation"),
                pikepdf.Name("/" + name),
                pikepdf.Name("/DeviceCMYK"),
                # Identity tint transform — good enough for the scanner.
                pikepdf.Dictionary(
                    {
                        "/FunctionType": 2,
                        "/Domain": pikepdf.Array([0, 1]),
                        "/C0": pikepdf.Array([0, 0, 0, 0]),
                        "/C1": pikepdf.Array([0, 0, 0, 1]),
                        "/N": 1,
                    }
                ),
            ]
        )

    form_b = pdf.make_stream(b"")
    form_b.Type = pikepdf.Name("/XObject")
    form_b.Subtype = pikepdf.Name("/Form")
    form_b.BBox = pikepdf.Array([0, 0, 100, 100])
    form_b.Resources = pikepdf.Dictionary({"/ColorSpace": inner_cs})

    # Form A wraps Form B.
    form_a = pdf.make_stream(b"")
    form_a.Type = pikepdf.Name("/XObject")
    form_a.Subtype = pikepdf.Name("/Form")
    form_a.BBox = pikepdf.Array([0, 0, 100, 100])
    form_a.Resources = pikepdf.Dictionary(
        {
            "/XObject": pikepdf.Dictionary({"/FormB": form_b}),
        }
    )

    page.Resources = pikepdf.Dictionary(
        {
            "/XObject": pikepdf.Dictionary({"/FormA": form_a}),
        }
    )

    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


class TestNestedFormSpotRecursion:
    """``list_separations`` must recurse through all nested Form XObjects."""

    @staticmethod
    def test_single_spot_in_double_nested_form() -> None:
        pdf_bytes = _make_nested_spot_pdf(["PANTONE_185"])
        channels = list_separations(pdf_bytes)
        names = [c["name"] for c in channels]
        assert "PANTONE_185" in names, (
            f"Spot hidden inside a nested Form XObject should surface. Got: {names}"
        )
        spot_rows = [c for c in channels if c["type"] == "spot"]
        assert len(spot_rows) == 1

    @staticmethod
    def test_multi_spot_packaging_artwork() -> None:
        """Mirror the Amalgam_Catalyst pattern: nine named spots."""
        spots = [
            "BUFF",
            "Dark_Biege",
            "Faint_Beige",
            "Splatter",
            "Foil_425",
            "Cutting",
            "Lt_Beige",
            "Med_Beige",
            "PANTONE_877_C",
        ]
        pdf_bytes = _make_nested_spot_pdf(spots)
        channels = list_separations(pdf_bytes)
        names = {c["name"] for c in channels if c["type"] == "spot"}
        missing = set(spots) - names
        assert not missing, f"Missing spots after recursive scan: {sorted(missing)}"

    @staticmethod
    def test_all_and_none_still_filtered() -> None:
        """``/All`` + ``/None`` are special PDF spot markers — keep
        filtering them even when they're nested. Packaging tooling
        emits ``/All`` to mean "apply every ink", which isn't a
        real ink channel the viewer can render, so it stays out of
        the inventory. This guard prevents a regression that would
        surface a phantom "All" channel next to the real spots.
        """
        pdf_bytes = _make_nested_spot_pdf(["All", "None", "PANTONE_877_C"])
        channels = list_separations(pdf_bytes)
        names = {c["name"] for c in channels}
        assert "PANTONE_877_C" in names
        assert "All" not in names
        assert "None" not in names

    @staticmethod
    def test_cyclic_form_reference_bounded() -> None:
        """A Form pointing back at itself must not loop forever."""
        pdf = pikepdf.Pdf.new()
        pdf.add_blank_page(page_size=(100, 100))
        page = pdf.pages[0]

        cs = pikepdf.Dictionary(
            {
                "/CS0": pikepdf.Array(
                    [
                        pikepdf.Name("/Separation"),
                        pikepdf.Name("/PANTONE_Reflex_Blue"),
                        pikepdf.Name("/DeviceCMYK"),
                        pikepdf.Dictionary(
                            {
                                "/FunctionType": 2,
                                "/Domain": pikepdf.Array([0, 1]),
                                "/C0": pikepdf.Array([0, 0, 0, 0]),
                                "/C1": pikepdf.Array([1, 0, 0, 0]),
                                "/N": 1,
                            }
                        ),
                    ]
                ),
            }
        )

        form = pdf.make_stream(b"")
        form.Type = pikepdf.Name("/XObject")
        form.Subtype = pikepdf.Name("/Form")
        form.BBox = pikepdf.Array([0, 0, 100, 100])
        form.Resources = pikepdf.Dictionary(
            {
                "/ColorSpace": cs,
                # Cyclic self-reference through the same XObject dict.
                "/XObject": pikepdf.Dictionary({"/Self": form}),
            }
        )
        page.Resources = pikepdf.Dictionary(
            {
                "/XObject": pikepdf.Dictionary({"/Root": form}),
            }
        )

        buf = io.BytesIO()
        pdf.save(buf)

        channels = list_separations(buf.getvalue())
        names = {c["name"] for c in channels}
        assert "PANTONE_Reflex_Blue" in names
