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
    get_codex_client,
)
from lintpdf.plugin.services import (
    ClauseFailure,
    ConformanceVerdict,
    noop_codex_client,
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
