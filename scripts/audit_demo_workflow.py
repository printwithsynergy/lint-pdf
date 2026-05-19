"""Audit the preflight engine end-to-end via the marketing-site demo workflow.

Follows the exact path a human visitor uses: upload PDF → lint job →
codex extraction → lens viewer URL. Enables AI analyzers by default.
Runs Claude Opus 4.7 (InternalAuditor) to flag false positives.
Emits a markdown report with per-PDF lens links, per-inspection_id
false-positive rates, and a check-coverage matrix showing which of the
engine's declared check IDs never fired across the corpus.

Usage::

    export DEMO_BASE_URL=https://lintpdf.com
    export DEMO_BULK_TOKEN=<token>         # operator bulk-bypass token
    export ANTHROPIC_API_KEY=<key>         # for InternalAuditor (Opus 4.7)
    uv run python scripts/audit_demo_workflow.py

Options::

    --only <label,...>   comma-separated corpus labels to run (default: all)
    --no-ai              upload without x-ai-enabled (disables AI analyzers)
    --skip-codex         skip codex extraction step (faster, no AI signals)
    --skip-audit         skip InternalAuditor (no ANTHROPIC_API_KEY needed)
    --poll-timeout N     seconds to wait per lint job (default: 300)
    --out <path>         override report output path
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

# Shared audit types from the engine package.
from lintpdf.audit.internal import InternalAuditor
from lintpdf.audit.types import AuditResult
from lintpdf.reports.check_names import CHECK_NAMES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("audit_demo_workflow")

# ── Paths ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
ACCURACY_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "accuracy"
MARKETING_DEMO_PDF = REPO_ROOT.parent / "lint-pdf-marketing" / "public" / "lintpdf_preflight_test_final.pdf"
# Fallback: packaged copy inside the web sub-package when both repos share a root
_FALLBACK_DEMO_PDF = REPO_ROOT / "packages" / "web" / "public" / "lintpdf_preflight_test_final.pdf"

# ── Corpus ────────────────────────────────────────────────────────────────────

def _build_corpus() -> list[tuple[str, Path, Path | None]]:
    """Return list of (label, pdf_path, expected_json_path|None) triples.

    In-repo accuracy fixtures come first (always present), then the marketing
    demo PDF, then external test files that are skipped gracefully if absent.
    """
    entries: list[tuple[str, Path, Path | None]] = []

    # 1. In-repo accuracy fixtures (11 PDFs with ground-truth .expected.json)
    if ACCURACY_FIXTURES.exists():
        for pdf in sorted(ACCURACY_FIXTURES.glob("*.pdf")):
            expected = pdf.with_suffix(".expected.json")
            entries.append((pdf.stem, pdf, expected if expected.exists() else None))

    # 2. Marketing demo PDF (10 pages, broad coverage)
    demo = MARKETING_DEMO_PDF if MARKETING_DEMO_PDF.exists() else _FALLBACK_DEMO_PDF
    if demo.exists():
        entries.append(("web_10p_test_final", demo, None))
    else:
        logger.warning("Demo PDF not found at %s — skipping", demo)

    # 3. External test files from the preflight-test-files checkout (optional)
    ext_root = REPO_ROOT.parent / "preflight-test-files"
    _EXTERNAL: list[tuple[str, Path]] = [
        ("Amalgam_Catalyst_ext", ext_root / "Amalgam_Catalyst_9_5x3_5.pdf"),
        ("Pavette_Pride_v99_ext", ext_root / "Pavette_Pride_v99.pdf"),
        (
            "Test1_Nutrops_LS_Dieline",
            ext_root
            / "Test1/1-Standard Version/Dielines/GFS0073-01_Nutrops10ctPouchLS030926.pdf",
        ),
        (
            "Test2_AN_Energy_Pink_Slush",
            ext_root / "Test2/AN-Energy_StickPack_CA_Pink-Slush_P2_OL.pdf",
        ),
        (
            "Test3_DailyFiber_10up",
            ext_root
            / "Test3/Jan 2026 Daily Fiber Stick Pack 10up Film Test Roll/10up/"
            "PKG-DSP-STL-AC(10 Lane, Dieline 114511).pdf",
        ),
        (
            "Test4_HSI_Outlined",
            ext_root / "Test4/AN_Energy_StickPack_CA_HSI/AN_Energy_StickPack_CA_HSI_OUTLINED.pdf",
        ),
    ]
    for label, path in _EXTERNAL:
        # Skip silently if checkout not present; warn on unexpected missing.
        if path.exists():
            entries.append((label, path, None))
        elif ext_root.exists():
            logger.warning("External fixture not found: %s", path)

    return entries


CORPUS = _build_corpus()

# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class _Finding:
    """Duck-typed finding shape expected by InternalAuditor."""

    inspection_id: str
    severity: str
    message: str
    page_num: int | None
    bbox_x0: float | None
    bbox_y0: float | None
    bbox_x1: float | None
    bbox_y1: float | None


@dataclass
class DemoAudit:
    label: str
    path: Path
    expected_json: Path | None = None
    # Upload result
    demo_id: str | None = None
    lens_link: str | None = None
    upload_error: str | None = None
    ai_enabled: bool = True
    # Lint result
    findings: list[dict[str, Any]] = field(default_factory=list)
    verdict: str | None = None
    dieline: dict[str, Any] | None = None
    art_size_mm: dict[str, Any] | None = None
    legend_swatches: list[dict[str, Any]] = field(default_factory=list)
    lint_error: str | None = None
    # Codex result
    codex_data: dict[str, Any] | None = None
    codex_signals: list[str] = field(default_factory=list)
    codex_error: str | None = None
    # Audit result
    verdicts: list[AuditResult | None] = field(default_factory=list)
    audit_error: str | None = None
    # Ground truth (from .expected.json)
    expected_ids: set[str] = field(default_factory=set)
    known_missing_ids: set[str] = field(default_factory=set)


# ── Upload ────────────────────────────────────────────────────────────────────

def upload(
    base_url: str,
    pdf_path: Path,
    bulk_token: str | None,
    *,
    ai_enabled: bool = True,
) -> tuple[str | None, str | None, str | None]:
    """Upload PDF to the demo API.

    Returns (demo_id, lens_link, error_or_None).
    """
    headers: dict[str, str] = {
        "Content-Type": "application/pdf",
        "x-filename": requests.utils.quote(pdf_path.name),
    }
    if bulk_token:
        headers["x-demo-bulk-token"] = bulk_token
    if ai_enabled:
        headers["x-ai-enabled"] = "1"

    try:
        pdf_bytes = pdf_path.read_bytes()
    except OSError as exc:
        return None, None, f"read pdf: {exc}"

    try:
        resp = requests.post(
            f"{base_url}/api/demo/upload",
            headers=headers,
            data=pdf_bytes,
            timeout=60,
        )
    except requests.RequestException as exc:
        return None, None, f"upload exception: {exc}"

    if resp.status_code not in (200, 201):
        return None, None, f"upload HTTP {resp.status_code}: {resp.text[:400]}"

    try:
        body = resp.json()
    except Exception as exc:
        return None, None, f"upload JSON decode: {exc}"

    demo_id = body.get("id")
    if not demo_id:
        return None, None, f"upload body missing id: {body}"

    viewer_path = body.get("viewerUrl", f"/demo/view/{demo_id}")
    lens_link = f"{base_url.rstrip('/')}{viewer_path}"
    return demo_id, lens_link, None


# ── Lint polling ──────────────────────────────────────────────────────────────

_TERMINAL = {"complete", "completed", "succeeded", "success", "failed", "error",
              "errored", "cancelled", "canceled", "skipped"}


def _is_terminal(status: str | None) -> bool:
    return isinstance(status, str) and status.lower() in _TERMINAL


def poll_lint(
    base_url: str,
    demo_id: str,
    *,
    timeout_s: int = 300,
    poll_interval_s: float = 3.0,
) -> tuple[dict[str, Any] | None, str | None]:
    """Poll /api/demo/lint/<id> until terminal. Returns (body, error)."""
    started = time.monotonic()
    while time.monotonic() - started < timeout_s:
        try:
            resp = requests.post(
                f"{base_url}/api/demo/lint/{demo_id}",
                json={},
                timeout=120,
            )
        except requests.RequestException as exc:
            logger.warning("lint poll exception on %s: %s", demo_id, exc)
            time.sleep(poll_interval_s)
            continue

        if not resp.ok:
            logger.warning("lint poll HTTP %d for %s", resp.status_code, demo_id)
            time.sleep(poll_interval_s)
            continue

        try:
            body = resp.json()
        except Exception:
            time.sleep(poll_interval_s)
            continue

        status = (body.get("job") or {}).get("status") or body.get("status")
        if _is_terminal(status) or (body.get("ok") and body.get("findings") is not None):
            return body, None

        # Still in-flight: echo pending status and wait.
        logger.debug("lint pending (%s) for %s", status, demo_id)
        time.sleep(poll_interval_s)

    return None, f"lint poll timed out after {timeout_s}s"


# ── Codex polling ─────────────────────────────────────────────────────────────

def poll_codex(
    base_url: str,
    demo_id: str,
    *,
    timeout_s: int = 120,
) -> tuple[dict[str, Any] | None, str | None]:
    """POST /api/demo/codex/<id> and return (body, error)."""
    try:
        resp = requests.post(
            f"{base_url}/api/demo/codex/{demo_id}",
            json={},
            timeout=timeout_s,
        )
    except requests.RequestException as exc:
        return None, f"codex request exception: {exc}"

    if not resp.ok:
        return None, f"codex HTTP {resp.status_code}: {resp.text[:300]}"

    try:
        return resp.json(), None
    except Exception as exc:
        return None, f"codex JSON decode: {exc}"


# ── InternalAuditor helpers ───────────────────────────────────────────────────
# Ported verbatim from audit_test_corpus.py so both scripts stay in sync.

def _to_audit_finding(raw: dict[str, Any]) -> _Finding:
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


def _run_audit(
    auditor: InternalAuditor,
    pdf_path: Path,
    findings: list[dict[str, Any]],
) -> tuple[list[AuditResult | None], str | None]:
    if not findings:
        return [], None
    try:
        pdf_bytes = pdf_path.read_bytes()
    except OSError as exc:
        return [], f"read pdf: {exc}"
    views = [_to_audit_finding(f) for f in findings]
    try:
        verdicts = auditor.audit(pdf_bytes, views)
    except Exception as exc:
        return [None] * len(findings), f"auditor raised: {exc}"
    return verdicts, None


# ── Codex signal summariser ───────────────────────────────────────────────────

def _extract_codex_signal_keys(codex_body: dict[str, Any]) -> list[str]:
    """Return a sorted list of non-empty top-level signal keys from codex data."""
    data = codex_body.get("data") or {}
    if not isinstance(data, dict):
        return []
    # AI signal fields present in CodexDocument
    signal_fields = [
        "detected_language", "detected_logos", "detected_symbols",
        "detected_barcodes", "spell_candidates", "document_classification",
    ]
    present: list[str] = []
    for key in signal_fields:
        val = data.get(key)
        if val:  # non-empty list or dict
            present.append(key)
    # Also report page-level signals if any page has them
    pages = data.get("pages") or []
    page_keys: set[str] = set()
    for page in pages[:3]:  # sample first 3 pages to limit cost
        if not isinstance(page, dict):
            continue
        for k in signal_fields:
            if page.get(k):
                page_keys.add(f"page.{k}")
    present.extend(sorted(page_keys - {k for k in signal_fields if k in present}))
    return sorted(present)


# ── Formatters ────────────────────────────────────────────────────────────────

def _fmt_verdict(v: AuditResult | None) -> str:
    return "skipped" if v is None else v.status


def _fmt_bbox(bbox: list[float] | None) -> str:
    if not bbox or len(bbox) != 4:
        return ""
    return f"[{bbox[0]:.0f},{bbox[1]:.0f}→{bbox[2]:.0f},{bbox[3]:.0f}]"


# ── Check coverage matrix ─────────────────────────────────────────────────────

def _load_prefix_categories() -> list[tuple[str, str, str]]:
    """Load _PREFIX_CATEGORIES from the sibling export_check_catalog script."""
    import importlib.util

    catalog_path = Path(__file__).parent / "export_check_catalog.py"
    spec = importlib.util.spec_from_file_location("export_check_catalog", catalog_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {catalog_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod._PREFIX_CATEGORIES  # type: ignore[attr-defined]


def _build_coverage_matrix(
    audits: list[DemoAudit],
) -> dict[str, dict[str, Any]]:
    """Return per-category coverage stats.

    Structure:
        {category: {label, checks: [{id, name, fired_count}], total, fired}}
    """
    _PREFIX_CATEGORIES = _load_prefix_categories()

    # Count how many times each inspection_id fired across the corpus.
    fired: dict[str, int] = {}
    for a in audits:
        for f in a.findings:
            iid = f.get("inspection_id") or ""
            if iid:
                fired[iid] = fired.get(iid, 0) + 1

    # Build per-category breakdown.
    result: dict[str, dict[str, Any]] = {}
    for prefix, cat_id, label in _PREFIX_CATEGORIES:
        checks = [
            {
                "id": cid,
                "name": info.name,
                "fired": fired.get(cid, 0),
            }
            for cid, info in CHECK_NAMES.items()
            if cid.startswith(prefix)
        ]
        if not checks:
            continue
        total = len(checks)
        fired_count = sum(1 for c in checks if c["fired"] > 0)
        result[cat_id] = {
            "label": label,
            "checks": checks,
            "total": total,
            "fired": fired_count,
        }

    # "other" bucket for IDs that didn't match any prefix.
    covered_prefixes = {prefix for prefix, _, _ in _PREFIX_CATEGORIES}

    def _is_covered(cid: str) -> bool:
        return any(cid.startswith(p) for p in covered_prefixes)

    other_checks = [
        {"id": cid, "name": info.name, "fired": fired.get(cid, 0)}
        for cid, info in CHECK_NAMES.items()
        if not _is_covered(cid)
    ]
    if other_checks:
        result["other"] = {
            "label": "Other",
            "checks": other_checks,
            "total": len(other_checks),
            "fired": sum(1 for c in other_checks if c["fired"] > 0),
        }

    return result


# ── Report writer ─────────────────────────────────────────────────────────────

def write_report(out_path: Path, audits: list[DemoAudit], ai_enabled: bool) -> None:
    lines: list[str] = []
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"# Preflight demo-workflow audit — {now}\n")
    lines.append(
        "End-to-end audit via the LintPDF marketing-site demo API. "
        f"AI analyzers {'**enabled** (`x-ai-enabled: 1`)' if ai_enabled else '**disabled**'}.\n"
        "Opus 4.7 independently verified every finding the engine emitted.\n"
    )

    # ── 1. Corpus summary ─────────────────────────────────────────────────────
    lines.append("## Corpus summary\n")
    lines.append(
        "| # | PDF | Lens link | Findings | Confirmed | Disputed | Needs ctx | Skipped | Verdict | Codex signals |"
    )
    lines.append(
        "|---|-----|-----------|:--------:|:---------:|:--------:|:---------:|:-------:|---------|---------------|"
    )
    for i, a in enumerate(audits, 1):
        if a.upload_error:
            lines.append(
                f"| {i} | `{a.label}` | — | — | — | — | — | — | upload fail | — |"
            )
            continue
        counts = {"confirmed": 0, "disputed": 0, "needs_context": 0, "skipped": 0}
        for v in a.verdicts:
            if v is None:
                counts["skipped"] += 1
            else:
                counts[v.status] = counts.get(v.status, 0) + 1
        lens = f"[view]({a.lens_link})" if a.lens_link else "—"
        sigs = ", ".join(a.codex_signals) or ("—" if not a.codex_error else f"err: {a.codex_error[:40]}")
        verdict_s = a.verdict or "—"
        lines.append(
            f"| {i} | `{a.label}` | {lens} | {len(a.findings)} | "
            f"{counts['confirmed']} | {counts['disputed']} | {counts['needs_context']} | "
            f"{counts['skipped']} | {verdict_s} | {sigs} |"
        )
    lines.append("")

    # ── 2. False-positive rate by inspection_id ───────────────────────────────
    lines.append("## False-positive rate by inspection_id\n")
    lines.append(
        "`disputed` = confirmed false positive; `needs_context` = indeterminate "
        "without brand spec / JDF. High-disputed IDs are tightening targets.\n"
    )
    rollup: dict[str, dict[str, int]] = {}
    for a in audits:
        for raw, v in zip(a.findings, a.verdicts, strict=False):
            iid = raw.get("inspection_id") or "?"
            row = rollup.setdefault(
                iid,
                {"confirmed": 0, "disputed": 0, "needs_context": 0, "skipped": 0, "total": 0},
            )
            row["total"] += 1
            status = v.status if v else "skipped"
            row[status] = row.get(status, 0) + 1

    def _disp_pct(row: dict[str, int]) -> float:
        return (row.get("disputed", 0) / row["total"]) if row["total"] else 0.0

    lines.append(
        "| inspection_id | total | confirmed | disputed | needs_ctx | skipped | dispute% |"
    )
    lines.append(
        "|---------------|------:|----------:|---------:|----------:|--------:|---------:|"
    )
    for iid in sorted(rollup, key=lambda k: (-_disp_pct(rollup[k]), -rollup[k]["total"])):
        row = rollup[iid]
        pct = _disp_pct(row) * 100
        lines.append(
            f"| `{iid}` | {row['total']} | {row.get('confirmed', 0)} | "
            f"{row.get('disputed', 0)} | {row.get('needs_context', 0)} | "
            f"{row.get('skipped', 0)} | {pct:5.1f}% |"
        )
    lines.append("")

    # ── 3. Check coverage matrix ──────────────────────────────────────────────
    lines.append("## Check coverage matrix\n")
    total_declared = len(CHECK_NAMES)
    all_fired_ids: set[str] = set()
    for a in audits:
        for f in a.findings:
            iid = f.get("inspection_id") or ""
            if iid:
                all_fired_ids.add(iid)
    total_fired = len(all_fired_ids)
    lines.append(
        f"**{total_fired}/{total_declared} declared check IDs fired** "
        f"({total_fired / total_declared * 100:.1f}%) across this corpus. "
        "IDs that never fired are candidates for either a corpus gap "
        "(add a PDF that triggers them) or a dead rule (remove).\n"
    )

    try:
        coverage = _build_coverage_matrix(audits)
        lines.append(
            "| Category | Declared | Fired | Coverage | Unfired IDs |"
        )
        lines.append("|----------|:--------:|:-----:|:--------:|-------------|")
        for cat_id, cat in coverage.items():
            unfired = [c["id"] for c in cat["checks"] if c["fired"] == 0]
            unfired_s = ", ".join(f"`{x}`" for x in unfired[:10])
            if len(unfired) > 10:
                unfired_s += f" … +{len(unfired) - 10}"
            pct = cat["fired"] / cat["total"] * 100 if cat["total"] else 0
            lines.append(
                f"| {cat['label']} | {cat['total']} | {cat['fired']} | "
                f"{pct:.0f}% | {unfired_s or '—'} |"
            )
    except Exception as exc:
        lines.append(f"*(coverage matrix unavailable: {exc})*")
    lines.append("")

    # ── 4. Expected vs observed (accuracy fixtures with ground truth) ─────────
    fixtures_with_ground_truth = [a for a in audits if a.expected_ids]
    if fixtures_with_ground_truth:
        lines.append("## Expected vs observed (accuracy fixtures)\n")
        lines.append(
            "Compares findings against the `.expected.json` ground truth for "
            "in-repo accuracy fixtures. `missed` = expected but not emitted; "
            "`new` = emitted but not expected.\n"
        )
        lines.append("| PDF | Expected | Observed | Missed | New (unexpected) |")
        lines.append("|-----|:--------:|:--------:|--------|-----------------|")
        for a in fixtures_with_ground_truth:
            observed_ids = {f.get("inspection_id") for f in a.findings if f.get("inspection_id")}
            # Exclude known-missing IDs from the missed set.
            missed = a.expected_ids - observed_ids - a.known_missing_ids
            new_ids = observed_ids - a.expected_ids
            missed_s = ", ".join(f"`{x}`" for x in sorted(missed)) or "—"
            new_s = ", ".join(f"`{x}`" for x in sorted(new_ids)[:8]) or "—"
            if len(new_ids) > 8:
                new_s += f" … +{len(new_ids) - 8}"
            lines.append(
                f"| `{a.label}` | {len(a.expected_ids)} | {len(observed_ids)} | "
                f"{missed_s} | {new_s} |"
            )
        lines.append("")

    # ── 5. Per-file detail ────────────────────────────────────────────────────
    lines.append("## Per-file detail\n")
    for i, a in enumerate(audits, 1):
        lines.append(f"### {i}. `{a.label}`\n")
        if a.lens_link:
            lines.append(f"- **Lens link**: {a.lens_link}")
        lines.append(f"- AI enabled: {a.ai_enabled}")
        if a.upload_error:
            lines.append(f"- **Upload error**: {a.upload_error}\n")
            continue
        lines.append(f"- Demo id: `{a.demo_id}`")
        lines.append(f"- Verdict: `{a.verdict or '—'}`")
        d = a.dieline or {}
        lines.append(
            f"- Dieline: source=`{d.get('source', '—')}` "
            f"spot=`{d.get('spot_name') or '—'}` "
            f"polys={len(d.get('polylines') or [])}"
        )
        asz = a.art_size_mm
        lines.append(
            f"- Art size: "
            + (f"{asz.get('width_mm', 0):.2f}mm × {asz.get('height_mm', 0):.2f}mm" if asz else "—")
        )
        lines.append(f"- Legend swatches: {len(a.legend_swatches)}")
        if a.codex_signals:
            lines.append(f"- Codex signals: {', '.join(a.codex_signals)}")
        elif a.codex_error:
            lines.append(f"- Codex error: {a.codex_error}")
        if a.lint_error:
            lines.append(f"- **Lint error**: {a.lint_error}")
        if a.audit_error:
            lines.append(f"- **Audit error**: {a.audit_error}")
        lines.append("")

        if a.findings:
            lines.append("| # | inspection_id | sev | page | bbox | verdict | rationale |")
            lines.append("|--:|---------------|-----|-----:|------|---------|-----------|")
            for j, (raw, v) in enumerate(zip(a.findings, a.verdicts, strict=False), 1):
                rationale = ""
                if v:
                    rationale = (v.rationale or "").replace("|", "/").strip()
                    if len(rationale) > 160:
                        rationale = rationale[:157] + "…"
                msg_frag = (raw.get("message") or "").replace("|", "/")[:60]
                bbox_s = _fmt_bbox(raw.get("bbox"))
                lines.append(
                    f"| {j} | `{raw.get('inspection_id', '')}` | "
                    f"{raw.get('severity', '')} | "
                    f"{raw.get('page_num') or ''} | {bbox_s} | "
                    f"**{_fmt_verdict(v)}** | {rationale or msg_frag} |"
                )
            lines.append("")

    # ── 6. Tightening notes ───────────────────────────────────────────────────
    lines.append("## Tightening notes\n")
    lines.append("*(Fill in after reviewing the disputed rows and coverage gaps above.)*\n")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))
    logger.info("report written → %s (%d lines)", out_path, len(lines))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo-base",
        default=os.environ.get("DEMO_BASE_URL", "https://lintpdf.com"),
        help="Marketing-site base URL (default: $DEMO_BASE_URL or https://lintpdf.com)",
    )
    parser.add_argument(
        "--bulk-token",
        default=os.environ.get("DEMO_BULK_TOKEN"),
        help="Operator bulk-bypass token (default: $DEMO_BULK_TOKEN)",
    )
    parser.add_argument(
        "--only",
        help="Comma-separated corpus labels to limit the run",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable AI analyzers (omit x-ai-enabled header)",
    )
    parser.add_argument(
        "--skip-codex",
        action="store_true",
        help="Skip codex extraction step",
    )
    parser.add_argument(
        "--skip-audit",
        action="store_true",
        help="Skip InternalAuditor (no ANTHROPIC_API_KEY needed)",
    )
    parser.add_argument(
        "--poll-timeout",
        type=int,
        default=300,
        help="Seconds to wait for each lint job (default: 300)",
    )
    parser.add_argument(
        "--out",
        default=str(
            REPO_ROOT
            / f"docs/audits/{datetime.now(UTC).strftime('%Y-%m-%d')}-demo-workflow-audit.md"
        ),
        help="Output report path",
    )
    args = parser.parse_args()

    if not args.bulk_token:
        logger.warning(
            "DEMO_BULK_TOKEN not set — uploads will be rate-limited (5 per 10 min) "
            "and TTL will be 15 min. Set --bulk-token or $DEMO_BULK_TOKEN for a "
            "full corpus run."
        )
    if not args.skip_audit and not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ERR: ANTHROPIC_API_KEY not set. Either set it or pass --skip-audit.",
            file=sys.stderr,
        )
        return 2

    ai_enabled = not args.no_ai

    corpus = CORPUS
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        corpus = [(label, path, exp) for label, path, exp in corpus if label in wanted]
        if not corpus:
            print(f"ERR: no corpus entries matched --only={args.only!r}", file=sys.stderr)
            return 2

    auditor: InternalAuditor | None = None
    if not args.skip_audit:
        auditor = InternalAuditor()

    audits: list[DemoAudit] = []

    for label, pdf_path, expected_json_path in corpus:
        logger.info("──── %s ────", label)

        if not pdf_path.exists():
            logger.error("PDF not found: %s — skipping", pdf_path)
            audits.append(
                DemoAudit(
                    label=label,
                    path=pdf_path,
                    upload_error=f"path not found: {pdf_path}",
                )
            )
            continue

        da = DemoAudit(label=label, path=pdf_path, expected_json=expected_json_path, ai_enabled=ai_enabled)

        # Load ground-truth expectations from .expected.json if present.
        if expected_json_path and expected_json_path.exists():
            try:
                gt = json.loads(expected_json_path.read_text())
                da.expected_ids = set(gt.get("expected_inspection_ids") or [])
                da.known_missing_ids = {
                    m["inspection_id"] for m in (gt.get("known_missing") or [])
                }
            except Exception as exc:
                logger.warning("could not load ground truth for %s: %s", label, exc)

        # Step 1: Upload.
        demo_id, lens_link, err = upload(
            args.demo_base, pdf_path, args.bulk_token, ai_enabled=ai_enabled
        )
        if err:
            da.upload_error = err
            audits.append(da)
            logger.error("upload failed: %s", err)
            continue
        assert demo_id is not None
        da.demo_id = demo_id
        da.lens_link = lens_link
        logger.info("uploaded → demo_id=%s  lens=%s", demo_id, lens_link)

        # Step 2: Poll lint until terminal.
        lint_body, err = poll_lint(
            args.demo_base,
            demo_id,
            timeout_s=args.poll_timeout,
        )
        if err or lint_body is None:
            da.lint_error = err or "no response"
            audits.append(da)
            logger.error("lint poll failed: %s", err)
            continue
        da.findings = lint_body.get("findings") or []
        da.verdict = lint_body.get("verdict")
        # Nested job object may carry dieline / art_size from the engine response.
        job_obj = lint_body.get("job") or {}
        da.dieline = job_obj.get("dieline") or lint_body.get("dieline")
        da.art_size_mm = job_obj.get("art_size_mm") or lint_body.get("art_size_mm")
        da.legend_swatches = job_obj.get("legend_swatches") or lint_body.get("legend_swatches") or []
        logger.info(
            "lint complete: findings=%d verdict=%s",
            len(da.findings),
            da.verdict,
        )

        # Step 3: Codex extraction (unless --skip-codex).
        if not args.skip_codex:
            codex_body, err = poll_codex(args.demo_base, demo_id)
            if err:
                da.codex_error = err
                logger.warning("codex failed: %s", err)
            else:
                da.codex_data = codex_body
                da.codex_signals = _extract_codex_signal_keys(codex_body or {})
                logger.info("codex signals: %s", da.codex_signals)

        # Step 4: InternalAuditor false-positive verification.
        if auditor is not None and da.findings:
            verdicts, err = _run_audit(auditor, pdf_path, da.findings)
            da.verdicts = verdicts
            if err:
                da.audit_error = err
                logger.warning("auditor error: %s", err)
            else:
                confirmed = sum(1 for v in verdicts if v and v.status == "confirmed")
                disputed = sum(1 for v in verdicts if v and v.status == "disputed")
                logger.info("audit: confirmed=%d disputed=%d", confirmed, disputed)
        else:
            da.verdicts = [None] * len(da.findings)

        audits.append(da)

        # Persist raw payload for follow-up scripts / replay.
        raw_dir = Path(args.out).parent / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"{label}.json").write_text(
            json.dumps(
                {
                    "label": label,
                    "demo_id": da.demo_id,
                    "lens_link": da.lens_link,
                    "ai_enabled": da.ai_enabled,
                    "findings": da.findings,
                    "dieline": da.dieline,
                    "art_size_mm": da.art_size_mm,
                    "legend_swatches": da.legend_swatches,
                    "verdict": da.verdict,
                    "codex_signals": da.codex_signals,
                    "verdicts": [
                        {"status": v.status, "rationale": v.rationale, "model": v.model}
                        if v
                        else None
                        for v in da.verdicts
                    ],
                },
                indent=2,
            )
        )

    write_report(Path(args.out), audits, ai_enabled=ai_enabled)
    return 0 if all(a.upload_error is None and a.lint_error is None for a in audits) else 1


if __name__ == "__main__":
    sys.exit(main())
