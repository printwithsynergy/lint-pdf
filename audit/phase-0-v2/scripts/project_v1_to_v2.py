"""Project v1 audit work into v2 taxonomy.

Reads:
  - packages/app/lib/rules/check-catalog.json (421 inspection IDs)
  - audit/phase-1/gap-mapping.json (93 v1 gaps, all 'present')
  - audit/phase-0/existing-checks.json (373 inspection IDs at v1-discovery; now ~421)

Produces:
  - audit/phase-0-v2/0.2-v1-v2-projection.json
  - audit/phase-0-v2/0.2-v1-v2-projection.md (summary)

v2 universe is the 412-artifact canonical list (84 Tier-0 + 328 user-facing) under
F-/C-/I-/TR-/P-/LA-/M-/L-/D-/W-/BR-/B-/T-/S-/V-/WF-/R-/ISO-/EPM- prefixes.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/home/user/lint-pdf")

# v2 user-facing categories with check-count from playbook §10
V2_USER_FACING = {
    "F": ("Fonts & Typography", 41),
    "C": ("Color & Ink", 67),
    "I": ("Images", 38),
    "TR": ("Transparency", 22),
    "P": ("Page Geometry / Boxes / Bleed", 36),
    "LA": ("Line Art / Paths / Strokes", 19),
    "M": ("Metadata / File Structure / Encryption / Interactive", 34),
    "L": ("Layers / OCG / Processing Steps", 21),
    "D": ("Dieline & Cut", 23),
    "W": ("White Ink / Varnish / Underprint", 16),
    "BR": ("Braille / Tactile", 9),
    "B": ("Barcodes & GS1", 28),
    "T": ("Trapping & Registration", 12),
    "S": ("Substrate / Press / Production", 18),
    "V": ("Variable Data", 7),
    "WF": ("Workflow / Job-Level", 11),
    "R": ("Industry-Specific Regulatory", 10),
    "ISO": ("ISO Standards (rolled-up)", 12),
    "EPM": ("EPM Candidacy", 22),
}

# Map v1 catalog category buckets → v2 prefixes (best-fit; many-to-one OK)
V1_CAT_TO_V2 = {
    "fonts": ["F"],
    "text": ["F"],
    "color": ["C"],
    "color_management": ["C"],
    "ink_coverage": ["C"],
    "spot_colors": ["C"],
    "overprint": ["C"],
    "transparency": ["TR"],
    "image": ["I"],
    "page_geometry": ["P"],
    "hairlines": ["LA"],
    "strokes": ["LA"],
    "paths": ["LA"],
    "document": ["M"],
    "structure": ["M", "L"],   # tag tree spans both
    "metadata": ["M"],
    "annotations": ["M"],
    "accessibility": ["M"],     # PDF/UA → metadata + structure tree
    "barcodes": ["B"],
    "packaging": ["D", "W", "BR"],
    "advanced": ["S", "T"],
    "standards": ["ISO"],
    # AI buckets:
    "ai:brand": ["WF"],         # brand checks
    "ai:cosmetics": ["R"],
    "ai:fda": ["R"],
    "ai:ghs": ["R"],
    "ai:pharma": ["R"],
    "ai:alcohol": ["R"],
    "ai:cannabis": ["R"],
    "ai:afp": ["R"],
    "ai:fibre": ["R"],
    "ai:logo": ["WF"],
    "ai:spelling": ["F"],
    "ai:language": ["F"],
    "ai:duplication": ["I"],
    "ai:nsfw": ["I"],
    "ai:image_quality": ["I"],
    "ai:scan_quality": ["I"],
    "ai:processing_steps": ["L"],
    "ai:recycling_symbols": ["R"],
    "ai:safe_zones": ["P"],
    "ai:similarity": ["I"],
    "ai:visual_diff": ["I"],
    "ai:tao": ["F"],
    "ai:dieline": ["D"],
    "ai:orgmetric": ["WF"],
    "other": [],
}


def load_catalog() -> dict:
    return json.loads((REPO / "packages/app/lib/rules/check-catalog.json").read_text())


def load_v1_gap_mapping() -> dict:
    return json.loads((REPO / "audit/phase-1/gap-mapping.json").read_text())


def project() -> dict:
    catalog = load_catalog()
    v1_gaps = load_v1_gap_mapping()

    # Coverage per v2 category, derived from catalog category bucket counts
    catalog_by_v2: dict[str, int] = Counter()
    catalog_uncategorized: list[str] = []

    for cat in catalog["categories"]:
        cat_id = cat["id"]
        n_checks = len(cat.get("checks", []))
        targets = V1_CAT_TO_V2.get(cat_id, [])
        if not targets:
            catalog_uncategorized.append(f"{cat_id}={n_checks}")
            continue
        # Distribute count across targets (rough)
        for t in targets:
            catalog_by_v2[t] += n_checks // max(1, len(targets))

    # Project v1 gaps to v2 categories using gap_id pattern (T<n>-<prefix><num>)
    v1_gaps_by_v2: dict[str, int] = Counter()
    v1_to_v2_hint = {
        "F": "F", "C": "C", "I": "I", "STR": "M",  # structure
        "GWG": "ISO", "ISO": "ISO", "RB": "F",      # rich-black-text
        "SPT": "C", "TRN": "TR",                     # transparency
        "XMP": "M", "CMP": "ISO",                    # compliance
        "D": "D",                                    # dieline
        "A": "M",                                    # accessibility (M for now)
        "N": "R",                                    # niche/regulatory
    }
    for m in v1_gaps["matches"]:
        gid = m["gap_id"]                            # e.g. T1-F01, T2-RB02, T3-D06
        # Strip Tn- prefix
        rest = gid.split("-", 1)[1] if "-" in gid else gid
        # Strip trailing digits to get prefix
        prefix = "".join(c for c in rest if not c.isdigit())
        # Special two-letter prefixes (RB, GWG, ISO, STR, XMP, CMP, SPT, TRN)
        v2 = v1_to_v2_hint.get(prefix, "?")
        v1_gaps_by_v2[v2] += 1

    # Build per-v2-category status row
    rows = []
    for v2_prefix, (label, v2_count) in V2_USER_FACING.items():
        catalog_count = catalog_by_v2.get(v2_prefix, 0)
        v1_gap_count = v1_gaps_by_v2.get(v2_prefix, 0)
        # naive coverage: implementations / v2 universe
        coverage_pct = round(min(catalog_count, v2_count) / v2_count * 100, 1)
        rows.append({
            "v2_prefix": v2_prefix,
            "label": label,
            "v2_universe_count": v2_count,
            "estimated_catalog_coverage": catalog_count,
            "v1_gaps_closed_in_bucket": v1_gap_count,
            "estimated_coverage_pct": coverage_pct,
        })

    rows.sort(key=lambda r: r["estimated_coverage_pct"])

    # Tier-0 primitives — blanket "absent" since v1 didn't enumerate primitives
    tier0_status = {
        "playbook_section": "v2 §10.1 / Section 4 of universe enumeration",
        "primitive_count": 84,
        "status": "absent (v1 did not produce a primitive registry)",
        "note": "The 84 atomic primitives are the foundation for Phase 2.0. v1 work emits findings via implicit ad-hoc PDF object inspection; no central primitive registry exists. Phase 2.0 must build it.",
    }

    # EPM module status (from 0.1 §I.1)
    epm_status = {
        "playbook_section": "v2 §2.EPM / §6 / Section 3.19",
        "module_count": 22,
        "status": "partial-foundations",
        "present_foundations": [
            "epm_analyzer.py (heuristics)",
            "rich-black recipe in advanced_color_analyzer.py",
            "TAC analyzer in ink_coverage_analyzer.py",
            "color_score.py LPDF_EPM_ category mapping",
        ],
        "absent": [
            "0-100 candidacy score / decision band output",
            "Hard disqualifier composition (EPM-A1..A8 as a unit)",
            "EPM-Advanced device-link ΔE / ΔC computation",
            "EPM AI-Explain LLM prompt + per-tenant cost-cap channel",
            "BYO EPM JSON ingestion path",
            "press_target routing (Indigo EPM/EPM+/CMYK/IndiChrome / Alwan HPM)",
        ],
    }

    # BYO mode status (from 0.1 §I.2)
    byo_status = {
        "playbook_section": "v2 §9 + Phase 2.EPM.5",
        "imports_present": [
            "pitstop.py (Adobe PitStop XML)",
            "callas.py (Callas pdfToolbox)",
            "acrobat.py (Adobe Acrobat XML)",
            "lintpdf_native.py (LintPDF JSON)",
            "custom.py (mapping-based)",
        ],
        "byo_v9_schema_status": "absent",
        "note": "Existing imports merge vendor findings into report. v2 §9 BYO is 'pre-computed analysis JSON to skip preflight' — different semantics and different schema (separations / rich_black / content_heuristics / precomputed_deltas / dieline). Greenfield work.",
    }

    # Wave V status (from 0.1 §G + §H)
    wave_v_status = {
        "playbook_section": "v2 §13 / §14 / §15 / §16 / §17",
        "viewer_overlay": "partial — TAC heatmap, separation toggle, dieline overlay, finding boxes exist; per-finding click + drawer absent (V-01..V-04)",
        "operator_decisions": "absent — flag/note/ignore at type or instance scope is greenfield (V-03..V-05)",
        "webhook_outbox_idempotent": "partial — basic webhooks + Worker-Webhooks exist; idempotency-key + outbox state schema absent (V-06)",
        "toggle_registry_cascade": "absent — no tenant→workflow→call resolver, no locked toggles, no audit log (V-07, V-08)",
        "byo_hydration": "absent (V-09)",
        "epm_overlay_extensions": "absent (V-10)",
        "tenant_theming": "absent — severity colors hardcoded in component files (V-11)",
        "legacy_migration_script": "absent (V-12)",
        "desktop_config_sync": "absent — desktop is HTTP-only mirror today (V-13)",
    }

    return {
        "schema_version": "0.2.v2",
        "generated_at": "2026-04-25",
        "v1_baseline": {
            "v1_gaps_total": v1_gaps["total"],
            "v1_gaps_present": v1_gaps["summary"]["present"],
            "v1_catalog_total": catalog["total_checks"],
        },
        "v2_universe_total": 412,
        "v2_user_facing_total": 328,
        "v2_tier0_primitives_total": 84,
        "user_facing_coverage": rows,
        "uncategorized_buckets": catalog_uncategorized,
        "tier0_primitives": tier0_status,
        "epm_module": epm_status,
        "byo_v9": byo_status,
        "wave_v": wave_v_status,
    }


if __name__ == "__main__":
    proj = project()
    out_json = REPO / "audit/phase-0-v2/0.2-v1-v2-projection.json"
    out_json.write_text(json.dumps(proj, indent=2))
    print(f"wrote {out_json}, {out_json.stat().st_size} bytes")
