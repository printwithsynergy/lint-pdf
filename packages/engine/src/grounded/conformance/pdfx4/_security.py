"""PDF/X-4 security checks (PDFX4-063-065).

PDF/X-4 prohibits encryption, security handlers, and permission restrictions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX4"


def validate_security(document: SemanticDocument) -> list[Finding]:
    """Run security conformance checks."""
    findings: list[Finding] = []

    # PDFX4-063: No encryption
    if document.is_encrypted:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-063",
                severity=Severity.ERROR,
                message="Document is encrypted (prohibited in PDF/X-4)",
                iso_clause="ISO 15930-7:2010 6.2.2",
            )
        )

    # PDFX4-064: No security handlers
    encrypt = document.trailer.get("/Encrypt")
    if encrypt is not None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-064",
                severity=Severity.ERROR,
                message="Security handler present in trailer /Encrypt (prohibited in PDF/X-4)",
                iso_clause="ISO 15930-7:2010 6.2.2",
            )
        )

    # PDFX4-065: No permission restrictions
    if isinstance(encrypt, dict):
        perms = encrypt.get("/P")
        if perms is not None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-065",
                    severity=Severity.ERROR,
                    message="Permission restrictions set (prohibited in PDF/X-4)",
                    iso_clause="ISO 15930-7:2010 6.2.2",
                    details={"permissions": perms},
                )
            )

    return findings
