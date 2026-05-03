#!/usr/bin/env python3
"""W7 tripwire: ensure new alembic migrations don't cross the engine ↔ SaaS line.

Classifies every table referenced by a migration against the
``audit/table-scopes.yaml`` source of truth and fails CI if a single
migration touches tables across scopes (e.g. an OSS migration that
adds a column to both ``jobs`` and ``tenant_ai_configs``).

Each new schema change should land in exactly one alembic stream:

* ``engine`` tables → OSS alembic (this repo).
* ``saas`` tables → SaaS alembic (``lint-pdf-saas`` repo).
* ``orphan`` tables → audit follow-up; treat as SaaS for now.

Usage:

    python scripts/check_migration_scope.py [migration_file ...]

When called with no arguments, scans every ``alembic/versions/*.py``
file in the repo. CI runs the no-arg form so a refactor that
introduces a violation in *any* migration (not just the new one)
fails the build.

Exit codes:
    0 — every migration is single-scope (or untouched / pure SQL).
    1 — at least one migration crosses scopes; details on stderr.
    2 — table seen in a migration is not classified in
        table-scopes.yaml (every new table must be classified).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore[import-not-found]
except ImportError:
    print(
        "check_migration_scope.py: PyYAML missing — install with `pip install pyyaml`",
        file=sys.stderr,
    )
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent.parent
SCOPES_PATH = REPO_ROOT / "audit" / "table-scopes.yaml"
VERSIONS_DIR = REPO_ROOT / "alembic" / "versions"

# Alembic ops where the FIRST string arg is the table name.
_TABLE_FIRST_OPS = (
    "create_table",
    "drop_table",
    "rename_table",
    "add_column",
    "drop_column",
    "alter_column",
)
# Ops where the FIRST arg is an index/constraint name and the SECOND
# arg is the table name (or source table for FKs).
_TABLE_SECOND_OPS = (
    "create_index",
    "drop_index",
    "drop_constraint",
    "create_unique_constraint",
    "create_check_constraint",
    "create_primary_key",
    "create_foreign_key",
)
_OP_FIRST_REGEX = re.compile(
    r"op\.(?P<op>" + "|".join(_TABLE_FIRST_OPS) + r")\(\s*['\"](?P<table>[\w_]+)['\"]"
)
_OP_SECOND_REGEX = re.compile(
    r"op\.(?P<op>" + "|".join(_TABLE_SECOND_OPS)
    + r")\(\s*['\"][\w_]+['\"]\s*,\s*['\"](?P<table>[\w_]+)['\"]"
)
# Some ops put the table name as a kw-arg (table_name=...) instead.
_KW_TABLE_REGEX = re.compile(r"table_name\s*=\s*['\"](?P<table>[\w_]+)['\"]")


def _load_scopes() -> dict[str, str]:
    """Return a flat ``{table: scope}`` map from ``table-scopes.yaml``."""
    raw = yaml.safe_load(SCOPES_PATH.read_text())
    flat: dict[str, str] = {}
    for scope, tables in raw.items():
        for t in tables or []:
            flat[t] = scope
    return flat


def _tables_touched(path: Path) -> set[str]:
    """Return the set of table names referenced by ``op.*`` calls."""
    text = path.read_text()
    tables: set[str] = set()
    for m in _OP_FIRST_REGEX.finditer(text):
        tables.add(m.group("table"))
    for m in _OP_SECOND_REGEX.finditer(text):
        tables.add(m.group("table"))
    for m in _KW_TABLE_REGEX.finditer(text):
        tables.add(m.group("table"))
    return tables


def _classify(path: Path, scopes: dict[str, str]) -> tuple[str, set[str], set[str]]:
    """Classify a migration file.

    Returns ``(verdict, tables, unclassified)`` where:
      - ``verdict`` is ``"engine"`` / ``"saas"`` / ``"orphan"`` / ``"mixed"`` /
        ``"empty"`` / ``"unknown"``.
      - ``tables`` is the set of table names referenced.
      - ``unclassified`` is the subset of tables not present in
        ``table-scopes.yaml``.
    """
    tables = _tables_touched(path)
    if not tables:
        return "empty", tables, set()
    unclassified = {t for t in tables if t not in scopes}
    if unclassified:
        return "unknown", tables, unclassified
    distinct_scopes = {scopes[t] for t in tables}
    if len(distinct_scopes) == 1:
        return distinct_scopes.pop(), tables, set()
    # ``orphan`` mixes are tolerated — they exist in historical alembic
    # files that pre-date the extraction. Only ``engine`` × ``saas``
    # crossings are real violations.
    if {"engine", "saas"}.issubset(distinct_scopes):
        return "mixed", tables, set()
    return distinct_scopes.pop(), tables, set()


def main(argv: list[str]) -> int:
    scopes = _load_scopes()
    targets = [Path(a) for a in argv[1:]] if len(argv) > 1 else sorted(VERSIONS_DIR.glob("*.py"))
    if not targets:
        print(f"check_migration_scope.py: no migrations found under {VERSIONS_DIR}")
        return 0

    violations: list[tuple[Path, str, set[str]]] = []
    unclassified_total: set[str] = set()

    for path in targets:
        verdict, tables, unclassified = _classify(path, scopes)
        if verdict == "mixed":
            # NB: only NEW migrations should trip this; historical ones
            # are tolerated via the baseline below.
            violations.append((path, verdict, tables))
        if unclassified:
            unclassified_total.update(unclassified)

    # Historical mixed migrations baseline. Pre-W6 the codebase had a
    # single ``Base`` so any migration that touched today's saas-side
    # tables alongside engine tables shows as ``mixed``. They're frozen
    # history; the tripwire only blocks NEW mixed migrations.
    baseline_path = REPO_ROOT / "scripts" / "migration_scope_baseline.txt"
    baseline = (
        set(baseline_path.read_text().splitlines()) if baseline_path.exists() else set()
    )
    new_violations = [
        (p, v, t) for (p, v, t) in violations if p.name not in baseline
    ]

    if unclassified_total:
        print(
            "check_migration_scope.py: tables seen in migrations but not "
            "classified in audit/table-scopes.yaml — every new table must "
            "be assigned a scope:",
            file=sys.stderr,
        )
        for t in sorted(unclassified_total):
            print(f"  - {t}", file=sys.stderr)
        return 2

    if new_violations:
        print(
            "check_migration_scope.py: NEW alembic migration(s) cross the "
            "engine ↔ SaaS line. Split the migration so each touches "
            "exactly one scope (engine OR saas).",
            file=sys.stderr,
        )
        for p, _v, tables in new_violations:
            print(f"\n  {p.name} touches tables across scopes:", file=sys.stderr)
            for t in sorted(tables):
                scope = scopes.get(t, "unknown")
                print(f"    - {t} ({scope})", file=sys.stderr)
        print(
            "\nTo silence on a historical migration that's already shipped, "
            "add its filename to scripts/migration_scope_baseline.txt.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
