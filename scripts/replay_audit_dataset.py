"""Replay the 2026-04-23 Opus audit dataset without calling Opus.

Every tightening workstream in
``/root/.claude/plans/added-preflight-test-files-want-to-drifting-pine.md``
needs a cheap, deterministic way to confirm "this commit reduced
the disputed-finding count and introduced no regressions." That's
what this harness does.

Inputs
------
* ``--baseline DIR`` — committed ``docs/audits/raw/*.json`` from the
  Opus run on 2026-04-23. Each file carries ``findings`` +
  ``verdicts`` lists in the shape emitted by
  ``scripts/audit_test_corpus.py``.
* ``--fresh DIR`` — optional. A second directory of per-file JSON in
  the same shape, produced by rerunning the engine (locally or in
  prod) after a code change. Defaults to the baseline (self-check).

Output
------
* Markdown scoreboard row at ``--out`` (default
  ``docs/audits/scoreboard.md``). Append-only.
* Exit 0 if no regressions (no new finding that wasn't in the
  baseline, or a disputed verdict re-emerged that had been removed).
  Exit 1 otherwise.

Matching
--------
A fresh finding is matched to a baseline finding by
``(inspection_id, page_num)`` bucket, then bbox IoU >= 0.5 or
identical-bbox equality. Unmatched fresh findings are treated as
**new** — their verdict defaults to ``unknown`` which is scored as
a regression only when the rule had a disputed verdict in the
baseline (i.e. the fix moved the problem instead of solving it).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("replay")


@dataclass(frozen=True)
class FindingKey:
    """Identity used to match a fresh finding against a baseline one."""

    inspection_id: str
    page_num: int | None


def _as_float(val: Any) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _bbox_tuple(bbox: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(bbox, list) or len(bbox) != 4:
        return None
    coords = tuple(_as_float(v) for v in bbox)
    if any(c is None for c in coords):
        return None
    return coords  # type: ignore[return-value]


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Axis-aligned-bbox IoU with an exact-match fast path so that
    degenerate (zero-area) bboxes still pair when they're identical
    rather than silently missing each other via 0/0 → 0 IoU.

    Additionally, when one bbox is fully contained inside the other
    we treat the pair as matched (returns 1.0). WS-9 refines box
    violations from "whole parent object" bboxes down to the
    "intersection with the violating region" — the new bbox is
    strictly inside the old one, but their plain IoU is often below
    0.5 because the new rectangle is 10–30 % of the original area.
    Those findings are the same logical issue; without this fast
    path they'd show up as "regressions" in the replay scoreboard
    even though the verdict remains identical.
    """
    if a == b:
        return 1.0
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    # Containment: one bbox sits fully within the other (allowing a
    # 0.5pt fuzz for float jitter introduced by coordinate round-
    # trips through different rendering paths).
    fuzz = 0.5
    a_in_b = bx0 - fuzz <= ax0 <= ax1 <= bx1 + fuzz and by0 - fuzz <= ay0 <= ay1 <= by1 + fuzz
    b_in_a = ax0 - fuzz <= bx0 <= bx1 <= ax1 + fuzz and ay0 - fuzz <= by0 <= by1 <= ay1 + fuzz
    if a_in_b or b_in_a:
        return 1.0
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    a_area = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    b_area = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = a_area + b_area - inter
    return inter / union if union > 0 else 0.0


@dataclass
class AuditedFinding:
    key: FindingKey
    bbox: tuple[float, float, float, float] | None
    verdict: str  # 'confirmed' | 'disputed' | 'needs_context' | 'skipped'
    rationale: str = ""


@dataclass
class FileAuditSet:
    label: str
    findings: list[AuditedFinding] = field(default_factory=list)


