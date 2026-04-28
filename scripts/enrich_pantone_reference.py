#!/usr/bin/env python3
"""Cross-reference and enrich pantone_reference.json from a Pantone library CSV.

Parses a pipe-delimited Pantone Complete Library CSV export, compares against
the existing reference database, and produces an enriched JSON with upgraded
Lab values and additional colors.

Usage:
    python -m scripts.enrich_pantone_reference \
        --csv Pantone_Complete_Library.csv \
        --existing src/lintpdf/profiles/icc/pantone_reference.json \
        --output src/lintpdf/profiles/icc/pantone_reference.json \
        --upgrade-threshold 2.0

    # Dry run (report only, no write):
    python -m scripts.enrich_pantone_reference \
        --csv Pantone_Complete_Library.csv \
        --existing src/lintpdf/profiles/icc/pantone_reference.json \
        --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
from datetime import date
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Name normalization (mirrors pantone_manager.py logic)
# ---------------------------------------------------------------------------

_SPACE_COLLAPSE = re.compile(r"\s+")


def normalize_pantone_name(name: str) -> str:
    """Normalize a Pantone name for matching."""
    s = name.strip().upper()
    s = _SPACE_COLLAPSE.sub(" ", s)
    return s


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "Library",
    "Pantone_Name",
    "Hex",
    "R",
    "G",
    "B",
    "C",
    "M",
    "Y",
    "K",
    "L",
    "a",
    "b",
    "Hex_Source",
    "RGB_Source",
    "CMYK_Source",
    "Lab_Source",
]


def parse_csv(csv_path: str | Path) -> list[dict[str, Any]]:
    """Parse the pipe-delimited Pantone CSV into a list of row dicts."""
    rows: list[dict[str, Any]] = []
    path = Path(csv_path)
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="|")
        for row in reader:
            try:
                parsed = {
                    "library": row["Library"].strip(),
                    "name": row["Pantone_Name"].strip(),
                    "lab": (
                        float(row["L"]),
                        float(row["a"]),
                        float(row["b"]),
                    ),
                    "cmyk": (
                        float(row["C"]),
                        float(row["M"]),
                        float(row["Y"]),
                        float(row["K"]),
                    ),
                    "lab_source": row.get("Lab_Source", "").strip(),
                    "cmyk_source": row.get("CMYK_Source", "").strip(),
                }
                rows.append(parsed)
            except (ValueError, KeyError) as exc:
                print(f"  WARN: skipping row {row.get('Pantone_Name', '?')}: {exc}", file=sys.stderr)
    return rows


# ---------------------------------------------------------------------------
# Delta-E (CIE76 — simple Euclidean in Lab)
# ---------------------------------------------------------------------------


def delta_e_76(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
) -> float:
    """CIE76 Delta-E (Euclidean distance in Lab)."""
    dl = lab1[0] - lab2[0]
    da = lab1[1] - lab2[1]
    db = lab1[2] - lab2[2]
    return math.sqrt(dl**2 + da**2 + db**2)


# ---------------------------------------------------------------------------
# Cross-reference logic
# ---------------------------------------------------------------------------

# Default libraries to include in enrichment
DEFAULT_LIBRARIES = [
    "Pantone Formula Guide Coated",
    "Pantone Formula Guide Uncoated",
    "Pantone Color Bridge Coated",
    "Pantone Color Bridge Uncoated",
    "Pantone CMYK Coated",
    "Pantone CMYK Uncoated",
    "Pantone Extended Gamut Coated",
    "Pantone Metallics Coated",
    "Pantone Pastels & Neons Coated",
    "Pantone Pastels & Neons Uncoated",
    "Pantone SkinTone Guide",
    "FHI Cotton TCX",
    "FHI Paper TPG",
    "FHI Polyester TSX",
    "FHI Metallic Shimmers TPM",
    "FHI Nylon TN",
]

# Libraries whose colors already exist in the reference (Formula Guide)
FORMULA_GUIDE_LIBRARIES = {
    "Pantone Formula Guide Coated",
    "Pantone Formula Guide Uncoated",
}

# Color Bridge libraries — CMYK values from these are preferred for cmyk_bridge
COLOR_BRIDGE_LIBRARIES = {
    "Pantone Color Bridge Coated",
    "Pantone Color Bridge Uncoated",
}


def _build_color_bridge_map(
    csv_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build a map from Formula Guide names to Color Bridge CMYK values.

    Maps "PANTONE 485 C" → Color Bridge "PANTONE 485 CP" CMYK values, and
    "PANTONE 485 U" → "PANTONE 485 UP" values.
    """
    bridge_map: dict[str, dict[str, Any]] = {}
    for row in csv_rows:
        if row["library"] not in COLOR_BRIDGE_LIBRARIES:
            continue
        name = row["name"]
        # Convert CP/UP suffix back to C/U for matching
        # "PANTONE 485 CP" → "PANTONE 485 C", "PANTONE 485 UP" → "PANTONE 485 U"
        if name.endswith(" CP"):
            fg_name = name[:-2] + "C"
        elif name.endswith(" UP"):
            fg_name = name[:-2] + "U"
        else:
            continue
        key = normalize_pantone_name(fg_name)
        if key not in bridge_map:
            bridge_map[key] = {
                "cmyk": row["cmyk"],
                "bridge_lab": row["lab"],
            }
    return bridge_map


