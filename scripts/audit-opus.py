#!/usr/bin/env python3
"""Opus parallel-preflight audit.

Reads engine findings from the most-recent smoke run, sends each PDF +
findings JSON to Claude Opus 4.7, captures Opus's adjudication (agree /
disagree / uncertain per engine finding + issues the engine missed
entirely), writes per-fixture audit JSON + a global summary.

Goal: surface engine misses (false negatives) and false positives so the
operator can decide which analyzers to tighten or add.

Usage:
    python3 scripts/audit-opus.py                  # auto-pick newest smoke run
    python3 scripts/audit-opus.py /tmp/smoke-batch-1777324136

Env:
    ANTHROPIC_API_KEY    Required. Direct Anthropic call (not via engine).
    OPUS_MODEL           Override. Default claude-opus-4-7.

Cost: ~$10 for 12 fixtures (12 calls × ~30K input + ~5K output tokens
each at Opus 4.7 prices).

Companion to scripts/smoke-preflight-batch.sh — that one mints a tenant
and runs preflight; this one independently audits the result.
"""

from __future__ import annotations

import base64
import glob
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "packages/engine/tests/fixtures"

OPUS_MODEL = os.environ.get("OPUS_MODEL", "claude-opus-4-7")
MAX_TOKENS = 8000
MAX_TOKENS_LARGE = 16000  # Bump for fixtures with > 200 findings.
RETRY_MAX = 3
RETRY_BASE_DELAY_S = 4

# When the native PDF would blow Anthropic limits (1 M context, 32 MB
# body), rasterize each page to a JPEG and send as image content
# blocks instead. The audit task is grounded against the *rendered*
# pages anyway — native PDF vision is unnecessary for this purpose.
FLATTEN_IF_BYTES = 1_000_000   # > 1 MB → flatten
FLATTEN_IF_PAGES = 10           # > 10 pages → flatten
FLATTEN_DPI = 144               # 144 dpi ≈ 2× screen, good enough for visual audit
FLATTEN_MAX_PIXELS = 1500       # Long-edge clamp; keep image content blocks ≤ ~1 MB.
FLATTEN_JPEG_QUALITY = 80
FILTER_FIXTURES = os.environ.get("AUDIT_FIXTURES", "").strip()  # space-sep slot names


@dataclass
class FixtureAudit:
    """Per-fixture audit result."""

    name: str
    engine_count: int
    agree: int
    disagree: int
    uncertain: int
    missed: int
    parse_failed: bool
    raw_path: Path | None


def fail(msg: str, code: int = 1) -> None:
    print(f"✘ {msg}", file=sys.stderr)
    sys.exit(code)


def load_smoke_run(run_dir: Path) -> list[tuple[str, Path, Path]]:
    """Walk a smoke run dir, return [(fixture_name, pdf_path, poll_json), ...]."""
    out: list[tuple[str, Path, Path]] = []
    for slot in sorted(run_dir.glob("[0-9][0-9]_*")):
        if not slot.is_dir():
            continue
        poll = slot / "poll.json"
        if not poll.exists():
            continue
        # The slot dirname is "<NN>_<basename-without-extension>".
        stem = slot.name.split("_", 1)[1]
        # Locate the matching PDF under tests/fixtures/{,accuracy/}.
        candidates = [
            FIXTURE_DIR / f"{stem}.pdf",
            *(FIXTURE_DIR / "accuracy").glob(f"{stem}.pdf"),
        ]
        pdf = next((c for c in candidates if c.exists()), None)
        if pdf is None:
            print(f"  ! no PDF for slot {slot.name}; skipping", file=sys.stderr)
            continue
        out.append((slot.name, pdf, poll))
    return out


