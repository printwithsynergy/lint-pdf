"""Parser for LintPDF's native JSON import schema.

The native schema is what third-party tools should produce when they
want a lossless round-trip through LintPDF. It's a thin wrapper over
the :class:`~siftpdf.analyzers.finding.Finding` dataclass with
first-class ``capabilities`` and ``source_metadata`` sections.

Canonical shape (see ``docs/import-schema.json``)::

    {
      "schema_version": "1",
      "source": {"tool": "MyTool", "version": "2.1", "profile": "PDF/X-4"},
      "capabilities": {"findings": true, "separations": true, ...},
      "findings": [
        {
          "inspection_id": "MYT-001",
          "severity": "error",
          "message": "Image resolution too low",
          "page_num": 3,
          "bbox": [72.0, 72.0, 144.0, 144.0],
          "object_id": "Im7",
          "object_type": "image",
          "iso_clause": "ISO 15930-7:2010 6.4.1",
          "category": "image",
          "details": {"resolution_dpi": 72}
        }
      ]
    }

Unknown fields are ignored; unknown severities fall back to
``warning`` so callers don't lose data.
"""

from __future__ import annotations

import json
from typing import Any

from ..analyzers.finding import Finding, Severity
from ..api.models import CAPABILITY_KEYS
from .base import ExternalReportParser, ImportedReport, ParserError, normalize_severity


class LintpdfNativeParser(ExternalReportParser):
    """Parse the LintPDF-native import JSON schema."""

    format = "lintpdf_json"
    version = "1"

    def parse(self, payload: bytes) -> ImportedReport:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParserError(f"LintPDF-native JSON is not valid: {exc}") from exc
        if not isinstance(data, dict):
            raise ParserError("LintPDF-native JSON must be an object at the root")

        report = self._new_report()

        source = data.get("source")
        if isinstance(source, dict):
            report.source_metadata = {
                k: v for k, v in source.items() if isinstance(v, (str, int, float, bool))
            }
        report.source_metadata.setdefault("schema_version", str(data.get("schema_version", "1")))

        caps = data.get("capabilities")
        if isinstance(caps, dict):
            for key in CAPABILITY_KEYS:
                if key in caps:
                    report.capabilities[key] = bool(caps[key])

        findings_raw = data.get("findings")
        if findings_raw is None:
            findings_raw = []
        if not isinstance(findings_raw, list):
            raise ParserError("LintPDF-native JSON: 'findings' must be an array")

        for item in findings_raw:
            if not isinstance(item, dict):
                continue
            finding = self._build_finding(item)
            if finding is not None:
                report.findings.append(finding)

        # Always mark findings capability based on whether we actually got any.
        if report.findings:
            report.mark_capability("findings", True)
        elif "findings" not in (caps or {}):
            # Explicit zero-findings payloads are common for clean files;
            # still mark findings as available because the report was valid.
            report.mark_capability("findings", True)

        return report

    # ------------------------------------------------------------------
    def _build_finding(self, item: dict[str, Any]) -> Finding | None:
        message = _as_str(item.get("message"))
        if not message:
            return None

        inspection_id = (
            _as_str(item.get("inspection_id")) or f"EXT-LPDF-{abs(hash(message)) % 100000:05d}"
        )
        if not inspection_id.startswith("EXT-"):
            inspection_id = f"EXT-LPDF-{inspection_id}"

        severity = Severity(normalize_severity(_as_str(item.get("severity"))))

        page_num = item.get("page_num", item.get("page", 0))
        if isinstance(page_num, str) and page_num.strip().isdigit():
            page_num = int(page_num.strip())
        if not isinstance(page_num, int):
            page_num = 0

        bbox_raw = item.get("bbox")
        bbox: tuple[float, float, float, float] | None = None
        if isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) == 4:
            try:
                bbox = tuple(float(v) for v in bbox_raw)  # type: ignore[assignment]
            except (TypeError, ValueError):
                bbox = None

        details_raw = item.get("details")
        details = details_raw if isinstance(details_raw, dict) else {}

        return Finding(
            inspection_id=inspection_id,
            severity=severity,
            message=message,
            page_num=page_num,
            details=details,
            iso_clause=_as_str(item.get("iso_clause")) or "",
            object_id=_as_str(item.get("object_id")),
            object_type=_as_str(item.get("object_type")),
            bbox=bbox,
            source="external:lintpdf",
            category=_as_str(item.get("category")) or "",
        )


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None
