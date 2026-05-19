"""Vision gap audit — compare engine findings against Claude vision inspection.

Runs the preflight engine locally on each accuracy fixture PDF, then sends
rendered page images to Claude with a detailed print/prepress checklist and
compares the results. Surfaces:

  * Issues Claude vision found that the engine MISSED
  * Engine findings Claude vision says are false positives
  * Coverage gaps per check category

Usage::

    ANTHROPIC_API_KEY=<key> uv run python scripts/audit_vision_gaps.py
    # or using the in-env token:
    uv run python scripts/audit_vision_gaps.py

Options::

    --only <label,...>   limit to these fixture labels
    --max-pages N        max pages to render per PDF (default: 3)
    --out <path>         report output path
    --skip-engine        skip engine run, use cached results
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

# ── Paths ─────────────────────────────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "accuracy"
DOCS_AUDITS = REPO_ROOT / "docs" / "audits"
DOCS_AUDITS.mkdir(parents=True, exist_ok=True)

# ── Engine imports ─────────────────────────────────────────────────────────────

from lintpdf.profiles.orchestrator import PreflightOrchestrator
from lintpdf.profiles.schema import AIFeatureConfig, PreflightProfile

# ── Claude client ──────────────────────────────────────────────────────────────

import anthropic

_ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_TOKEN")

# ── Dataclasses ────────────────────────────────────────────────────────────────


@dataclass
class VisionFinding:
    category: str        # e.g. "hairline", "small_text", "color", "barcode"
    page: int
    description: str
    severity: str        # "error", "warning", "info"
    matched_engine_id: str | None = None  # LPDF_* if matched


@dataclass
class GapResult:
    label: str
    path: Path
    engine_ids: list[str] = field(default_factory=list)
    engine_findings: list[dict] = field(default_factory=list)
    vision_findings: list[VisionFinding] = field(default_factory=list)
    engine_error: str | None = None
    vision_error: str | None = None
    expected_ids: set[str] = field(default_factory=set)


# ── Profile ────────────────────────────────────────────────────────────────────

def _make_profile() -> PreflightProfile:
    return PreflightProfile(
        name="audit-vision-gaps",
        description="Full CPU checks, no AI (fast local run)",
        conformance=None,
        workflow="CMYK",
        checks={
            "enabled": ["LPDF_*", "PDFX4-*"],
            "disabled": [],
            "severity_overrides": {},
        },
        thresholds={"min_dpi": 150.0, "min_dpi_warning": 200.0, "max_tac": 340.0},
        ai=AIFeatureConfig(enabled=False, categories=[]),
    )


# ── Engine runner ──────────────────────────────────────────────────────────────

def run_engine(pdf_bytes: bytes) -> tuple[list[dict], str | None]:
    try:
        orch = PreflightOrchestrator(_make_profile())
        result = orch.run(pdf_bytes)
        findings = [
            {
                "id": f.inspection_id,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "message": f.message,
                "page": getattr(f, "page_num", None),
                "bbox": getattr(f, "bbox", None),
            }
            for f in result.findings
        ]
        return findings, None
    except Exception as exc:
        return [], str(exc)


# ── PDF renderer ───────────────────────────────────────────────────────────────

def render_pages(pdf_bytes: bytes, max_pages: int) -> list[tuple[int, str]]:
    """Return list of (page_num, base64_png) for up to max_pages pages."""
    try:
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(pdf_bytes, dpi=150, fmt="png", first_page=1, last_page=max_pages)
        out = []
        for i, img in enumerate(images, start=1):
            buf = BytesIO()
            img.save(buf, format="PNG")
            out.append((i, base64.standard_b64encode(buf.getvalue()).decode()))
        return out
    except Exception as exc:
        print(f"  [render] {exc}", file=sys.stderr)
        return []


# ── Claude vision prompt ───────────────────────────────────────────────────────

_SYSTEM = """\
You are a professional print production inspector with 20+ years of prepress experience.
You examine PDF page images for print quality issues. Be precise and concise.
Respond ONLY with a JSON array of findings. Each finding has:
  { "category": string, "page": int, "description": string, "severity": "error"|"warning"|"info" }

Categories to check:
- hairline_stroke: strokes thinner than 0.25pt that will drop out on press
- small_text: text below 6pt (body), below 4pt (legal), or outlined text below 8pt
- low_resolution: images that appear pixelated/blurry (likely <150 DPI)
- color_issue: RGB images in CMYK doc, rich black text, wrong color model
- barcode: barcode that looks damaged, low contrast, or too small to scan
- bleed_missing: art appears to go to edge but no bleed visible
- placeholder_text: variable-data tokens (LOT NUMBER, DATE CODE, PANEL labels, template markers)
- overprint: white objects that may disappear if overprint is on
- spot_color: unexpected spot/Pantone usage or spot color issues
- registration: registration marks, crop marks, or technical printing marks visible in live area
- font_issue: jagged/missing font rendering suggesting font not embedded
- transparency: transparency effect that may not separate correctly
- other: any other significant print issue