def flatten_pdf_to_image_blocks(pdf_path: Path) -> list[dict[str, Any]]:
    """Rasterize each page to a JPEG; return Anthropic image content blocks.

    Used when the native PDF would exceed Anthropic API limits (1 M
    input tokens or 32 MB body). PyMuPDF (fitz) is preferred — pure
    Python wheel, no external poppler dep. JPEG quality + long-edge
    clamp keep total bytes under a few MB even for dense fixtures.
    """
    import fitz  # PyMuPDF
    from io import BytesIO
    try:
        from PIL import Image
    except Exception as e:
        raise RuntimeError(
            "Pillow (PIL) is required for flattening; "
            "pip install Pillow"
        ) from e

    blocks: list[dict[str, Any]] = []
    doc = fitz.open(pdf_path)
    try:
        for page in doc:
            mat = fitz.Matrix(FLATTEN_DPI / 72.0, FLATTEN_DPI / 72.0)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            # Long-edge clamp to bound bytes per page.
            if max(img.size) > FLATTEN_MAX_PIXELS:
                ratio = FLATTEN_MAX_PIXELS / max(img.size)
                img = img.resize(
                    (int(img.size[0] * ratio), int(img.size[1] * ratio)),
                    Image.LANCZOS,
                )
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=FLATTEN_JPEG_QUALITY, optimize=True)
            jpg_b64 = base64.standard_b64encode(buf.getvalue()).decode("ascii")
            blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": jpg_b64,
                    },
                }
            )
    finally:
        doc.close()
    return blocks


DETAILS_CHAR_CAP = 500  # Per-finding details JSON cap.


def _truncate_details(details: Any) -> Any:
    """Cap a `details` payload so a single finding can't blow the prompt.

    Some engine findings (e.g. LPDF_INK_001 ink-coverage samples) carry
    multi-megabyte arrays of per-pixel data. Useful for tile-level
    rendering, useless for an Opus audit. Drop array fields and
    serialize-then-truncate the rest.
    """
    if details is None:
        return None
    if isinstance(details, dict):
        cleaned: dict[str, Any] = {}
        for k, v in details.items():
            if isinstance(v, list) and len(v) > 8:
                cleaned[k] = f"<list len={len(v)}>"
            elif isinstance(v, str) and len(v) > 200:
                cleaned[k] = v[:200] + "…"
            elif isinstance(v, dict):
                cleaned[k] = "<dict>" if len(json.dumps(v)) > 200 else v
            else:
                cleaned[k] = v
        if len(json.dumps(cleaned)) > DETAILS_CHAR_CAP:
            return {"_summary": "details truncated (over cap)", "keys": list(cleaned.keys())[:8]}
        return cleaned
    s = json.dumps(details)
    if len(s) > DETAILS_CHAR_CAP:
        return s[: DETAILS_CHAR_CAP] + "…"
    return details


def trim_findings(poll_path: Path) -> list[dict[str, Any]]:
    """Return a slim per-finding projection — drop UUIDs + AI fields, cap details."""
    body = json.loads(poll_path.read_text())
    findings = body.get("findings") or []
    keep_keys = ("inspection_id", "severity", "message", "page_num", "details", "category")
    out: list[dict[str, Any]] = []
    for f in findings:
        row = {k: f.get(k) for k in keep_keys}
        row["details"] = _truncate_details(row.get("details"))
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# Prompts (filled in by next Edit pass)
# ---------------------------------------------------------------------------

AUDIT_SYSTEM = """\
You are an expert print-production preflight auditor. You have decades \
of experience with offset, flexo, and digital print, with deep knowledge \
of PDF/X conformance, color management (ICC, spot colors, gamut, total \
ink coverage), font embedding, image resolution, page geometry (bleed, \
trim, safe zones), trapping, and packaging-specific concerns (dielines, \
barcodes, regulatory artwork).

You will be given:
  1. A PDF file (via document vision) — the actual artefact under review.
  2. A list of findings produced by an automated rule-based engine.

Your job is to independently audit the PDF and:
  A. For each engine finding, decide whether you agree the issue exists.
  B. Identify any issues the engine MISSED entirely.

Be calibrated and conservative:
  - Only mark "disagree" if you can see in the PDF that the engine's \
claim is wrong (false positive).
  - Mark "uncertain" if you can't tell from the rendered PDF (e.g. the \
finding requires inspecting the underlying object structure, ICC \
profile bytes, or metadata that PDF rendering doesn't expose).
  - Default to "agree" when the issue is plausibly visible in the PDF \
or is a metadata/structural claim that's reasonable to trust the engine on.

For misses, only list issues a competent print operator would flag at \
prepress. Don't invent issues. Cite the page and what makes it problematic.

Return STRICT JSON only — no prose before or after, no markdown fences. \
Schema:

{
  "engine_audit": [
    {"finding_index": 0, "verdict": "agree" | "disagree" | "uncertain",
     "rationale": "1-2 sentence reason"}
  ],
  "engine_missed": [
    {"category": "color | fonts | images | geometry | text | metadata | dieline | barcode | other",
     "severity": "error | warning | advisory",
     "page_num": 1,
     "issue": "what the engine missed",
     "evidence": "how you can see it in the PDF"}
  ],
  "summary": {"agree": 0, "disagree": 0, "uncertain": 0, "missed": 0}
}
"""