def cross_reference(
    existing: dict[str, dict[str, Any]],
    csv_rows: list[dict[str, Any]],
    include_libraries: list[str] | None = None,
    upgrade_threshold: float = 2.0,
) -> dict[str, Any]:
    """Cross-reference CSV data against existing reference.

    Returns a dict with:
        - enriched_colors: the merged color database
        - report: comparison statistics
    """
    libs = set(include_libraries or DEFAULT_LIBRARIES)

    # Build normalized lookup from existing data
    existing_norm: dict[str, tuple[str, dict[str, Any]]] = {}
    for orig_name, data in existing.items():
        key = normalize_pantone_name(orig_name)
        existing_norm[key] = (orig_name, data)

    # Build Color Bridge CMYK lookup (always, regardless of library filter)
    bridge_map = _build_color_bridge_map(csv_rows)

    # Group CSV rows by normalized name (first occurrence per library wins)
    csv_by_name: dict[str, dict[str, Any]] = {}
    csv_formula_guide: dict[str, dict[str, Any]] = {}
    for row in csv_rows:
        if row["library"] not in libs:
            continue
        key = normalize_pantone_name(row["name"])
        if key not in csv_by_name:
            csv_by_name[key] = row
        # Track Formula Guide separately for cross-reference
        if row["library"] in FORMULA_GUIDE_LIBRARIES and key not in csv_formula_guide:
            csv_formula_guide[key] = row

    # Phase 1: Cross-reference existing colors against Formula Guide
    matched_deltas: list[float] = []
    upgraded_count = 0
    cmyk_upgraded_count = 0
    missing_from_csv: list[str] = []
    enriched: dict[str, dict[str, Any]] = {}

    for key, (orig_name, data) in existing_norm.items():
        existing_lab = tuple(data["lab"])
        entry: dict[str, Any] = {
            "lab": list(existing_lab),
        }

        # Determine library from suffix
        if orig_name.rstrip().endswith(" C"):
            entry["library"] = "Pantone Formula Guide Coated"
        elif orig_name.rstrip().endswith(" U"):
            entry["library"] = "Pantone Formula Guide Uncoated"

        # Check against CSV Formula Guide for Lab upgrade
        csv_match = csv_formula_guide.get(key)
        if csv_match:
            csv_lab = csv_match["lab"]
            de = delta_e_76(existing_lab, csv_lab)
            matched_deltas.append(de)

            if de >= upgrade_threshold:
                # Upgrade Lab to PANTONE_PUBLISHED
                entry["lab"] = list(csv_lab)
                entry["lab_source"] = "PANTONE_PUBLISHED"
                upgraded_count += 1
            else:
                entry["lab_source"] = "community_measured"
        else:
            missing_from_csv.append(orig_name)
            entry["lab_source"] = "community_measured"

        # CMYK bridge: prefer Color Bridge values, fall back to CSV Formula Guide,
        # then existing values
        bridge = bridge_map.get(key)
        if bridge:
            entry["cmyk_bridge"] = list(bridge["cmyk"])
            entry["cmyk_source"] = "color_bridge"
            cmyk_upgraded_count += 1
        elif csv_match:
            entry["cmyk_bridge"] = list(csv_match["cmyk"])
            entry["cmyk_source"] = "computed_from_lab"
            cmyk_upgraded_count += 1
        elif data.get("cmyk_bridge"):
            entry["cmyk_bridge"] = data["cmyk_bridge"]
            entry["cmyk_source"] = "community_measured"

        enriched[orig_name] = entry

    # Phase 2: Add new colors from CSV
    new_formula_guide = 0
    new_other_library = 0
    library_counts: dict[str, int] = {}

    for key, row in csv_by_name.items():
        if key in existing_norm:
            # Already handled above
            lib = row["library"]
            library_counts[lib] = library_counts.get(lib, 0) + 1
            continue

        # Use the original name from CSV
        color_name = row["name"]
        entry: dict[str, Any] = {
            "lab": list(row["lab"]),
            "library": row["library"],
            "lab_source": "PANTONE_PUBLISHED",
        }

        if row["library"] in FORMULA_GUIDE_LIBRARIES:
            # Prefer Color Bridge CMYK for Formula Guide colors
            bridge = bridge_map.get(key)
            if bridge:
                entry["cmyk_bridge"] = list(bridge["cmyk"])
                entry["cmyk_source"] = "color_bridge"
            else:
                entry["cmyk_bridge"] = list(row["cmyk"])
                entry["cmyk_source"] = "computed_from_lab"
            new_formula_guide += 1
        else:
            # For non-Formula-Guide, include CMYK if available
            if any(v > 0 for v in row["cmyk"]):
                entry["cmyk_bridge"] = list(row["cmyk"])
                entry["cmyk_source"] = "computed_from_lab"
            new_other_library += 1

        enriched[color_name] = entry
        lib = row["library"]
        library_counts[lib] = library_counts.get(lib, 0) + 1

    # Count existing formula guide in library_counts
    for key, (orig_name, _) in existing_norm.items():
        if orig_name.rstrip().endswith(" C"):
            lib = "Pantone Formula Guide Coated"
        elif orig_name.rstrip().endswith(" U"):
            lib = "Pantone Formula Guide Uncoated"
        else:
            lib = "Unknown"
        library_counts[lib] = library_counts.get(lib, 0) + 1

    # Build report
    report: dict[str, Any] = {
        "total_existing": len(existing_norm),
        "total_csv_filtered": len(csv_by_name),
        "total_enriched": len(enriched),
        "matched_count": len(matched_deltas),
        "upgraded_lab_count": upgraded_count,
        "cmyk_upgraded_count": cmyk_upgraded_count,
        "upgrade_threshold": upgrade_threshold,
        "new_formula_guide": new_formula_guide,
        "new_other_library": new_other_library,
        "missing_from_csv": missing_from_csv,
        "missing_from_csv_count": len(missing_from_csv),
        "libraries": dict(sorted(library_counts.items(), key=lambda x: -x[1])),
    }

    if matched_deltas:
        report["delta_e_stats"] = {
            "count": len(matched_deltas),
            "mean": round(statistics.mean(matched_deltas), 2),
            "median": round(statistics.median(matched_deltas), 2),
            "max": round(max(matched_deltas), 2),
            "min": round(min(matched_deltas), 2),
            "stdev": round(statistics.stdev(matched_deltas), 2) if len(matched_deltas) > 1 else 0,
            "histogram": {
                "0-1": sum(1 for d in matched_deltas if d < 1),
                "1-2": sum(1 for d in matched_deltas if 1 <= d < 2),
                "2-5": sum(1 for d in matched_deltas if 2 <= d < 5),
                "5+": sum(1 for d in matched_deltas if d >= 5),
            },
        }

    return {"enriched_colors": enriched, "report": report}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_enriched_json(
    enriched_colors: dict[str, dict[str, Any]],
    report: dict[str, Any],
) -> dict[str, Any]:
    """Build the final JSON structure."""
    # Count Formula Guide colors
    fg_count = sum(
        1
        for c in enriched_colors.values()
        if c.get("library", "").startswith("Pantone Formula Guide")
    )

    return {
        "_meta": {
            "source": "Enriched from Pantone_Complete_Library.csv + community-measured bridge values",
            "license": "Public domain color science measurements — not official Pantone data",
            "count": len(enriched_colors),
            "formula_guide_count": fg_count,
            "last_updated": date.today().isoformat(),
            "libraries": sorted(report.get("libraries", {}).keys()),
        },
        "colors": enriched_colors,
    }


