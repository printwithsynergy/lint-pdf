"""Fail CI when a new ``Field(...)`` in api/schemas.py lacks ``description=``.

Phase 1 establishes the rule for *new* schemas; the existing ~108-field
backlog stays as-is until Phase 2 backfills it. This script enforces
that with a baseline counter checked into
``scripts/openapi_descriptions_baseline.txt``: a count of fields without
``description=`` on a known-good revision. If the current count exceeds
the baseline, the build fails.

Run from the engine package root:

    python scripts/check_openapi_descriptions.py

Usage:

  --update-baseline  Regenerate the baseline (do this after a Phase 2
                     backfill PR lands or after intentionally adding
                     new well-described fields).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ENGINE_ROOT / "src" / "siftpdf" / "api" / "schemas.py"
BASELINE_FILE = ENGINE_ROOT / "scripts" / "openapi_descriptions_baseline.txt"

# Match ``Field(...)`` calls — including multi-line. We collapse
# whitespace inside the call to make the description= check robust to
# line-breaks in the source.
_FIELD_CALL_RE = re.compile(r"Field\s*\(\s*(?P<args>.*?)\s*\)", re.DOTALL)


def count_undescribed_fields(source: str) -> int:
    """Return the number of ``Field(...)`` calls that lack ``description=``."""

    undescribed = 0
    for match in _FIELD_CALL_RE.finditer(source):
        args = " ".join(match.group("args").split())
        if "description=" in args:
            continue
        undescribed += 1
    return undescribed


def read_baseline() -> int | None:
    if not BASELINE_FILE.exists():
        return None
    text = BASELINE_FILE.read_text().strip()
    try:
        return int(text)
    except ValueError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Write the current undescribed-field count to the baseline file.",
    )
    args = parser.parse_args(argv)

    if not SCHEMAS.exists():
        print(f"❌ api/schemas.py not found at {SCHEMAS}", file=sys.stderr)
        return 2

    source = SCHEMAS.read_text()
    current = count_undescribed_fields(source)

    if args.update_baseline:
        BASELINE_FILE.write_text(f"{current}\n")
        print(f"✓ openapi-descriptions: baseline updated to {current}")
        return 0

    baseline = read_baseline()
    if baseline is None:
        BASELINE_FILE.write_text(f"{current}\n")
        print(
            f"openapi-descriptions: established baseline at "
            f"{BASELINE_FILE.relative_to(ENGINE_ROOT)} ({current} fields)"
        )
        return 0

    if current > baseline:
        print(
            f"❌ openapi-descriptions: {current} Field(...) calls missing "
            f"`description=` (baseline: {baseline}). New fields must include "
            f"a description so /openapi.json + /redoc surface them."
        )
        return 1

    if current < baseline:
        print(
            f"✓ openapi-descriptions: {current} undescribed fields "
            f"(baseline: {baseline} — DOWN {baseline - current}). Lock in "
            f"the improvement with: python scripts/check_openapi_descriptions.py "
            f"--update-baseline"
        )
        return 0

    print(f"✓ openapi-descriptions: {current} undescribed fields (matches baseline)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
