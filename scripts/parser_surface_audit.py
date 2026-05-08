"""Parser-surface audit for lint-pdf.

Two layers:

1. **Migrated analyzers (pre-codex-cluster).** ``dieline.py``,
   ``dieline_quality.py`` and ``spot_name_normaliser.py`` must keep
   importing through ``lintpdf.codex_adapter`` and reach zero direct
   PDF parser modules.

2. **Codex-authoritative renderer surface (post-1.2.0).** Every
   non-export module under ``src/lintpdf/`` must avoid:

   - ``pikepdf.open`` / ``pikepdf.parse_content_stream``
   - ``pdfminer`` / ``fitz`` / ``pymupdf``
   - Ghostscript subprocess invocations (``"gs"`` argv literal)

   Exports (the report writers that emit one-off markup / annotated
   PDFs and the post-render anonymous-metadata sanitiser) are
   exempt — listed in :data:`EXPORT_ALLOWLIST`.

Exits non-zero when either layer fails. Writes a JSON report to
``--json`` if supplied so CI can pin the audit alongside the
parity-corpus baseline.

Usage:
    python scripts/parser_surface_audit.py
    python scripts/parser_surface_audit.py --json reports/parity/parser_surface_audit.json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src" / "lintpdf"
ANALYZER_ROOT = SRC_ROOT / "analyzers"

# ---------------------------------------------------------------------------
# Layer 1 — codex-cluster migrated analyzers (unchanged from 1.0).
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Layer 2 — codex-authoritative renderer surface.
# ---------------------------------------------------------------------------

# Modules whose pikepdf / Ghostscript usage is part of the export
# path (one-off PDF assets — markup / annotated / sanitised) and is
# explicitly exempt from the codex-only enforcement. Paths are
# relative to ``SRC_ROOT`` so the allow-list reads naturally.
EXPORT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "reports/markup_pdf_report.py",
        "reports/annotated_pdf_report.py",
        # service.py is allowed only for the post-export anonymous-metadata
        # sanitiser (`sanitize_pdf_metadata_for_anonymous`); the audit narrows
        # the check to that function below.
        "reports/service.py",
    }
)

# Function names inside otherwise non-export modules where pikepdf usage is allowed.
EXPORT_FUNCTION_ALLOWLIST: dict[str, frozenset[str]] = {
    "reports/service.py": frozenset({"sanitize_pdf_metadata_for_anonymous"}),
}

# Patterns that are forbidden in non-export paths.
PIKEPDF_OPEN_RE = re.compile(r"pikepdf\.\s*(?:Pdf\.\s*)?open\b")
PIKEPDF_PCS_RE = re.compile(r"pikepdf\.\s*parse_content_stream\b")
PDFMINER_IMPORT_RE = re.compile(r"\bimport\s+pdfminer\b|\bfrom\s+pdfminer\b")
FITZ_IMPORT_RE = re.compile(r"\bimport\s+fitz\b|\bfrom\s+fitz\b|\bimport\s+pymupdf\b|\bfrom\s+pymupdf\b")
GS_SUBPROCESS_RE = re.compile(r'subprocess\.\s*(?:run|Popen|call|check_output)\s*\(\s*\[\s*["\']gs["\']')


def _is_banned_module(module: str | None) -> bool:
    if not module:
        return False
    return any(module == prefix or module.startswith(prefix + ".") for prefix in BANNED_MODULE_PREFIXES)


def audit_migrated_analyzer(path: Path) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    banned_imports: list[dict[str, object]] = []
    has_codex_adapter = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_banned_module(alias.name):
                    banned_imports.append(
                        {"kind": "import", "module": alias.name, "line": node.lineno}
                    )
                if alias.name == REQUIRED_CODEX_IMPORT:
                    has_codex_adapter = True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _is_banned_module(module):
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


def _file_is_in_function(source: str, line: int, allowed_functions: frozenset[str]) -> bool:
    """Return True iff ``line`` falls inside one of the named def blocks."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in allowed_functions:
                start = node.lineno
                end = getattr(node, "end_lineno", start)
                if start <= line <= end:
                    return True
    return False