AUDIT_USER = """\
Audit this PDF against the engine's findings below. Return strict JSON only.

ENGINE FINDINGS (0-indexed; reference by `finding_index`):
{findings_json}
"""


# ---------------------------------------------------------------------------
# Anthropic call (filled in by next Edit pass)
# ---------------------------------------------------------------------------


def call_opus(
    pdf_blocks: list[dict[str, Any]],
    findings_json: str,
    max_tokens: int = MAX_TOKENS,
) -> tuple[str, dict[str, Any]]:
    """Send PDF blocks + findings JSON to Opus; return (raw_text, parsed_dict_or_empty).

    `pdf_blocks` is either a single document content block (native PDF
    path) or a list of image content blocks (flattened path).

    Uses the anthropic Python SDK. Retries on transient errors (network /
    5xx) with exponential backoff. Surfaces non-retryable errors to the
    caller, which converts them to FixtureAudit(parse_failed=True).
    """
    import anthropic  # local import — module isn't on the critical-path cold start

    client = anthropic.Anthropic()
    last_err: Exception | None = None
    for attempt in range(1, RETRY_MAX + 1):
        try:
            resp = client.messages.create(
                model=OPUS_MODEL,
                max_tokens=max_tokens,
                system=AUDIT_SYSTEM,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            *pdf_blocks,
                            {
                                "type": "text",
                                "text": AUDIT_USER.format(findings_json=findings_json),
                            },
                        ],
                    },
                ],
            )
            text_blocks = [
                b.text for b in resp.content if getattr(b, "type", "") == "text"
            ]
            raw = "\n".join(text_blocks).strip()
            # Strip any accidental ```json ... ``` fences.
            if raw.startswith("```"):
                first_nl = raw.find("\n")
                last_fence = raw.rfind("```")
                if first_nl != -1 and last_fence > first_nl:
                    raw = raw[first_nl + 1 : last_fence].strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {}
            return raw, parsed
        except (anthropic.APIConnectionError, anthropic.APIStatusError) as e:
            last_err = e
            status = getattr(e, "status_code", None)
            if status is not None and status < 500 and status != 429:
                # Non-retryable client error — surface immediately.
                raise
            time.sleep(RETRY_BASE_DELAY_S * (2 ** (attempt - 1)))
    if last_err is not None:
        raise last_err
    return "", {}


# ---------------------------------------------------------------------------
# Per-fixture audit (filled in by next Edit pass)
# ---------------------------------------------------------------------------


def load_existing_audit(name: str, poll: Path, out_dir: Path) -> FixtureAudit | None:
    """Return a FixtureAudit if `<out_dir>/<name>.json` already exists.

    Lets a re-run skip already-audited fixtures (idempotent + cheap to
    re-aggregate). Returns None when there's no prior audit.
    """
    json_path = out_dir / f"{name}.json"
    if not json_path.exists():
        return None
    try:
        body = json.loads(json_path.read_text())
    except json.JSONDecodeError:
        return None
    audit_rows = body.get("engine_audit") or []
    missed_rows = body.get("engine_missed") or []
    findings = trim_findings(poll)
    return FixtureAudit(
        name=name,
        engine_count=len(findings),
        agree=sum(1 for r in audit_rows if r.get("verdict") == "agree"),
        disagree=sum(1 for r in audit_rows if r.get("verdict") == "disagree"),
        uncertain=sum(1 for r in audit_rows if r.get("verdict") == "uncertain"),
        missed=len(missed_rows),
        parse_failed=False,
        raw_path=out_dir / f"{name}.raw.txt",
    )


