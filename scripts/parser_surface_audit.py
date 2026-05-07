"""Parser-surface audit for the codex-migrated lint-pdf analyzers.

Confirms that the three analyzers migrated to consume codex output
(`dieline.py`, `dieline_quality.py`, `spot_name_normaliser.py`) carry
zero direct PDF parser imports (pikepdf / pdfminer / pdfplumber /
pymupdf / pypdf / reportlab / lintpdf.parser) and reach PDF facts only
through ``lintpdf.codex_adapter``.

Exits non-zero on any direct parser import in the migrated analyzers.

Usage:
    python scripts/parser_surface_audit.py
    python scripts/parser_surface_audit.py --json reports/parity/parser_surface_audit.json
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER_ROOT = ROOT / "src" / "lintpdf" / "analyzers"

MIGRATED_ANALYZERS: tuple[str, ...] = (
    "dieline.py",
    "dieline_quality.py",
    "spot_name_normaliser.py",
)

BANNED_MODULE_PREFIXES: tuple[str, ...] = (
    "pikepdf",
    "pdfminer",
    "pdfplumber",
    "fitz",
    "pymupdf",
    "pypdf",
    "reportlab",
    "lintpdf.parser",
)

REQUIRED_CODEX_IMPORT = "lintpdf.codex_adapter"


def _is_banned(module: str | None) -> bool:
    if not module:
        return False
    return any(module == prefix or module.startswith(prefix + ".") for prefix in BANNED_MODULE_PREFIXES)


def audit_file(path: Path) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    banned_imports: list[dict[str, object]] = []
    has_codex_adapter = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_banned(alias.name):
                    banned_imports.append(
                        {
                            "kind": "import",
                            "module": alias.name,
                            "line": node.lineno,
                        }
                    )
                if alias.name == REQUIRED_CODEX_IMPORT:
                    has_codex_adapter = True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _is_banned(module):
                banned_imports.append(
                    {
                        "kind": "from-import",
                        "module": module,
                        "names": [alias.name for alias in node.names],
                        "line": node.lineno,
                    }
                )
            if module == REQUIRED_CODEX_IMPORT:
                has_codex_adapter = True

    return {
        "path": path.relative_to(ROOT).as_posix(),
        "banned_imports": banned_imports,
        "uses_codex_adapter": has_codex_adapter,
        "status": "PASS" if not banned_imports and has_codex_adapter else "FAIL",
    }


def build_report() -> dict[str, object]:
    files = []
    for analyzer in MIGRATED_ANALYZERS:
        path = ANALYZER_ROOT / analyzer
        if not path.exists():
            files.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "banned_imports": [],
                    "uses_codex_adapter": False,
                    "status": "MISSING",
                }
            )
            continue
        files.append(audit_file(path))
    overall = "PASS" if all(item["status"] == "PASS" for item in files) else "FAIL"
    return {
        "schema_version": "1.0.0",
        "report_kind": "lint-pdf.parser-surface-audit",
        "migrated_analyzers": list(MIGRATED_ANALYZERS),
        "banned_module_prefixes": list(BANNED_MODULE_PREFIXES),
        "required_codex_import": REQUIRED_CODEX_IMPORT,
        "files": files,
        "status": overall,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=None, help="Optional JSON output path.")
    args = parser.parse_args()

    report = build_report()
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json:
        out = Path(args.json).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")

    print(payload)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