If no issues found, return [].
"""

_PAGE_PROMPT = "Page {page_num} of {label}. Inspect for ALL print issues listed in your instructions."


def vision_inspect_pages(
    label: str,
    page_images: list[tuple[int, str]],
    client: anthropic.Anthropic,
) -> tuple[list[VisionFinding], str | None]:
    if not page_images:
        return [], "no pages rendered"

    content: list[dict] = []
    for page_num, b64 in page_images:
        content.append({"type": "text", "text": f"\n--- Page {page_num} ---"})
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": b64},
        })
    content.append({"type": "text", "text": f"Inspect all pages of '{label}' for print issues. Return JSON array only."})

    try:
        resp = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            system=_SYSTEM,
            messages=[{"role": "user", "content": content}],
        )
        raw = resp.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        findings = [
            VisionFinding(
                category=f.get("category", "other"),
                page=int(f.get("page", 1)),
                description=str(f.get("description", "")),
                severity=str(f.get("severity", "warning")),
            )
            for f in data
            if isinstance(f, dict)
        ]
        return findings, None
    except Exception as exc:
        return [], str(exc)


# ── Match engine IDs to vision categories ─────────────────────────────────────

_CATEGORY_TO_ENGINE_PREFIX: dict[str, list[str]] = {
    "hairline_stroke": ["LPDF_STROKE_", "LPDF_PATH_", "LPDF_TEXT_001", "LPDF_TEXT_002"],
    "small_text": ["LPDF_TEXT_", "LPDF_TEXT_OUTLINED_SMALL", "LPDF_LEGIBILITY_"],
    "low_resolution": ["LPDF_IMG_"],
    "color_issue": ["LPDF_COLOR_", "LPDF_ADV_", "LPDF_ICC_", "LPDF_INK_"],
    "barcode": ["LPDF_BARCODE_"],
    "bleed_missing": ["LPDF_BOX_"],
    "placeholder_text": ["LPDF_PLACEHOLDER_"],
    "overprint": ["LPDF_OVER_"],
    "spot_color": ["LPDF_SPOT_"],
    "font_issue": ["LPDF_FONT_"],
    "transparency": ["LPDF_TRANS_"],
}


def _engine_ids_for_category(cat: str, engine_ids: list[str]) -> list[str]:
    prefixes = _CATEGORY_TO_ENGINE_PREFIX.get(cat, [])
    return [eid for eid in engine_ids if any(eid.startswith(p) for p in prefixes)]


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--max-pages", type=int, default=3)
    ap.add_argument("--out", default="")
    ap.add_argument("--skip-engine", action="store_true")
    args = ap.parse_args()

    only = {s.strip() for s in args.only.split(",") if s.strip()}

    if not _ANTHROPIC_KEY:
        print("ERR: set ANTHROPIC_API_KEY or CLAUDE_API_TOKEN", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=_ANTHROPIC_KEY)

    # Collect corpus
    pdfs = sorted(FIXTURES.glob("*.pdf"))
    if only:
        pdfs = [p for p in pdfs if p.stem in only]

    results: list[GapResult] = []

    for pdf_path in pdfs:
        label = pdf_path.stem
        print(f"\n{'='*60}\n{label}")
        res = GapResult(label=label, path=pdf_path)

        # Load expected IDs
        exp_path = pdf_path.with_suffix(".expected.json")
        if exp_path.exists():
            try:
                exp = json.loads(exp_path.read_text())
                res.expected_ids = set(exp.get("expected_inspection_ids", []))
            except Exception:
                pass

        pdf_bytes = pdf_path.read_bytes()

        # Engine run
        if not args.skip_engine:
            print("  [engine] running...")
            findings, err = run_engine(pdf_bytes)
            res.engine_findings = findings
            res.engine_ids = [f["id"] for f in findings]
            res.engine_error = err
            print(f"  [engine] {len(findings)} findings, error={err}")
        else:
            print("  [engine] skipped")

        # Render pages
        print(f"  [render] up to {args.max_pages} pages...")
        page_images = render_pages(pdf_bytes, args.max_pages)
        print(f"  [render] {len(page_images)} pages rendered")

        # Vision inspection
        if page_images:
            print("  [vision] inspecting with Claude Opus...")
            vision_findings, verr = vision_inspect_pages(label, page_images, client)
            res.vision_findings = vision_findings
            res.vision_error = verr
            print(f"  [vision] {len(vision_findings)} findings, error={verr}")
            # Rate limit
            time.sleep(3)

        results.append(res)

    # ── Report ────────────────────────────────────────────────────────────────

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    out_path = Path(args.out) if args.out else DOCS_AUDITS / f"{today}-vision-gap-audit.md"

    lines: list[str] = [
        f"# Vision gap audit — {today}",
        "",
        "Engine (CPU checks only, no AI) vs Claude Opus vision on rendered pages.",
        f"Max pages per PDF: {args.max_pages}. Corpus: {len(results)} PDFs.",
        "",
        "## Summary table",
        "",
        "| PDF | Engine findings | Vision findings | Vision-only (gaps) | Engine-only (FP?) |",
        "|-----|:--------------:|:---------------:|:------------------:|:-----------------:|",
    ]

    all_gaps: list[tuple[str, VisionFinding]] = []
    all_engine_only: list[tuple[str, str]] = []

    for res in results:
        engine_cats = set()
        for eid in res.engine_ids:
            for cat, prefixes in _CATEGORY_TO_ENGINE_PREFIX.items():
                if any(eid.startswith(p) for p in prefixes):
                    engine_cats.add(cat)

        vision_cats = {f.category for f in res.vision_findings}
        gaps = [f for f in res.vision_findings if not _engine_ids_for_category(f.category, res.engine_ids)]
        engine_only_cats = engine_cats - vision_cats
        all_gaps.extend((res.label, f) for f in gaps)
        all_engine_only.extend((res.label, c) for c in engine_only_cats)

        lines.append(
            f"| `{res.label}` | {len(res.engine_ids)} | {len(res.vision_findings)}"
            f" | {len(gaps)} | {len(engine_only_cats)} |"
        )

    lines += [
        "",
        "## Vision-only findings (engine misses)",
        "",
        "These are issues Claude vision found but the engine produced **zero** matching check IDs.",
        "These are the most actionable gaps.",
        "",
        "| PDF | Category | Page | Severity | Description |",
        "|-----|----------|:----:|:--------:|-------------|",
    ]
    for label, vf in all_gaps:
        lines.append(f"| `{label}` | `{vf.category}` | {vf.page} | {vf.severity} | {vf.description} |")

    if not all_gaps:
        lines.append("_No vision-only gaps found._")

    lines += [
        "",
        "## Engine-only categories (possible false positives or vision blind spots)",
        "",
        "Categories where the engine fired but vision saw nothing.",
        "",
        "| PDF | Category |",
        "|-----|----------|",
    ]
    for label, cat in all_engine_only:
        lines.append(f"| `{label}` | `{cat}` |")

    if not all_engine_only:
        lines.append("_None._")

    lines += [
        "",
        "## Per-PDF detail",
        "",
    ]
    for res in results:
        lines += [
            f"### {res.label}",
            "",
            f"**Engine:** {len(res.engine_ids)} findings  ",
            f"**Vision:** {len(res.vision_findings)} findings  ",
        ]
        if res.engine_error:
            lines.append(f"**Engine error:** `{res.engine_error}`  ")
        if res.vision_error:
            lines.append(f"**Vision error:** `{res.vision_error}`  ")

        if res.expected_ids:
            missed = res.expected_ids - set(res.engine_ids)
            lines.append(f"**Expected IDs missed by engine:** {', '.join(sorted(missed)) or 'none'}  ")

        if res.engine_ids:
            lines += ["", "**Engine check IDs:**", ""]
            for eid in sorted(set(res.engine_ids)):
                lines.append(f"- `{eid}`")

        if res.vision_findings:
            lines += ["", "**Vision findings:**", ""]
            for vf in res.vision_findings:
                matched = _engine_ids_for_category(vf.category, res.engine_ids)
                match_str = f" ← engine: {', '.join(matched)}" if matched else " ← **NO ENGINE MATCH**"
                lines.append(f"- p{vf.page} `{vf.category}` [{vf.severity}]: {vf.description}{match_str}")

        lines.append("")

    report = "\n".join(lines)
    out_path.write_text(report)
    print(f"\nReport written: {out_path}")

    # Print gap summary to stdout
    print(f"\n{'='*60}")
    print(f"VISION-ONLY GAPS (engine misses): {len(all_gaps)}")
    for label, vf in all_gaps:
        print(f"  {label} p{vf.page} [{vf.category}] {vf.description[:80]}")


if __name__ == "__main__":
    main()