def audit_one(name: str, pdf: Path, poll: Path, out_dir: Path) -> FixtureAudit:
    """Audit a single fixture, write JSON, return summary."""
    # Skip if already audited (idempotent re-runs).
    existing = load_existing_audit(name, poll, out_dir)
    if existing is not None:
        print("  (skipping — audit json already exists)")
        return existing

    findings = trim_findings(poll)
    findings_json = json.dumps(findings, indent=2)

    # Decide native-PDF vs flattened-images based on file size + page count.
    pdf_bytes = pdf.read_bytes()
    page_count = 0
    try:
        import fitz
        with fitz.open(pdf) as _d:
            page_count = _d.page_count
    except Exception:
        pass
    too_big = len(pdf_bytes) > FLATTEN_IF_BYTES or page_count > FLATTEN_IF_PAGES

    if too_big:
        print(
            f"  flattening ({len(pdf_bytes)//1024} KB, {page_count} pages → JPEG @ {FLATTEN_DPI} dpi)"
        )
        pdf_blocks = flatten_pdf_to_image_blocks(pdf)
        approx_kb = sum(len(b["source"]["data"]) for b in pdf_blocks) // 1024 * 3 // 4
        print(f"  flattened to {len(pdf_blocks)} image blocks (~{approx_kb} KB total)")
    else:
        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")
        pdf_blocks = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_b64,
                },
            }
        ]

    # Bump output budget for fixtures with > 200 findings — Opus needs
    # room to enumerate every audit row + missed item.
    max_tokens = MAX_TOKENS_LARGE if len(findings) > 200 else MAX_TOKENS

    raw, parsed = call_opus(pdf_blocks, findings_json, max_tokens=max_tokens)

    # Write whatever we got.
    json_path = out_dir / f"{name}.json"
    if parsed:
        json_path.write_text(json.dumps(parsed, indent=2))
    raw_path = out_dir / f"{name}.raw.txt"
    raw_path.write_text(raw)

    if not parsed:
        return FixtureAudit(name, len(findings), 0, 0, 0, 0, parse_failed=True, raw_path=raw_path)

    # Tally.
    audit_rows = parsed.get("engine_audit") or []
    missed_rows = parsed.get("engine_missed") or []
    agree = sum(1 for r in audit_rows if r.get("verdict") == "agree")
    disagree = sum(1 for r in audit_rows if r.get("verdict") == "disagree")
    uncertain = sum(1 for r in audit_rows if r.get("verdict") == "uncertain")
    return FixtureAudit(
        name=name,
        engine_count=len(findings),
        agree=agree,
        disagree=disagree,
        uncertain=uncertain,
        missed=len(missed_rows),
        parse_failed=False,
        raw_path=raw_path,
    )


# ---------------------------------------------------------------------------
# Summary aggregator (filled in by next Edit pass)
# ---------------------------------------------------------------------------


