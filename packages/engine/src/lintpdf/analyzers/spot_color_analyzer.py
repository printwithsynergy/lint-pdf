"""SpotColorAnalyzer — spot color and DeviceN color space validation.

Processes SemanticDocument color space data to detect spot color naming,
structural, and consistency issues across pages.

Check IDs:
    LPDF_SPOT_001 — Full spot color inventory
    LPDF_SPOT_002 — Spot color fallback Delta-E validation
    LPDF_SPOT_003 — Spot color naming issues
    LPDF_SPOT_004 — DeviceN structural validation
    LPDF_SPOT_005 — DeviceN process color consistency
    LPDF_SPOT_006 — Pantone not in reference database
    LPDF_SPOT_007 — Unknown spot color name (not in any known library)
    LPDF_SPOT_008 — Spot color alternate space mismatch for color library
    LPDF_SPOT_009 — Duplicate spot color definitions on same page
    LPDF_SPOT_010 — Spot color count exceeds maximum
    LPDF_SPOT_011 — Spot color with zero tint (invisible)
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import PdfColorSpace, SemanticDocument

logger = logging.getLogger(__name__)

# Well-known spot color naming prefixes
_KNOWN_SPOT_PREFIXES = ("PANTONE", "DIC", "TOYO", "HKS")

# All known spot color library prefixes (including RAL)
_ALL_KNOWN_LIBRARY_PREFIXES = ("PANTONE", "HKS", "TOYO", "DIC", "RAL")

# Expected alternate color spaces per library
_LIBRARY_EXPECTED_ALTERNATES: dict[str, set[str]] = {
    "PANTONE": {"DeviceCMYK", "ICCBased"},
    "HKS": {"DeviceCMYK", "ICCBased"},
    "TOYO": {"DeviceCMYK", "ICCBased"},
    "DIC": {"DeviceCMYK", "ICCBased"},
    "RAL": {"DeviceCMYK", "ICCBased", "DeviceRGB"},
}

# Process color names used in DeviceN spaces
_PROCESS_COLOR_NAMES = frozenset({"Cyan", "Magenta", "Yellow", "Black"})

# Pattern for PANTONE names (e.g., "PANTONE 485 C", "PANTONE Reflex Blue CV")
_PANTONE_PATTERN = re.compile(r"^PANTONE\s+.+$", re.IGNORECASE)


class SpotColorAnalyzer(BaseAnalyzer):
    """Analyzer for spot color and DeviceN color space validation.

    Args:
        custom_pantone_data: Customer-uploaded Pantone overrides.
        icc_profile_bytes: ICC profile for accurate CMYK→Lab conversion.
        delta_e_warning: Delta-E threshold for WARNING severity (default 5.0).
        delta_e_advisory: Delta-E threshold for ADVISORY severity (default 2.0).
        max_spot_colors: Maximum number of spot colors before advisory (default 8).
    """

    def __init__(
        self,
        custom_pantone_data: dict[str, Any] | None = None,
        icc_profile_bytes: bytes | None = None,
        delta_e_warning: float = 5.0,
        delta_e_advisory: float = 2.0,
        max_spot_colors: int = 8,
    ) -> None:
        self._custom_pantone_data = custom_pantone_data
        self._icc_profile_bytes = icc_profile_bytes
        self._delta_e_warning = delta_e_warning
        self._delta_e_advisory = delta_e_advisory
        self._max_spot_colors = max_spot_colors

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze spot colors and DeviceN spaces across the document."""
        findings: list[Finding] = []

        findings.extend(self._check_spot_inventory(document))
        findings.extend(self._check_pantone_fallback(document))
        findings.extend(self._check_spot_naming(document))
        findings.extend(self._check_devicen_structure(document))
        findings.extend(self._check_devicen_process_consistency(document))
        findings.extend(self._check_unknown_spot_color(document))
        findings.extend(self._check_alternate_space_mismatch(document))
        findings.extend(self._check_duplicate_spot_definitions(document))
        findings.extend(self._check_spot_color_count(document))
        findings.extend(self._check_zero_tint(document, events))

        return findings

    @staticmethod
    def _check_spot_inventory(  # skipcq: PY-R1000
        document: SemanticDocument,
    ) -> list[Finding]:
        """Build full spot color inventory and check consistency (LPDF_SPOT_001).

        Collects all Separation and DeviceN color spaces across all pages,
        reports the complete inventory, and flags inconsistencies when the
        same colorant name has different alternate spaces on different pages.
        """
        findings: list[Finding] = []

        # colorant_name -> {pages, alternate descriptions, cs_types}
        colorant_pages: dict[str, list[int]] = {}
        colorant_alternates: dict[str, set[str]] = {}
        colorant_cs_types: dict[str, set[str]] = {}

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type not in ("Separation", "DeviceN"):
                    continue
                if not cs.colorant_names:
                    continue

                for colorant in cs.colorant_names:
                    if colorant in ("All", "None"):
                        continue

                    if colorant not in colorant_pages:
                        colorant_pages[colorant] = []
                        colorant_alternates[colorant] = set()
                        colorant_cs_types[colorant] = set()

                    if page.page_num not in colorant_pages[colorant]:
                        colorant_pages[colorant].append(page.page_num)

                    colorant_cs_types[colorant].add(cs.cs_type)

                    alt_desc = _describe_alternate(cs.alternate)
                    colorant_alternates[colorant].add(alt_desc)

        # Emit inventory advisory for each colorant
        for colorant, pages in colorant_pages.items():
            alt_descriptions = colorant_alternates[colorant]
            cs_types = colorant_cs_types[colorant]

            findings.append(
                Finding(
                    inspection_id="LPDF_SPOT_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Spot color '{colorant}' found on "
                        f"page{'s' if len(pages) > 1 else ''} {_format_page_list(pages)} "
                        f"(type: {', '.join(sorted(cs_types))}, "
                        f"alternate: {', '.join(sorted(alt_descriptions))})"
                    ),
                    details={
                        "colorant_name": colorant,
                        "pages": pages,
                        "cs_types": sorted(cs_types),
                        "alternates": sorted(alt_descriptions),
                    },
                    iso_clause="ISO 32000-2:2020 8.6.6.4",
                )
            )

        # Flag inconsistencies: same name with different alternates
        for colorant, alternates in colorant_alternates.items():
            if len(alternates) > 1:
                findings.append(
                    Finding(
                        inspection_id="LPDF_SPOT_001",
                        severity=Severity.WARNING,
                        message=(
                            f"Spot color '{colorant}' has inconsistent alternate "
                            f"color spaces across pages {_format_page_list(colorant_pages[colorant])}: "
                            f"{', '.join(sorted(alternates))}"
                        ),
                        details={
                            "colorant_name": colorant,
                            "pages": colorant_pages[colorant],
                            "alternates": sorted(alternates),
                        },
                        iso_clause="ISO 32000-2:2020 8.6.6.4",
                    )
                )

        return findings

    def _check_pantone_fallback(
        self,
        document: SemanticDocument,
    ) -> list[Finding]:
        """Validate Pantone spot color CMYK fallbacks via Delta-E (LPDF_SPOT_002).

        Compares the CMYK alternate values for each Pantone spot color
        against the Pantone reference Lab database using CIEDE2000 Delta-E.
        Also emits LPDF_SPOT_006 for Pantone colors not found in the
        reference database.
        """
        from lintpdf.profiles.icc.pantone_manager import PantoneManager

        findings: list[Finding] = []
        seen_pantone: set[str] = set()

        manager = PantoneManager(custom_overrides=self._custom_pantone_data)

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "Separation":
                    continue
                if not cs.colorant_names:
                    continue

                colorant = cs.colorant_names[0] if cs.colorant_names else ""
                if not _PANTONE_PATTERN.match(colorant):
                    continue
                if colorant in seen_pantone:
                    continue
                seen_pantone.add(colorant)

                alt_desc = _describe_alternate(cs.alternate)
                alt_type = cs.alternate.cs_type if cs.alternate else None

                # Check if Pantone name is in reference database
                ref = manager.lookup(colorant)
                if ref is None:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_SPOT_006",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Pantone spot color '{colorant}' not found in "
                                f"reference database — upload custom Pantone data "
                                f"for Delta-E validation"
                            ),
                            page_num=page.page_num,
                            details={
                                "colorant_name": colorant,
                                "note": "Not in reference database; upload custom "
                                "Pantone data for validation",
                            },
                            iso_clause="ISO 32000-2:2020 8.6.6.4",
                        )
                    )
                    continue

                # If alternate is CMYK, validate via Delta-E
                if cs.alternate and alt_type in ("DeviceCMYK", "ICCBased"):
                    # Use reference CMYK bridge as proxy for the fallback values
                    # (actual tintTransform values would require evaluation)
                    if ref.cmyk_bridge:
                        cmyk_01 = (
                            ref.cmyk_bridge[0] / 100.0,
                            ref.cmyk_bridge[1] / 100.0,
                            ref.cmyk_bridge[2] / 100.0,
                            ref.cmyk_bridge[3] / 100.0,
                        )
                        de_result = manager.validate_cmyk_fallback(
                            colorant,
                            cmyk_01,
                            icc_profile_bytes=self._icc_profile_bytes,
                            warning_threshold=self._delta_e_warning,
                            advisory_threshold=self._delta_e_advisory,
                        )

                        if de_result:
                            if de_result.delta_e > self._delta_e_warning:
                                severity = Severity.WARNING
                            elif de_result.delta_e > self._delta_e_advisory:
                                severity = Severity.ADVISORY
                            else:
                                # Delta-E is acceptable — emit informational
                                findings.append(
                                    Finding(
                                        inspection_id="LPDF_SPOT_002",
                                        severity=Severity.ADVISORY,
                                        message=(
                                            f"Pantone '{colorant}' CMYK fallback "
                                            f"Delta-E = {de_result.delta_e:.1f} "
                                            f"(acceptable)"
                                        ),
                                        page_num=page.page_num,
                                        details={
                                            "colorant_name": colorant,
                                            "delta_e": de_result.delta_e,
                                            "reference_lab": list(de_result.reference_lab),
                                            "fallback_lab": list(de_result.fallback_lab),
                                            "acceptable": True,
                                        },
                                        iso_clause="ISO 32000-2:2020 8.6.6.4",
                                    )
                                )
                                continue

                            findings.append(
                                Finding(
                                    inspection_id="LPDF_SPOT_002",
                                    severity=severity,
                                    message=(
                                        f"Pantone '{colorant}' CMYK fallback "
                                        f"Delta-E = {de_result.delta_e:.1f} "
                                        f"(threshold: {self._delta_e_warning})"
                                    ),
                                    page_num=page.page_num,
                                    details={
                                        "colorant_name": colorant,
                                        "delta_e": de_result.delta_e,
                                        "reference_lab": list(de_result.reference_lab),
                                        "fallback_lab": list(de_result.fallback_lab),
                                        "acceptable": de_result.acceptable,
                                        "alternate_type": alt_type,
                                    },
                                    iso_clause="ISO 32000-2:2020 8.6.6.4",
                                )
                            )
                            continue

                # No CMYK alternate or no bridge data — report informational
                findings.append(
                    Finding(
                        inspection_id="LPDF_SPOT_002",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Pantone spot color '{colorant}' uses alternate space '{alt_desc}'"
                        ),
                        page_num=page.page_num,
                        details={
                            "colorant_name": colorant,
                            "alternate_space": alt_desc,
                            "reference_lab": list(ref.lab),
                        },
                        iso_clause="ISO 32000-2:2020 8.6.6.4",
                    )
                )

        return findings

    @staticmethod
    def _check_spot_naming(  # skipcq: PY-R1000
        document: SemanticDocument,
    ) -> list[Finding]:
        """Check spot color naming conventions (LPDF_SPOT_003).

        Flags:
        - Ambiguous Pantone naming (C and U variants, or missing suffix)
        - Non-standard naming (not PANTONE, DIC, TOYO, HKS)
        - Empty or unnamed colorant names
        """
        findings: list[Finding] = []
        checked_names: set[str] = set()

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type not in ("Separation", "DeviceN"):
                    continue
                if not cs.colorant_names:
                    continue

                for colorant in cs.colorant_names:
                    if colorant in ("All", "None"):
                        continue
                    if colorant in checked_names:
                        continue
                    checked_names.add(colorant)

                    # Check for empty or whitespace-only names
                    if not colorant or not colorant.strip():
                        findings.append(
                            Finding(
                                inspection_id="LPDF_SPOT_003",
                                severity=Severity.WARNING,
                                message=(
                                    f"Empty or unnamed colorant in {cs.cs_type} "
                                    f"color space on page {page.page_num}"
                                ),
                                page_num=page.page_num,
                                details={
                                    "colorant_name": colorant,
                                    "color_space_type": cs.cs_type,
                                },
                                iso_clause="ISO 32000-2:2020 8.6.6.4",
                            )
                        )
                        continue

                    # Check Pantone-specific naming issues
                    upper = colorant.upper()
                    if upper.startswith("PANTONE"):
                        # Ambiguous: contains both C and U variant markers
                        has_c = upper.endswith(" C") or " C " in upper
                        has_u = upper.endswith(" U") or " U " in upper
                        if has_c and has_u:
                            findings.append(
                                Finding(
                                    inspection_id="LPDF_SPOT_003",
                                    severity=Severity.WARNING,
                                    message=(
                                        f"Ambiguous Pantone name '{colorant}' "
                                        f"contains both C and U variant markers"
                                    ),
                                    page_num=page.page_num,
                                    details={
                                        "colorant_name": colorant,
                                        "issue": "ambiguous_variant",
                                    },
                                    iso_clause="ISO 32000-2:2020 8.6.6.4",
                                )
                            )
                        elif not (
                            upper.endswith(" C")
                            or upper.endswith(" U")
                            or upper.endswith(" M")
                            or upper.endswith(" CP")
                            or upper.endswith(" CV")
                            or upper.endswith(" CVC")
                            or upper.endswith(" CVU")
                            or upper.endswith(" CVP")
                            or upper.endswith(" UP")
                        ):
                            findings.append(
                                Finding(
                                    inspection_id="LPDF_SPOT_003",
                                    severity=Severity.WARNING,
                                    message=(
                                        f"Pantone name '{colorant}' is missing a "
                                        f"coated/uncoated suffix (e.g., C, U, M)"
                                    ),
                                    page_num=page.page_num,
                                    details={
                                        "colorant_name": colorant,
                                        "issue": "missing_suffix",
                                    },
                                    iso_clause="ISO 32000-2:2020 8.6.6.4",
                                )
                            )
                        continue

                    # Check for non-standard naming
                    if not any(upper.startswith(prefix) for prefix in _KNOWN_SPOT_PREFIXES):
                        # Skip process color names — they are valid in DeviceN
                        if colorant in _PROCESS_COLOR_NAMES:
                            continue
                        findings.append(
                            Finding(
                                inspection_id="LPDF_SPOT_003",
                                severity=Severity.ADVISORY,
                                message=(
                                    f"Spot color '{colorant}' does not follow standard "
                                    f"naming conventions (PANTONE, DIC, TOYO, HKS)"
                                ),
                                page_num=page.page_num,
                                details={
                                    "colorant_name": colorant,
                                    "issue": "non_standard_name",
                                },
                                iso_clause="ISO 32000-2:2020 8.6.6.4",
                            )
                        )

        return findings

    @staticmethod
    def _check_devicen_structure(  # skipcq: PY-R1000
        document: SemanticDocument,
    ) -> list[Finding]:
        """Validate DeviceN color space structure (LPDF_SPOT_004).

        For each DeviceN color space:
        - Verify colorant count matches components field
        - Check alternate space is present and valid
        - Verify colorant names are non-empty
        """
        findings: list[Finding] = []

        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "DeviceN":
                    continue

                # Check colorant count matches components
                if cs.colorant_names and len(cs.colorant_names) != cs.components:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_SPOT_004",
                            severity=Severity.ERROR,
                            message=(
                                f"DeviceN '{cs_name}' on page {page.page_num}: "
                                f"colorant count ({len(cs.colorant_names)}) does not match "
                                f"components ({cs.components})"
                            ),
                            page_num=page.page_num,
                            details={
                                "color_space_name": cs_name,
                                "colorant_count": len(cs.colorant_names),
                                "components": cs.components,
                                "colorant_names": list(cs.colorant_names),
                            },
                            iso_clause="ISO 32000-2:2020 8.6.6.5",
                        )
                    )

                # Check alternate space is present
                if cs.alternate is None:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_SPOT_004",
                            severity=Severity.ERROR,
                            message=(
                                f"DeviceN '{cs_name}' on page {page.page_num} "
                                f"has no alternate color space"
                            ),
                            page_num=page.page_num,
                            details={
                                "color_space_name": cs_name,
                                "issue": "missing_alternate",
                            },
                            iso_clause="ISO 32000-2:2020 8.6.6.5",
                        )
                    )

                # Check for empty colorant names
                if not cs.colorant_names:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_SPOT_004",
                            severity=Severity.ERROR,
                            message=(
                                f"DeviceN '{cs_name}' on page {page.page_num} "
                                f"has no colorant names defined"
                            ),
                            page_num=page.page_num,
                            details={
                                "color_space_name": cs_name,
                                "issue": "no_colorant_names",
                            },
                            iso_clause="ISO 32000-2:2020 8.6.6.5",
                        )
                    )
                else:
                    # Check individual colorant names for empty strings
                    empty_indices = [
                        i
                        for i, name in enumerate(cs.colorant_names)
                        if not name or not name.strip()
                    ]
                    if empty_indices:
                        findings.append(
                            Finding(
                                inspection_id="LPDF_SPOT_004",
                                severity=Severity.WARNING,
                                message=(
                                    f"DeviceN '{cs_name}' on page {page.page_num} "
                                    f"has empty colorant name(s) at "
                                    f"index{'es' if len(empty_indices) > 1 else ''} "
                                    f"{empty_indices}"
                                ),
                                page_num=page.page_num,
                                details={
                                    "color_space_name": cs_name,
                                    "empty_indices": empty_indices,
                                    "colorant_names": list(cs.colorant_names),
                                    "issue": "empty_colorant_names",
                                },
                                iso_clause="ISO 32000-2:2020 8.6.6.5",
                            )
                        )

        return findings

    @staticmethod
    def _check_devicen_process_consistency(  # skipcq: PY-R1000
        document: SemanticDocument,
    ) -> list[Finding]:
        """Check DeviceN process color consistency (LPDF_SPOT_005).

        For DeviceN spaces that include process color names (Cyan, Magenta,
        Yellow, Black), verify that the process color set is consistent
        across all DeviceN instances in the document.
        """
        findings: list[Finding] = []

        # Collect process color sets per DeviceN instance
        # key: frozenset of process colors, value: list of (page_num, cs_name)
        process_sets: dict[frozenset[str], list[tuple[int, str]]] = {}
        all_devicen_with_process: list[tuple[int, str, frozenset[str]]] = []

        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "DeviceN":
                    continue
                if not cs.colorant_names:
                    continue

                process_colors = frozenset(
                    name for name in cs.colorant_names if name in _PROCESS_COLOR_NAMES
                )

                if not process_colors:
                    continue

                all_devicen_with_process.append((page.page_num, cs_name, process_colors))

                if process_colors not in process_sets:
                    process_sets[process_colors] = []
                process_sets[process_colors].append((page.page_num, cs_name))

        # Emit advisory inventory for each DeviceN with process colors
        for page_num, cs_name, process_colors in all_devicen_with_process:
            findings.append(
                Finding(
                    inspection_id="LPDF_SPOT_005",
                    severity=Severity.ADVISORY,
                    message=(
                        f"DeviceN '{cs_name}' on page {page_num} includes "
                        f"process colors: {', '.join(sorted(process_colors))}"
                    ),
                    page_num=page_num,
                    details={
                        "color_space_name": cs_name,
                        "process_colors": sorted(process_colors),
                    },
                    iso_clause="ISO 32000-2:2020 8.6.6.5",
                )
            )

        # Flag inconsistencies if multiple different process color sets exist
        if len(process_sets) > 1:
            set_descriptions = []
            for pset, locations in process_sets.items():
                pages = [loc[0] for loc in locations]
                set_descriptions.append(
                    f"{{{', '.join(sorted(pset))}}} on "
                    f"page{'s' if len(pages) > 1 else ''} {_format_page_list(pages)}"
                )

            findings.append(
                Finding(
                    inspection_id="LPDF_SPOT_005",
                    severity=Severity.WARNING,
                    message=(
                        f"Inconsistent process color sets in DeviceN spaces: "
                        f"{'; '.join(set_descriptions)}"
                    ),
                    details={
                        "process_sets": {
                            str(sorted(pset)): [loc[0] for loc in locations]
                            for pset, locations in process_sets.items()
                        },
                    },
                    iso_clause="ISO 32000-2:2020 8.6.6.5",
                )
            )

        return findings

    # ------------------------------------------------------------------
    # LPDF_SPOT_007 — Unknown spot color name
    # ------------------------------------------------------------------

    @staticmethod
    def _check_unknown_spot_color(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Flag spot colors whose name doesn't match any known library (LPDF_SPOT_007).

        Checks colorant names against PANTONE, HKS, TOYO, DIC, and RAL
        prefixes.  Process color names (Cyan, Magenta, Yellow, Black) and
        the special names All/None are excluded.
        """
        findings: list[Finding] = []
        checked: set[str] = set()

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type not in ("Separation", "DeviceN"):
                    continue
                if not cs.colorant_names:
                    continue

                for colorant in cs.colorant_names:
                    if colorant in ("All", "None"):
                        continue
                    if colorant in _PROCESS_COLOR_NAMES:
                        continue
                    if colorant in checked:
                        continue
                    checked.add(colorant)

                    upper = colorant.upper()
                    if not any(upper.startswith(prefix) for prefix in _ALL_KNOWN_LIBRARY_PREFIXES):
                        findings.append(
                            Finding(
                                inspection_id="LPDF_SPOT_007",
                                severity=Severity.ADVISORY,
                                message=(
                                    f"Unknown spot color '{colorant}' does not match "
                                    f"any known color library "
                                    f"(PANTONE, HKS, TOYO, DIC, RAL)"
                                ),
                                page_num=page.page_num,
                                details={
                                    "colorant_name": colorant,
                                    "known_libraries": list(_ALL_KNOWN_LIBRARY_PREFIXES),
                                },
                                iso_clause="ISO 32000-2:2020 8.6.6.4",
                            )
                        )

        return findings

    # ------------------------------------------------------------------
    # LPDF_SPOT_008 — Spot color alternate space mismatch
    # ------------------------------------------------------------------

    @staticmethod
    def _check_alternate_space_mismatch(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Flag spot colors whose alternate space doesn't match library expectations (LPDF_SPOT_008).

        For each known library prefix, verifies the alternate color space
        type matches the expected set (e.g., PANTONE expects DeviceCMYK
        or ICCBased).
        """
        findings: list[Finding] = []
        checked: set[str] = set()

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "Separation":
                    continue
                if not cs.colorant_names:
                    continue

                colorant = cs.colorant_names[0] if cs.colorant_names else ""
                if not colorant or colorant in ("All", "None"):
                    continue
                if colorant in checked:
                    continue
                checked.add(colorant)

                upper = colorant.upper()
                matched_library: str | None = None
                for prefix in _ALL_KNOWN_LIBRARY_PREFIXES:
                    if upper.startswith(prefix):
                        matched_library = prefix
                        break

                if matched_library is None:
                    continue

                expected = _LIBRARY_EXPECTED_ALTERNATES.get(matched_library)
                if expected is None:
                    continue

                alt_type = cs.alternate.cs_type if cs.alternate else "none"
                if alt_type not in expected:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_SPOT_008",
                            severity=Severity.WARNING,
                            message=(
                                f"Spot color '{colorant}' ({matched_library} library) "
                                f"has alternate space '{alt_type}' which is not "
                                f"expected (expected: {', '.join(sorted(expected))})"
                            ),
                            page_num=page.page_num,
                            details={
                                "colorant_name": colorant,
                                "library": matched_library,
                                "alternate_type": alt_type,
                                "expected_alternates": sorted(expected),
                            },
                            iso_clause="ISO 32000-2:2020 8.6.6.4",
                        )
                    )

        return findings

    # ------------------------------------------------------------------
    # LPDF_SPOT_009 — Duplicate spot color definitions
    # ------------------------------------------------------------------

    @staticmethod
    def _check_duplicate_spot_definitions(  # skipcq: PY-R1000
        document: SemanticDocument,
    ) -> list[Finding]:
        """Flag duplicate spot color definitions on the same page (LPDF_SPOT_009).

        Detects when the same colorant name appears in multiple
        Separation color spaces on a single page with different
        alternate space parameters.
        """
        findings: list[Finding] = []

        for page in document.pages:
            # colorant -> list of (cs_name, alternate_desc)
            colorant_defs: dict[str, list[tuple[str, str]]] = {}

            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type != "Separation":
                    continue
                if not cs.colorant_names:
                    continue

                colorant = cs.colorant_names[0] if cs.colorant_names else ""
                if not colorant or colorant in ("All", "None"):
                    continue

                alt_desc = _describe_alternate(cs.alternate)
                if colorant not in colorant_defs:
                    colorant_defs[colorant] = []
                colorant_defs[colorant].append((cs_name, alt_desc))

            for colorant, defs in colorant_defs.items():
                if len(defs) <= 1:
                    continue

                alt_descriptions = {d[1] for d in defs}
                if len(alt_descriptions) > 1:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_SPOT_009",
                            severity=Severity.WARNING,
                            message=(
                                f"Duplicate spot color '{colorant}' on page "
                                f"{page.page_num} defined {len(defs)} time(s) with "
                                f"different parameters: "
                                f"{', '.join(sorted(alt_descriptions))}"
                            ),
                            page_num=page.page_num,
                            details={
                                "colorant_name": colorant,
                                "definition_count": len(defs),
                                "alternates": sorted(alt_descriptions),
                                "color_space_names": [d[0] for d in defs],
                            },
                            iso_clause="ISO 32000-2:2020 8.6.6.4",
                        )
                    )

        return findings

    # ------------------------------------------------------------------
    # LPDF_SPOT_010 — Spot color count exceeds maximum
    # ------------------------------------------------------------------

    def _check_spot_color_count(
        self,
        document: SemanticDocument,
    ) -> list[Finding]:
        """Flag when spot color count exceeds configurable maximum (LPDF_SPOT_010).

        Counts distinct spot colorant names (excluding process colors
        and All/None) across the entire document.
        """
        findings: list[Finding] = []
        all_spots: set[str] = set()

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type not in ("Separation", "DeviceN"):
                    continue
                if not cs.colorant_names:
                    continue

                for colorant in cs.colorant_names:
                    if colorant in ("All", "None"):
                        continue
                    if colorant in _PROCESS_COLOR_NAMES:
                        continue
                    all_spots.add(colorant)

        if len(all_spots) > self._max_spot_colors:
            findings.append(
                Finding(
                    inspection_id="LPDF_SPOT_010",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Document uses {len(all_spots)} spot color(s), "
                        f"exceeding the maximum of {self._max_spot_colors}: "
                        f"{', '.join(sorted(all_spots))}"
                    ),
                    details={
                        "spot_color_count": len(all_spots),
                        "max_spot_colors": self._max_spot_colors,
                        "spot_colors": sorted(all_spots),
                    },
                    iso_clause="ISO 32000-2:2020 8.6.6.4",
                )
            )

        return findings

    # ------------------------------------------------------------------
    # LPDF_SPOT_011 — Spot color with zero tint
    # ------------------------------------------------------------------

    @staticmethod
    def _check_zero_tint(
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Flag spot colors used at 0% tint, making them invisible (LPDF_SPOT_011).

        Checks content stream events for Separation color space usage
        where the tint value is 0.0 (fully transparent).
        """
        findings: list[Finding] = []
        seen: set[tuple[int, str]] = set()

        for event in events:
            # Check fill and stroke color values for separation spaces
            color_space: str | None = None
            color_values: tuple[float, ...] = ()
            page_num: int = 0

            # Duck-type: look for fill/stroke separation colors
            if hasattr(event, "fill_color_space") and hasattr(event, "fill_color_values"):
                if event.fill_color_space and "Separation" in str(event.fill_color_space):
                    color_space = event.fill_color_space
                    color_values = event.fill_color_values
                    page_num = event.page_num
            if hasattr(event, "color_space") and hasattr(event, "color_values"):
                if event.color_space and "Separation" in str(event.color_space):
                    color_space = event.color_space
                    color_values = event.color_values
                    page_num = event.page_num

            if color_space is None or not color_values:
                continue

            # Tint is the single component value for Separation spaces
            if len(color_values) == 1 and color_values[0] == 0.0:
                key = (page_num, color_space)
                if key in seen:
                    continue
                seen.add(key)

                findings.append(
                    Finding(
                        inspection_id="LPDF_SPOT_011",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Spot color '{color_space}' used at 0% tint "
                            f"on page {page_num} (invisible)"
                        ),
                        page_num=page_num,
                        details={
                            "color_space": color_space,
                            "tint_value": 0.0,
                        },
                        iso_clause="ISO 32000-2:2020 8.6.6.4",
                    )
                )

        return findings


def _describe_alternate(alternate: PdfColorSpace | None) -> str:
    """Return a human-readable description of an alternate color space."""
    if alternate is None:
        return "none"
    if alternate.name:
        return f"{alternate.cs_type} ({alternate.name})"
    return alternate.cs_type


def _format_page_list(pages: list[int]) -> str:
    """Format a list of page numbers for display."""
    if len(pages) <= 5:
        return ", ".join(str(p) for p in pages)
    return f"{', '.join(str(p) for p in pages[:4])}, ... ({len(pages)} pages)"
