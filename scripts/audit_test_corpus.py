"""Submit a hand-picked corpus to prod, pull findings, audit with Opus 4.7.

Not wired into CI — run manually when you want a grounded accuracy
read on a specific set of PDFs. Writes a markdown report at
``docs/audits/<date>-preflight-opus-audit.md`` with per-file findings,
per-finding Opus verdicts, per-inspection_id false-positive rollup,
and a dieline / art_size / legend accuracy section.

Usage::

    export ANTHROPIC_API_KEY=...
    export LINTPDF_API_BASE=https://api.lintpdf.com
    export LINTPDF_API_KEY=...
    uv run python scripts/audit_test_corpus.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from lintpdf.audit.internal import InternalAuditor
from lintpdf.audit.types import AuditResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("audit_test_corpus")


REPO_ROOT = Path(__file__).resolve().parents[3]

# 1 PDF per test folder + the 2 in the main dir + the 10-page test file.
CORPUS: list[tuple[str, Path]] = [
    ("Amalgam_Catalyst", REPO_ROOT / "preflight-test-files/Amalgam_Catalyst_9_5x3_5.pdf"),
    ("Pavette_Pride_v99", REPO_ROOT / "preflight-test-files/Pavette_Pride_v99.pdf"),
    (
        "Test1_Nutrops_LS_Dieline",
        REPO_ROOT
        / "preflight-test-files/Test1/1-Standard Version/Dielines/GFS0073-01_Nutrops10ctPouchLS030926.pdf",
    ),
    (
        "Test2_AN_Energy_Pink_Slush",
        REPO_ROOT / "preflight-test-files/Test2/AN-Energy_StickPack_CA_Pink-Slush_P2_OL.pdf",
    ),
    (
        "Test3_DailyFiber_10up",
        REPO_ROOT
        / "preflight-test-files/Test3/Jan 2026 Daily Fiber Stick Pack 10up Film Test Roll/10up/PKG-DSP-STL-AC(10 Lane, Dieline 114511).pdf",
    ),
    (
        "Test4_HSI_Outlined",
        REPO_ROOT
        / "preflight-test-files/Test4/AN_Energy_StickPack_CA_HSI/AN_Energy_StickPack_CA_HSI_OUTLINED.pdf",
    ),
    (
        "web_10p_test_final",
        REPO_ROOT / "packages/web/public/lintpdf_preflight_test_final.pdf",
    ),
]


@dataclass
class _Finding:
    """Duck-typed JobFinding shape InternalAuditor needs."""

    inspection_id: str
    severity: str
    message: str
    page_num: int | None
    bbox_x0: float | None
    bbox_y0: float | None
    bbox_x1: float | None
    bbox_y1: float | None


@dataclass
class FileAudit:
    label: str
    path: Path
    job_id: str | None = None
    submit_error: str | None = None
    findings: list[dict[str, Any]] = field(default_factory=list)
    dieline: dict[str, Any] | None = None
    art_size_mm: dict[str, Any] | None = None
    legend_swatches: list[dict[str, Any]] = field(default_factory=list)
    verdicts: list[AuditResult | None] = field(default_factory=list)
    audit_error: str | None = None


def submit(api_base: str, api_key: str, pdf_path: Path) -> tuple[str | None, str | None]:
    try:
        with pdf_path.open("rb") as fh:
            resp = requests.post(
                f"{api_base}/api/v1/jobs",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (pdf_path.name, fh, "application/pdf")},
                timeout=60,
            )
    except requests.RequestException as exc:
        return None, f"submit exception: {exc}"
    if resp.status_code not in (200, 201, 202):
        return None, f"submit HTTP {resp.status_code}: {resp.text[:400]}"
    try:
        body = resp.json()
        # API returns either {id: ...} or {job_id: ...} depending on route version.
        job_id = body.get("job_id") or body.get("id")
        if not job_id:
            return None, f"submit body missing job id: {body}"
        return job_id, None
    except Exception as exc:  # pragma: no cover
        return None, f"submit JSON decode: {exc} / body {resp.text[:400]}"


def poll_until_complete(
    api_base: str, api_key: str, job_id: str, *, timeout_s: int = 300
) -> tuple[dict[str, Any] | None, str | None]:
    started = time.time()
    while time.time() - started < timeout_s:
        try:
            resp = requests.get(
                f"{api_base}/api/v1/jobs/{job_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            )
        except requests.RequestException as exc:
            logger.warning("poll exception on %s: %s", job_id, exc)
            time.sleep(3)
            continue
        if resp.status_code != 200:
            time.sleep(3)
            continue
        body = resp.json()
        status = body.get("status")
        if status in ("complete", "failed", "error"):
            if status != "complete":
                return None, f"job {status}: {body.get('error_message', '(no message)')}"
            return body, None
        time.sleep(3)
    return None, f"timeout after {timeout_s}s"


def to_audit_finding(raw: dict[str, Any]) -> _Finding:
    bbox = raw.get("bbox")
    if isinstance(bbox, list) and len(bbox) == 4:
        x0, y0, x1, y1 = (float(v) if v is not None else None for v in bbox)
    else:
        x0 = y0 = x1 = y1 = None
    return _Finding(
        inspection_id=raw.get("inspection_id", ""),
        severity=raw.get("severity", "advisory"),
        message=raw.get("message", ""),
        page_num=raw.get("page_num"),
        bbox_x0=x0,
        bbox_y0=y0,
        bbox_x1=x1,
        bbox_y1=y1,
    )


def run_audit(
    auditor: InternalAuditor, pdf_path: Path, findings: list[dict[str, Any]]
) -> tuple[list[AuditResult | None], str | None]:
    if not findings:
        return [], None
    try:
        pdf_bytes = pdf_path.read_bytes()
    except OSError as exc:
        return [], f"read pdf: {exc}"
    views = [to_audit_finding(f) for f in findings]
    try:
        verdicts = auditor.audit(pdf_bytes, views)
    except Exception as exc:  # pragma: no cover
        return [None] * len(findings), f"auditor raised: {exc}"
    return verdicts, None


def _fmt_verdict(v: AuditResult | None) -> str:
    if v is None:
        return "skipped"
    return v.status


def _fmt_bbox(bbox: list[float] | None) -> str:
    if not bbox or len(bbox) != 4:
        return ""
    return f"[{bbox[0]:.0f},{bbox[1]:.0f}→{bbox[2]:.0f},{bbox[3]:.0f}]"


def write_report(out_path: Path, audits: list[FileAudit]) -> None:
    lines: list[str] = []
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"# Preflight Opus audit — {now}\n")
    lines.append(
        "Opus 4.7 independently verified every finding the engine emitted for\n"
        "the corpus below. Each finding lands as `confirmed` (engine right),\n"
        "`disputed` (engine clearly wrong), `needs_context` (needs a JDF /\n"
        "brand spec to decide), or `skipped` (auditor returned no verdict —\n"
        "e.g. doc-level finding with no page to render).\n"
    )

    # ----- Summary table -----
    lines.append("## Corpus summary\n")
    lines.append(
        "| # | File | Findings | Confirmed | Disputed | Needs ctx | Skipped | Dieline | Art size |"
    )
    lines.append(
        "|---|------|---------:|---------:|---------:|----------:|--------:|---------|----------|"
    )
    for i, a in enumerate(audits, 1):
        if a.submit_error:
            lines.append(f"| {i} | `{a.label}` | — | — | — | — | — | — | submit fail |")
            continue
        counts = {"confirmed": 0, "disputed": 0, "needs_context": 0, "skipped": 0, "error": 0}
        for v in a.verdicts:
            if v is None:
                counts["skipped"] += 1
            else:
                counts[v.status] = counts.get(v.status, 0) + 1
        dsrc = (a.dieline or {}).get("source", "—")
        asz = a.art_size_mm
        asz_txt = (
            "—" if not asz else f"{asz.get('width_mm', 0):.1f}×{asz.get('height_mm', 0):.1f}mm"
        )
        lines.append(
            f"| {i} | `{a.label}` | {len(a.findings)} | {counts['confirmed']} | "
            f"{counts['disputed']} | {counts['needs_context']} | "
            f"{counts['skipped'] + counts['error']} | {dsrc} | {asz_txt} |"
        )
    lines.append("")

    # ----- Per-inspection_id false-positive rollup -----
    lines.append("## False-positive rate by inspection_id\n")
    lines.append(
        "Aggregated across the whole corpus. `disputed` = false positive;\n"
        "`needs_context` = indeterminate without a JDF / brand spec. Rules with\n"
        "a high disputed rate are the first to tighten.\n"
    )
    rollup: dict[str, dict[str, int]] = {}
    for a in audits:
        for raw, v in zip(a.findings, a.verdicts, strict=False):
            ins = raw.get("inspection_id") or "?"
            row = rollup.setdefault(
                ins, {"confirmed": 0, "disputed": 0, "needs_context": 0, "skipped": 0, "total": 0}
            )
            row["total"] += 1
            status = v.status if v else "skipped"
            row[status] = row.get(status, 0) + 1
    lines.append(
        "| inspection_id | total | confirmed | disputed | needs_ctx | skipped | dispute% |"
    )
    lines.append("|---------------|------:|---------:|---------:|----------:|--------:|---------:|")

    # Sort by dispute percentage desc, then by volume
    def _disp(row: dict[str, int]) -> float:
        return (row.get("disputed", 0) / row["total"]) if row["total"] else 0.0

    for ins in sorted(rollup.keys(), key=lambda k: (-_disp(rollup[k]), -rollup[k]["total"])):
        row = rollup[ins]
        pct = _disp(row) * 100
        lines.append(
            f"| `{ins}` | {row['total']} | {row.get('confirmed', 0)} | "
            f"{row.get('disputed', 0)} | {row.get('needs_context', 0)} | "
            f"{row.get('skipped', 0) + row.get('error', 0)} | {pct:5.1f}% |"
        )
    lines.append("")

    # ----- Per-file detail -----
    lines.append("## Per-file detail\n")
    for i, a in enumerate(audits, 1):
        lines.append(f"### {i}. `{a.label}`\n")
        lines.append(f"- Path: `{a.path.relative_to(REPO_ROOT)}`")
        if a.submit_error:
            lines.append(f"- **Submit error**: {a.submit_error}\n")
            continue
        lines.append(f"- Job id: `{a.job_id}`")
        d = a.dieline or {}
        lines.append(
            f"- Dieline: source=`{d.get('source', '—')}` spot=`{d.get('spot_name') or '—'}` polys={len(d.get('polylines') or [])}"
        )
        asz = a.art_size_mm
        if asz:
            asz_line = f"{asz.get('width_mm', 0):.2f}mm × {asz.get('height_mm', 0):.2f}mm"
        else:
            asz_line = "—"
        lines.append(f"- Art size: {asz_line}")
        lines.append(f"- Legend swatches: {len(a.legend_swatches)}")
        if a.audit_error:
            lines.append(f"- **Audit error**: {a.audit_error}")
        lines.append("")

        if a.findings:
            lines.append("| # | id | sev | page | bbox | verdict | rationale |")
            lines.append("|--:|----|-----|-----:|------|---------|-----------|")
            for j, (raw, v) in enumerate(zip(a.findings, a.verdicts, strict=False), 1):
                rationale = (v.rationale or "").replace("|", "/").strip() if v else ""
                if len(rationale) > 160:
                    rationale = rationale[:157] + "…"
                msg_frag = (raw.get("message") or "").replace("|", "/")[:70]
                bbox_s = _fmt_bbox(raw.get("bbox"))
                lines.append(
                    f"| {j} | `{raw.get('inspection_id', '')}` | {raw.get('severity', '')} | "
                    f"{raw.get('page_num') or ''} | {bbox_s} | **{_fmt_verdict(v)}** | "
                    f"{rationale or msg_frag} |"
                )
            lines.append("")

    # ----- Recommendations section (human fills after review) -----
    lines.append("## Tightening notes\n")
    lines.append("(Fill in after review of the disputed rows above.)\n")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))
    logger.info("report written → %s (%d lines)", out_path, len(lines))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api-base", default=os.environ.get("LINTPDF_API_BASE", "https://api.lintpdf.com")
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LINTPDF_API_KEY") or os.environ.get("LINTPDF_ADMIN_API_KEY"),
    )
    parser.add_argument("--poll-timeout", type=int, default=300)
    parser.add_argument(
        "--out",
        default=str(
            REPO_ROOT
            / f"docs/audits/{datetime.now(UTC).strftime('%Y-%m-%d')}-preflight-opus-audit.md"
        ),
    )
    parser.add_argument(
        "--only",
        help="comma-separated labels to limit corpus (e.g. 'Amalgam_Catalyst,web_10p_test_final')",
    )
    args = parser.parse_args()

    if not args.api_key:
        print(
            "ERR: provide LINTPDF_API_KEY (or LINTPDF_ADMIN_API_KEY) in env or --api-key",
            file=sys.stderr,
        )
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERR: ANTHROPIC_API_KEY not set — auditor needs it", file=sys.stderr)
        return 2

    corpus = CORPUS
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        corpus = [(label, path) for label, path in CORPUS if label in wanted]
        if not corpus:
            print(f"ERR: no corpus entries matched --only={args.only}", file=sys.stderr)
            return 2

    auditor = InternalAuditor()
    audits: list[FileAudit] = []

    for label, path in corpus:
        logger.info("---- %s ----", label)
        if not path.exists():
            audits.append(FileAudit(label=label, path=path, submit_error=f"path not found: {path}"))
            continue
        fa = FileAudit(label=label, path=path)

        job_id, err = submit(args.api_base, args.api_key, path)
        if err:
            fa.submit_error = err
            audits.append(fa)
            logger.error("submit failed: %s", err)
            continue
        fa.job_id = job_id
        logger.info("submitted: %s", job_id)

        body, err = poll_until_complete(
            args.api_base, args.api_key, job_id, timeout_s=args.poll_timeout
        )
        if err:
            fa.submit_error = err
            audits.append(fa)
            logger.error("poll failed: %s", err)
            continue
        assert body is not None
        fa.findings = body.get("findings") or []
        fa.dieline = body.get("dieline")
        fa.art_size_mm = body.get("art_size_mm")
        fa.legend_swatches = body.get("legend_swatches") or []
        logger.info(
            "findings=%d dieline=%s art_size=%s",
            len(fa.findings),
            (fa.dieline or {}).get("source"),
            bool(fa.art_size_mm),
        )

        verdicts, err = run_audit(auditor, path, fa.findings)
        fa.verdicts = verdicts
        if err:
            fa.audit_error = err
            logger.warning("audit error: %s", err)
        else:
            confirmed = sum(1 for v in verdicts if v and v.status == "confirmed")
            disputed = sum(1 for v in verdicts if v and v.status == "disputed")
            logger.info("audit: confirmed=%d disputed=%d", confirmed, disputed)
        audits.append(fa)

        # Persist the raw payload alongside the report for follow-up scripts.
        raw_dir = Path(args.out).parent / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"{label}.json").write_text(
            json.dumps(
                {
                    "job_id": fa.job_id,
                    "findings": fa.findings,
                    "dieline": fa.dieline,
                    "art_size_mm": fa.art_size_mm,
                    "legend_swatches": fa.legend_swatches,
                    "verdicts": [
                        {"status": v.status, "rationale": v.rationale, "model": v.model}
                        if v
                        else None
                        for v in fa.verdicts
                    ],
                },
                indent=2,
            )
        )

    write_report(Path(args.out), audits)
    # Exit non-zero if any submit failures happened (so CI can catch).
    return 0 if all(a.submit_error is None for a in audits) else 1


if __name__ == "__main__":
    sys.exit(main())
