"""MetadataAuditAnalyzer — metadata + naming hygiene checks added by
PR-U (audit miss closure).

Two new check IDs:

* ``LPDF_DOC_PDF_VERSION_DATED`` (advisory) — PDF header version
  < 1.4. Profile-independent: many modern prepress workflows
  assume 1.4+ for transparency, 1.6+ for PDF/X-4. The existing
  ``LPDF_DOC_*`` family only flags version mismatches when the
  active profile sets ``min_pdf_version`` / ``max_pdf_version``;
  this fires unconditionally on stale headers.
* ``LPDF_SPOT_NAME_CASE_MIXED`` (advisory) — spot color inventory
  mixes ALL-UPPERCASE names with mixed-case names (e.g. ``/BUFF``
  alongside ``/Lt Beige``, ``/Med Beige``). Inconsistent naming
  hygiene complicates ink-room matching and colour-database
  lookups. Caught by Opus on Amalgam_Catalyst.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.analyzers.base import BaseAnalyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument


# PDF versions below this are considered "dated" for prepress.
_MIN_RECOMMENDED_VERSION = (1, 4)
# Process / dieline / ProcessingStep names we deliberately exclude
# from the case-mix check — they're conventional and aren't intended
# to follow brand-name casing rules.
_EXCLUDED_FROM_CASE_CHECK: frozenset[str] = frozenset(
    {
        "all",
        "none",
        "cyan",
        "magenta",
        "yellow",
        "black",
        "dieline",
        "die_line",
        "cutcontour",
        "cut_contour",
        "cut",
        "trim",
        "diecut",
        "die_cut",
        "cutting",
        "perforating",
        "creasing",
        "crease",
        "kiss_cut",
        "kisscut",
        "score",
        "scoring",
        "foldline",
        "fold_line",
        "varnish",
        "varnishing",
    }
)
# Pantone / DIC / TOYO / HKS prefixes — entire Pantone library uses
# UPPERCASE so its presence shouldn't trigger a case-mix advisory
# against other UPPERCASE custom spots.
_LIBRARY_PREFIXES: tuple[str, ...] = ("PANTONE", "DIC", "TOYO", "HKS", "RAL", "PMS")


class MetadataAuditAnalyzer(BaseAnalyzer):
    """Two metadata hygiene checks (PR-U)."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_pdf_version(document))
        findings.extend(self._check_spot_name_case_mix(document))
        return findings

    @staticmethod
    def _check_pdf_version(document: SemanticDocument) -> list[Finding]:
        version_str = getattr(document, "version", None)
        if not version_str:
            return []
        try:
            major_str, minor_str = str(version_str).split(".", 1)
            current = (int(major_str), int(minor_str))
        except (TypeError, ValueError):
            return []
        if current >= _MIN_RECOMMENDED_VERSION:
            return []
        return [
            Finding(
                inspection_id="LPDF_DOC_PDF_VERSION_DATED",
                severity=Severity.ADVISORY,
                message=(
                    f"PDF header version {version_str} is dated. Many "
                    "modern prepress workflows assume 1.4+ for transparency "
                    "and 1.6+ for PDF/X-4 conformance. Re-export from the "
                    "design tool with a current version target."
                ),
                page_num=0,
                details={
                    "pdf_version": version_str,
                    "min_recommended": ".".join(str(p) for p in _MIN_RECOMMENDED_VERSION),
                },
                category="metadata",
                object_type="document",
            )
        ]

    @staticmethod
    def _check_spot_name_case_mix(document: SemanticDocument) -> list[Finding]:
        # Collect distinct custom-spot names (skip process/dieline/PMS).
        custom_names: list[str] = []
        for page in getattr(document, "pages", None) or []:
            for cs in (getattr(page, "color_spaces", None) or {}).values():
                if getattr(cs, "cs_type", None) not in ("Separation", "DeviceN", "NChannel"):
                    continue
                for raw in getattr(cs, "colorant_names", None) or ():
                    if not raw:
                        continue
                    name = str(raw).strip().lstrip("/").strip()
                    if not name:
                        continue
                    norm = name.lower().replace("-", "_").replace(" ", "_")
                    if norm in _EXCLUDED_FROM_CASE_CHECK:
                        continue
                    upper = name.upper()
                    if any(upper.startswith(p) for p in _LIBRARY_PREFIXES):
                        continue
                    if name not in custom_names:
                        custom_names.append(name)

        if len(custom_names) < 2:
            return []

        all_upper: list[str] = []
        mixed_case: list[str] = []
        for name in custom_names:
            # Strip non-letters to compare casing.
            letters = "".join(c for c in name if c.isalpha())
            if not letters:
                continue
            if letters.isupper():
                all_upper.append(name)
            elif letters != letters.upper() and letters != letters.lower():
                mixed_case.append(name)
            elif letters.islower():
                # Treat all-lower the same as mixed for the purpose of
                # this check (the conflict is "BUFF" vs "Lt Beige" or
                # "buff").
                mixed_case.append(name)

        if not all_upper or not mixed_case:
            return []

        return [
            Finding(
                inspection_id="LPDF_SPOT_NAME_CASE_MIXED",
                severity=Severity.ADVISORY,
                message=(
                    f"Spot inventory mixes ALL-UPPERCASE names "
                    f"({', '.join(all_upper)}) with mixed-case names "
                    f"({', '.join(mixed_case)}). Inconsistent naming "
                    "hygiene complicates ink-room matching and colour-"
                    "database lookups. Pick one casing convention "
                    "across the brand palette."
                ),
                details={
                    "uppercase_names": all_upper,
                    "mixed_case_names": mixed_case,
                },
                category="metadata",
                object_type="document",
            )
        ]