def print_report(report: dict[str, Any]) -> None:
    """Print a human-readable comparison report."""
    print("\n" + "=" * 60)
    print("PANTONE REFERENCE ENRICHMENT REPORT")
    print("=" * 60)

    print(f"\nExisting reference:  {report['total_existing']:,} colors")
    print(f"CSV (filtered):      {report['total_csv_filtered']:,} colors")
    print(f"Enriched total:      {report['total_enriched']:,} colors")

    print(f"\n--- Cross-Reference (Formula Guide) ---")
    print(f"Matched:             {report['matched_count']:,}")
    print(f"Lab upgraded (ΔE ≥ {report['upgrade_threshold']}): {report['upgraded_lab_count']:,}")
    print(f"CMYK upgraded:       {report.get('cmyk_upgraded_count', 'N/A'):,}")
    print(f"New Formula Guide:   {report['new_formula_guide']:,}")
    print(f"New other libraries: {report['new_other_library']:,}")

    if report["missing_from_csv_count"] > 0:
        print(f"\n⚠ Colors in existing ref but NOT in CSV: {report['missing_from_csv_count']}")
        for name in report["missing_from_csv"][:10]:
            print(f"    {name}")
        if report["missing_from_csv_count"] > 10:
            print(f"    ... and {report['missing_from_csv_count'] - 10} more")

    if "delta_e_stats" in report:
        stats = report["delta_e_stats"]
        print(f"\n--- Delta-E Statistics (existing vs CSV Lab) ---")
        print(f"  Count:    {stats['count']}")
        print(f"  Mean:     {stats['mean']}")
        print(f"  Median:   {stats['median']}")
        print(f"  Min:      {stats['min']}")
        print(f"  Max:      {stats['max']}")
        print(f"  StdDev:   {stats['stdev']}")
        hist = stats["histogram"]
        print(f"  ΔE < 1:   {hist['0-1']} ({hist['0-1']/stats['count']*100:.1f}%)")
        print(f"  1 ≤ ΔE < 2: {hist['1-2']} ({hist['1-2']/stats['count']*100:.1f}%)")
        print(f"  2 ≤ ΔE < 5: {hist['2-5']} ({hist['2-5']/stats['count']*100:.1f}%)")
        print(f"  ΔE ≥ 5:   {hist['5+']} ({hist['5+']/stats['count']*100:.1f}%)")

    print(f"\n--- Library Breakdown ---")
    for lib, count in sorted(report.get("libraries", {}).items(), key=lambda x: -x[1]):
        print(f"  {lib:40s} {count:>6,}")

    print("\n" + "=" * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cross-reference and enrich Pantone reference database from CSV export.",
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to Pantone_Complete_Library.csv (pipe-delimited)",
    )
    parser.add_argument(
        "--existing",
        required=True,
        help="Path to existing pantone_reference.json",
    )
    parser.add_argument(
        "--output",
        help="Path to write enriched JSON (omit for --dry-run)",
    )
    parser.add_argument(
        "--report",
        help="Path to write JSON report (optional)",
    )
    parser.add_argument(
        "--upgrade-threshold",
        type=float,
        default=2.0,
        help="Delta-E threshold for upgrading Lab values (default: 2.0)",
    )
    parser.add_argument(
        "--include-libraries",
        help="Comma-separated list of libraries to include (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print report only, do not write output",
    )

    args = parser.parse_args(argv)

    # Parse CSV
    print(f"Parsing CSV: {args.csv}")
    csv_rows = parse_csv(args.csv)
    print(f"  Parsed {len(csv_rows):,} rows")

    # Load existing reference
    print(f"Loading existing reference: {args.existing}")
    with open(args.existing, encoding="utf-8") as f:
        existing_data = json.load(f)
    existing_colors = existing_data.get("colors", {})
    print(f"  Loaded {len(existing_colors):,} colors")

    # Parse library filter
    include_libs = None
    if args.include_libraries:
        include_libs = [lib.strip() for lib in args.include_libraries.split(",")]

    # Cross-reference
    print("\nCross-referencing...")
    result = cross_reference(
        existing_colors,
        csv_rows,
        include_libraries=include_libs,
        upgrade_threshold=args.upgrade_threshold,
    )

    # Print report
    print_report(result["report"])

    # Write report JSON
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(result["report"], f, indent=2)
        print(f"\nReport written to: {args.report}")

    # Write enriched JSON
    if args.dry_run:
        print("\n[DRY RUN] No output written.")
        return 0

    if not args.output:
        print("\nNo --output specified and not --dry-run. Use --output or --dry-run.")
        return 1

    enriched_json = build_enriched_json(result["enriched_colors"], result["report"])
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(enriched_json, f, indent=2, ensure_ascii=False)
    print(f"\nEnriched reference written to: {args.output}")
    print(f"  Total colors: {enriched_json['_meta']['count']:,}")
    print(f"  Formula Guide: {enriched_json['_meta']['formula_guide_count']:,}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