def write_summary(audits: list[FixtureAudit], out_dir: Path) -> None:
    """Emit summary.txt + engine_missed_by_category.txt."""
    # ── summary table ───────────────────────────────────────────
    lines = [
        "Opus 4.7 vs engine — preflight audit",
        "=" * 90,
        f"{'Fixture':<46} {'Engine':>8} {'Agree':>8} {'Disagree':>10} {'Uncertain':>10} {'Missed':>8}",
        "-" * 90,
    ]
    tot_engine = tot_agree = tot_disagree = tot_uncertain = tot_missed = 0
    for a in audits:
        flag = " (parse_failed)" if a.parse_failed else ""
        name_disp = (a.name + flag)[:46]
        lines.append(
            f"{name_disp:<46} {a.engine_count:>8} {a.agree:>8} "
            f"{a.disagree:>10} {a.uncertain:>10} {a.missed:>8}"
        )
        tot_engine += a.engine_count
        tot_agree += a.agree
        tot_disagree += a.disagree
        tot_uncertain += a.uncertain
        tot_missed += a.missed
    lines.append("-" * 90)
    lines.append(
        f"{'TOTAL':<46} {tot_engine:>8} {tot_agree:>8} "
        f"{tot_disagree:>10} {tot_uncertain:>10} {tot_missed:>8}"
    )

    # Percentages (avoid divide-by-zero).
    if tot_engine > 0:
        pct_agree = 100.0 * tot_agree / tot_engine
        pct_disagree = 100.0 * tot_disagree / tot_engine
        pct_uncertain = 100.0 * tot_uncertain / tot_engine
        lines.append("")
        lines.append(
            f"  Agree:     {pct_agree:5.1f}%   Disagree:  {pct_disagree:5.1f}%   "
            f"Uncertain: {pct_uncertain:5.1f}%"
        )

    summary_text = "\n".join(lines) + "\n"
    (out_dir / "summary.txt").write_text(summary_text)

    # ── engine_missed grouped by category ────────────────────────
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for a in audits:
        if a.parse_failed:
            continue
        json_path = out_dir / f"{a.name}.json"
        if not json_path.exists():
            continue
        body = json.loads(json_path.read_text())
        for item in body.get("engine_missed") or []:
            cat = item.get("category") or "other"
            row = dict(item)
            row["fixture"] = a.name
            by_cat.setdefault(cat, []).append(row)

    cat_lines = ["Engine misses by category (Opus 4.7's view)", "=" * 80]
    for cat in sorted(by_cat.keys(), key=lambda c: -len(by_cat[c])):
        items = by_cat[cat]
        cat_lines.append(f"\n## {cat}  ({len(items)} miss{'es' if len(items) != 1 else ''})")
        for it in items:
            sev = it.get("severity", "?")
            page = it.get("page_num", "?")
            issue = it.get("issue", "")
            evidence = it.get("evidence", "")
            cat_lines.append(f"  - [{sev}] {it['fixture']} p.{page}: {issue}")
            if evidence:
                cat_lines.append(f"    evidence: {evidence}")
    (out_dir / "engine_missed_by_category.txt").write_text("\n".join(cat_lines) + "\n")

    # Echo summary to stdout.
    print()
    print(summary_text)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        fail("ANTHROPIC_API_KEY is required (Opus call goes direct to Anthropic).")

    # Resolve smoke run dir (arg or newest /tmp/smoke-batch-*).
    if len(sys.argv) > 1:
        run_dir = Path(sys.argv[1])
    else:
        candidates = sorted(glob.glob("/tmp/smoke-batch-*"), reverse=True)
        if not candidates:
            fail("No /tmp/smoke-batch-* dirs found. Run scripts/smoke-preflight-batch.sh first.")
        run_dir = Path(candidates[0])
    if not run_dir.is_dir():
        fail(f"smoke run dir not found: {run_dir}")
    print(f"  smoke run : {run_dir}")

    # Locate fixtures.
    fixtures = load_smoke_run(run_dir)
    if not fixtures:
        fail(f"No <NN>_<fixture>/poll.json slots found under {run_dir}.")

    # Optional filter: AUDIT_FIXTURES="04_Amalgam_Catalyst_9_5x3_5 05_Cherry-Twist_OUTLINED"
    if FILTER_FIXTURES:
        wanted = set(FILTER_FIXTURES.split())
        fixtures = [f for f in fixtures if f[0] in wanted]
        if not fixtures:
            fail(f"AUDIT_FIXTURES filter matched 0 slots: {wanted}")

    print(f"  fixtures  : {len(fixtures)}")
    print(f"  model     : {OPUS_MODEL}")

    # Output dir — env override lets a re-run of failed fixtures land
    # in the same dir as the original partial run, so the aggregate
    # summary covers all 12 fixtures.
    if os.environ.get("AUDIT_OUT_DIR"):
        out_dir = Path(os.environ["AUDIT_OUT_DIR"])
    else:
        ts = int(time.time())
        out_dir = Path(f"/tmp/audit-opus-{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"  out dir   : {out_dir}")
    print()

    # Audit each fixture.
    audits: list[FixtureAudit] = []
    for idx, (name, pdf, poll) in enumerate(fixtures, start=1):
        print(f"[{idx}/{len(fixtures)}] {name} ...")
        try:
            a = audit_one(name, pdf, poll, out_dir)
        except Exception as e:
            print(f"  ✘ {e}", file=sys.stderr)
            a = FixtureAudit(name, 0, 0, 0, 0, 0, parse_failed=True, raw_path=None)
        audits.append(a)
        print(
            f"  ✓ engine={a.engine_count}  agree={a.agree}  "
            f"disagree={a.disagree}  uncertain={a.uncertain}  missed={a.missed}"
            + ("  [parse_failed]" if a.parse_failed else "")
        )

    # Global summary.
    write_summary(audits, out_dir)
    print(f"\nSummary written to: {out_dir}/summary.txt")
    print(f"Misses by category: {out_dir}/engine_missed_by_category.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
