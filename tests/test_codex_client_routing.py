from __future__ import annotations

from lintpdf import codex_adapter, codex_render


def test_codex_render_client_respects_route_env(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    class _StubClient:
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            captured["route_mode"] = kwargs.get("route_mode")
            captured["plant"] = kwargs.get("plant")
            captured["affinity_key"] = kwargs.get("affinity_key")

    monkeypatch.setenv("CODEX_ROUTE_MODE", "hybrid")
    monkeypatch.setenv("CODEX_PLANT", "plant-a")
    monkeypatch.setenv("CODEX_AFFINITY_KEY", "lint-tests")
    monkeypatch.setattr("lintpdf.codex_render.HttpClient", _StubClient)
    codex_render.get_client.cache_clear()
    _ = codex_render.get_client()
    assert captured == {
        "route_mode": "hybrid",
        "plant": "plant-a",
        "affinity_key": "lint-tests",
    }


def test_codex_adapter_extract_respects_route_env(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    class _StubClient:
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            captured["route_mode"] = kwargs.get("route_mode")
            captured["plant"] = kwargs.get("plant")
            captured["affinity_key"] = kwargs.get("affinity_key")

        def extract(self, _pdf_bytes):  # type: ignore[no-untyped-def]
            return {"schema_version": "1.0.0", "pages": []}

    monkeypatch.setenv("CODEX_ROUTE_MODE", "hybrid")
    monkeypatch.setenv("CODEX_PLANT", "plant-b")
    monkeypatch.setenv("CODEX_AFFINITY_KEY", "job-42")
    monkeypatch.setattr("codex_pdf.client.HttpClient", _StubClient)
    _ = codex_adapter.extract_codex_document_via_codex(b"%PDF-1.7\n")
    assert captured == {
        "route_mode": "hybrid",
        "plant": "plant-b",
        "affinity_key": "job-42",
    }
