"""Phase 1.4 — Unmapped existing checks.

For every engine inspection_id, identify whether it's claimed by a v2 ID
in v2-id-coverage.json. Anything claimed = mapped. Anything unclaimed =
'unmapped existing' — the lintPDF surface beyond the canonical v2 universe.

Outputs:
  - audit/phase-1-v2/unmapped-existing.json
  - audit/phase-1-v2/unmapped-existing.md
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

REPO = Path("/home/user/lint-pdf")


def main() -> None:
    cov = json.loads((REPO / "audit/phase-1-v2/v2-id-coverage.json").read_text())
    ec = json.loads((REPO / "audit/phase-0/existing-checks.json").read_text())

    # claimed ids = union of matched_inspection_ids across all v2 user_facing rows
    claimed: set[str] = set()
    for row in cov["user_facing"]:
        for iid in (row.get("matched_inspection_ids") or []):
            claimed.add(iid)

    # all engine ids from existing-checks.json
    all_engine_ids: dict[str, dict] = {}
    for c in ec.get("checks", []):
        all_engine_ids[c["id"]] = c

    unmapped = sorted(set(all_engine_ids.keys()) - claimed)
    print(f"engine ids total: {len(all_engine_ids)}")
    print(f"claimed by v2: {len(claimed)}")
    print(f"unmapped: {len(unmapped)}")

    # Group unmapped by category prefix
    by_prefix: dict[str, list[dict]] = defaultdict(list)
    for iid in unmapped:
        check = all_engine_ids[iid]
        # Engine prefix conventions: LPDF_<CAT>_<NN> or AI_<CAT>_<NN>
        parts = iid.split("_")
        if len(parts) >= 2:
            prefix = "_".join(parts[:2])
        else:
            prefix = parts[0]
        by_prefix[prefix].append({
            "id": iid,
            "name": check.get("name") or check.get("description") or "",
            "category_id": check.get("category_id"),
            "status": check.get("status"),
            "source_files": check.get("source_files") or [],
        })

    # Sort prefixes by count
    sorted_prefixes = sorted(by_prefix.items(), key=lambda x: -len(x[1]))

    # Write JSON
    out_json = REPO / "audit/phase-1-v2/unmapped-existing.json"
    out_json.write_text(json.dumps({
        "schema_version": "1.4.v2",
        "engine_ids_total": len(all_engine_ids),
        "claimed_by_v2": len(claimed),
        "unmapped": len(unmapped),
        "by_prefix": {p: rows for p, rows in by_prefix.items()},
    }, indent=2))

    # Write Markdown
    lines = [
        "# Phase 1.4 — Unmapped Existing Checks",
        "",
        "**Date:** 2026-04-25",
        "**Source:** `audit/phase-0/existing-checks.json` ∩ `audit/phase-1-v2/v2-id-coverage.json`",
        "",
        f"- **Engine inspection_ids total:** {len(all_engine_ids)}",
        f"- **Claimed by v2 universe:** {len(claimed)}",
        f"- **Unmapped (lintPDF surface beyond v2):** {len(unmapped)}",
        "",
        "## What 'unmapped' means",
        "",
        "An engine `inspection_id` is unmapped if no v2 ID's `matched_inspection_ids`",
        "claims it. These are checks lintPDF emits today that aren't in the v2",
        "canonical universe — they are net-new surface beyond the published",
        "competitive baselines (callas, PitStop, Esko, etc.).",
        "",
        "Per Phase 0.2: this is largely **AI-tier surface** (color compliance,",
        "barcode subfamily, regulatory subfamily, dieline-detection, etc.) plus",
        "Tier-1 supplements within established families.",
        "",
        "## Default recommendation per category",
        "",
        "Per playbook §1.4: for each, decide **Keep / Rename to match v2 / Deprecate / Escalate to v2 universe**.",
        "Default: **KEEP** for AI-tier categories; **RENAME to v2 ID** for items that semantically map to a v2 slot but use a different engine id.",
        "",
        "## Counts by engine-prefix",
        "",
        "| Prefix | Unmapped | Sample |",
        "|--------|---------:|--------|",
    ]
    for p, rows in sorted_prefixes[:30]:
        sample = ", ".join(r["id"] for r in rows[:3])
        if len(rows) > 3:
            sample += "…"
        lines.append(f"| `{p}` | {len(rows)} | {sample} |")
    lines += [
        "",
        f"({len(sorted_prefixes)} prefixes total; top 30 shown.)",
        "",
        "## Triage actions",
        "",
        "1. **AI_*_*** prefixes (`AI_BAR_*`, `AI_COL_*`, `AI_REG_*`, etc.) — these",
        "   are AI-tier checks. **Keep** by default; they're lintPDF's net-new",
        "   surface beyond the v2 published baselines.",
        "",
        "2. **`LPDF_<CAT>_*` items not in v2** — likely candidates for v2 universe",
        "   inclusion or rename to a v2 slot. Triage per-item during Phase 2 design",
        "   notes; default action **NO CHANGE** until evidence for rename surfaces.",
        "",
        "3. **Catalog-only / docstring-only items** — verify against `audit/phase-",
        "   0/existing-checks-summary.md` and the catalog generator. Stale entries",
        "   should be deprecated; placeholder analyzers should be flagged for",
        "   completion.",
        "",
        "## Full list (machine-readable)",
        "",
        "See `audit/phase-1-v2/unmapped-existing.json` for the full list with",
        "human names, source files, and status. The Markdown above is summary only.",
    ]
    (REPO / "audit/phase-1-v2/unmapped-existing.md").write_text("\n".join(lines) + "\n")
    print(f"wrote markdown {len(lines)} lines")


if __name__ == "__main__":
    main()
