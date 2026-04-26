"""Phase 1.2 — Backlog generation per playbook §1.3 priority formula.

Reads:
  - audit/phase-1-v2/v2-id-coverage.json (post-1.1b verification sweep)

Outputs:
  - audit/phase-1-v2/backlog.json — every absent + partial v2 ID with priority score
  - audit/phase-1-v2/backlog-summary.md — top-N table + per-wave breakdown

§1.3 priority scoring:
  Base by tier: T1=90, T2=70, T3=50, T4=40, T5=10
  +15 if remediation guidance is unique/articulable
  +10 if dieline_adjacent
  +5  if Wave A or Wave B sequence
  +5  if genuinely unclaimed (per playbook §10.5)
  -10 if difficulty=hard AND tier > 2
  -5  if requires rasterization or ICC infra not yet present
  cap 100, floor 1
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/home/user/lint-pdf")

# §10.5 unclaimed list — high-leverage wedge IDs
UNCLAIMED = {
    "D-06", "D-03", "D-04", "D-07", "D-08", "D-09", "D-12",
    "P-30", "P-31", "P-32",
    "W-02", "W-03", "W-04", "W-07", "W-12", "W-16",
    "B-15", "B-16", "B-17",
    "BR-07",
    "L-18", "L-21",
    "T-05",
    "R-05", "R-07",
    "C-63",
    "T3-D17",  # legacy v1 id
}

# IDs requiring rasterization or ICC (not present per Phase 0.3)
NEEDS_RASTER_OR_ICC = {
    # Rasterization-dependent
    "C-43", "C-44", "C-45", "C-46", "C-47",  # TAC/region/per-page
    "C-48", "C-49",                            # Substrate-aware TAC + min-dot area
    "P-26",                                     # Object hidden under another
    # ICC / device-link
    "EPM-A6", "EPM-A7", "EPM-B3", "EPM-B5",   # Advanced ΔE/ΔC + skin-tone + deep-shadow
    # White-underprint geometry
    "W-02", "W-03", "W-04", "W-07",
}

# Difficulty inferred from playbook tables (E/M/H column)
HARD_IDS = {
    "F-30", "F-41",
    "C-44", "C-63",
    "P-26",
    "I-38",
    "TR-19",
    "BR-05",
    "B-08", "B-09",
    "T-03", "T-05", "T-12",
    "R-02", "R-05",
    "W-02", "W-03", "W-04", "W-06", "W-07", "W-16",
    "D-14", "D-19", "D-20",
}

# Remediation-guidance unique flag (playbook §10.5 + dieline-adjacent F-/P- + EPM)
HAS_UNIQUE_GUIDANCE = (
    UNCLAIMED
    | {"F-32", "F-33", "F-34", "F-35", "F-36", "F-37"}
    | {"D-15", "D-16", "D-17", "D-18", "D-22", "D-23"}
    | {"P-30", "P-31", "P-32"}
    | {f"EPM-A{i}" for i in range(1, 9)}
    | {f"EPM-B{i}" for i in range(1, 7)}
)


def score(row: dict) -> int:
    tier = row.get("tier") or 2
    wave = row.get("wave") or "D"
    v2_id = row["v2_id"]

    base = {1: 90, 2: 70, 3: 50, 4: 40, 5: 10}.get(tier, 50)
    s = base
    if v2_id in HAS_UNIQUE_GUIDANCE:
        s += 15
    if row.get("dieline_adjacent"):
        s += 10
    if wave in {"A", "B"}:
        s += 5
    if v2_id in UNCLAIMED:
        s += 5

    # Difficulty estimation from table column (universe enumeration)
    is_hard = v2_id in HARD_IDS
    if is_hard and tier > 2:
        s -= 10
    if v2_id in NEEDS_RASTER_OR_ICC:
        s -= 5

    return max(1, min(100, s))


def main() -> None:
    cov = json.loads((REPO / "audit/phase-1-v2/v2-id-coverage.json").read_text())

    backlog: list[dict] = []
    for row in cov["user_facing"]:
        if row.get("status") == "present":
            continue
        prio = score(row)
        backlog.append({
            "v2_id": row["v2_id"],
            "human_name": row.get("v2_human_name"),
            "tier": row.get("tier"),
            "wave": row.get("wave"),
            "dieline_adjacent": row.get("dieline_adjacent"),
            "status": row.get("status"),
            "priority_score": prio,
            "is_unclaimed": row["v2_id"] in UNCLAIMED,
            "needs_raster_or_icc": row["v2_id"] in NEEDS_RASTER_OR_ICC,
            "is_hard": row["v2_id"] in HARD_IDS,
            "absent_extension_target": row.get("absent_extension_target"),
            "remediation_guidance_present": row.get("remediation_guidance_present"),
        })

    # Add Tier-0 primitives (absent only)
    tier0_backlog = []
    for p in cov.get("tier0_primitives", []):
        if p.get("status") == "present":
            continue
        tier0_backlog.append({
            "primitive": p.get("primitive"),
            "category": p.get("category"),
            "status": p.get("status"),
            "downstream_consumers": p.get("downstream_consumers", []),
            "priority_score": 100,  # all Tier-0 maxed; foundation
            "wave": "0",
        })

    # Add Wave V foundation deliverables (V-07/V-08/V-12) — always priority 100
    wave_v_foundation = [
        {
            "wave_v_id": "V-07",
            "name": "Toggle resolver (tenant → workflow → per-call)",
            "wave": "V",
            "priority_score": 100,
            "design_handoff": "audit/phase-1-v2/wave-v-design-handoff.md §V-07",
        },
        {
            "wave_v_id": "V-08",
            "name": "Config audit log + surface attribution",
            "wave": "V",
            "priority_score": 100,
            "design_handoff": "audit/phase-1-v2/wave-v-design-handoff.md §V-08",
        },
        {
            "wave_v_id": "V-12",
            "name": "Legacy config migration script (idempotent + reversible)",
            "wave": "V",
            "priority_score": 100,
            "design_handoff": "audit/phase-1-v2/wave-v-design-handoff.md §V-12",
        },
    ]

    backlog.sort(key=lambda r: -r["priority_score"])

    out = REPO / "audit/phase-1-v2/backlog.json"
    out.write_text(json.dumps({
        "schema_version": "1.2.v2",
        "generated_at": "2026-04-25",
        "totals": {
            "user_facing_absent": len(backlog),
            "tier0_absent": len(tier0_backlog),
            "wave_v_foundation": len(wave_v_foundation),
        },
        "wave_v_foundation": wave_v_foundation,
        "tier0_primitives_absent": tier0_backlog,
        "user_facing_backlog": backlog,
    }, indent=2))

    # Markdown summary
    lines = [
        "# Phase 1.2 — Backlog Summary",
        "",
        "**Date:** 2026-04-25",
        "**Source:** `audit/phase-1-v2/v2-id-coverage.json` (post-1.1b verification)",
        "",
        "## Totals",
        "",
        f"- **Wave V foundation deliverables:** {len(wave_v_foundation)} (V-07 / V-08 / V-12 — priority 100; ship parallel with Tier-0)",
        f"- **Tier-0 primitives absent:** {len(tier0_backlog)} (priority 100 — Wave 0 foundation)",
        f"- **User-facing v2 IDs absent:** {len(backlog)}",
        "",
        "## Top-30 absent user-facing IDs by priority",
        "",
        "| # | v2_id | T | Wave | DL | Score | Unclaimed | Hard | Human name |",
        "|--:|-------|--:|:----:|:--:|------:|:---------:|:----:|------------|",
    ]
    for i, row in enumerate(backlog[:30], 1):
        dl = "✓" if row.get("dieline_adjacent") else " "
        unc = "✓" if row["is_unclaimed"] else " "
        hard = "✓" if row["is_hard"] else " "
        lines.append(
            f"| {i} | {row['v2_id']} | {row['tier']} | {row['wave']} | {dl} | "
            f"{row['priority_score']} | {unc} | {hard} | {row.get('human_name','')} |"
        )

    # Per-wave count summary
    from collections import Counter
    by_wave = Counter(r["wave"] for r in backlog)
    lines += [
        "",
        "## Absent count per wave",
        "",
        "| Wave | Count | Notes |",
        "|------|------:|-------|",
    ]
    wave_notes = {
        "B": "T1 catch-up (1.0 EM)",
        "A": "T3 dieline wedge (3.5 EM) — marketing moment",
        "D": "T2 parity (2.0 EM)",
        "C": "T4 packaging specialty (4.0 EM)",
        "E": "T5 regulatory (2.0 EM) — paid add-on",
    }
    for w in ["B", "A", "D", "C", "E"]:
        lines.append(f"| {w} | {by_wave.get(w, 0)} | {wave_notes.get(w, '')} |")

    # Tier breakdown
    by_tier = Counter(r["tier"] for r in backlog)
    lines += [
        "",
        "## Absent count per tier",
        "",
        "| Tier | Count | Description |",
        "|-----:|------:|-------------|",
    ]
    tier_notes = {
        1: "table stakes",
        2: "mainstream commercial preflight",
        3: "dieline-focused differentiator (lintPDF wedge)",
        4: "packaging-specialty (white/varnish/barcode-vs-fold/Braille)",
        5: "long-tail / niche / regulatory",
    }
    for t in [1, 2, 3, 4, 5]:
        lines.append(f"| T{t} | {by_tier.get(t, 0)} | {tier_notes.get(t, '')} |")

    # Top unclaimed
    unc = [r for r in backlog if r["is_unclaimed"]]
    lines += [
        "",
        f"## Unclaimed wedge backlog ({len(unc)} IDs)",
        "",
        "These are the §10.5 genuinely-unclaimed checks — lintPDF's marketing wedge.",
        "",
        "| v2_id | Score | Human name |",
        "|-------|------:|------------|",
    ]
    for r in sorted(unc, key=lambda x: -x["priority_score"]):
        lines.append(f"| {r['v2_id']} | {r['priority_score']} | {r.get('human_name','')} |")

    (REPO / "audit/phase-1-v2/backlog-summary.md").write_text("\n".join(lines) + "\n")
    print(f"backlog: {len(backlog)} user-facing entries; top score = {backlog[0]['priority_score']}")
    print(f"unclaimed wedge backlog: {len(unc)} IDs")


if __name__ == "__main__":
    main()
