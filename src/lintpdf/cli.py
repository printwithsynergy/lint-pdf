"""lint-pdf CLI adapters used by local migration orchestration."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lintpdf.analyzers.document import DocumentAnalyzer
from lintpdf.analyzers.metadata import MetadataAnalyzer
from lintpdf.analyzers.metadata_audit import MetadataAuditAnalyzer
from lintpdf.analyzers.page_geometry import PageGeometryAnalyzer
from lintpdf.analyzers.page_geometry_extra import PageGeometryExtraAnalyzer
from lintpdf.codex_adapter import (
    extract_codex_document_via_codex,
    extract_semantic_document_via_codex,
)

if TYPE_CHECKING:
    from lintpdf.analyzers.finding import Finding


def _serialize_finding(finding: Finding) -> dict[str, Any]:
    return {
        "inspection_id": finding.inspection_id,
        "severity": finding.severity.value,
        "message": finding.message,
        "page_num": finding.page_num,
        "details": finding.details,
        "iso_clause": finding.iso_clause,
        "object_id": finding.object_id,
        "object_type": finding.object_type,
        "bbox": list(finding.bbox) if finding.bbox is not None else None,
        "source": finding.source,
        "category": finding.category,
    }


def _run_document_cluster(document: Any, events: list[Any]) -> list[Finding]:
    analyzer = DocumentAnalyzer()
    return analyzer.analyze(document, events)


def _run_page_geometry_cluster(document: Any, events: list[Any]) -> list[Finding]:
    analyzers = [PageGeometryAnalyzer(), PageGeometryExtraAnalyzer()]
    findings: list[Finding] = []
    for analyzer in analyzers:
        findings.extend(analyzer.analyze(document, events))
    return findings


def _run_metadata_cluster(document: Any, events: list[Any]) -> list[Finding]:
    analyzers = [MetadataAnalyzer(), MetadataAuditAnalyzer()]
    findings: list[Finding] = []
    for analyzer in analyzers:
        findings.extend(analyzer.analyze(document, events))
    return findings


def cmd_codex_cluster(args: argparse.Namespace) -> int:
    pdf_path = Path(args.input_pdf)
    pdf_bytes = pdf_path.read_bytes()
    document, events = extract_semantic_document_via_codex(pdf_bytes)
    codex_payload = extract_codex_document_via_codex(pdf_bytes)

    if args.cluster == "document":
        findings = _run_document_cluster(document, events)
    elif args.cluster == "metadata":
        findings = _run_metadata_cluster(document, events)
    else:
        findings = _run_page_geometry_cluster(document, events)

    findings.sort(key=lambda finding: (finding.inspection_id, finding.page_num, finding.message))
    payload = {
        "adapter_path": "codex",
        "cluster": args.cluster,
        "pdf_path": str(pdf_path),
        "codex_schema_version": codex_payload.get("schema_version"),
        "page_count": document.page_count,
        "finding_count": len(findings),
        "findings": [_serialize_finding(finding) for finding in findings],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


_PARITY_CLUSTERS: tuple[str, ...] = ("document", "page-geometry", "metadata")


def _normalize_bbox(bbox: Any) -> list[float] | None:
    if bbox is None:
        return None
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        try:
            return [round(float(v), 4) for v in bbox]
        except (TypeError, ValueError):
            return None
    return None


def _identity_key(finding_dict: dict[str, Any]) -> tuple[Any, ...]:
    return (
        finding_dict.get("inspection_id") or "",
        finding_dict.get("severity") or "",
        finding_dict.get("message") or "",
        int(finding_dict.get("page_num") or 0),
        tuple(finding_dict.get("bbox") or ()),
    )


def _serialize_finding_for_parity(finding: Finding) -> dict[str, Any]:
    return {
        "inspection_id": finding.inspection_id,
        "severity": finding.severity.value,
        "message": finding.message,
        "page_num": finding.page_num,
        "bbox": _normalize_bbox(list(finding.bbox) if finding.bbox is not None else None),
        "iso_clause": finding.iso_clause,
        "object_id": finding.object_id,
        "object_type": finding.object_type,
        "category": finding.category,
        "source": finding.source,
    }


def _run_cluster(cluster: str, document: Any, events: list[Any]) -> list[Finding]:
    if cluster == "document":
        return _run_document_cluster(document, events)
    if cluster == "metadata":
        return _run_metadata_cluster(document, events)
    return _run_page_geometry_cluster(document, events)


def _build_pdf_record(pdf_path: Path, root: Path) -> dict[str, Any]:
    pdf_bytes = pdf_path.read_bytes()
    document, events = extract_semantic_document_via_codex(pdf_bytes)
    codex_payload = extract_codex_document_via_codex(pdf_bytes)
    rel_path = pdf_path.resolve().relative_to(root.resolve()).as_posix()

    clusters: dict[str, dict[str, Any]] = {}
    for cluster in _PARITY_CLUSTERS:
        findings = _run_cluster(cluster, document, events)
        finding_dicts = [_serialize_finding_for_parity(f) for f in findings]
        finding_dicts.sort(key=_identity_key)
        clusters[cluster] = {
            "finding_count": len(finding_dicts),
            "findings": finding_dicts,
        }

    return {
        "path": rel_path,
        "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "page_count": document.page_count,
        "codex_schema_version": codex_payload.get("schema_version"),
        "clusters": clusters,
    }


def _build_corpus_report(root: Path) -> dict[str, Any]:
    pdf_paths = sorted(root.rglob("*.pdf")) + sorted(root.rglob("*.PDF"))
    seen: set[str] = set()
    unique_paths: list[Path] = []
    for path in pdf_paths:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique_paths.append(path)
    unique_paths.sort(key=lambda p: p.resolve().as_posix())

    fixtures: list[dict[str, Any]] = []
    for path in unique_paths:
        fixtures.append(_build_pdf_record(path, root))

    fixtures.sort(key=lambda record: record["path"])
    total_findings = sum(
        cluster_data["finding_count"]
        for record in fixtures
        for cluster_data in record["clusters"].values()
    )
    return {
        "schema_version": "1.0.0",
        "report_kind": "lint-pdf.parity-corpus",
        "root": str(root.resolve()),
        "fixture_count": len(fixtures),
        "clusters": list(_PARITY_CLUSTERS),
        "total_finding_count": total_findings,
        "fixtures": fixtures,
    }


def _diff_payloads(baseline: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    base_fixtures = {f["path"]: f for f in baseline.get("fixtures", [])}
    curr_fixtures = {f["path"]: f for f in current.get("fixtures", [])}

    only_baseline = sorted(set(base_fixtures) - set(curr_fixtures))
    only_current = sorted(set(curr_fixtures) - set(base_fixtures))
    for path in only_baseline:
        diffs.append({"kind": "missing-fixture", "path": path})
    for path in only_current:
        diffs.append({"kind": "new-fixture", "path": path})

    for path in sorted(set(base_fixtures) & set(curr_fixtures)):
        base_clusters = base_fixtures[path].get("clusters", {})
        curr_clusters = curr_fixtures[path].get("clusters", {})
        for cluster in _PARITY_CLUSTERS:
            base_findings = base_clusters.get(cluster, {}).get("findings", [])
            curr_findings = curr_clusters.get(cluster, {}).get("findings", [])
            base_keys = {_identity_key(f) for f in base_findings}
            curr_keys = {_identity_key(f) for f in curr_findings}
            for missing in sorted(base_keys - curr_keys):
                diffs.append(
                    {
                        "kind": "missing-finding",
                        "path": path,
                        "cluster": cluster,
                        "identity": list(missing),
                    }
                )
            for new in sorted(curr_keys - base_keys):
                diffs.append(
                    {
                        "kind": "new-finding",
                        "path": path,
                        "cluster": cluster,
                        "identity": list(new),
                    }
                )
    return diffs


def cmd_parity_corpus(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"parity-corpus: --root must be a directory: {root}", file=sys.stderr)
        return 2

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = _build_corpus_report(root)
    report_for_disk = dict(report)
    report_for_disk["root"] = "<root>"
    payload = json.dumps(report_for_disk, indent=2, sort_keys=True) + "\n"
    output_path.write_text(payload, encoding="utf-8")

    if args.baseline:
        baseline_path = Path(args.baseline).resolve()
        if not baseline_path.exists():
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            baseline_path.write_text(payload, encoding="utf-8")
            print(
                json.dumps(
                    {
                        "status": "baseline-created",
                        "baseline": str(baseline_path),
                        "output": str(output_path),
                        "fixture_count": report["fixture_count"],
                        "total_finding_count": report["total_finding_count"],
                    },
                    indent=2,
                )
            )
            return 0
        baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
        diffs = _diff_payloads(baseline_payload, report_for_disk)
        diff_path = output_path.with_suffix(".diff.json")
        diff_path.write_text(
            json.dumps(
                {
                    "diff_count": len(diffs),
                    "diffs": diffs,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": "ok" if not diffs else "diff",
                    "baseline": str(baseline_path),
                    "output": str(output_path),
                    "diff_path": str(diff_path),
                    "fixture_count": report["fixture_count"],
                    "total_finding_count": report["total_finding_count"],
                    "diff_count": len(diffs),
                },
                indent=2,
            )
        )
        if diffs and args.fail_on_diff:
            return 1
        return 0

    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output_path),
                "fixture_count": report["fixture_count"],
                "total_finding_count": report["total_finding_count"],
            },
            indent=2,
        )
    )
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    """Run `alembic upgrade head` against the configured DATABASE_URL.

    Uses the alembic config bundled inside the lintpdf wheel
    (``lintpdf._migrations``) so callers don't need the upstream repo
    on disk. Reads ``DATABASE_URL`` (or ``LINTPDF_DATABASE_URL``) at
    runtime — the same env wiring used by the running engine.

    Idempotent: running on an already-up-to-date database is a no-op
    single metadata query.
    """
    import importlib.resources

    from alembic import config as alembic_config

    target = args.target or "head"
    ini_path = importlib.resources.files("lintpdf._migrations") / "alembic.ini"
    alembic_config.main(argv=["-c", str(ini_path), "upgrade", target])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lint-pdf")
    sub = parser.add_subparsers(dest="command", required=True)

    codex_cluster = sub.add_parser(
        "codex-cluster",
        help="Run a codex-backed analyzer cluster for local orchestration.",
    )
    codex_cluster.add_argument("input_pdf")
    codex_cluster.add_argument(
        "--cluster",
        choices=["document", "page-geometry", "metadata"],
        default="page-geometry",
        help="Which coherent rule cluster to run with codex-derived semantic data.",
    )
    codex_cluster.set_defaults(func=cmd_codex_cluster)

    parity_corpus = sub.add_parser(
        "parity-corpus",
        help="Run codex-backed analyzers across a corpus and emit a deterministic parity report.",
    )
    parity_corpus.add_argument(
        "--root",
        required=True,
        help="Fixtures root directory; *.pdf files are walked recursively.",
    )
    parity_corpus.add_argument(
        "--output",
        required=True,
        help="Destination JSON path for the parity report.",
    )
    parity_corpus.add_argument(
        "--baseline",
        default=None,
        help="Optional baseline report path. If missing, this run becomes the baseline.",
    )
    parity_corpus.add_argument(
        "--fail-on-diff",
        action="store_true",
        default=True,
        help="Exit non-zero when diffs against baseline are found (default true).",
    )
    parity_corpus.add_argument(
        "--no-fail-on-diff",
        dest="fail_on_diff",
        action="store_false",
        help="Disable non-zero exit on diff (still writes diff report).",
    )
    parity_corpus.set_defaults(func=cmd_parity_corpus)

    migrate = sub.add_parser(
        "migrate",
        help="Run Alembic migrations against the configured DATABASE_URL.",
    )
    migrate.add_argument(
        "--target",
        default="head",
        help="Alembic revision target (default: head).",
    )
    migrate.set_defaults(func=cmd_migrate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
