"""Regulatory reference registry.

Maintains a registry of regulatory references (FDA, EU, GHS, etc.)
with their current status, effective dates, and links to the checks
that enforce them.

Each regulatory reference tracks:
- Standard/regulation name and version
- Effective date and sunset date
- Status (active, draft, superseded, withdrawn)
- Linked check IDs that implement the requirement
- Source URL for the regulation text
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


class RegulatoryStatus(StrEnum):
    ACTIVE = "active"
    DRAFT = "draft"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"


@dataclass
class RegulatoryReference:
    """A regulatory reference record."""

    id: str  # e.g., "FDA-CFR-21-211"
    name: str
    authority: str  # e.g., "FDA", "EU", "ISO"
    version: str = ""
    status: RegulatoryStatus = RegulatoryStatus.ACTIVE
    effective_date: date | None = None
    sunset_date: date | None = None
    linked_checks: list[str] = field(default_factory=list)
    source_url: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class RegulatoryRegistry:
    """Registry of regulatory references and their currency status."""

    def __init__(self) -> None:
        self._refs: dict[str, RegulatoryReference] = {}
        self._load_builtin()

    def get(self, ref_id: str) -> RegulatoryReference | None:
        return self._refs.get(ref_id)

    def list_active(self, authority: str | None = None) -> list[RegulatoryReference]:
        refs = [r for r in self._refs.values() if r.status == RegulatoryStatus.ACTIVE]
        if authority:
            refs = [r for r in refs if r.authority.upper() == authority.upper()]
        return refs

    def list_by_check(self, check_id: str) -> list[RegulatoryReference]:
        return [r for r in self._refs.values() if check_id in r.linked_checks]

    def register(self, ref: RegulatoryReference) -> None:
        self._refs[ref.id] = ref

    def _load_builtin(self) -> None:
        """Load built-in regulatory references."""
        builtins = [
            RegulatoryReference(
                id="FDA-21-CFR-211",
                name="FDA 21 CFR Part 211 - cGMP for Finished Pharmaceuticals",
                authority="FDA",
                version="2024",
                status=RegulatoryStatus.ACTIVE,
                linked_checks=[
                    "AI_FDA_001",
                    "AI_FDA_002",
                    "AI_FDA_003",
                    "AI_FDA_004",
                    "AI_FDA_005",
                ],
                description="Current Good Manufacturing Practice for pharma labeling",
            ),
            RegulatoryReference(
                id="EU-1169-2011",
                name="EU Regulation 1169/2011 - Food Information to Consumers",
                authority="EU",
                version="2011",
                status=RegulatoryStatus.ACTIVE,
                linked_checks=["AI_EU1169_001", "AI_EU1169_002", "AI_EU1169_003"],
                description="Food labeling requirements for EU market",
            ),
            RegulatoryReference(
                id="GHS-REV9",
                name="GHS Revision 9 - Globally Harmonized System",
                authority="UN",
                version="Rev.9 (2021)",
                status=RegulatoryStatus.ACTIVE,
                linked_checks=[
                    "AI_GHS_001",
                    "AI_GHS_002",
                    "AI_GHS_003",
                    "AI_GHS_004",
                    "AI_GHS_005",
                    "AI_GHS_006",
                    "AI_GHS_007",
                    "AI_GHS_008",
                ],
                description="Chemical classification and labeling",
            ),
            RegulatoryReference(
                id="EU-FMD-2016-161",
                name="EU Falsified Medicines Directive 2016/161",
                authority="EU",
                version="2016",
                status=RegulatoryStatus.ACTIVE,
                linked_checks=["GRD_BARCODE_023"],
                description="Anti-tampering and serialization requirements",
            ),
            RegulatoryReference(
                id="FDA-UDI",
                name="FDA Unique Device Identification (UDI)",
                authority="FDA",
                version="2023",
                status=RegulatoryStatus.ACTIVE,
                linked_checks=["GRD_BARCODE_022"],
                description="Medical device barcode labeling requirements",
            ),
            RegulatoryReference(
                id="ISO-15416-2016",
                name="ISO/IEC 15416:2016 - Bar Code Print Quality Test",
                authority="ISO",
                version="2016",
                status=RegulatoryStatus.ACTIVE,
                linked_checks=[
                    "GRD_BARCODE_005",
                    "GRD_BARCODE_007",
                    "GRD_BARCODE_008",
                    "GRD_BARCODE_010",
                    "GRD_BARCODE_012",
                    "GRD_BARCODE_013",
                ],
                description="Linear barcode print quality grading specification",
            ),
            RegulatoryReference(
                id="ISO-15415-2011",
                name="ISO/IEC 15415:2011 - 2D Symbol Print Quality",
                authority="ISO",
                version="2011",
                status=RegulatoryStatus.ACTIVE,
                linked_checks=["GRD_BARCODE_014", "GRD_BARCODE_016", "GRD_BARCODE_017"],
                description="2D barcode print quality grading specification",
            ),
            RegulatoryReference(
                id="ISO-15930-4",
                name="ISO 15930-4:2003 - PDF/X-1a",
                authority="ISO",
                version="2003",
                status=RegulatoryStatus.ACTIVE,
                linked_checks=[f"PDFX1A-{i:03d}" for i in range(1, 46)],
                description="PDF/X-1a conformance standard",
            ),
            RegulatoryReference(
                id="ISO-15930-7",
                name="ISO 15930-7:2010 - PDF/X-4",
                authority="ISO",
                version="2010",
                status=RegulatoryStatus.ACTIVE,
                linked_checks=[f"PDFX4-{i:03d}" for i in range(1, 93)],
                description="PDF/X-4 conformance standard",
            ),
            RegulatoryReference(
                id="ISO-19005",
                name="ISO 19005 - PDF/A",
                authority="ISO",
                version="2005-2020",
                status=RegulatoryStatus.ACTIVE,
                linked_checks=[f"PDFA-{i:03d}" for i in range(1, 41)],
                description="PDF for long-term archival",
            ),
            RegulatoryReference(
                id="AI-PHARMA-001",
                name="Pharmaceutical Labeling Compliance",
                authority="FDA",
                status=RegulatoryStatus.ACTIVE,
                linked_checks=["AI_PHARMA_001", "AI_PHARMA_002", "AI_PHARMA_003", "AI_PHARMA_004"],
                description="AI-powered pharmaceutical label validation",
            ),
        ]
        for ref in builtins:
            self._refs[ref.id] = ref
