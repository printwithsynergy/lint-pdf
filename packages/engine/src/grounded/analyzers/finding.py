"""Finding — the universal output of all analyzers and rules.

A Finding represents a single preflight check result: pass or fail,
with severity, message, and traceability to an ISO clause.

Severity levels use nautical-themed brand language:
- aground: Critical spec violation (blocks approval)
- squall: Warning (does not block but should be reviewed)
- advisory: Informational (no action required)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    """Finding severity levels."""

    AGROUND = "aground"
    SQUALL = "squall"
    ADVISORY = "advisory"


@dataclass(frozen=True)
class Finding:
    """A single preflight check result.

    Attributes:
        inspection_id: Unique check identifier (e.g., GRD_IMG_001).
        severity: aground, squall, or advisory.
        message: Human-readable description of the finding.
        page_num: 1-indexed page number, or 0 for document-level.
        details: Additional structured data about the finding.
        iso_clause: ISO standard clause reference (e.g., "ISO 32000-2:2020 8.9").
        object_id: Resource name of the object (e.g., "Im42", "F1").
        object_type: Kind of object ("image", "text", "path", "font").
        bbox: Bounding box in points (x0, y0, x1, y1), or None.
    """

    inspection_id: str
    severity: Severity
    message: str
    page_num: int = 0
    details: dict[str, Any] = field(default_factory=dict)
    iso_clause: str = ""
    object_id: str | None = None
    object_type: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    source: str = "engine"
    category: str = ""