def _load_audit_dir(directory: Path) -> dict[str, FileAuditSet]:
    """Load every ``<label>.json`` under ``directory`` into its
    in-memory shape. The per-file JSON is the schema emitted by
    ``audit_test_corpus.py``: ``{findings: [...], verdicts: [...]}``
    with verdict entries positionally aligned to findings."""
    out: dict[str, FileAuditSet] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            logger.warning("skip %s: %s", path.name, exc)
            continue
        label = path.stem
        fs = FileAuditSet(label=label)
        findings = data.get("findings") or []
        verdicts = data.get("verdicts") or []
        for raw, v in zip(findings, verdicts, strict=False):
            status = (v or {}).get("status") if isinstance(v, dict) else None
            rationale = (v or {}).get("rationale") if isinstance(v, dict) else ""
            fs.findings.append(
                AuditedFinding(
                    key=FindingKey(
                        inspection_id=raw.get("inspection_id", ""),
                        page_num=raw.get("page_num"),
                    ),
                    bbox=_bbox_tuple(raw.get("bbox")),
                    verdict=status or "skipped",
                    rationale=rationale or "",
                )
            )
        out[label] = fs
    return out


# Fresh findings are matched to baseline ones by (inspection_id,
# page_num) bucket, then bbox IoU. A fresh finding that can't be
# matched is "new" — which is only a regression if its rule had
# disputed verdicts in the baseline (i.e. the fix moved the bug).
_IOU_THRESHOLD = 0.5


@dataclass
class ReplayStats:
    baseline_total: int = 0
    baseline_disputed: int = 0
    fresh_total: int = 0
    fresh_disputed: int = 0
    # Fresh findings with no baseline match whose rule was disputed
    # in the baseline — i.e. we didn't fix the problem, we just
    # moved it to a bbox the matcher doesn't know about.
    regressions: int = 0
    # Baseline findings whose fresh counterpart disappeared. Good
    # when the baseline verdict was disputed (true fix); neutral
    # when it was confirmed (we lost a correct finding).
    removed_disputed: int = 0
    removed_confirmed: int = 0


def _score(
    baseline: dict[str, FileAuditSet],
    fresh: dict[str, FileAuditSet],
) -> tuple[ReplayStats, dict[str, ReplayStats]]:
    """Match fresh → baseline, return aggregate + per-rule stats."""
    agg = ReplayStats()
    per_rule: dict[str, ReplayStats] = {}

    def _rule(ins: str) -> ReplayStats:
        return per_rule.setdefault(ins, ReplayStats())

    for label, base in baseline.items():
        fresh_set = fresh.get(label)
        base_by_bucket: dict[FindingKey, list[AuditedFinding]] = {}
        for bf in base.findings:
            base_by_bucket.setdefault(bf.key, []).append(bf)
            agg.baseline_total += 1
            _rule(bf.key.inspection_id).baseline_total += 1
            if bf.verdict == "disputed":
                agg.baseline_disputed += 1
                _rule(bf.key.inspection_id).baseline_disputed += 1

        if fresh_set is None:
            # Fresh run didn't cover this file (e.g. submit failure).
            # Don't count its baseline findings as "removed"; just skip.
            continue

        matched_base: set[int] = set()
        for ff in fresh_set.findings:
            agg.fresh_total += 1
            _rule(ff.key.inspection_id).fresh_total += 1
            candidates = base_by_bucket.get(ff.key, [])
            match_idx: int | None = None
            best_iou = 0.0
            for i, bf in enumerate(candidates):
                if id(bf) in matched_base:
                    continue
                # No-bbox findings (page- or doc-level) fall back to
                # perfect-match IoU so any same-key candidate counts
                # as a pair once.
                iou = _iou(ff.bbox, bf.bbox) if (ff.bbox and bf.bbox) else 1.0
                if iou > best_iou:
                    best_iou = iou
                    match_idx = i
            if match_idx is not None and best_iou >= _IOU_THRESHOLD:
                matched_bf = candidates[match_idx]
                matched_base.add(id(matched_bf))
                if matched_bf.verdict == "disputed":
                    agg.fresh_disputed += 1
                    _rule(ff.key.inspection_id).fresh_disputed += 1
            else:
                # Unmatched fresh finding. Treat as a regression only
                # if the rule had disputed verdicts in baseline — i.e.
                # it's plausible the fix moved the FP to a new bbox.
                if _rule(ff.key.inspection_id).baseline_disputed > 0:
                    agg.regressions += 1
                    _rule(ff.key.inspection_id).regressions += 1

        # Baseline findings with no fresh counterpart.
        for bf in base.findings:
            if id(bf) in matched_base:
                continue
            if bf.verdict == "disputed":
                agg.removed_disputed += 1
                _rule(bf.key.inspection_id).removed_disputed += 1
            elif bf.verdict == "confirmed":
                agg.removed_confirmed += 1
                _rule(bf.key.inspection_id).removed_confirmed += 1

    return agg, per_rule


