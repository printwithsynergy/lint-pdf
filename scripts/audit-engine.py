#!/usr/bin/env python3
"""Internal engine audit — diff current findings vs locked baseline.

Replaces ``scripts/audit-opus.py`` for routine engine work. Zero API
cost, runs in ~60 seconds, catches regressions and surfaces new
coverage.

Usage:
    python3 scripts/audit-engine.py                    # diff vs baseline
    python3 scripts/audit-engine.py --update-baseline  # rebase the baseline

What it tells you:
    * **Regressions**: check IDs that were firing in the baseline but
      no longer fire on a fixture (lost coverage). Hard fail.
    * **New findings**: check IDs that fire now but didn't in baseline
      (improved coverage or new analyzer). Soft warning — confirm
      they're intentional.
    * **Count drift**: same check ID firing more / fewer times than
      baseline (calibration changes).
    * **Per-category roll-up**: errors / warnings / advisories per
      fixture compared to baseline.

When to use:
    * Routine PR work. Run before push to confirm no regressions.
    * Run with ``--update-baseline`` after a batch of intentional
      engine improvements + an Opus audit sign-off.

When NOT to use:
    * Discovering NEW miss categories Opus would surface — that's
      what ``scripts/audit-opus.py`` is for. Run that one occasionally
      (release-time, monthly), not per-PR.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = REPO / "packages/engine/tests/fixtures"
BASELINE_PATH = FIXTURE_ROOT / "expected_findings_baseline.json"

# Same 12 fixtures the Opus audit baseline used. Order matters — slot
# names ("01_<stem>") encode this.
FIXTURES: list[tuple[str, Path]] = [
    ("01", FIXTURE_ROOT / "test-sample.pdf"),
    ("02", FIXTURE_ROOT / "accuracy/AN-Energy_StickPack_CA_Pink-Slush_P2_OL.pdf"),
    ("03", FIXTURE_ROOT / "accuracy/AN_Energy_StickPack_CA_HSI_ADM_P1_OL.pdf"),
    ("04", FIXTURE_ROOT / "accuracy/Amalgam_Catalyst_9_5x3_5.pdf"),
    ("05", FIXTURE_ROOT / "accuracy/Cherry-Twist_OUTLINED.pdf"),
    ("06", FIXTURE_ROOT / "accuracy/DailyFiber_10up.pdf"),
    ("07", FIXTURE_ROOT / "accuracy/HSI_OUTLINED.pdf"),
    ("08", FIXTURE_ROOT / "accuracy/Nutrops_LS_Dieline.pdf"),
    ("09", FIXTURE_ROOT / "accuracy/Nutrops_SF_Dieline.pdf"),
    ("10", FIXTURE_ROOT / "accuracy/OrangeKiss_OUTLINED.pdf"),
    ("11", FIXTURE_ROOT / "accuracy/Pavette_Pride_v99.pdf"),
    ("12", FIXTURE_ROOT / "accuracy/Pink-Slush_OUTLINED.pdf"),
]


def run_engine(pdf: Path) -> dict:
    """Run the local engine against ``pdf`` and return a fixture-summary
    dict in the same shape as the baseline.
    """
    sys.path.insert(0, str(REPO / "packages/engine/src"))
    from lintpdf.profiles.orchestrator import PreflightOrchestrator
    from lintpdf.profiles.registry import ProfileRegistry

    profile = ProfileRegistry().get("lintpdf-default")
    pdf_bytes = pdf.read_bytes()
    orch = PreflightOrchestrator(
        profile=profile, profile_id="lintpdf-default", pdf_bytes=pdf_bytes
    )
    result = orch.run(pdf_bytes)

    counts: dict[str, int] = {}
    for f in result.findings:
        counts[f.inspection_id] = counts.get(f.inspection_id, 0) + 1

    return {
        "total_findings": result.summary.total_findings,
        "error_count": result.summary.error_count,
        "warning_count": result.summary.warning_count,
        "advisory_count": result.summary.advisory_count,
        "finding_counts": counts,
        "finding_ids": sorted(counts),
    }


def diff_fixture(slot: str, baseline: dict, current: dict) -> dict:
    """Return a structured diff for one fixture."""
    base_ids = set(baseline.get("finding_ids", []))
    curr_ids = set(current["finding_ids"])
    base_counts = baseline.get("finding_counts", {})
    curr_counts = current["finding_counts"]

    regressions = sorted(base_ids - curr_ids)
    new_findings = sorted(curr_ids - base_ids)

    drift = []
    for cid in sorted(base_ids & curr_ids):
        b = base_counts.get(cid, 0)
        c = curr_counts.get(cid, 0)
        if b != c:
            drift.append({"id": cid, "baseline_count": b, "current_count": c})

    return {
        "slot": slot,
        "baseline_total": baseline.get("total_findings", 0),
        "current_total": current["total_findings"],
        "regressions": regressions,
        "new_findings": new_findings,
        "count_drift": drift,
        "severity_delta": {
            "errors": current["error_count"] - baseline.get("error_count", 0),
            "warnings": current["warning_count"] - baseline.get("warning_count", 0),
            "advisories": current["advisory_count"] - baseline.get("advisory_count", 0),
        },
    }


def print_report(diffs: list[dict]) -> int:
    """Print a human-readable diff report and return the exit code
    (0 = clean, 1 = regressions detected)."""
    has_regressions = False
    has_changes = False
    print()
    print("=" * 96)
    print(
        f"{'Fixture':<46} {'Baseline':>8} {'Now':>5} {'Δ':>4}  "
        f"{'Regress':>7} {'New':>4} {'Drift':>5}"
    )
    print("-" * 96)
    for d in diffs:
        b = d["baseline_total"]
        c = d["current_total"]
        delta = c - b
        regs = len(d["regressions"])
        news = len(d["new_findings"])
        drift = len(d["count_drift"])
        if regs > 0:
            has_regressions = True
        if regs or news or drift:
            has_changes = True
        marker = " " if regs == 0 else "*"
        print(
            f"{marker} {d['slot']:<44} {b:>8} {c:>5} {delta:>+4}  "
            f"{regs:>7} {news:>4} {drift:>5}"
        )
    print("-" * 96)

    # Detail section.
    if has_changes:
        print()
        print("DETAIL")
        print("-" * 96)
        for d in diffs:
            if not (d["regressions"] or d["new_findings"] or d["count_drift"]):
                continue
            print(f"\n{d['slot']}")
            if d["regressions"]:
                print(f"  REGRESSIONS ({len(d['regressions'])}):")
                for r in d["regressions"]:
                    print(f"    - {r}")
            if d["new_findings"]:
                print(f"  new findings ({len(d['new_findings'])}):")
                for n in d["new_findings"]:
                    print(f"    + {n}")
            if d["count_drift"]:
                print(f"  count drift ({len(d['count_drift'])}):")
                for it in d["count_drift"]:
                    arrow = "↑" if it["current_count"] > it["baseline_count"] else "↓"
                    print(
                        f"    {arrow} {it['id']}: "
                        f"{it['baseline_count']} → {it['current_count']}"
                    )

    print()
    if has_regressions:
        print("FAIL: regressions detected (check IDs lost coverage). Investigate before merge.")
        return 1
    if has_changes:
        print("OK: no regressions. New findings / count drift are improvements — confirm intentional.")
        return 0
    print("OK: no changes vs baseline.")
    return 0


def update_baseline(diffs: list[dict], current_results: dict[str, dict]) -> None:
    """Overwrite the baseline JSON with current results."""
    out = {
        slot: {
            "fixture": slot,
            "total_findings": data["total_findings"],
            "error_count": data["error_count"],
            "warning_count": data["warning_count"],
            "advisory_count": data["advisory_count"],
            "finding_counts": data["finding_counts"],
            "finding_ids": data["finding_ids"],
        }
        for slot, data in current_results.items()
    }
    BASELINE_PATH.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"baseline updated: {BASELINE_PATH}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--update-baseline",
        action="store_true",
        help="Overwrite the baseline JSON with current findings",
    )
    args = ap.parse_args()

    if not BASELINE_PATH.exists():
        print(f"baseline missing: {BASELINE_PATH}", file=sys.stderr)
        return 2
    baseline = json.loads(BASELINE_PATH.read_text())

    current_results: dict[str, dict] = {}
    diffs: list[dict] = []
    print(f"running {len(FIXTURES)} fixtures locally...")
    t0 = time.monotonic()
    for slot, pdf in FIXTURES:
        if not pdf.exists():
            print(f"  ! missing fixture: {pdf}", file=sys.stderr)
            continue
        try:
            stem = pdf.stem
            slot_name = f"{slot}_{stem}"
            current = run_engine(pdf)
            current_results[slot_name] = current
            base = baseline.get(slot_name, {})
            diffs.append(diff_fixture(slot_name, base, current))
            print(f"  {slot_name}: {current['total_findings']} findings")
        except Exception as exc:
            print(f"  ! {slot}: {type(exc).__name__}: {exc}", file=sys.stderr)
    print(f"done in {time.monotonic() - t0:.1f}s")

    if args.update_baseline:
        update_baseline(diffs, current_results)
        return 0

    return print_report(diffs)


if __name__ == "__main__":
    sys.exit(main())
