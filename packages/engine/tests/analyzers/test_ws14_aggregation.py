"""WS-14 — per-page aggregation for LPDF_TEXT_001, LPDF_TEXT_004, LPDF_OVER_007.

Verifies that on a 10-up repeat layout (or any vector-dense page with
many matching text events) these rules now fire **once per page**
with ``details.object_count`` tracking the underlying event count —
instead of one finding per event, which on the 2026-04-23 Test3
corpus fixture emitted 940 / 290 / 228 findings per page and made
the viewer's findings panel unusable.

The aggregation has to collapse same-page events without dropping
data; these tests keep that contract honest.
"""

from __future__ import annotations

from lintpdf.analyzers.finding import Severity
from lintpdf.analyzers.hairline import HairlineAnalyzer
from lintpdf.analyzers.overprint import OverprintAnalyzer
from lintpdf.semantic.events import (
    ColorChangedEvent,
    OverprintChangedEvent,
    TextRenderedEvent,
)
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document(pages: int = 1) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=pages,
        is_encrypted=False,
        pages=[
            SemanticPage(page_num=i + 1, media_box=PdfBox(0, 0, 612, 792)) for i in range(pages)
        ],
    )


def _text(
    *,
    font_size: float = 5.0,
    color_space: str = "DeviceGray",
    color_values: tuple[float, ...] = (0.0,),
    page_num: int = 1,
    bbox: tuple[float, float, float, float] | None = None,
) -> TextRenderedEvent:
    return TextRenderedEvent(
        operator="Tj",
        page_num=page_num,
        operator_index=0,
        font_name="F1",
        font_size=font_size,
        ctm=TransformationMatrix(),
        text_matrix=TransformationMatrix(),
        color_space=color_space,
        color_values=color_values,
        rendering_mode=0,
        bbox=bbox,
    )


class TestText001Aggregation:
    @staticmethod
    def test_many_small_text_events_collapse_to_one_finding_per_page() -> None:
        events = [_text(font_size=5.0, bbox=(i, 0, i + 10, 10)) for i in range(50)]
        findings = HairlineAnalyzer().analyze(_make_document(), events)
        rows = [f for f in findings if f.inspection_id == "LPDF_TEXT_001"]
        assert len(rows) == 1
        row = rows[0]
        assert row.page_num == 1
        assert row.severity == Severity.ADVISORY
        assert row.details["object_count"] == 50
        # Representative bboxes keep at most 5 samples — viewer
        # renders them as highlights without the panel blowing up.
        assert len(row.details["representative_bboxes"]) == 5

    @staticmethod
    def test_per_page_split() -> None:
        events = [_text(font_size=5.0, page_num=1) for _ in range(3)]
        events += [_text(font_size=5.0, page_num=2) for _ in range(4)]
        findings = HairlineAnalyzer().analyze(_make_document(pages=2), events)
        rows = sorted(
            (f for f in findings if f.inspection_id == "LPDF_TEXT_001"),
            key=lambda f: f.page_num,
        )
        assert [r.page_num for r in rows] == [1, 2]
        assert [r.details["object_count"] for r in rows] == [3, 4]


class TestText004Aggregation:
    @staticmethod
    def test_many_white_text_events_collapse() -> None:
        events = [_text(color_space="DeviceGray", color_values=(1.0,)) for _ in range(10)]
        findings = HairlineAnalyzer().analyze(_make_document(), events)
        rows = [f for f in findings if f.inspection_id == "LPDF_TEXT_004"]
        assert len(rows) == 1
        assert rows[0].details["object_count"] == 10

    @staticmethod
    def test_single_white_text_still_emits() -> None:
        # The pre-existing test_white_gray_text expects exactly 1
        # finding; aggregation must preserve that shape so downstream
        # consumers don't break on single-event pages.
        event = _text(color_space="DeviceGray", color_values=(1.0,))
        findings = HairlineAnalyzer().analyze(_make_document(), [event])
        rows = [f for f in findings if f.inspection_id == "LPDF_TEXT_004"]
        assert len(rows) == 1
        assert rows[0].details["object_count"] == 1


class TestOver007Aggregation:
    @staticmethod
    def test_many_knockout_black_events_collapse() -> None:
        events: list = [
            ColorChangedEvent(
                operator="K",
                page_num=1,
                operator_index=0,
                stroking=False,
                color_space="DeviceCMYK",
                color_values=(0.0, 0.0, 0.0, 1.0),
            )
        ]
        events += [
            _text(
                font_size=1.0,
                color_space="DeviceCMYK",
                color_values=(0.0, 0.0, 0.0, 1.0),
            )
            for _ in range(20)
        ]
        findings = OverprintAnalyzer().analyze(_make_document(), events)
        rows = [f for f in findings if f.inspection_id == "LPDF_OVER_007"]
        assert len(rows) == 1
        row = rows[0]
        assert row.page_num == 1
        assert row.severity == Severity.WARNING
        assert row.details["object_count"] == 20
        assert row.details["overprint_active"] is False

    @staticmethod
    def test_overprint_active_suppresses_aggregate() -> None:
        # When overprint IS active, no LPDF_OVER_007 finding should
        # fire — the aggregate machinery must respect the same
        # precondition as the old per-event emit.
        events: list = [
            OverprintChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=0,
                overprint_non_stroking=True,
            ),
            ColorChangedEvent(
                operator="K",
                page_num=1,
                operator_index=1,
                stroking=False,
                color_space="DeviceCMYK",
                color_values=(0.0, 0.0, 0.0, 1.0),
            ),
        ]
        events += [
            _text(
                font_size=1.0,
                color_space="DeviceCMYK",
                color_values=(0.0, 0.0, 0.0, 1.0),
            )
            for _ in range(20)
        ]
        findings = OverprintAnalyzer().analyze(_make_document(), events)
        rows = [f for f in findings if f.inspection_id == "LPDF_OVER_007"]
        assert rows == []
