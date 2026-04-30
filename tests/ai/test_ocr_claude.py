"""Unit tests for Claude OCR result conversion (WS-C).

The wire-protocol of the Anthropic SDK + the actual vision pass
are exercised by the live smoke tests; these cover the
deterministic shape-conversion helpers.
"""

from __future__ import annotations

from lintpdf.ai.ocr_claude import ocr_result_to_json
from lintpdf.ai.ocr_types import OCRPage, OCRTextBlock


class TestOcrResultToJson:
    @staticmethod
    def test_empty_list_roundtrips() -> None:
        assert ocr_result_to_json([]) == []

    @staticmethod
    def test_single_page_single_block() -> None:
        out = ocr_result_to_json(
            [
                OCRPage(
                    page_num=1,
                    blocks=[
                        OCRTextBlock(
                            text="HELLO",
                            bbox=[10.0, 20.0, 50.0, 30.0],
                            confidence=0.95,
                        )
                    ],
                )
            ]
        )
        assert out == [
            {
                "page_num": 1,
                "blocks": [
                    {
                        "text": "HELLO",
                        "bbox": [10.0, 20.0, 50.0, 30.0],
                        "confidence": 0.95,
                    }
                ],
            }
        ]

    @staticmethod
    def test_multiple_pages_preserved_in_order() -> None:
        pages = [
            OCRPage(page_num=3, blocks=[]),
            OCRPage(
                page_num=1,
                blocks=[OCRTextBlock(text="A", bbox=[0, 0, 1, 1], confidence=0.5)],
            ),
        ]
        out = ocr_result_to_json(pages)
        # Caller ordering preserved — caller chose the traversal.
        assert [p["page_num"] for p in out] == [3, 1]
