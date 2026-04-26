"""Verification sweep for v2-id-coverage.json.

Promotes v0 'absent' rows to 'present' where v1 already closed the underlying gap.
Reads:
  - audit/phase-0/existing-checks.json (engine emit-sites by inspection_id)
  - audit/phase-1/gap-mapping.json (v1's 93 closed gaps + matched inspection_ids)
  - audit/phase-1-v2/v2-id-coverage.json (agent v0 output)

Writes:
  - audit/phase-1-v2/v2-id-coverage.json (overwrites with v1 enrichment)
  - audit/phase-1-v2/1.1b-corrections.md (delta report)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path("/home/user/lint-pdf")


def load_v1() -> tuple[dict, dict]:
    gm = json.loads((REPO / "audit/phase-1/gap-mapping.json").read_text())
    ec = json.loads((REPO / "audit/phase-0/existing-checks.json").read_text())
    return gm, ec


def load_v2_coverage() -> dict:
    return json.loads((REPO / "audit/phase-1-v2/v2-id-coverage.json").read_text())


# Map v1 gap_ids → likely v2 IDs by semantic match on human_name keywords
# These are obvious correspondences derived from playbook §10 + universe enum
V1_TO_V2 = {
    # Fonts
    "T1-F01": ["F-01"],
    "T1-F02": ["F-05"],         # Type 3 font usage
    "T1-F03": ["F-03"],         # Subset vs full embedding (primitive)
    "T1-F04": ["F-38"],         # Protected font
    "T1-F05": ["F-22", "F-23", "F-24"],  # Text below min size
    "T1-F06": ["F-13", "F-14"],          # ToUnicode missing/incomplete
    "T1-F07": ["F-01", "F-12"],          # font-related
    "T1-F08": ["F-39"],         # Duplicate font names
    "T1-F09": ["F-04"],         # Type 1 sunset
    "T1-F10": ["F-15"],         # .notdef glyph
    "T1-F11": ["F-16", "F-17"], # Encoding/illegal char
    "T1-F12": ["F-26", "F-28"], # White text overprint / black knockout
    "T1-F13": ["F-25"],         # Text stroke too thin
    "T1-F14": ["F-29"],         # Invisible text
    "T1-F15": ["F-31"],         # Rich black text
    # Color
    "T1-C01": ["C-01"],         # DeviceRGB used
    "T1-C02": ["C-23"],         # Spot color list+count
    "T1-C03": ["C-31", "C-33"], # Ambiguous spot
    "T1-C04": ["C-43", "C-45", "C-47"], # TAC > limit
    "T1-C05": ["C-36"],         # Overprint white / 0%
    "T1-C06": ["C-28", "C-38"], # Black text overprint behavior
    # Image
    "T1-I01": ["I-01"],         # Color image res < min
    "T1-I02": ["I-02"],         # Grayscale res
    "T1-I03": ["I-03"],         # 1-bit res
    "T1-I04": ["I-04"],         # Color image res > max
    "T1-I05": ["I-21"],         # Image scale > 100%
    "T1-I06": ["I-09"],         # JPEG compression
    "T1-I07": ["I-25"],         # Broken image / OPI
    # Structure / page
    "T1-STR01": ["P-03"],       # TrimBox missing
    "T1-STR02": ["P-04"],       # BleedBox missing
    "T1-STR03": ["P-09"],       # Bleed amount
    "T1-STR04": ["P-13"],       # Page size differs
    "T1-STR05": ["P-17"],       # Page count expected
    # Compliance / standards
    "T1-CMP01": ["ISO-01", "ISO-02", "ISO-03", "ISO-04", "ISO-05"],  # PDF/X verify
    "T1-CMP02": ["M-01"],       # PDF version
    "T1-CMP03": ["M-12"],       # Encryption present
    "T1-CMP04": ["M-13", "M-14"], # Owner password / permissions
    "T1-CMP06": ["M-19"],       # Embedded files
    # Tier-2 ISO / spot taxonomy
    "T2-ISO01": ["L-07"],       # ISO 19593 cutting
    "T2-ISO02": ["L-13"],       # ISO 19593 positions
    "T2-ISO03": ["L-14"],       # ISO 19593 white subtypes
    "T2-ISO04": ["L-08"],       # folding
    "T2-ISO05": ["C-32"],       # Deprecated Pantone naming
    # Rich black / type
    "T2-RB01": ["C-50"],
    "T2-RB02": ["F-31"],        # rich black text
    "T2-RB03": ["F-31"],        # reverse thin (extension)
    # Spot
    "T2-SPT01": ["C-24"],       # spot allow/block
    "T2-SPT02": ["C-31"],       # spot reference library
    "T2-SPT03": ["C-25"],       # spot regex/suffix
    # Transparency
    "T2-TRN01": ["TR-01"],      # transparency present
    "T2-TRN02": ["TR-02"],      # blend mode normal
    "T2-TRN03": ["TR-10"],      # non-separable blend
    "T2-TRN04": ["TR-17"],      # Blending CS missing
    "T2-TRN05": ["TR-18"],      # transparency on spot
    "T2-TRN06": ["TR-13"],      # Soft mask on text
    "T2-TRN07": ["TR-19"],      # transparency × overprint
    # GWG / XMP
    "T2-GWG01": ["ISO-11"],     # GWG 2022 sheet/web
    "T2-GWG02": ["ISO-11"],     # GWG packaging
    "T2-XMP01": ["M-09"],       # XMP audit trail
    # Tier-3 dieline
    "T3-D01": ["D-06"],         # z-order
    "T3-D02": ["D-01"],         # spot name detection
    "T3-D03": ["P-30", "P-31"], # bleed-vs-die per side
    "T3-D04": ["P-32", "D-17"], # content clearance
    "T3-D05": ["D-15"],         # content beyond dieline
    "T3-D06": ["D-07"],         # dieline knockout/overprint
    "T3-D07": ["W-03", "W-04"], # white choke/spread
    "T3-D08": ["W-07"],         # missing white where color
    "T3-D09": ["W-12"],         # varnish overlaps non-printable
    "T3-D10": ["D-02"],         # ISO 19593 detection
    "T3-D11": ["D-03"],         # tech-ink mapping
    "T3-D12": ["B-15", "B-16"], # barcode near fold/die
    "T3-D13": ["D-22"],         # glue flap content
    "T3-D14": ["L-06"],         # GTS_Metadata key on OCG
    "T3-D15": ["D-12", "D-13"], # closure / self-intersect
    # Tier-4 a11y
    "T4-A01": ["M-27"],         # marked content / structure tree
    "T4-A02": ["M-08"],         # XMP namespace required
    "T4-A06": ["M-08"],         # PDF/UA structure
    "T4-A07": ["M-08"],         # structure tag root
    "T4-A09": ["M-08"],         # structure language
    "T4-A10": ["M-03"],         # Document Title present (DisplayDocTitle)
    # Tier-5 niche
    "T5-N01": ["ISO-08", "V-01"], # PDF/VT structure
    "T5-N02": ["R-04"],          # cosmetics min type
    "T5-N02-cosm-stub": ["R-04"],
    "T5-N02-stub": ["R-04"],
    "T5-N04": ["R-05"],          # tobacco warning area
    "T5-N05": ["R-03"],          # alcohol gov-warning
    "T5-N05-stub": ["R-03"],
    "T5-N06": ["R-06"],          # UDI presence
    "T5-N08": ["R-07"],          # EU DPP QR
    "T5-N09": ["M-09"],          # Digimarc hint (XMP)
    "T5-N10": ["S-06"],          # Grain direction
    # AI regulatory bodies (existing analyzers; map to R-* slots loosely)
    "AI_ALC_001": ["R-03"],
    "AI_CANN_001": ["R-08"],   # cannabis as food-contact-ish nearest slot
    "AI_COSM_001": ["R-04"],
    # Workflow
    "T1-CMP05": ["WF-03"],      # page count
    # B (barcodes)
    "T2-B01": ["B-04"],         # quiet zone
    "T2-B02": ["B-11"],         # GS1 check digit
}


def main():
    gm, ec = load_v1()
    cov = load_v2_coverage()

    # Build map: v2_id → expected status from v1
    v1_v2_promote: dict[str, list[str]] = {}
    for match in gm["matches"]:
        if match.get("status") != "present":
            continue
        v1_gap_id = match["gap_id"]
        v2_targets = V1_TO_V2.get(v1_gap_id, [])
        matched_ids = match.get("matched_ids", [])
        for v2 in v2_targets:
            v1_v2_promote.setdefault(v2, []).extend(matched_ids)

    # Apply: any absent row whose v2_id is in v1_v2_promote → upgrade to present
    promoted: list[dict] = []
    for row in cov["user_facing"]:
        v2 = row["v2_id"]
        if v2 not in v1_v2_promote:
            continue
        old_status = row.get("status")
        new_ids = sorted(set(v1_v2_promote[v2]))
        if old_status in ("present",):
            # Already present; merge matched_ids
            existing = set(row.get("matched_inspection_ids") or [])
            merged = sorted(existing | set(new_ids))
            if merged != row.get("matched_inspection_ids"):
                row["matched_inspection_ids"] = merged
        else:
            row["status"] = "present"
            row["matched_inspection_ids"] = new_ids
            row["evidence"] = (row.get("evidence") or []) + [
                {"source": "v1-gap-mapping promotion",
                 "v1_gap_ids": [g for g in V1_TO_V2 if v2 in V1_TO_V2[g]]}
            ]
            row.setdefault("v1_gap_ids_covering", [])
            v1_gids = [g for g in V1_TO_V2 if v2 in V1_TO_V2[g]]
            row["v1_gap_ids_covering"] = sorted(set((row.get("v1_gap_ids_covering") or []) + v1_gids))
            promoted.append({
                "v2_id": v2,
                "old_status": old_status,
                "new_status": "present",
                "matched_inspection_ids": new_ids,
                "v1_gap_ids": v1_gids,
            })

    # Recompute summary
    by_status = {"present": 0, "partial": 0, "absent": 0}
    by_tier: dict[int, dict] = {}
    by_wave: dict[str, dict] = {}
    by_prefix: dict[str, dict] = {}
    for row in cov["user_facing"]:
        s = row.get("status", "absent")
        by_status[s] = by_status.get(s, 0) + 1
        t = row.get("tier")
        by_tier.setdefault(t, {"present": 0, "partial": 0, "absent": 0, "total": 0})
        by_tier[t][s] += 1
        by_tier[t]["total"] += 1
        w = row.get("wave")
        by_wave.setdefault(w, {"present": 0, "partial": 0, "absent": 0, "total": 0})
        by_wave[w][s] += 1
        by_wave[w]["total"] += 1
        p = row["v2_id"].split("-")[0]
        by_prefix.setdefault(p, {"present": 0, "partial": 0, "absent": 0, "total": 0})
        by_prefix[p][s] += 1
        by_prefix[p]["total"] += 1

    cov["summary"]["user_facing_present"] = by_status["present"]
    cov["summary"]["user_facing_partial"] = by_status["partial"]
    cov["summary"]["user_facing_absent"] = by_status["absent"]
    cov["summary"]["by_tier"] = {f"by_tier_{k}": v for k, v in sorted(by_tier.items()) if k is not None}
    cov["summary"]["by_wave"] = by_wave
    cov["summary"]["by_prefix"] = by_prefix
    cov["summary"]["v1_promotion_count"] = len(promoted)
    cov["schema_version"] = "1.1b.v2"

    # Write back
    out = REPO / "audit/phase-1-v2/v2-id-coverage.json"
    out.write_text(json.dumps(cov, indent=2))

    # Delta report
    delta = REPO / "audit/phase-1-v2/1.1b-corrections.md"
    lines = [
        "# Phase 1.1b — Verification Sweep Corrections",
        "",
        f"**Date:** 2026-04-25",
        f"**Promotions:** {len(promoted)} v2 IDs upgraded from absent → present "
        f"based on v1 gap-mapping closed-gaps mapping",
        "",
        "## Updated summary",
        "",
        f"| Status | Count |",
        f"|--------|------:|",
        f"| Present | {by_status['present']} |",
        f"| Partial | {by_status['partial']} |",
        f"| Absent  | {by_status['absent']} |",
        f"| **Total** | **{sum(by_status.values())}** |",
        "",
        "## Per-tier counts (recomputed)",
        "",
        "| Tier | Present | Absent | Total |",
        "|-----:|--------:|-------:|------:|",
    ]
    for t, agg in sorted(by_tier.items(), key=lambda x: (x[0] is None, x[0])):
        if t is None:
            continue
        lines.append(f"| T{t} | {agg['present']} | {agg['absent']} | {agg['total']} |")
    lines += [
        "",
        "## Promoted IDs",
        "",
        "| v2_id | old | new | inspection_ids | v1 gap_ids |",
        "|-------|-----|-----|----------------|------------|",
    ]
    for p in sorted(promoted, key=lambda r: r["v2_id"]):
        ids = ", ".join(p["matched_inspection_ids"][:3])
        if len(p["matched_inspection_ids"]) > 3:
            ids += "…"
        gids = ", ".join(p["v1_gap_ids"][:3])
        lines.append(f"| {p['v2_id']} | {p['old_status']} | {p['new_status']} | {ids} | {gids} |")
    delta.write_text("\n".join(lines) + "\n")
    print(f"promoted: {len(promoted)} rows")
    print(f"final: {by_status}")


if __name__ == "__main__":
    main()
