"""Unit tests for the CodexClient seam.

The HTTP-backed client is exercised end-to-end via a stub HttpClient
so we cover the wire-shape parsing logic without standing up a real
codex sidecar. The no-op stub's contract (is_enabled() == False,
last_stage_durations_ms() == {}) is locked here too — the orchestrator
relies on those defaults for the flag-off fallback.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from lintpdf.codex_client import (
    CodexUnavailableError,
    _CodexHttpClient,
    compute_pdf_hash,
    dispatch_text_region_pass,
    get_codex_client,
)
from lintpdf.plugin.services import (
    ClauseFailure,
    ConformanceVerdict,
    noop_codex_client,
)
from lintpdf.semantic.model import (
    DetectedTextRegion,
    PdfBox,
    PdfImage,
    SemanticDocument,
    SemanticPage,
)


class _StubResponse:
    """Tiny stand-in for an httpx-style response — covers .json()
    and .headers without pulling httpx into the test deps."""

    def __init__(self, payload: Any, headers: dict[str, str] | None = None) -> None:
        self._payload = payload
        self.headers = headers or {}

    def json(self) -> Any:
        return self._payload


class _StubHttpClient:
    """Captures the request the CodexClient makes and returns a canned
    response. Mirrors the ``.get_json`` / ``.post_json`` surface the
    real ``codex_pdf.client.HttpClient`` is expected to grow once
    codex publishes the unified-extraction endpoints.
    """

    def __init__(self, response: _StubResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, str, Any]] = []

    def get_json(self, path: str, params: Any = None) -> _StubResponse:
        self.calls.append(("GET", path, params))
        return self._response

    def post_json(self, path: str, json: Any = None) -> _StubResponse:
        self.calls.append(("POST", path, json))
        return self._response


def _patched_client(stub: _StubHttpClient) -> Any:
    """Patch the lazy HttpClient construction in _CodexHttpClient so the
    test never reaches ``codex_pdf.client``."""
    return patch.object(_CodexHttpClient, "_http_client", return_value=stub)


class TestNoOpCodexClient:
    """The no-op stub locks the flag-off default behaviour. Any change
    to these contracts breaks the parity gate."""

    def test_is_enabled_is_false(self) -> None:
        assert noop_codex_client().is_enabled() is False

    def test_last_stage_durations_is_empty(self) -> None:
        assert noop_codex_client().last_stage_durations_ms() == {}

    def test_get_text_regions_raises_without_guard(self) -> None:
        with pytest.raises(RuntimeError, match="is_enabled"):
            noop_codex_client().get_text_regions(pdf_hash="x", page_index=0, dpi=200)

    def test_get_conformance_raises_without_guard(self) -> None:
        with pytest.raises(RuntimeError, match="is_enabled"):
            noop_codex_client().get_conformance_verdict(document_id="x", profile="pdfx4")


class TestCodexHttpClientTextRegions:
    def test_decodes_text_regions_payload(self) -> None:
        stub = _StubHttpClient(
            _StubResponse(
                {
                    "regions": [
                        {
                            "bbox": {"x0": 10, "y0": 20, "x1": 100, "y1": 50},
                            "text": "Hello",
                            "confidence": 0.91,
                            "polygon": [[10, 20], [100, 20], [100, 50], [10, 50]],
                            "source": "codex.paddleocr",
                        }
                    ]
                }
            )
        )
        client = _CodexHttpClient()
        with _patched_client(stub):
            regions = client.get_text_regions(pdf_hash="abc123", page_index=2, dpi=200)

        assert len(regions) == 1
        region = regions[0]
        assert region.text == "Hello"
        assert region.confidence == pytest.approx(0.91)
        assert region.bbox.x0 == 10
        assert region.bbox.y1 == 50
        assert region.source == "codex.paddleocr"
        assert region.polygon is not None and len(region.polygon) == 4

        # Wire-shape correctness — codex contract uses GET on
        # /documents/{id}/text-regions with page_index + dpi query params.
        assert stub.calls == [
            ("GET", "/documents/abc123/text-regions", {"page_index": 2, "dpi": 200})
        ]

    def test_empty_payload_returns_empty_list(self) -> None:
        stub = _StubHttpClient(_StubResponse({"regions": []}))
        client = _CodexHttpClient()
        with _patched_client(stub):
            assert client.get_text_regions(pdf_hash="x", page_index=0, dpi=200) == []

    def test_unavailable_when_http_method_missing(self) -> None:
        class _BareClient:
            pass

        client = _CodexHttpClient()
        with (
            patch.object(_CodexHttpClient, "_http_client", return_value=_BareClient()),
            pytest.raises(CodexUnavailableError, match="GET"),
        ):
            client.get_text_regions(pdf_hash="x", page_index=0, dpi=200)


class TestCodexHttpClientConformance:
    def test_decodes_passed_verdict(self) -> None:
        stub = _StubHttpClient(_StubResponse({"passed": True, "clauses": []}))
        client = _CodexHttpClient()
        with _patched_client(stub):
            verdict = client.get_conformance_verdict(document_id="doc-1", profile="pdfx4")
        assert verdict == ConformanceVerdict(passed=True, clauses=[])
        assert stub.calls == [("POST", "/documents/doc-1/conformance/pdfx4", {})]

    def test_decodes_failed_clauses(self) -> None:
        stub = _StubHttpClient(
            _StubResponse(
                {
                    "passed": False,
                    "clauses": [
                        {
                            "clause": "6.2.2.3",
                            "test_number": "1",
                            "description": "Missing OutputIntent",
                            "failed_check_count": 1,
                        }
                    ],
                }
            )
        )
        client = _CodexHttpClient()
        with _patched_client(stub):
            verdict = client.get_conformance_verdict(document_id="doc-2", profile="pdfx4")

        assert verdict.passed is False
        assert verdict.clauses == [
            ClauseFailure(
                clause="6.2.2.3",
                test_number="1",
                description="Missing OutputIntent",
                failed_check_count=1,
            )
        ]


class TestStageDurationCapture:
    def test_reads_header(self) -> None:
        stub = _StubHttpClient(
            _StubResponse(
                {"regions": []},
                headers={
                    "X-Codex-Stage-Durations-Ms": json.dumps({"extract": 100, "text_regions": 200})
                },
            )
        )
        client = _CodexHttpClient()
        with _patched_client(stub):
            client.get_text_regions(pdf_hash="x", page_index=0, dpi=200)

        assert client.last_stage_durations_ms() == {
            "extract": 100,
            "text_regions": 200,
        }

    def test_falls_back_to_envelope_when_header_absent(self) -> None:
        stub = _StubHttpClient(
            _StubResponse(
                {
                    "regions": [],
                    "stage_durations_ms": {"extract": 12, "render": 34},
                }
            )
        )
        client = _CodexHttpClient()
        with _patched_client(stub):
            client.get_text_regions(pdf_hash="x", page_index=0, dpi=200)

        assert client.last_stage_durations_ms() == {"extract": 12, "render": 34}

    def test_clears_between_calls(self) -> None:
        stub_with = _StubHttpClient(
            _StubResponse(
                {"regions": []},
                headers={"X-Codex-Stage-Durations-Ms": json.dumps({"extract": 5})},
            )
        )
        stub_without = _StubHttpClient(_StubResponse({"regions": []}))

        client = _CodexHttpClient()
        with _patched_client(stub_with):
            client.get_text_regions(pdf_hash="x", page_index=0, dpi=200)
        assert client.last_stage_durations_ms() == {"extract": 5}

        with _patched_client(stub_without):
            client.get_text_regions(pdf_hash="x", page_index=0, dpi=200)
        assert client.last_stage_durations_ms() == {}


def _trigger_qualifying_doc() -> SemanticDocument:
    """Build a SemanticDocument whose single page passes the
    image-heavy trigger heuristic in ``text_region_pass``. Required
    for the codex dispatch helper to ask the client for regions.
    """
    img = PdfImage(
        name="Im1",
        width=600,
        height=800,
        bits_per_component=8,
        color_space=None,
        filters=("DCTDecode",),
        page_num=1,
    )
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        images=[img],
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


class _FakeCodexClient:
    """Stub CodexClient that records the dispatch helper's calls."""

    def __init__(
        self,
        *,
        enabled: bool,
        regions: list[DetectedTextRegion] | None = None,
        raise_unavailable: bool = False,
    ) -> None:
        self._enabled = enabled
        self._regions = regions or []
        self._raise = raise_unavailable
        self.calls: list[tuple[str, int, int]] = []

    def is_enabled(self) -> bool:
        return self._enabled

    def get_text_regions(
        self,
        *,
        pdf_hash: str,
        page_index: int,
        dpi: int,
    ) -> list[DetectedTextRegion]:
        self.calls.append((pdf_hash, page_index, dpi))
        if self._raise:
            raise CodexUnavailableError("simulated outage")
        return list(self._regions)

    def get_conformance_verdict(self, **_: Any) -> ConformanceVerdict:
        raise NotImplementedError

    def last_stage_durations_ms(self) -> dict[str, int]:
        return {}


