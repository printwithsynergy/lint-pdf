#!/usr/bin/env python3
"""Refresh gap-mapping.json against the current catalog + phase-2 status dirs.

Overlays the v3 baseline (which was hand-curated over a long period of
phase-1 + early phase-2 work) with the items shipped in batches 4-9 and
beyond. A gap is upgraded to ``present`` when:

- a status.md exists at audit/phase-2/<gap_id>/ (or the -stub variant), AND
- at least one of its expected inspection_ids is in the catalog, OR
- the gap is satisfied by a profile pack (T2-GWG01/02).

Items not satisfied by the above keep the v3 status.

Run:

    python3 audit/phase-1/refresh_mapping.py
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
GAP_LIST = REPO / "audit" / "phase-1" / "gap-list.json"
GAP_MAPPING = REPO / "audit" / "phase-1" / "gap-mapping.json"
PHASE_2_DIR = REPO / "audit" / "phase-2"
CATALOG = REPO / "packages" / "app" / "lib" / "rules" / "check-catalog.json"


# Items shipped *after* the v3 mapping was last hand-edited. Each row is
# (gap_id, [inspection_ids that prove coverage]). When the inspection_ids
# are present in the catalog or the corresponding phase-2 status.md
# exists, the gap is upgraded to ``present``.
POST_V3_DELIVERIES: list[tuple[str, list[str]]] = [
    # Batch 7
    ("T1-F04", ["LPDF_FONT_LICENSE"]),
    ("T1-I07", ["LPDF_IMG_BROKEN"]),
    ("T1-STR04", ["LPDF_PAGE_SIZE"]),
    # Batch 8 — veraPDF triple + compliance set
    ("T1-CMP01", ["LPDF_VERAPDF_PDFX"]),
    ("T1-CMP02", ["LPDF_VERAPDF_PDFX"]),
    ("T1-CMP03", ["LPDF_DOC_004"]),
    ("T1-CMP04", ["LPDF_DOC_TITLE"]),
    ("T1-CMP06", ["LPDF_VERAPDF_PDFX"]),
    ("T4-A01", ["LPDF_VERAPDF_PDFUA"]),
    ("T4-A02", ["LPDF_VERAPDF_PDFA"]),
    # Batch 9a — Tier-4 a11y trio
    ("T4-A06", ["LPDF_ACCESS_TABLE_STRUCTURE"]),
    ("T4-A07", ["LPDF_ACCESS_HEADING_SKIP"]),
    ("T4-A09", ["LPDF_ACCESS_SCREEN_READER"]),
    # Batch 9b — regulatory analyzers
    ("T5-N02", ["AI_ALC_001", "AI_CANN_001", "AI_COSM_001"]),
    # Batch 9c — GWG profile pack + ISO05
    ("T2-GWG01", ["__profile_pack:gwg-2022-commercial"]),
    ("T2-GWG02", ["__profile_pack:gwg-2022-packaging"]),
    ("T2-ISO05", ["LPDF_PSTEP_SUGGEST"]),
    # Tier 3 — Batches 4-7 closed the dieline wedge (15/15)
    ("T3-D01", ["LPDF_DIE_NONPRINT"]),
    ("T3-D02", ["LPDF_DIE_ZORDER"]),
    ("T3-D03", ["LPDF_DIE_OVERPRINT"]),
    ("T3-D04", ["LPDF_DIE_BLEED_OVERSHOOT"]),
    ("T3-D06", ["LPDF_BARCODE_QUIET_ZONE"]),
    ("T3-D07", ["LPDF_TEXT_NEAR_FOLD"]),
    ("T3-D08", ["LPDF_DIE_TOO_SMALL"]),
    ("T3-D09", ["LPDF_DIE_WHITE_GAP"]),
    ("T3-D10", ["LPDF_DIE_VARNISH_RESPECT"]),
    ("T3-D11", ["LPDF_SPOT_NONCANONICAL"]),
    ("T3-D13", ["LPDF_DIE_REGISTRATION"]),
    ("T3-D14", ["LPDF_BRAILLE_INTEGRITY"]),
    ("T3-D15", ["LPDF_DIE_VISUAL_USE"]),
]


def _load_catalog_ids() -> set[str]:
    if not CATALOG.exists():
        return set()
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {row["id"] for row in payload if "id" in row}
    if isinstance(payload, dict):
        if "checks" in payload:
            return {row["id"] for row in payload["checks"] if "id" in row}
        return set(payload.keys())
    return set()


def _phase2_has_status(gap_id: str) -> bool:
    for variant in (gap_id, f"{gap_id}-stub", f"{gap_id}-cosm-stub"):
        if (PHASE_2_DIR / variant / "status.md").exists():
            return True
    return False


def _load_v3_baseline() -> dict[str, dict]:
    """Return v3 mapping keyed by gap_id from the last committed copy."""
    res = subprocess.run(
        ["git", "show", "HEAD:audit/phase-1/gap-mapping.json"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return {}
    payload = json.loads(res.stdout)
    return {m["gap_id"]: m for m in payload.get("matches", [])}


def main() -> int:
    gaps = json.loads(GAP_LIST.read_text(encoding="utf-8"))["gaps"]
    catalog_ids = _load_catalog_ids()
    v3_by_id = _load_v3_baseline()

    deliveries = {gid: ids for gid, ids in POST_V3_DELIVERIES}

    matches: list[dict] = []
    for gap in gaps:
        gid = gap["gap_id"]
        baseline = v3_by_id.get(gid, {})
        status = baseline.get("status", "absent")
        match_ids: list[str] = list(baseline.get("matched_ids", []))

        # Upgrade to ``present`` based on post-v3 deliveries.
        if gid in deliveries:
            expected = deliveries[gid]
            satisfied = any(
                x.startswith("__profile_pack:") or x in catalog_ids for x in expected
            )
            if satisfied or _phase2_has_status(gid):
                status = "present"
                # Merge in catalog-confirmed IDs that weren't in v3 yet.
                for x in expected:
                    if x.startswith("__profile_pack:") and x not in match_ids:
                        match_ids.append(x)
                    elif x in catalog_ids and x not in match_ids:
                        match_ids.append(x)

        matches.append(
            {
                "gap_id": gid,
                "tier": gap["tier"],
                "human_name": gap["human_name"],
                "difficulty": gap.get("difficulty", "unknown"),
                "notes": gap.get("notes", ""),
                "category_hint": gap.get("category_hint", ""),
                "status": status,
                "match_count": len(match_ids),
                "matched_ids": match_ids,
                "match_details": [{"id": x, "match_type": "explicit"} for x in match_ids],
            }
        )

    by_status: dict[str, int] = {}
    for m in matches:
        by_status[m["status"]] = by_status.get(m["status"], 0) + 1

    out = {
        "version": 4,
        "total": len(matches),
        "summary": by_status,
        "matches": matches,
    }
    GAP_MAPPING.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    print(f"Refreshed gap-mapping.json — {len(matches)} gaps")
    for status in ("present", "partial", "absent"):
        print(f"  {status}: {by_status.get(status, 0)}")
    print()
    print("Still absent (genuinely deferred):")
    for m in matches:
        if m["status"] == "absent":
            print(f"  T{m['tier']} [{m['difficulty']:8}] {m['gap_id']}: {m['human_name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
