from lintpdf.codex_summary import ensure_codex_summary


def test_codex_summary_adds_analysis_only_spot_with_deterministic_hash() -> None:
    payload = {
        "analysis": {
            "spot_names": ["Mystery Ink 42"],
            "page_1": {"cs_to_spot": {"CS1": "Mystery Ink 42"}},
        }
    }
    out = ensure_codex_summary(payload)
    colors = out["summary"]["spot_colors"]["colors"]
    mystery = next(c for c in colors if c["name"] == "Mystery Ink 42")
    assert mystery["swatch_source"] == "hash"
    assert mystery["swatch_note"] == "Analysis-only deterministic fallback"
    assert mystery["swatch_hex"].startswith("#")