def _attr_chain(node: ast.AST) -> str:
    """Build dotted name for ``foo.bar.baz`` Attribute / Name chains."""
    if isinstance(node, ast.Attribute):
        return f"{_attr_chain(node.value)}.{node.attr}"
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _ast_violations(source: str) -> list[tuple[str, int]]:
    """Return ``(kind, line)`` violations found via AST walking.

    Skips matches that appear only inside string literals (docstrings,
    error messages) since those aren't real call sites.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        # Banned imports of pdfminer / fitz / pymupdf.
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = ""
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("pdfminer"):
                        out.append(("pdfminer", node.lineno))
                    if alias.name in ("fitz", "pymupdf") or alias.name.startswith(
                        ("fitz.", "pymupdf.")
                    ):
                        out.append(("fitz/pymupdf", node.lineno))
            else:
                module = node.module or ""
                if module.startswith("pdfminer"):
                    out.append(("pdfminer", node.lineno))
                if module in ("fitz", "pymupdf") or module.startswith(("fitz.", "pymupdf.")):
                    out.append(("fitz/pymupdf", node.lineno))

        # Banned function calls.
        if isinstance(node, ast.Call):
            chain = _attr_chain(node.func)
            if chain in ("pikepdf.open", "pikepdf.Pdf.open"):
                out.append(("pikepdf.open", node.lineno))
            if chain == "pikepdf.parse_content_stream":
                out.append(("pikepdf.parse_content_stream", node.lineno))
            # subprocess.* calls whose first argv element is "gs".
            if chain in (
                "subprocess.run",
                "subprocess.Popen",
                "subprocess.call",
                "subprocess.check_output",
                "subprocess.check_call",
            ):
                if node.args:
                    first = node.args[0]
                    if isinstance(first, ast.List) and first.elts:
                        head = first.elts[0]
                        if isinstance(head, ast.Constant) and head.value == "gs":
                            out.append(("subprocess gs", node.lineno))

    return out


def audit_renderer_surface(path: Path) -> dict[str, object]:
    """Find banned PDF byte-level invocations in ``path``."""
    rel = path.relative_to(SRC_ROOT).as_posix()
    if rel in EXPORT_ALLOWLIST and rel not in EXPORT_FUNCTION_ALLOWLIST:
        return {"path": path.relative_to(ROOT).as_posix(), "violations": [], "status": "EXEMPT"}

    source = path.read_text(encoding="utf-8")
    function_allow = EXPORT_FUNCTION_ALLOWLIST.get(rel, frozenset())
    raw_lines = source.splitlines()

    violations: list[dict[str, object]] = []
    for kind, line in _ast_violations(source):
        if function_allow and _file_is_in_function(source, line, function_allow):
            continue
        snippet = raw_lines[line - 1] if line - 1 < len(raw_lines) else ""
        if "LINTPDF_EXPORT_PIKEPDF" in snippet:
            continue
        violations.append({"kind": kind, "line": line, "snippet": snippet.strip()})

    return {
        "path": path.relative_to(ROOT).as_posix(),
        "violations": violations,
        "status": "PASS" if not violations else "FAIL",
    }


def build_migrated_report() -> dict[str, object]:
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
        files.append(audit_migrated_analyzer(path))
    overall = "PASS" if all(item["status"] == "PASS" for item in files) else "FAIL"
    return {
        "schema_version": "1.0.0",
        "report_kind": "lint-pdf.parser-surface-audit.migrated-analyzers",
        "migrated_analyzers": list(MIGRATED_ANALYZERS),
        "banned_module_prefixes": list(BANNED_MODULE_PREFIXES),
        "required_codex_import": REQUIRED_CODEX_IMPORT,
        "files": files,
        "status": overall,
    }


def build_renderer_report() -> dict[str, object]:
    files = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        result = audit_renderer_surface(path)
        if result["status"] == "FAIL" or result["status"] == "EXEMPT":
            files.append(result)
    overall = "PASS" if all(item["status"] != "FAIL" for item in files) else "FAIL"
    return {
        "schema_version": "1.0.0",
        "report_kind": "lint-pdf.parser-surface-audit.renderer-surface",
        "export_allowlist": sorted(EXPORT_ALLOWLIST),
        "export_function_allowlist": {
            k: sorted(v) for k, v in EXPORT_FUNCTION_ALLOWLIST.items()
        },
        "banned_patterns": [
            "pikepdf.open",
            "pikepdf.parse_content_stream",
            "pdfminer",
            "fitz/pymupdf",
            "subprocess gs",
        ],
        "files": files,
        "status": overall,
    }


# ---------------------------------------------------------------------------
# Layer 3 — codex-color authority (post-1.4.0).
#
# codex-pdf 1.4.0 absorbed the Pantone reference catalogue + colour
# math + curated semantic spot map. lint-pdf consumes that surface in
# process via :mod:`codex_pdf.color`. The ONLY module allowed to ship
# Pantone string literals or colour-math constants is the thin façade
# that adapts codex back into the analyzer's historical types
# (``lintpdf/profiles/icc/pantone_manager.py``). Anything else
# carrying a hand-rolled Pantone table or colour-math conversion is a
# regression and must be flagged.
# ---------------------------------------------------------------------------

CODEX_COLOR_FACADE = "lintpdf/profiles/icc/pantone_manager.py"
COLOR_AUTHORITY_ALLOWLIST: frozenset[str] = frozenset(
    {
        CODEX_COLOR_FACADE,
        # Test fixtures may reference Pantone names verbatim — they
        # exercise the codex-bridge code path, they don't ship a
        # parallel reference catalogue.
        "tests/fixtures",
        "tests/conftest.py",
    }
)
PANTONE_LITERAL_RE = re.compile(r"['\"]PANTONE\s+[^'\"]+['\"]")
COLOR_MATH_CONSTANT_NAMES: tuple[str, ...] = (
    "PANTONE_REFERENCE",
    "PANTONE_FORMULA_GUIDE",
    "_PANTONE_REFERENCE",
)


def _walk_dict_keys_and_data_values(tree: ast.AST) -> list[tuple[str, int]]:
    """Yield ``(name, line)`` pantone literals appearing in catalogue-shaped data.

    A "catalogue-shaped" usage is:

    * the literal is a key in a ``dict`` literal whose value is itself
      a numeric list/tuple or dict mapping (``"lab"``, ``"cmyk"`` etc.),
      OR
    * the literal is the first element of a tuple whose remaining
      elements are numeric — the legacy ``("PANTONE 485 C", [50, 70, 30])``
      list-of-rows shape.

    Pantone literals that show up in docstrings, error messages,
    ``Field(description=...)`` examples, and other documentation
    contexts are intentionally ignored — they don't act as a parallel
    catalogue, they describe the real one.
    """
    out: list[tuple[str, int]] = []

    def is_pantone_literal(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.upper().startswith("PANTONE "):
                return node.value
        return None

    def has_data_shape(value: ast.AST) -> bool:
        if isinstance(value, ast.Dict):
            for k in value.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    if k.value.lower() in {"lab", "cmyk", "cmyk_bridge", "rgb", "library"}:
                        return True
            return False
        if isinstance(value, (ast.List, ast.Tuple)):
            numeric = sum(
                1
                for item in value.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, (int, float))
            )
            return numeric >= 2
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if key is None:
                    continue
                literal = is_pantone_literal(key)
                if literal and has_data_shape(value):
                    out.append((literal, key.lineno))
        if isinstance(node, ast.Tuple) and len(node.elts) >= 2:
            head = node.elts[0]
            literal = is_pantone_literal(head)
            if literal and any(has_data_shape(elt) for elt in node.elts[1:]):
                out.append((literal, head.lineno))
    return out


def audit_color_authority(path: Path) -> dict[str, object]:
    rel = path.relative_to(ROOT).as_posix()
    if any(rel == entry or rel.startswith(entry + "/") for entry in COLOR_AUTHORITY_ALLOWLIST):
        return {"path": rel, "violations": [], "status": "EXEMPT"}
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {
            "path": rel,
            "violations": [{"kind": "parse-error", "detail": str(exc)}],
            "status": "FAIL",
        }
    raw_lines = source.splitlines()
    violations: list[dict[str, object]] = []

    for literal, line in _walk_dict_keys_and_data_values(tree):
        snippet = raw_lines[line - 1] if line - 1 < len(raw_lines) else ""
        violations.append(
            {
                "kind": "pantone-catalogue-outside-authority",
                "line": line,
                "snippet": snippet.strip(),
                "match": literal,
            }
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in COLOR_MATH_CONSTANT_NAMES:
                    snippet = (
                        raw_lines[target.lineno - 1].strip()
                        if target.lineno - 1 < len(raw_lines)
                        else ""
                    )
                    violations.append(
                        {
                            "kind": "pantone-constant-outside-authority",
                            "line": target.lineno,
                            "snippet": snippet,
                            "constant": target.id,
                        }
                    )
    return {
        "path": rel,
        "violations": violations,
        "status": "PASS" if not violations else "FAIL",
    }


def build_color_authority_report() -> dict[str, object]:
    files: list[dict[str, object]] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        result = audit_color_authority(path)
        if result["status"] == "FAIL" or result["status"] == "EXEMPT":
            files.append(result)
    overall = "PASS" if all(item["status"] != "FAIL" for item in files) else "FAIL"
    return {
        "schema_version": "1.0.0",
        "report_kind": "lint-pdf.parser-surface-audit.color-authority",
        "color_authority_facade": CODEX_COLOR_FACADE,
        "allowlist": sorted(COLOR_AUTHORITY_ALLOWLIST),
        "files": files,
        "status": overall,
    }


def build_combined_report() -> dict[str, object]:
    migrated = build_migrated_report()
    renderer = build_renderer_report()
    color = build_color_authority_report()
    overall = "PASS" if all(
        section["status"] == "PASS" for section in (migrated, renderer, color)
    ) else "FAIL"
    return {
        "schema_version": "1.2.0",
        "report_kind": "lint-pdf.parser-surface-audit",
        "migrated_analyzers": migrated,
        "renderer_surface": renderer,
        "color_authority": color,
        "status": overall,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=None, help="Optional JSON output path.")
    args = parser.parse_args()

    report = build_combined_report()
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json:
        out = Path(args.json).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")

    print(payload)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
