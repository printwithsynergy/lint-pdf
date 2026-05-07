from __future__ import annotations

from lintpdf import codex_adapter


def test_extract_analysis_signals_passthrough(monkeypatch) -> None:
    payload = {
        "pdf_version": "1.7",
        "is_encrypted": False,
        "pages": [],
        "analysis": {"spot_names": ["Dieline"], "page_1": {"content_ops": []}},
    }

    monkeypatch.setattr(codex_adapter, "_extract_codex_payload", lambda _pdf: payload)
    analysis = codex_adapter.extract_analysis_signals_via_codex(b"%PDF-1.7\n")
    assert analysis["spot_names"] == ["Dieline"]


def test_semantic_document_contains_codex_analysis(monkeypatch) -> None:
    payload = {
        "pdf_version": "1.7",
        "is_encrypted": False,
        "pages": [
            {
                "page_num": 1,
                "rotation": 0,
                "boxes": {"media": {"x0": 0, "y0": 0, "x1": 100, "y1": 200}},
                "resources": {"color_space_ids": []},
            }
        ],
        "analysis": {"page_1": {"cs_to_spot": {"CS_DIE": "Dieline"}}},
    }

    monkeypatch.setattr(codex_adapter, "_extract_codex_payload", lambda _pdf: payload)
    doc, events = codex_adapter.extract_semantic_document_via_codex(b"%PDF-1.7\n")
    assert events == []
    assert doc.catalog["codex_analysis"]["page_1"]["cs_to_spot"]["CS_DIE"] == "Dieline"
    assert doc.pages[0].resources["codex_analysis"]["cs_to_spot"]["CS_DIE"] == "Dieline"
