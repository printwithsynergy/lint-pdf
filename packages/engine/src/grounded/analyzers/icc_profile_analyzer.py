"""IccProfileAnalyzer — ICC profile and output intent validation.

Processes SemanticDocument color space and output intent data to detect
ICC profile and output intent issues.

Check IDs:
    GRD_ICC_001 — ICC profile structural validation
    GRD_ICC_002 — ICC profile version compatibility
    GRD_ICC_003 — ICC profile corruption detection
    GRD_ICC_004 — Output intent deep validation
    GRD_ICC_005 — Output intent condition cross-reference
    GRD_ICC_006 — Multiple output intent consistency
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

# Valid component counts for ICCBased color spaces
_VALID_ICC_COMPONENTS = frozenset({1, 3, 4})

# Known output intent subtypes
_KNOWN_SUBTYPES = frozenset({"GTS_PDFX", "GTS_PDFA1", "ISO_PDFE1"})

# Known output condition identifiers
KNOWN_CONDITIONS = frozenset({
    "FOGRA39",
    "FOGRA39L",
    "FOGRA45",
    "FOGRA47",
    "FOGRA51",
    "FOGRA52",
    "FOGRA55",
    "GRACoL2006_Coated1v2",
    "GRACoL2013_CRPC6",
    "SWOP2006_Coated3v2",
    "SWOP2006_Coated5v2",
    "JC200103",
    "CGATS TR 001",
    "CGATS TR 003",
    "CGATS TR 006",
})


class IccProfileAnalyzer(BaseAnalyzer):
    """Analyzer for ICC profile and output intent validation."""

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze ICC profiles and output intents across the document."""
        findings: list[Finding] = []

        # ICC profile checks from page color spaces
        findings.extend(self._check_icc_structure(document))
        findings.extend(self._check_icc_version_compatibility(document))
        findings.extend(self._check_icc_corruption(document))

        # Output intent checks
        findings.extend(self._check_output_intent_validity(document))
        findings.extend(self._check_output_intent_conditions(document))
        findings.extend(self._check_output_intent_consistency(document))

        return findings

    @staticmethod
    def _check_icc_structure(document: SemanticDocument) -> list[Finding]:
        """Validate ICCBased color space component counts (GRD_ICC_001).

        ICCBased color spaces must have 1, 3, or 4 components corresponding
        to Gray, RGB/Lab, or CMYK profiles respectively.
        """
        findings: list[Finding] = []

        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "ICCBased":
                    continue

                if cs.components not in _VALID_ICC_COMPONENTS:
                    findings.append(
                        Finding(
                            inspection_id="GRD_ICC_001",
                            severity=Severity.AGROUND,
                            message=(
                                f"ICCBased color space '{cs_name}' on page "
                                f"{page.page_num} has invalid component count "
                                f"{cs.components} (expected 1, 3, or 4)"
                            ),
                            page_num=page.page_num,
                            details={
                                "color_space_name": cs_name,
                                "components": cs.components,
                                "icc_profile_ref": cs.icc_profile_ref,
                            },
                            iso_clause="ISO 32000-2:2020 8.6.5.5",
                        )
                    )

        return findings

    @staticmethod
    def _check_icc_version_compatibility(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Check ICC profile version compatibility (GRD_ICC_002).

        Reports detected ICC profiles and flags when both v2 and v4 naming
        conventions appear (heuristic based on profile reference names).
        """
        findings: list[Finding] = []
        profile_refs: set[str] = set()

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type == "ICCBased" and cs.icc_profile_ref:
                    profile_refs.add(cs.icc_profile_ref)

        if not profile_refs:
            return findings

        # Heuristic: classify profiles by naming convention
        v2_refs: list[str] = []
        v4_refs: list[str] = []
        for ref in profile_refs:
            ref_lower = ref.lower()
            if "v2" in ref_lower or "icc2" in ref_lower or "2.0" in ref_lower:
                v2_refs.append(ref)
            if "v4" in ref_lower or "icc4" in ref_lower or "4.0" in ref_lower:
                v4_refs.append(ref)

        if v2_refs and v4_refs:
            findings.append(
                Finding(
                    inspection_id="GRD_ICC_002",
                    severity=Severity.ADVISORY,
                    message=(
                        "Document contains both ICC v2 and v4 profile naming "
                        "conventions — verify profile compatibility"
                    ),
                    details={
                        "v2_profiles": sorted(v2_refs),
                        "v4_profiles": sorted(v4_refs),
                        "total_profiles": len(profile_refs),
                    },
                    iso_clause="ICC.1:2022 7.2",
                )
            )
        else:
            findings.append(
                Finding(
                    inspection_id="GRD_ICC_002",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Document references {len(profile_refs)} ICC "
                        f"profile(s): {', '.join(sorted(profile_refs))}"
                    ),
                    details={
                        "profile_refs": sorted(profile_refs),
                        "total_profiles": len(profile_refs),
                    },
                    iso_clause="ICC.1:2022 7.2",
                )
            )

        return findings

    @staticmethod
    def _check_icc_corruption(document: SemanticDocument) -> list[Finding]:
        """Check for missing ICC profile references (GRD_ICC_003).

        An ICCBased color space without a profile reference is potentially
        corrupt or malformed.
        """
        findings: list[Finding] = []

        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "ICCBased":
                    continue

                if not cs.icc_profile_ref:
                    findings.append(
                        Finding(
                            inspection_id="GRD_ICC_003",
                            severity=Severity.AGROUND,
                            message=(
                                f"ICCBased color space '{cs_name}' on page "
                                f"{page.page_num} has no ICC profile reference "
                                f"(potentially corrupt)"
                            ),
                            page_num=page.page_num,
                            details={
                                "color_space_name": cs_name,
                                "components": cs.components,
                            },
                            iso_clause="ISO 32000-2:2020 8.6.5.5",
                        )
                    )

        return findings

    @staticmethod
    def _check_output_intent_validity(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Validate output intent structure (GRD_ICC_004).

        Each OutputIntent dictionary must have required keys "S" (subtype)
        and "OutputConditionIdentifier", and "S" must be a known subtype.
        """
        findings: list[Finding] = []

        for idx, oi in enumerate(document.output_intents):
            subtype = oi.get("S")
            condition_id = oi.get("OutputConditionIdentifier")

            if not subtype:
                findings.append(
                    Finding(
                        inspection_id="GRD_ICC_004",
                        severity=Severity.SQUALL,
                        message=(
                            f"Output intent #{idx + 1} is missing required "
                            f"'S' (subtype) entry"
                        ),
                        details={
                            "intent_index": idx,
                            "intent_keys": list(oi.keys()),
                        },
                        iso_clause="ISO 32000-2:2020 14.11.5",
                    )
                )
            elif subtype not in _KNOWN_SUBTYPES:
                findings.append(
                    Finding(
                        inspection_id="GRD_ICC_004",
                        severity=Severity.SQUALL,
                        message=(
                            f"Output intent #{idx + 1} has unknown subtype "
                            f"'{subtype}' (expected one of "
                            f"{', '.join(sorted(_KNOWN_SUBTYPES))})"
                        ),
                        details={
                            "intent_index": idx,
                            "subtype": subtype,
                            "known_subtypes": sorted(_KNOWN_SUBTYPES),
                        },
                        iso_clause="ISO 32000-2:2020 14.11.5",
                    )
                )

            if not condition_id:
                findings.append(
                    Finding(
                        inspection_id="GRD_ICC_004",
                        severity=Severity.SQUALL,
                        message=(
                            f"Output intent #{idx + 1} is missing required "
                            f"'OutputConditionIdentifier' entry"
                        ),
                        details={
                            "intent_index": idx,
                            "intent_keys": list(oi.keys()),
                        },
                        iso_clause="ISO 32000-2:2020 14.11.5",
                    )
                )

        return findings

    @staticmethod
    def _check_output_intent_conditions(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Cross-reference output condition identifiers (GRD_ICC_005).

        Check OutputConditionIdentifier values against the set of known
        standard conditions (FOGRA, GRACoL, SWOP, etc.).
        """
        findings: list[Finding] = []

        for idx, oi in enumerate(document.output_intents):
            condition_id = oi.get("OutputConditionIdentifier")
            if not condition_id:
                continue

            if condition_id in KNOWN_CONDITIONS:
                findings.append(
                    Finding(
                        inspection_id="GRD_ICC_005",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Output intent #{idx + 1} condition validated: "
                            f"{condition_id}"
                        ),
                        details={
                            "intent_index": idx,
                            "condition_identifier": condition_id,
                        },
                        iso_clause="ISO 32000-2:2020 14.11.5",
                    )
                )
            else:
                findings.append(
                    Finding(
                        inspection_id="GRD_ICC_005",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Output intent #{idx + 1} has unrecognized "
                            f"condition '{condition_id}'"
                        ),
                        details={
                            "intent_index": idx,
                            "condition_identifier": condition_id,
                            "known_conditions": sorted(KNOWN_CONDITIONS),
                        },
                        iso_clause="ISO 32000-2:2020 14.11.5",
                    )
                )

        return findings

    @staticmethod
    def _check_output_intent_consistency(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Check consistency across multiple output intents (GRD_ICC_006).

        When multiple OutputIntents exist, verify they share consistent
        color space information (e.g., all CMYK or all RGB).
        """
        findings: list[Finding] = []

        if len(document.output_intents) < 2:
            return findings

        # Collect color space indicators from each intent
        color_hints: list[str] = []
        for oi in document.output_intents:
            hint = _extract_color_hint(oi)
            color_hints.append(hint)

        # Filter out unknowns for comparison
        known_hints = [h for h in color_hints if h != "unknown"]
        if len(set(known_hints)) > 1:
            findings.append(
                Finding(
                    inspection_id="GRD_ICC_006",
                    severity=Severity.SQUALL,
                    message=(
                        f"Multiple output intents have inconsistent color "
                        f"space types: {', '.join(known_hints)}"
                    ),
                    details={
                        "intent_count": len(document.output_intents),
                        "color_hints": color_hints,
                    },
                    iso_clause="ISO 32000-2:2020 14.11.5",
                )
            )

        return findings


def _extract_color_hint(oi: dict[str, object]) -> str:
    """Extract a color space hint from an output intent dictionary.

    Uses heuristics on OutputConditionIdentifier, Info, and
    DestOutputProfileRef to determine whether the intent targets
    CMYK, RGB, or Gray.
    """
    searchable = " ".join(
        str(oi.get(key, ""))
        for key in ("OutputConditionIdentifier", "Info", "DestOutputProfileRef")
    ).upper()

    if any(term in searchable for term in ("CMYK", "FOGRA", "SWOP", "GRACOL")):
        return "CMYK"
    if any(term in searchable for term in ("RGB", "SRGB")):
        return "RGB"
    if "GRAY" in searchable:
        return "Gray"

    return "unknown"
