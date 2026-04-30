"""Generator for the GWG 2022 profile family (T2-GWG01 + T2-GWG02).

Emits one JSON file per substrate x workflow combination into
``packages/engine/src/siftpdf/profiles/builtin/``. Each profile
inherits a common base (PDF/X-4 conformance, GWG check enable list)
and varies the substrate-specific thresholds:

- ``tac_limit``  — total area coverage ceiling for the substrate
- ``min_dpi``    — minimum image resolution (substrate scales)
- ``min_bleed_mm`` — minimum bleed for the workflow
- ``hairline_threshold`` — minimum stroke width for the workflow

The output JSON is deterministic (sorted keys, stable ordering) so
re-running the generator never produces a no-op churn.

Run:

    uv run python scripts/generate_gwg_profiles.py

Pass ``--check`` to assert the on-disk profiles match the generated
output exactly (CI-friendly mode).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROFILES_DIR = Path(__file__).resolve().parent.parent / "src" / "siftpdf" / "profiles" / "builtin"


@dataclass(frozen=True)
class SubstrateSpec:
    slug: str
    label: str
    tac_limit: float
    min_dpi: float
    min_bleed_mm: float
    hairline_threshold: float
    description_suffix: str
    workflow: str = "CMYK"


@dataclass(frozen=True)
class WorkflowSpec:
    slug: str
    label: str
    description: str
    base: SubstrateSpec
    overrides: dict[str, float | str] = field(default_factory=dict)


# 30 commercial-print profiles (T2-GWG01) — sheet-fed offset, web
# offset (heatset / coldset), magazine, newspaper, digital print
# (laser / inkjet / wide-format), large-format / sign-display, plus
# heritage profiles. Each substrate has 5 paper-stock variants where
# meaningful so colour-managed shops can pick a tighter profile.

_SHEETFED = SubstrateSpec(
    slug="sheetfed-offset",
    label="Sheet-fed Offset",
    tac_limit=300.0,
    min_dpi=300.0,
    min_bleed_mm=3.0,
    hairline_threshold=0.25,
    description_suffix="commercial sheet-fed offset, GWG 2022 process control",
)

_WEB_HEATSET = SubstrateSpec(
    slug="web-heatset",
    label="Web-Offset Heatset",
    tac_limit=300.0,
    min_dpi=240.0,
    min_bleed_mm=3.0,
    hairline_threshold=0.30,
    description_suffix="web-offset heatset (commercial web), GWG 2022",
)

_WEB_COLDSET = SubstrateSpec(
    slug="web-coldset",
    label="Web-Offset Coldset",
    tac_limit=240.0,
    min_dpi=200.0,
    min_bleed_mm=3.0,
    hairline_threshold=0.40,
    description_suffix="web-offset coldset (newspaper-style web), GWG 2022",
)

_MAGAZINE = SubstrateSpec(
    slug="magazine-offset",
    label="Magazine Offset",
    tac_limit=300.0,
    min_dpi=300.0,
    min_bleed_mm=3.0,
    hairline_threshold=0.25,
    description_suffix="magazine offset (high-quality coated stock), GWG 2022",
)

_NEWSPAPER = SubstrateSpec(
    slug="newspaper",
    label="Newspaper",
    tac_limit=240.0,
    min_dpi=170.0,
    min_bleed_mm=3.0,
    hairline_threshold=0.40,
    description_suffix="newspaper printing (newsprint stock), GWG 2022",
)

_DIGITAL = SubstrateSpec(
    slug="digital-print",
    label="Digital Print",
    tac_limit=300.0,
    min_dpi=240.0,
    min_bleed_mm=3.0,
    hairline_threshold=0.25,
    description_suffix="digital toner / inkjet press, GWG 2022",
)

_LARGE_FORMAT = SubstrateSpec(
    slug="large-format",
    label="Large Format",
    tac_limit=280.0,
    min_dpi=120.0,
    min_bleed_mm=10.0,
    hairline_threshold=0.50,
    description_suffix="large-format wide-format print, GWG 2022",
)

_SIGN_DISPLAY = SubstrateSpec(
    slug="sign-display",
    label="Sign / Display",
    tac_limit=280.0,
    min_dpi=72.0,
    min_bleed_mm=15.0,
    hairline_threshold=0.75,
    description_suffix="sign and display POS / banner, GWG 2022",
)


def _commercial_print() -> list[WorkflowSpec]:
    """30 GWG-2022 commercial print variants."""
    return [
        # Sheet-fed offset (5 variants)
        WorkflowSpec(
            "sheetfed-offset-coated",
            "Sheet-fed Offset / Coated",
            "Sheet-fed offset on coated stock (Fogra39 / GRACoL).",
            _SHEETFED,
        ),
        WorkflowSpec(
            "sheetfed-offset-coated-light",
            "Sheet-fed Offset / Coated Light",
            "Sheet-fed offset on light coated stock (LWC).",
            _SHEETFED,
            {"tac_limit": 280.0},
        ),
        WorkflowSpec(
            "sheetfed-offset-uncoated",
            "Sheet-fed Offset / Uncoated",
            "Sheet-fed offset on uncoated stock (Fogra47).",
            _SHEETFED,
            {"tac_limit": 280.0},
        ),
        WorkflowSpec(
            "sheetfed-offset-text-bond",
            "Sheet-fed Offset / Text & Bond",
            "Sheet-fed offset on writing / bond stock.",
            _SHEETFED,
            {"tac_limit": 260.0, "min_dpi": 250.0},
        ),
        WorkflowSpec(
            "sheetfed-offset-board",
            "Sheet-fed Offset / Board",
            "Sheet-fed offset on solid bleached / unbleached board.",
            _SHEETFED,
            {"tac_limit": 320.0, "min_bleed_mm": 5.0},
        ),
        # Web offset heatset (5 variants)
        WorkflowSpec(
            "web-heatset-coated",
            "Web Heatset / Coated",
            "Web-offset heatset on coated stock (PSO_LWC_Standard).",
            _WEB_HEATSET,
        ),
        WorkflowSpec(
            "web-heatset-improved",
            "Web Heatset / Improved",
            "Web-offset heatset on improved coated stock (PSO_LWC_Improved).",
            _WEB_HEATSET,
            {"tac_limit": 290.0},
        ),
        WorkflowSpec(
            "web-heatset-mfc",
            "Web Heatset / MFC",
            "Web-offset heatset on machine-finished coated (PSO_MFC).",
            _WEB_HEATSET,
            {"tac_limit": 290.0, "min_dpi": 220.0},
        ),
        WorkflowSpec(
            "web-heatset-snp",
            "Web Heatset / SNP",
            "Web-offset heatset on supercalendered newsprint (PSO_SNP).",
            _WEB_HEATSET,
            {"tac_limit": 240.0, "min_dpi": 180.0},
        ),
        WorkflowSpec(
            "web-heatset-uncoated",
            "Web Heatset / Uncoated",
            "Web-offset heatset on uncoated stock.",
            _WEB_HEATSET,
            {"tac_limit": 260.0},
        ),
        # Web offset coldset (3 variants)
        WorkflowSpec(
            "web-coldset-snp",
            "Web Coldset / SNP",
            "Web-offset coldset on supercalendered newsprint.",
            _WEB_COLDSET,
        ),
        WorkflowSpec(
            "web-coldset-newsprint",
            "Web Coldset / Newsprint",
            "Web-offset coldset on standard newsprint.",
            _WEB_COLDSET,
            {"tac_limit": 220.0, "min_dpi": 170.0},
        ),
        WorkflowSpec(
            "web-coldset-improved",
            "Web Coldset / Improved News",
            "Web-offset coldset on improved newsprint.",
            _WEB_COLDSET,
            {"tac_limit": 240.0},
        ),
        # Magazine (3 variants)
        WorkflowSpec(
            "magazine-glossy",
            "Magazine / Glossy",
            "Magazine offset on high-gloss coated stock.",
            _MAGAZINE,
        ),
        WorkflowSpec(
            "magazine-matte",
            "Magazine / Matte",
            "Magazine offset on matte coated stock.",
            _MAGAZINE,
            {"tac_limit": 290.0},
        ),
        WorkflowSpec(
            "magazine-supplement",
            "Magazine / Supplement",
            "Magazine offset on supplement stock (LWC).",
            _MAGAZINE,
            {"tac_limit": 280.0, "min_dpi": 240.0},
        ),
        # Newspaper (2 variants)
        WorkflowSpec(
            "newspaper-newsprint",
            "Newspaper / Newsprint",
            "Newspaper printing on standard newsprint (ISO 12647-3).",
            _NEWSPAPER,
        ),
        WorkflowSpec(
            "newspaper-improved",
            "Newspaper / Improved News",
            "Newspaper printing on improved newsprint stock.",
            _NEWSPAPER,
            {"tac_limit": 260.0, "min_dpi": 200.0},
        ),
        # Digital print (6 variants)
        WorkflowSpec(
            "digital-toner-coated",
            "Digital Toner / Coated",
            "Digital toner press on coated stock (HP Indigo, Xerox iGen).",
            _DIGITAL,
        ),
        WorkflowSpec(
            "digital-toner-uncoated",
            "Digital Toner / Uncoated",
            "Digital toner press on uncoated stock.",
            _DIGITAL,
            {"tac_limit": 280.0},
        ),
        WorkflowSpec(
            "digital-inkjet-coated",
            "Digital Inkjet / Coated",
            "Digital inkjet press on coated stock (HP PageWide, Canon ProStream).",
            _DIGITAL,
            {"min_dpi": 220.0},
        ),
        WorkflowSpec(
            "digital-inkjet-uncoated",
            "Digital Inkjet / Uncoated",
            "Digital inkjet press on uncoated stock.",
            _DIGITAL,
            {"tac_limit": 260.0, "min_dpi": 200.0},
        ),
        WorkflowSpec(
            "digital-toner-board",
            "Digital Toner / Board",
            "Digital toner press on board / cartonboard.",
            _DIGITAL,
            {"tac_limit": 320.0},
        ),
        WorkflowSpec(
            "digital-on-demand",
            "Digital / On-Demand",
            "Digital print for short-run on-demand jobs.",
            _DIGITAL,
            {"tac_limit": 280.0, "min_dpi": 220.0},
        ),
        # Large format / sign-display (6 variants)
        WorkflowSpec(
            "large-format-photo",
            "Large Format / Photo",
            "Wide-format print for photographic output.",
            _LARGE_FORMAT,
            {"min_dpi": 200.0},
        ),
        WorkflowSpec(
            "large-format-fine-art",
            "Large Format / Fine Art",
            "Wide-format print for fine-art reproduction.",
            _LARGE_FORMAT,
            {"min_dpi": 240.0, "min_bleed_mm": 5.0},
        ),
        WorkflowSpec(
            "large-format-banner",
            "Large Format / Banner",
            "Wide-format banner / vinyl print.",
            _LARGE_FORMAT,
            {"min_dpi": 100.0, "min_bleed_mm": 15.0},
        ),
        WorkflowSpec(
            "sign-display-pos",
            "Sign-Display / POS",
            "Point-of-sale signage / shelf-talkers.",
            _SIGN_DISPLAY,
            {"min_dpi": 100.0},
        ),
        WorkflowSpec(
            "sign-display-billboard",
            "Sign-Display / Billboard",
            "Outdoor billboard / large signage.",
            _SIGN_DISPLAY,
            {"min_dpi": 50.0, "min_bleed_mm": 25.0},
        ),
        WorkflowSpec(
            "sign-display-vehicle",
            "Sign-Display / Vehicle Wrap",
            "Vehicle wrap / outdoor durable.",
            _SIGN_DISPLAY,
            {"min_dpi": 100.0, "min_bleed_mm": 20.0},
        ),
    ]


def _packaging() -> list[WorkflowSpec]:
    """15 GWG-2022 packaging variants (T2-GWG02)."""
    folding_carton = SubstrateSpec(
        slug="packaging-folding-carton",
        label="Packaging / Folding Carton",
        tac_limit=320.0,
        min_dpi=300.0,
        min_bleed_mm=3.0,
        hairline_threshold=0.30,
        description_suffix="folding carton GWG 2022 packaging profile",
    )
    corrugated = SubstrateSpec(
        slug="packaging-corrugated",
        label="Packaging / Corrugated",
        tac_limit=260.0,
        min_dpi=200.0,
        min_bleed_mm=5.0,
        hairline_threshold=0.50,
        description_suffix="corrugated post-print GWG 2022 packaging profile",
    )
    flexo_label = SubstrateSpec(
        slug="packaging-flexo-label",
        label="Packaging / Flexo Label",
        tac_limit=280.0,
        min_dpi=240.0,
        min_bleed_mm=3.0,
        hairline_threshold=0.40,
        description_suffix="flexo-printed label GWG 2022 packaging profile",
    )
    flexo_film = SubstrateSpec(
        slug="packaging-flexo-film",
        label="Packaging / Flexo Film",
        tac_limit=260.0,
        min_dpi=200.0,
        min_bleed_mm=5.0,
        hairline_threshold=0.50,
        description_suffix="flexo-printed flexible film GWG 2022 packaging profile",
    )
    gravure = SubstrateSpec(
        slug="packaging-gravure",
        label="Packaging / Gravure",
        tac_limit=300.0,
        min_dpi=300.0,
        min_bleed_mm=3.0,
        hairline_threshold=0.30,
        description_suffix="gravure-printed packaging GWG 2022 profile",
    )

    return [
        # Folding carton (3 variants)
        WorkflowSpec(
            "packaging-folding-carton-offset",
            "Folding Carton / Offset",
            "Sheet-fed offset on folding carton stock.",
            folding_carton,
        ),
        WorkflowSpec(
            "packaging-folding-carton-digital",
            "Folding Carton / Digital",
            "Digital toner / inkjet on folding carton stock.",
            folding_carton,
            {"min_dpi": 240.0},
        ),
        WorkflowSpec(
            "packaging-folding-carton-flexo",
            "Folding Carton / Flexo",
            "Flexo on folding carton stock.",
            folding_carton,
            {"hairline_threshold": 0.40, "min_dpi": 240.0},
        ),
        # Corrugated (3 variants)
        WorkflowSpec(
            "packaging-corrugated-postprint",
            "Corrugated / Post-Print",
            "Direct flexo on corrugated board (post-print).",
            corrugated,
        ),
        WorkflowSpec(
            "packaging-corrugated-preprint",
            "Corrugated / Pre-Print",
            "Pre-printed liner laminated to corrugated.",
            corrugated,
            {"tac_limit": 280.0, "min_dpi": 240.0},
        ),
        WorkflowSpec(
            "packaging-corrugated-litho-laminate",
            "Corrugated / Litho-Laminate",
            "Litho-laminated (sheet-fed offset on liner) corrugated.",
            corrugated,
            {"tac_limit": 300.0, "min_dpi": 300.0, "hairline_threshold": 0.30},
        ),
        # Flexo label (3 variants)
        WorkflowSpec(
            "packaging-flexo-label-paper",
            "Flexo Label / Paper",
            "Flexo on coated paper labels.",
            flexo_label,
        ),
        WorkflowSpec(
            "packaging-flexo-label-film",
            "Flexo Label / Film",
            "Flexo on synthetic film labels (PP, PE).",
            flexo_label,
            {"min_bleed_mm": 4.0},
        ),
        WorkflowSpec(
            "packaging-flexo-label-clear",
            "Flexo Label / Clear",
            "Flexo on clear-on-clear labels with white underprint.",
            flexo_label,
            {"tac_limit": 260.0, "min_bleed_mm": 4.0},
        ),
        # Flexo film (3 variants)
        WorkflowSpec(
            "packaging-flexo-film-pe", "Flexo Film / PE", "Flexo on polyethylene film.", flexo_film
        ),
        WorkflowSpec(
            "packaging-flexo-film-pp",
            "Flexo Film / PP",
            "Flexo on polypropylene film.",
            flexo_film,
            {"tac_limit": 280.0},
        ),
        WorkflowSpec(
            "packaging-flexo-film-laminate",
            "Flexo Film / Laminate",
            "Flexo on multi-layer laminate film.",
            flexo_film,
            {"tac_limit": 280.0, "min_bleed_mm": 6.0},
        ),
        # Gravure (3 variants)
        WorkflowSpec(
            "packaging-gravure-paper", "Gravure / Paper", "Gravure on paper / paperboard.", gravure
        ),
        WorkflowSpec(
            "packaging-gravure-film",
            "Gravure / Film",
            "Gravure on flexible film substrate.",
            gravure,
            {"tac_limit": 280.0, "min_bleed_mm": 5.0},
        ),
        WorkflowSpec(
            "packaging-gravure-foil",
            "Gravure / Foil",
            "Gravure on metallised foil substrate.",
            gravure,
            {"tac_limit": 280.0, "min_bleed_mm": 5.0, "hairline_threshold": 0.40},
        ),
    ]


def _build_profile(ws: WorkflowSpec) -> dict[str, object]:
    base = ws.base
    thresholds: dict[str, float | str] = {
        "min_dpi": base.min_dpi,
        "max_dpi": 600.0,
        "tac_limit": base.tac_limit,
        "min_bleed_mm": base.min_bleed_mm,
        "hairline_threshold": base.hairline_threshold,
        "small_text_threshold": 6.0,
        "very_small_text_threshold": 4.0,
        "safety_margin_mm": 3.0,
        "max_file_size_mb": 500.0,
        "min_pdf_version": "1.6",
    }
    thresholds.update(ws.overrides)

    return {
        "name": f"GWG 2022 — {ws.label}",
        "description": ws.description,
        "version": "1.0",
        "conformance": "pdfx4",
        "workflow": base.workflow,
        "checks": {
            "enabled": ["LPDF_*", "PDFX4-*"],
            "disabled": ["LPDF_FONT_016", "LPDF_FONT_017"],
            "severity_overrides": {},
        },
        "thresholds": thresholds,
    }


def _filename_for(slug: str) -> str:
    return f"gwg-2022-{slug}.json"


def write_profiles() -> list[Path]:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for ws in _commercial_print() + _packaging():
        target = PROFILES_DIR / _filename_for(ws.slug)
        payload = _build_profile(ws)
        text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
        target.write_text(text, encoding="utf-8")
        written.append(target)
    return written


def check_profiles() -> int:
    diffs: list[str] = []
    for ws in _commercial_print() + _packaging():
        target = PROFILES_DIR / _filename_for(ws.slug)
        expected = json.dumps(_build_profile(ws), indent=2, sort_keys=False) + "\n"
        if not target.exists() or target.read_text(encoding="utf-8") != expected:
            diffs.append(str(target.relative_to(PROFILES_DIR.parent.parent.parent.parent)))
    if diffs:
        print(f"GWG profiles out of sync — {len(diffs)} file(s) drift:", file=sys.stderr)
        for path in diffs:
            print(f"  {path}", file=sys.stderr)
        return 1
    print(f"GWG profiles up-to-date ({len(_commercial_print()) + len(_packaging())} files).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify on-disk profiles match generator output (CI mode).",
    )
    args = parser.parse_args(argv)

    if args.check:
        return check_profiles()

    written = write_profiles()
    print(f"Wrote {len(written)} GWG profiles to {PROFILES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
