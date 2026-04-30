"""AnalyzerContext + Capabilities unit tests."""

from __future__ import annotations

from typing import Any, ClassVar

from lintpdf.plugin import AnalyzerContext, Capabilities


class _FakeDoc:
    pages: ClassVar[list] = []


def test_context_minimal_construction():
    ctx = AnalyzerContext(document=_FakeDoc(), events=[])
    assert ctx.events == []
    assert ctx.pdf_bytes == b""
    assert ctx.config == {}
    assert ctx.tenant_id is None
    assert ctx.services is None
    assert ctx.capabilities.page_images is None
    assert ctx.capabilities.text_regions is None


def test_context_with_config_and_tenant():
    ctx = AnalyzerContext(
        document=_FakeDoc(),
        events=[],
        config={"ai_config": {"foo": 1}, "lintpdf.test": {"bar": 2}},
        tenant_id="t_abc",
    )
    assert ctx.config["ai_config"]["foo"] == 1
    assert ctx.config["lintpdf.test"]["bar"] == 2
    assert ctx.tenant_id == "t_abc"


def test_capabilities_default_all_none():
    caps = Capabilities()
    assert caps.page_images is None
    assert caps.text_regions is None
    assert caps.content_stream_events is None


def test_capabilities_partial_population():
    class _FakePageImages:
        def get_page_image(self, *, page_num: int, dpi: int) -> bytes:
            return b"png-bytes"

    caps = Capabilities(page_images=_FakePageImages())
    assert caps.page_images is not None
    assert caps.text_regions is None

    img: Any = caps.page_images.get_page_image(page_num=1, dpi=300)
    assert img == b"png-bytes"
