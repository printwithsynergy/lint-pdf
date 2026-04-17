"""IccProfileAnalyzer — ICC profile and output intent validation.

Processes SemanticDocument color space and output intent data to detect
ICC profile and output intent issues.

Check IDs:
    LPDF_ICC_001 — ICC profile structural validation
    LPDF_ICC_002 — ICC profile version compatibility
    LPDF_ICC_003 — ICC profile corruption detection
    LPDF_ICC_004 — Output intent deep validation
    LPDF_ICC_005 — Output intent condition cross-reference
    LPDF_ICC_006 — Multiple output intent consistency
    LPDF_ICC_007 — Required ICC tag validation
    LPDF_ICC_008 — Rendering intent consistency
    LPDF_ICC_009 — PCS illuminant validation (D50 check)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

# Valid component counts for ICCBased color spaces
_VALID_ICC_COMPONENTS = frozenset({1, 3, 4})

# Known output intent subtypes
_KNOWN_SUBTYPES = frozenset({"GTS_PDFX", "GTS_PDFA1", "ISO_PDFE1"})

# Known output condition identifiers
KNOWN_CONDITIONS = frozenset(
    {
        # ECI / Europe
        "FOGRA39",
        "FOGRA39L",
        "FOGRA45",
        "FOGRA47",
        "FOGRA51",
        "FOGRA52",
        "FOGRA53",
        "FOGRA54",
        "FOGRA55",
        "FOGRA56",
        "FOGRA57",
        "FOGRA58",
        "FOGRA59",
        # IDEAlliance / North America
        "GRACoL2006_Coated1v2",
        "GRACoL2013_CRPC6",
        "SWOP2006_Coated3v2",
        "SWOP2006_Coated5v2",
        "SWOP2013_CRPC5",
        "GRACoL2013UNC_CRPC3",
        # CGATS / CRPC characterization datasets
        "CGATS TR 001",
        "CGATS TR 003",
        "CGATS TR 006",
        "CRPC1",
        "CRPC2",
        "CRPC3",
        "CRPC4",
        "CRPC5",
        "CRPC6",
        "CRPC7",
        # Japan
        "JC200103",
        "Japan Color 2001 Coated",
        "Japan Color 2002 Newspaper",
        "Japan Color 2003 Web Coated",
        "Japan Color 2011 Coated",
        # ECG / Extended Gamut
        "XCMYK",
        "XCMYK_2017",
        # North America newspaper
        "SNAP 2007",
        "IFRA26",
    }
)


class IccProfileAnalyzer(BaseAnalyzer):
    """Analyzer for ICC profile and output intent validation."""

    def __init__(self, icc_profile_bytes_map: dict[str, bytes] | None = None) -> None:
        """Initialize with optional ICC profile binary data.

        Args:
            icc_profile_bytes_map: Map of profile ref → raw bytes for deep
                validation. When available, enables tag directory parsing
                and PCS illuminant checks.
        """
        self._profile_bytes = icc_profile_bytes_map or {}

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

        # Deep ICC binary checks (when profile bytes available)
        findings.extend(self._check_required_tags(document))
        findings.extend(self._check_rendering_intent(document))
        findings.extend(self._check_pcs_illuminant(document))

        # Output intent checks
        findings.extend(self._check_output_intent_validity(document))
        findings.extend(self._check_output_intent_conditions(document))
        findings.extend(self._check_output_intent_consistency(document))

        return findings

    @staticmethod
    def _check_icc_structure(document: SemanticDocument) -> list[Finding]:
        """Validate ICCBased color space component counts (LPDF_ICC_001).

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
                            inspection_id="LPDF_ICC_001",
                            severity=Severity.ERROR,
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
        """Check ICC profile version compatibility (LPDF_ICC_002).

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
                    inspection_id="LPDF_ICC_002",
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
                    inspection_id="LPDF_ICC_002",
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
        """Check for missing ICC profile references (LPDF_ICC_003).

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
                            inspection_id="LPDF_ICC_003",
                            severity=Severity.ERROR,
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
        """Validate output intent structure (LPDF_ICC_004).

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
                        inspection_id="LPDF_ICC_004",
                        severity=Severity.WARNING,
                        message=(
                            f"Output intent #{idx + 1} is missing required 'S' (subtype) entry"
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
                        inspection_id="LPDF_ICC_004",
                        severity=Severity.WARNING,
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
                        inspection_id="LPDF_ICC_004",
                        severity=Severity.WARNING,
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
        """Cross-reference output condition identifiers (LPDF_ICC_005).

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
                        inspection_id="LPDF_ICC_005",
                        severity=Severity.ADVISORY,
                        message=(f"Output intent #{idx + 1} condition validated: {condition_id}"),
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
                        inspection_id="LPDF_ICC_005",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Output intent #{idx + 1} has unrecognized condition '{condition_id}'"
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
        """Check consistency across multiple output intents (LPDF_ICC_006).

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
                    inspection_id="LPDF_ICC_006",
                    severity=Severity.WARNING,
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

    def _check_required_tags(self, document: SemanticDocument) -> list[Finding]:
        """Validate required ICC tags are present (LPDF_ICC_007).

        When ICC profile binary data is available, parses the tag directory
        and verifies mandatory tags per ICC.1:2022 §9.
        """
        from lintpdf.profiles.icc.profile_manager import validate_icc_profile_bytes

        findings: list[Finding] = []

        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "ICCBased" or not cs.icc_profile_ref:
                    continue

                profile_bytes = self._profile_bytes.get(cs.icc_profile_ref)
                if not profile_bytes:
                    continue

                result = validate_icc_profile_bytes(profile_bytes)
                tags_info = result.get("tags", {})
                missing = tags_info.get("required_tags_missing", set())

                if missing:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_ICC_007",
                            severity=Severity.WARNING,
                            message=(
                                f"ICC profile '{cs.icc_profile_ref}' on page "
                                f"{page.page_num} is missing required tag(s): "
                                f"{', '.join(sorted(missing))}"
                            ),
                            page_num=page.page_num,
                            details={
                                "color_space_name": cs_name,
                                "profile_ref": cs.icc_profile_ref,
                                "missing_tags": sorted(missing),
                                "present_tags": sorted(
                                    tags_info.get("required_tags_present", set())
                                ),
                            },
                            iso_clause="ICC.1:2022 9",
                        )
                    )

                # Check for tag directory structural errors
                tag_errors = tags_info.get("errors", [])
                if tag_errors:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_ICC_007",
                            severity=Severity.WARNING,
                            message=(
                                f"ICC profile '{cs.icc_profile_ref}' on page "
                                f"{page.page_num} has tag directory errors: "
                                f"{'; '.join(tag_errors)}"
                            ),
                            page_num=page.page_num,
                            details={
                                "color_space_name": cs_name,
                                "profile_ref": cs.icc_profile_ref,
                                "errors": tag_errors,
                            },
                            iso_clause="ICC.1:2022 7.3",
                        )
                    )

        return findings

    def _check_rendering_intent(
        self,
        document: SemanticDocument,
    ) -> list[Finding]:
        """Check rendering intent consistency (LPDF_ICC_008).

        Compares the rendering intent embedded in ICC profiles against
        what the document specifies for those objects.
        """
        from lintpdf.profiles.icc.profile_manager import validate_icc_profile_bytes

        findings: list[Finding] = []
        seen_intents: dict[str, str] = {}

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "ICCBased" or not cs.icc_profile_ref:
                    continue

                profile_bytes = self._profile_bytes.get(cs.icc_profile_ref)
                if not profile_bytes:
                    continue

                result = validate_icc_profile_bytes(profile_bytes)
                metadata = result.get("metadata", {})
                intent = metadata.get("rendering_intent", "")
                if intent:
                    seen_intents[cs.icc_profile_ref] = intent

        # Report if mixed rendering intents across profiles
        unique_intents = set(seen_intents.values())
        if len(unique_intents) > 1:
            findings.append(
                Finding(
                    inspection_id="LPDF_ICC_008",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Document uses ICC profiles with different rendering "
                        f"intents: {', '.join(sorted(unique_intents))}"
                    ),
                    details={
                        "profiles_and_intents": {
                            ref: intent for ref, intent in sorted(seen_intents.items())
                        },
                    },
                    iso_clause="ICC.1:2022 7.2.15",
                )
            )

        return findings

    def _check_pcs_illuminant(
        self,
        document: SemanticDocument,
    ) -> list[Finding]:
        """Validate PCS illuminant is D50 (LPDF_ICC_009).

        ICC profiles must use D50 (X=0.9642, Y=1.0, Z=0.8249) as PCS
        illuminant per ICC.1:2022 §7.2.16.
        """
        from lintpdf.profiles.icc.profile_manager import validate_icc_profile_bytes

        findings: list[Finding] = []
        checked_refs: set[str] = set()

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "ICCBased" or not cs.icc_profile_ref:
                    continue
                if cs.icc_profile_ref in checked_refs:
                    continue
                checked_refs.add(cs.icc_profile_ref)

                profile_bytes = self._profile_bytes.get(cs.icc_profile_ref)
                if not profile_bytes:
                    continue

                result = validate_icc_profile_bytes(profile_bytes)
                illuminant = result.get("pcs_illuminant")
                illuminant_valid = result.get("pcs_illuminant_valid", True)

                if illuminant and not illuminant_valid:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_ICC_009",
                            severity=Severity.WARNING,
                            message=(
                                f"ICC profile '{cs.icc_profile_ref}' has "
                                f"non-D50 PCS illuminant: X={illuminant['X']}, "
                                f"Y={illuminant['Y']}, Z={illuminant['Z']} "
                                f"(expected X=0.9642, Y=1.0, Z=0.8249)"
                            ),
                            page_num=page.page_num,
                            details={
                                "profile_ref": cs.icc_profile_ref,
                                "pcs_illuminant": illuminant,
                                "expected": {"X": 0.9642, "Y": 1.0, "Z": 0.8249},
                            },
                            iso_clause="ICC.1:2022 7.2.16",
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
