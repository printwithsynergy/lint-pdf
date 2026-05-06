"""lint-pdf CLI adapters used by local migration orchestration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lintpdf.analyzers.document import DocumentAnalyzer
from lintpdf.analyzers.finding import Finding
from lintpdf.analyzers.metadata import MetadataAnalyzer
from lintpdf.analyzers.metadata_audit import MetadataAuditAnalyzer
from lintpdf.analyzers.page_geometry import PageGeometryAnalyzer
from lintpdf.analyzers.page_geometry_extra import PageGeometryExtraAnalyzer
from lintpdf.codex_adapter import extract_codex_document_via_codex, extract_semantic_document_via_codex


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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