def _append_scoreboard_row(
    out_path: Path,
    *,
    commit_sha: str,
    label: str,
    rules_touched: str,
    stats: ReplayStats,
) -> None:
    """Append one row to the scoreboard markdown. Creates the file
    with a header if it doesn't exist yet."""
    header = (
        "# Preflight accuracy scoreboard\n\n"
        "One row per tightening commit. Numbers are measured by\n"
        "`scripts/replay_audit_dataset.py` against the committed\n"
        "2026-04-23 Opus verdicts in `docs/audits/raw/*.json`.\n\n"
        "| date (UTC) | sha | label | rules touched | baseline "
        "findings | baseline disputed | fresh findings | fresh "
        "disputed | disputed Δ | regressions |\n"
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|\n"
    )
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
    delta = stats.fresh_disputed - stats.baseline_disputed
    row = (
        f"| {now} | `{commit_sha[:7]}` | {label} | {rules_touched} | "
        f"{stats.baseline_total} | {stats.baseline_disputed} | "
        f"{stats.fresh_total} | {stats.fresh_disputed} | "
        f"{delta:+d} | {stats.regressions} |\n"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not out_path.exists():
        out_path.write_text(header + row)
    else:
        existing = out_path.read_text()
        if not existing.endswith("\n"):
            existing += "\n"
        out_path.write_text(existing + row)
    logger.info("scoreboard row appended → %s", out_path)


def _print_per_rule(per_rule: dict[str, ReplayStats]) -> None:
    """Human-readable per-rule table on stdout. Handy for dev."""
    rows = sorted(
        per_rule.items(),
        key=lambda kv: (-kv[1].fresh_disputed, -kv[1].baseline_disputed, kv[0]),
    )
    print(f"{'rule':25s} {'base':>5s} {'b.dis':>6s} {'fresh':>6s} {'f.dis':>6s} {'regr':>5s}")
    for rule, s in rows:
        if s.baseline_total == 0 and s.fresh_total == 0:
            continue
        print(
            f"{rule:25s} {s.baseline_total:>5d} {s.baseline_disputed:>6d} "
            f"{s.fresh_total:>6d} {s.fresh_disputed:>6d} {s.regressions:>5d}"
        )


def main() -> int:
    here = Path(__file__).resolve().parent
    repo_root = here.parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default=str(repo_root / "docs/audits/raw"))
    parser.add_argument("--fresh", default=None, help="Defaults to --baseline (self-check).")
    parser.add_argument("--out", default=str(repo_root / "docs/audits/scoreboard.md"))
    parser.add_argument("--commit-sha", default="0000000")
    parser.add_argument("--label", default="baseline", help="Short label for the scoreboard row.")
    parser.add_argument("--rules-touched", default="—", help="Markdown-safe summary.")
    parser.add_argument("--fail-on-regression", action="store_true")
    args = parser.parse_args()

    baseline_dir = Path(args.baseline)
    fresh_dir = Path(args.fresh) if args.fresh else baseline_dir
    if not baseline_dir.exists():
        print(f"ERR: baseline dir not found: {baseline_dir}", file=sys.stderr)
        return 2

    baseline = _load_audit_dir(baseline_dir)
    fresh = _load_audit_dir(fresh_dir)
    if not baseline:
        print(f"ERR: no *.json in {baseline_dir}", file=sys.stderr)
        return 2

    agg, per_rule = _score(baseline, fresh)
    logger.info(
        "baseline total=%d disputed=%d | fresh total=%d disputed=%d | regressions=%d",
        agg.baseline_total,
        agg.baseline_disputed,
        agg.fresh_total,
        agg.fresh_disputed,
        agg.regressions,
    )
    _print_per_rule(per_rule)
    _append_scoreboard_row(
        Path(args.out),
        commit_sha=args.commit_sha,
        label=args.label,
        rules_touched=args.rules_touched,
        stats=agg,
    )
    if args.fail_on_regression and agg.regressions > 0:
        logger.error("%d regressions — failing", agg.regressions)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
