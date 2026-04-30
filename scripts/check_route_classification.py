"""Track FastAPI route classification: SaaS-only vs engine-public.

Phase 2 / Q4-B introduces an opt-in `tags=["x:saas-only"]` marker
on routes that should NOT ship with the OSS engine post-Phase-3
(billing, admin, tenant config, AI-credit accounting, etc.).
Everything else defaults to engine-public.

This script counts how many route files declare the marker and
compares the count to a baseline checked in at
`scripts/route_classification_baseline.txt`. The baseline is
intentionally a floor, not a ceiling — adding more SaaS-only tags
is fine; *removing* one (or accidentally introducing a SaaS-only
route without tagging it) is what we want to surface in review.

Why a floor (not a ceiling): with Q4a-B's "default engine-public"
posture, an unclassified SaaS-coupled route silently leaks into
the OSS extraction. Baseline-as-floor catches removals; combined
with code review for additions, it gives us a forward-only
classification ratchet.

Usage:

    python scripts/check_route_classification.py

  --update-baseline  Regenerate the baseline. Do this after
                     intentionally tagging a new route or
                     intentionally re-classifying.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Where the route source files live.
ROUTES_DIR = Path(__file__).parent.parent / "src" / "siftpdf" / "api" / "routes"

# Where the baseline lives.
BASELINE_FILE = Path(__file__).parent / "route_classification_baseline.txt"

# Pattern: tags=["x:saas-only", ...] OR tags=["..., x:saas-only", ...]
# We use a literal-string match against "x:saas-only" since FastAPI
# tags can be declared in many ways (positional, keyword, on the
# APIRouter or per-route decorator). Counting raw occurrences is
# good enough for a tripwire.
SAAS_ONLY_MARKER = '"x:saas-only"'


def count_saas_only_files() -> tuple[int, list[str]]:
    """Count route files containing the SaaS-only marker.

    Returns:
        (count, list of file basenames that contain the marker)
    """
    files_with_marker: list[str] = []
    for py_file in sorted(ROUTES_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        if SAAS_ONLY_MARKER in content:
            files_with_marker.append(py_file.stem)
    return len(files_with_marker), files_with_marker


def read_baseline() -> int:
    if not BASELINE_FILE.exists():
        return 0
    text = BASELINE_FILE.read_text(encoding="utf-8").strip()
    # Baseline file may have a comment header — first line that
    # parses as int wins.
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            return int(line)
        except ValueError:
            continue
    return 0


def write_baseline(count: int) -> None:
    BASELINE_FILE.write_text(
        "# Route classification baseline (Q4-B / Phase 2).\n"
        "# Number of route files in packages/engine/src/siftpdf/api/routes/\n"
        "# that declare tags=['x:saas-only', ...].\n"
        "#\n"
        "# Regenerate with `python scripts/check_route_classification.py\n"
        "# --update-baseline` after intentionally tagging a new route or\n"
        "# re-classifying.\n"
        f"{count}\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Regenerate the baseline file with the current count.",
    )
    args = parser.parse_args()

    count, files = count_saas_only_files()

    if args.update_baseline:
        write_baseline(count)
        print(
            f"✅ Baseline updated: {count} SaaS-only route file(s).",
        )
        for f in files:
            print(f"    • {f}.py")
        return 0

    baseline = read_baseline()
    if count < baseline:
        print(
            f"❌ SaaS-only route count dropped from {baseline} to {count}.",
            file=sys.stderr,
        )
        print(
            "   A route was either un-tagged or deleted. If intentional,",
            file=sys.stderr,
        )
        print(
            "   regenerate the baseline with",
            file=sys.stderr,
        )
        print(
            "   `python scripts/check_route_classification.py --update-baseline`.",
            file=sys.stderr,
        )
        return 1

    print(
        f"✅ SaaS-only routes: {count} (baseline {baseline}).",
    )
    if count > baseline:
        print(
            f"   Up by {count - baseline}. Lock in via "
            "`python scripts/check_route_classification.py --update-baseline`.",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
