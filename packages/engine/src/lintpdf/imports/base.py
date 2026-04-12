"""Base classes and types for external preflight report parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..analyzers.finding import Finding
from ..api.models import CAPABILITY_KEYS, default_capabilities


class ParserError(Exception):
    """Raised when an external preflight report cannot be parsed.

    The engine treats this as a user error (HTTP 422) — the caller supplied
    a file we couldn't interpret, not an internal failure.
    """


@dataclass
class ImportedReport:
    """Structured result of parsing a third-party preflight report.

    ``findings`` are ready-to-persist :class:`Finding` instances — parsers
    set ``Finding.source = "external:<parser_name>"`` so downstream code
    (report templates, viewer overlays) can tell imported findings apart
    from engine-produced ones without special-casing.

    ``capabilities`` defaults to only ``{"findings": true, "metadata": true}``
    — other viewer tools (separations, TAC, layers, fonts, images,
    thumbnails) are only marked available when the source format actually
    carries that data. Missing capabilities can be filled in on demand by
    the viewer's fill-capability endpoint.

    ``source_metadata`` captures parser-derived context (source tool name
    and version, profile name, timestamp). It is persisted on the
    ``JobImportedReport`` row for audit / re-parse.
    """

    findings: list[Finding] = field(default_factory=list)
    capabilities: dict[str, bool] = field(default_factory=lambda: default_capabilities(False))
    source_metadata: dict[str, Any] = field(default_factory=dict)
    format: str = ""
    parser_version: str = "1"

    def mark_capability(self, name: str, value: bool = True) -> None:
        """Flag a capability as available (or explicitly unavailable).

        Raises ``ValueError`` for unknown capability keys so typos surface
        at parse time rather than silently producing dead UI.
        """
        if name not in CAPABILITY_KEYS:
            raise ValueError(
                f"Unknown capability {name!r}; expected one of {CAPABILITY_KEYS}"
            )
        self.capabilities[name] = value


class ExternalReportParser(ABC):
    """Abstract base class for third-party preflight report parsers."""

    #: Format token persisted to ``Job.external_format``. Subclasses set this.
    format: str = ""

    #: Parser version — bump when parse output changes materially so we can
    #: re-parse older raw artifacts into the new shape.
    version: str = "1"

    @abstractmethod
    def parse(self, payload: bytes) -> ImportedReport:
        """Parse raw bytes into an :class:`ImportedReport`.

        Implementations MUST raise :class:`ParserError` on invalid input.
        """

    def _new_report(self) -> ImportedReport:
        """Allocate an :class:`ImportedReport` with this parser's identity."""
        return ImportedReport(
            format=self.format,
            parser_version=self.version,
            capabilities=default_capabilities(False),
        )


# Severity words commonly used across third-party tools. Mapped to the
# engine's three-tier severity enum. All unknown strings default to
# ``warning`` so they still surface in reports.
_SEVERITY_WORDS: dict[str, str] = {
    "error": "error",
    "fatal": "error",
    "critical": "error",
    "fail": "error",
    "failure": "error",
    "problem": "error",
    "warning": "warning",
    "warn": "warning",
    "caution": "warning",
    "info": "advisory",
    "information": "advisory",
    "note": "advisory",
    "notice": "advisory",
    "advisory": "advisory",
    "hint": "advisory",
    "sign-off": "advisory",
}


def normalize_severity(raw: str | None) -> str:
    """Map a free-form severity string onto ``error|warning|advisory``."""
    if not raw:
        return "warning"
    return _SEVERITY_WORDS.get(str(raw).strip().lower(), "warning")
