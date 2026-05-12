"""Phase 3 codex_signals readers — unit tests against a synthetic codex
payload.

The readers don't talk to codex directly; they read from
``ctx.config["codex_payload"]``. These tests build a minimal codex-
shaped dict and assert each reader emits the expected findings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lintpdf.ai.analyzers.codex_signals.barcodes_reader import CodexBarcodesReader
from lintpdf.ai.analyzers.codex_signals.classification_reader import (
    CodexClassificationReader,
)
from lintpdf.ai.analyzers.codex_signals.language_reader import CodexLanguageReader
from lintpdf.ai.analyzers.codex_signals.logos_reader import CodexLogosReader
from lintpdf.ai.analyzers.codex_signals.spell_reader import CodexSpellReader
from lintpdf.ai.analyzers.codex_signals.symbols_reader import CodexSymbolsReader


@dataclass
class _FakeCtx:
    config: dict[str, Any] = field(default_factory=dict)
    document: Any = None
    events: list[Any] = field(default_factory=list)
    pdf_bytes: bytes = b""
    tenant_id: str | None = None
    services: Any = None
    capabilities: Any = None


_BBOX = {"x0": 10.0, "y0": 20.0, "x1": 60.0, "y1": 70.0}


def _payload_with_signals() -> dict[str, Any]:
    return {
        "schema_version": "1.3.0",
        "pages": [
            {
                "page_num": 1,
                "detected_language": {
                    "code": "en-US",
                    "confidence": 0.97,
                    "source": "codex-ai/claude-haiku-4-5",
                },
                "detected_logos": [
                    {
                        "bbox": _BBOX,
                        "identity": "FedEx",
                        "confidence": 0.92,
                        "source": "codex-ai/claude-sonnet-4-6",
                    }
                ],
                "detected_symbols": [
                    {
                        "bbox": _BBOX,
                        "kind": "ce_marking",
                        "confidence": 0.88,
                        "source": "codex-ai/claude-sonnet-4-6",
                    }
                ],
                "detected_barcodes": [
                    {
                        "bbox": _BBOX,
                        "format": "ean13",
                        "value": "5012345678900",
                        "confidence": 1.0,
                        "source": "codex-cpu/pyzbar",
                    }
                ],
                "spell_candidates": ["tyIenol", "asprin"],
            }
        ],
        "document_classification": {"label": 0.7, "folding_carton": 0.25},
        "extraction_warnings": [
            {"code": "ai_tier", "message": "cpu+claude", "scope": "signals.ai"}
        ],
    }


def test_language_reader_emits_one_finding_per_page() -> None:
    ctx = _FakeCtx(config={"codex_payload": _payload_with_signals()})
    findings = CodexLanguageReader().analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].inspection_id == "CODEX_LANGUAGE"
    assert findings[0].page_num == 1
    assert "en-US" in findings[0].message


def test_logos_reader_emits_one_finding_per_logo() -> None:
    ctx = _FakeCtx(config={"codex_payload": _payload_with_signals()})
    findings = CodexLogosReader().analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].inspection_id == "CODEX_LOGO"
    assert "FedEx" in findings[0].message
    assert findings[0].details["identity"] == "FedEx"


def test_symbols_reader_uses_canonical_kind() -> None:
    ctx = _FakeCtx(config={"codex_payload": _payload_with_signals()})
    findings = CodexSymbolsReader().analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].details["kind"] == "ce_marking"


def test_barcodes_reader_includes_value_and_format() -> None:
    ctx = _FakeCtx(config={"codex_payload": _payload_with_signals()})
    findings = CodexBarcodesReader().analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].details["format"] == "ean13"
    assert findings[0].details["value"] == "5012345678900"


def test_spell_reader_summarises_candidates() -> None:
    ctx = _FakeCtx(config={"codex_payload": _payload_with_signals()})
    findings = CodexSpellReader().analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].details["candidates"] == ["tyIenol", "asprin"]


def test_classification_reader_emits_document_level_finding() -> None:
    ctx = _FakeCtx(config={"codex_payload": _payload_with_signals()})
    findings = CodexClassificationReader().analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].page_num == 0
    assert "label" in findings[0].message


def test_readers_short_circuit_when_ai_disabled() -> None:
    payload = _payload_with_signals()
    payload["extraction_warnings"] = [{"code": "ai_disabled", "scope": "signals.ai"}]
    ctx = _FakeCtx(config={"codex_payload": payload})
    for reader_cls in (
        CodexLanguageReader,
        CodexLogosReader,
        CodexSymbolsReader,
        CodexBarcodesReader,
        CodexSpellReader,
        CodexClassificationReader,
    ):
        assert reader_cls().analyze_v2(ctx) == [], reader_cls.__name__


def test_readers_short_circuit_when_payload_missing() -> None:
    ctx = _FakeCtx(config={})
    for reader_cls in (
        CodexLanguageReader,
        CodexLogosReader,
        CodexSymbolsReader,
        CodexBarcodesReader,
        CodexSpellReader,
        CodexClassificationReader,
    ):
        assert reader_cls().analyze_v2(ctx) == [], reader_cls.__name__
