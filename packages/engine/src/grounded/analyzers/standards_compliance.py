"""StandardsComplianceAnalyzer — G7, GRACoL, and ISO 12647 compliance checks.

Validates PDF documents against industry printing standards by inspecting
OutputIntent profiles, TAC limits, and color space usage.

Check IDs:
    GRD_STD_001 — G7 pre-compliance readiness
    GRD_STD_002 — GRACoL compliance validation
    GRD_STD_003 — ISO 12647 compliance validation
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

# G7-compatible profile identifiers
_G7_IDENTIFIERS = frozenset(
    {
        "GRACoL",
        "GRACOL",
        "GRACoL2006",
        "GRACoL2013",
        "SWOP",
        "CGATS TR 006",
        "CGATS TR006",
        "CGATS TR 001",
    }
)

# GRACoL-compatible profile identifiers
_GRACOL_IDENTIFIERS = frozenset(
    {
        "GRACoL",
        "GRACOL",
        "GRACoL2006",
        "GRACoL2013",
        "GRACoL2006_Coated1v2",
        "CGATS TR 006",
        "CGATS TR006",
    }
)

# ISO 12647-2 reference condition identifiers
_ISO_12647_IDENTIFIERS = frozenset(
    {
        "FOGRA39",
        "FOGRA39L",
        "FOGRA51",
        "FOGRA52",
    }
)

# TAC limits
_G7_TAC_LIMIT = 320.0
_GRACOL_TAC_LIMIT = 340.0
_MIN_DOT_THRESHOLD = 0.03  # 3%


class StandardsComplianceAnalyzer(BaseAnalyzer):
    """Analyzer for G7, GRACoL, and ISO 12647 standards compliance."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze document for standards compliance."""
        from grounded.semantic.events import PathPaintingEvent

        findings: list[Finding] = []

        # Compute max TAC from events
        max_tac = 0.0
        max_tac_page = 0
        max_tac_values: tuple[float, ...] = ()

        # Track light CMYK fills for min dot check
        light_fills: list[dict[str, object]] = []

        for event in events:
            if isinstance(event, PathPaintingEvent):
                # Check fill TAC
                if event.fill and event.fill_color_space == "DeviceCMYK":
                    vals = event.fill_color_values
                    if len(vals) == 4:
                        tac = sum(vals) * 100.0
                        if tac > max_tac:
                            max_tac = tac
                            max_tac_page = event.page_num
                            max_tac_values = vals

                        # Check for light CMYK values (min dot)
                        for i, v in enumerate(vals):
                            if 0 < v < _MIN_DOT_THRESHOLD:
                                light_fills.append(
                                    {
                                        "page_num": event.page_num,
                                        "channel": ["C", "M", "Y", "K"][i],
                                        "value": v,
                                        "color_values": list(vals),
                                    }
                                )

                # Check stroke TAC
                if event.stroke and event.stroke_color_space == "DeviceCMYK":
                    vals = event.stroke_color_values
                    if len(vals) == 4:
                        tac = sum(vals) * 100.0
                        if tac > max_tac:
                            max_tac = tac
                            max_tac_page = event.page_num
                            max_tac_values = vals

        # GRD_STD_001: G7 pre-compliance
        findings.extend(self._check_g7_compliance(document, max_tac, max_tac_page, max_tac_values))

        # GRD_STD_002: GRACoL compliance
        findings.extend(
            self._check_gracol_compliance(
                document, max_tac, max_tac_page, max_tac_values, light_fills
            )
        )

        # GRD_STD_003: ISO 12647 compliance
        findings.extend(self._check_iso_12647_compliance(document))

        return findings

    @staticmethod
    def _find_profile_match(
        output_intents: list[dict[str, object]],
        identifiers: frozenset[str],
    ) -> str | None:
        """Search OutputIntents for a matching profile identifier.

        Returns the matched identifier string, or None.
        """
        for oi in output_intents:
            for key in (
                "/OutputConditionIdentifier",
                "/Info",
                "/DestOutputProfileRef",
                "/RegistryName",
            ):
                val = str(oi.get(key, ""))
                for ident in identifiers:
                    if ident.upper() in val.upper():
                        return ident
        return None

    def _check_g7_compliance(
        self,
        document: SemanticDocument,
        max_tac: float,
        max_tac_page: int,
        max_tac_values: tuple[float, ...],
    ) -> list[Finding]:
        """GRD_STD_001: G7 pre-compliance readiness check."""
        findings: list[Finding] = []

        matched_profile = self._find_profile_match(document.output_intents, _G7_IDENTIFIERS)
        has_g7_profile = matched_profile is not None
        tac_compliant = max_tac <= _G7_TAC_LIMIT

        if not has_g7_profile:
            findings.append(
                Finding(
                    inspection_id="GRD_STD_001",
                    severity=Severity.WARNING,
                    message=(
                        "G7 pre-compliance: No G7-compatible OutputIntent profile found "
                        "(expected GRACoL or SWOP identifier)"
                    ),
                    details={
                        "output_intent_count": len(document.output_intents),
                        "g7_profile_found": False,
                    },
                )
            )
        else:
            findings.append(
                Finding(
                    inspection_id="GRD_STD_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"G7 pre-compliance: G7-compatible profile '{matched_profile}' "
                        f"found in OutputIntent"
                    ),
                    details={
                        "matched_profile": matched_profile,
                        "g7_profile_found": True,
                    },
                )
            )

        if not tac_compliant:
            findings.append(
                Finding(
                    inspection_id="GRD_STD_001",
                    severity=Severity.WARNING,
                    message=(
                        f"G7 pre-compliance: TAC {max_tac:.0f}% exceeds G7 limit "
                        f"of {_G7_TAC_LIMIT:.0f}% on page {max_tac_page}"
                    ),
                    page_num=max_tac_page,
                    details={
                        "max_tac": max_tac,
                        "tac_limit": _G7_TAC_LIMIT,
                        "color_values": list(max_tac_values),
                    },
                )
            )
        elif max_tac > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_STD_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"G7 pre-compliance: TAC {max_tac:.0f}% is within G7 limit "
                        f"of {_G7_TAC_LIMIT:.0f}%"
                    ),
                    details={
                        "max_tac": max_tac,
                        "tac_limit": _G7_TAC_LIMIT,
                    },
                )
            )

        return findings

    def _check_gracol_compliance(
        self,
        document: SemanticDocument,
        max_tac: float,
        max_tac_page: int,
        max_tac_values: tuple[float, ...],
        light_fills: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_STD_002: GRACoL compliance validation."""
        findings: list[Finding] = []

        matched_profile = self._find_profile_match(document.output_intents, _GRACOL_IDENTIFIERS)
        has_gracol_profile = matched_profile is not None

        if not has_gracol_profile:
            findings.append(
                Finding(
                    inspection_id="GRD_STD_002",
                    severity=Severity.WARNING,
                    message=("GRACoL compliance: No GRACoL-compatible OutputIntent profile found"),
                    details={
                        "output_intent_count": len(document.output_intents),
                        "gracol_profile_found": False,
                    },
                )
            )
        else:
            findings.append(
                Finding(
                    inspection_id="GRD_STD_002",
                    severity=Severity.ADVISORY,
                    message=(
                        f"GRACoL compliance: GRACoL profile '{matched_profile}' "
                        f"found in OutputIntent"
                    ),
                    details={
                        "matched_profile": matched_profile,
                        "gracol_profile_found": True,
                    },
                )
            )

        # TAC check for GRACoL 2006 (340%)
        if max_tac > _GRACOL_TAC_LIMIT:
            findings.append(
                Finding(
                    inspection_id="GRD_STD_002",
                    severity=Severity.WARNING,
                    message=(
                        f"GRACoL compliance: TAC {max_tac:.0f}% exceeds GRACoL 2006 limit "
                        f"of {_GRACOL_TAC_LIMIT:.0f}% on page {max_tac_page}"
                    ),
                    page_num=max_tac_page,
                    details={
                        "max_tac": max_tac,
                        "tac_limit": _GRACOL_TAC_LIMIT,
                        "color_values": list(max_tac_values),
                    },
                )
            )

        # Min dot check: light CMYK values below 3%
        if light_fills:
            first = light_fills[0]
            findings.append(
                Finding(
                    inspection_id="GRD_STD_002",
                    severity=Severity.WARNING,
                    message=(
                        f"GRACoL compliance: CMYK {first['channel']} channel value "
                        f"{float(first['value']) * 100:.1f}% is below {_MIN_DOT_THRESHOLD * 100:.0f}% "  # type: ignore[arg-type]
                        f"minimum dot on page {first['page_num']} "
                        f"({len(light_fills)} occurrence(s) total)"
                    ),
                    page_num=int(first["page_num"]),  # type: ignore[arg-type]
                    details={
                        "min_dot_threshold": _MIN_DOT_THRESHOLD,
                        "occurrences": len(light_fills),
                        "first_value": first["value"],
                        "first_channel": first["channel"],
                    },
                )
            )

        return findings

    @staticmethod
    def _check_iso_12647_compliance(
        document: SemanticDocument,
    ) -> list[Finding]:
        """GRD_STD_003: ISO 12647 compliance validation."""
        findings: list[Finding] = []

        # Check OutputIntents for ISO 12647-2 reference conditions
        matched_condition: str | None = None
        for oi in document.output_intents:
            for key in (
                "/OutputConditionIdentifier",
                "/Info",
                "/DestOutputProfileRef",
                "/RegistryName",
            ):
                val = str(oi.get(key, ""))
                for ident in _ISO_12647_IDENTIFIERS:
                    if ident.upper() in val.upper():
                        matched_condition = ident
                        break
                if matched_condition:
                    break
            if matched_condition:
                break

        if not document.output_intents:
            findings.append(
                Finding(
                    inspection_id="GRD_STD_003",
                    severity=Severity.WARNING,
                    message=(
                        "ISO 12647 compliance: No OutputIntent defined; "
                        "cannot validate against ISO 12647-2 reference conditions"
                    ),
                    details={
                        "iso_12647_compliant": False,
                        "reason": "no_output_intent",
                    },
                    iso_clause="ISO 12647-2",
                )
            )
        elif matched_condition is None:
            findings.append(
                Finding(
                    inspection_id="GRD_STD_003",
                    severity=Severity.WARNING,
                    message=(
                        "ISO 12647 compliance: OutputIntent ICC profile does not match "
                        "known ISO 12647-2 reference conditions "
                        "(expected FOGRA39, FOGRA51, or FOGRA52)"
                    ),
                    details={
                        "iso_12647_compliant": False,
                        "reason": "no_matching_reference_condition",
                        "output_intent_count": len(document.output_intents),
                    },
                    iso_clause="ISO 12647-2",
                )
            )
        else:
            findings.append(
                Finding(
                    inspection_id="GRD_STD_003",
                    severity=Severity.ADVISORY,
                    message=(
                        f"ISO 12647 compliance: OutputIntent matches ISO 12647-2 "
                        f"reference condition '{matched_condition}'"
                    ),
                    details={
                        "iso_12647_compliant": True,
                        "matched_condition": matched_condition,
                    },
                    iso_clause="ISO 12647-2",
                )
            )

        return findings