class TestDispatchTextRegionPass:
    """The orchestrator's text-region dispatch must pick codex when the
    flag is on AND the client is enabled, fall back to the local pass
    on any unavailability, and be a no-op when the flag is off (default).
    """

    def test_flag_off_runs_local_pass(self) -> None:
        document = _trigger_qualifying_doc()
        fake = _FakeCodexClient(enabled=True)  # is_enabled True but flag off
        with patch("lintpdf.ai.text_region_pass.run") as local:
            dispatch_text_region_pass(
                document,
                [],
                b"pdf",
                codex_client=fake,
                ai_config=None,
                use_codex=False,
            )
        local.assert_called_once()
        assert fake.calls == []

    def test_flag_on_but_client_disabled_runs_local_pass(self) -> None:
        document = _trigger_qualifying_doc()
        fake = _FakeCodexClient(enabled=False)
        with patch("lintpdf.ai.text_region_pass.run") as local:
            dispatch_text_region_pass(
                document,
                [],
                b"pdf",
                codex_client=fake,
                ai_config=None,
                use_codex=True,
            )
        local.assert_called_once()
        assert fake.calls == []

    def test_flag_on_and_client_enabled_routes_to_codex(self) -> None:
        document = _trigger_qualifying_doc()
        regions = [
            DetectedTextRegion(
                bbox=PdfBox(10, 20, 100, 50),
                text="Hello",
                confidence=0.9,
                polygon=None,
                source="codex",
            )
        ]
        fake = _FakeCodexClient(enabled=True, regions=regions)
        # Force the trigger heuristic open — the heuristic itself is
        # tested in text_region_pass tests; this test isolates the
        # dispatch path.
        with (
            patch("lintpdf.ai.text_region_pass.run") as local,
            patch("lintpdf.ai.text_region_pass.should_run_for_page", return_value=True),
        ):
            dispatch_text_region_pass(
                document,
                [],
                b"pdf-bytes",
                codex_client=fake,
                ai_config=None,
                use_codex=True,
            )
        local.assert_not_called()
        assert len(fake.calls) == 1
        pdf_hash, page_index, dpi = fake.calls[0]
        assert pdf_hash == compute_pdf_hash(b"pdf-bytes")
        assert page_index == 1
        assert dpi == 200
        # Mutated the page in place.
        assert document.pages[0].detected_text_regions == regions

    def test_codex_failure_falls_back_to_local_pass(self) -> None:
        document = _trigger_qualifying_doc()
        fake = _FakeCodexClient(enabled=True, raise_unavailable=True)
        with (
            patch("lintpdf.ai.text_region_pass.run") as local,
            patch("lintpdf.ai.text_region_pass.should_run_for_page", return_value=True),
        ):
            dispatch_text_region_pass(
                document,
                [],
                b"pdf",
                codex_client=fake,
                ai_config=None,
                use_codex=True,
            )
        local.assert_called_once()


class TestFactory:
    def test_returns_a_codex_client(self) -> None:
        """The factory always returns a CodexClient instance, regardless
        of whether codex's SDK is importable. Locks the public
        ``get_codex_client()`` shape; the SDK-availability branch is
        covered implicitly by the orchestrator's
        ``is_enabled()``-guarded dispatch."""
        client = get_codex_client()
        assert hasattr(client, "is_enabled")
        assert hasattr(client, "get_text_regions")
        assert hasattr(client, "get_conformance_verdict")
        assert hasattr(client, "last_stage_durations_ms")
