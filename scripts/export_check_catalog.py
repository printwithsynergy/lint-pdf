#!/usr/bin/env python3
"""Emit ``check-catalog.json`` for the app's Rules editor.

Reads :data:`siftpdf.reports.check_names.CHECK_NAMES` (the
single source of truth for inspection_id → friendly name +
description) and writes it out in a shape the Rules editor
consumes, grouped by category with a guessed default severity.

Categories map off the inspection_id prefix: ``LPDF_IMG_*`` →
``image``, ``AI_FDA_*`` → ``ai:fda``, and so on. Categories that
don't have a known prefix fall under ``other``; the editor
treats that as "uncategorised" so new checks still appear even
before the catalog has a bespoke grouping for them.

Default severity is a best-effort guess based on the ID suffix:

* ``_001``/``_002`` under error-leaning prefixes (``_CRIT``,
  ``STD``, ``ICC``) → ``error``
* Everything else → ``advisory``

Override severity at profile level via the ``severity_overrides``
block in the PreflightProfile JSON.

Run:

    python scripts/export_check_catalog.py \\
        --out ../app/lib/rules/check-catalog.json

The script is deterministic given the same CHECK_NAMES input,
so wiring it into CI (``pnpm catalog:generate && git diff
--exit-code``) catches accidental drift between the engine
registry and the UI catalog.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add the engine src directory to the import path so this script
# works whether it's invoked from the engine root or the repo
# root.
ENGINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_ROOT / "src"))

from siftpdf.reports.check_names import CHECK_NAMES  # noqa: E402

# ── Category mapping ────────────────────────────────────────

# Prefix → (category_id, display_label). The category_id is the
# stable key the Rules editor groups on; the label is the human
# heading shown above each group. Order of insertion here drives
# the order in the exported JSON so the editor renders groups
# in the same order deterministically.
_PREFIX_CATEGORIES: list[tuple[str, str, str]] = [
    ("LPDF_IMG_", "image", "Image quality"),
    ("LPDF_COLOR_", "color", "Color"),
    ("LPDF_ICC_", "color_management", "Color management"),
    ("LPDF_INK_", "ink_coverage", "Ink coverage"),
    ("LPDF_SPOT_", "spot_colors", "Spot colors"),
    ("LPDF_OVER_", "overprint", "Overprint"),
    ("LPDF_TRANS_", "transparency", "Transparency"),
    ("LPDF_FONT_", "fonts", "Fonts"),
    ("LPDF_TEXT_", "text", "Text"),
    ("LPDF_HAIR_", "hairlines", "Hairlines"),
    ("LPDF_STROKE_", "strokes", "Strokes"),
    ("LPDF_PATH_", "paths", "Paths & vectors"),
    ("LPDF_BOX_", "page_geometry", "Page geometry"),
    ("LPDF_DOC_", "document", "Document structure"),
    ("LPDF_STRUCT_", "structure", "Tagged structure"),
    ("LPDF_META_", "metadata", "Metadata"),
    ("LPDF_ANNOT_", "annotations", "Annotations"),
    ("LPDF_ACCESS_", "accessibility", "Accessibility"),
    ("LPDF_BARCODE_", "barcodes", "Barcodes"),
    ("LPDF_PKG_", "packaging", "Packaging"),
    ("LPDF_ADV_", "advanced", "Advanced print production"),
    ("LPDF_STD_", "standards", "Standards compliance"),
    ("PDFX4-", "pdfx4", "PDF/X-4 conformance"),
    ("PDFX_", "conformance", "PDF/X conformance"),
    ("PDFA_", "conformance_pdfa", "PDF/A conformance"),
    ("AI_BRAND_", "ai:brand", "AI — brand"),
    ("AI_COSM_", "ai:cosmetics", "AI — cosmetics"),
    ("AI_FDA_", "ai:fda", "AI — FDA labelling"),
    ("AI_EU_", "ai:eu1169", "AI — EU 1169 labelling"),
    ("AI_GHS_", "ai:ghs", "AI — GHS / CLP"),
    ("AI_PHARMA_", "ai:pharma", "AI — pharma"),
    ("AI_ALC_", "ai:alcohol", "AI — alcohol"),
    ("AI_CANN_", "ai:cannabis", "AI — cannabis"),
    ("AI_AFP_", "ai:afp", "AI — anti-forgery"),
    ("AI_FCLASS_", "ai:fibre", "AI — fibre classification"),
    ("AI_LOGO_", "ai:logo", "AI — logo matching"),
    ("AI_SPELL_", "ai:spelling", "AI — spelling & grammar"),
    ("AI_LANG_", "ai:language", "AI — language"),
    ("AI_DUP_", "ai:duplication", "AI — duplication"),
    ("AI_NSFW_", "ai:nsfw", "AI — NSFW"),
    ("AI_IQ_", "ai:image_quality", "AI — image quality"),
    ("AI_SCAN_", "ai:scan_quality", "AI — scan quality"),
    ("AI_PSTEP_", "ai:processing_steps", "AI — processing steps"),
    ("AI_RSYM_", "ai:recycling_symbols", "AI — recycling symbols"),
    ("AI_SZ_", "ai:safe_zones", "AI — safe zones"),
    ("AI_SIM_", "ai:similarity", "AI — similarity"),
    ("AI_VDIFF_", "ai:visual_diff", "AI — visual diff"),
    ("AI_TAO_", "ai:tao", "AI — TAO inspection"),
    ("AI_DIE_", "ai:dieline", "AI — dieline"),
    ("AI_ORG_", "ai:orgmetric", "AI — organisation metric"),
]


# Severity defaults. A check matches on prefix precedence (longest
# match wins); if nothing matches, falls back to ``advisory``.
# Standards-conformance + catastrophic image/font problems default
# to ``error`` so a brand-new custom profile out of the box still
# raises the common "this won't print" issues.
_ERROR_PREFIXES: tuple[str, ...] = (
    "PDFX4-",
    "PDFX_",
    "PDFA_",
    "LPDF_STD_",
    "LPDF_ICC_",
)

_WARNING_PREFIXES: tuple[str, ...] = (
    "LPDF_IMG_",
    "LPDF_FONT_",
    "LPDF_COLOR_",
    "LPDF_OVER_",
    "LPDF_TRANS_",
    "LPDF_HAIR_",
    "LPDF_STROKE_",
    "LPDF_INK_",
    "LPDF_BOX_",
    "LPDF_BARCODE_",
)


def _categorise(check_id: str) -> tuple[str, str]:
    """Pick the ``(category_id, label)`` pair for an inspection_id."""
    for prefix, cat_id, label in _PREFIX_CATEGORIES:
        if check_id.startswith(prefix):
            return cat_id, label
    return "other", "Other"


def _default_severity(check_id: str) -> str:
    """Best-effort default severity for a check. See module docstring."""
    if any(check_id.startswith(p) for p in _ERROR_PREFIXES):
        return "error"
    if any(check_id.startswith(p) for p in _WARNING_PREFIXES):
        return "warning"
    return "advisory"


def build_catalog() -> dict[str, object]:
    """Return the catalog payload in the shape the Rules editor consumes."""
    by_category: dict[str, dict[str, object]] = {}

    # Initialise categories in the declared order so the editor
    # renders them deterministically.
    for _, cat_id, label in _PREFIX_CATEGORIES:
        by_category[cat_id] = {"id": cat_id, "label": label, "checks": []}
    by_category["other"] = {"id": "other", "label": "Other", "checks": []}

    for check_id in sorted(CHECK_NAMES.keys()):
        info = CHECK_NAMES[check_id]
        cat_id, label = _categorise(check_id)
        by_category[cat_id]["checks"].append(  # type: ignore[union-attr]
            {
                "id": check_id,
                "name": info.name,
                "description": info.description,
                "default_severity": _default_severity(check_id),
            }
        )

    # Drop categories with zero checks so the editor doesn't render
    # empty sections for prefixes that aren't represented yet.
    categories = [c for c in by_category.values() if c["checks"]]  # type: ignore[index]

    return {
        "version": 1,
        "generated_by": "packages/engine/scripts/export_check_catalog.py",
        "total_checks": sum(len(c["checks"]) for c in categories),  # type: ignore[arg-type]
        "categories": categories,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ENGINE_ROOT.parent / "app" / "lib" / "rules" / "check-catalog.json",
        help="Where to write the catalog JSON (defaults to packages/app/lib/rules/check-catalog.json).",
    )
    args = parser.parse_args()

    catalog = build_catalog()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(catalog, indent=2, sort_keys=False) + "\n")
    print(
        f"Wrote {catalog['total_checks']} checks across "
        f"{len(catalog['categories'])} categories to {args.out}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
