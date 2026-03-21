"""SpotColorAnalyzer — spot color and DeviceN color space validation.

Processes SemanticDocument color space data to detect spot color naming,
structural, and consistency issues across pages.

Check IDs:
    GRD_SPOT_001 — Full spot color inventory
    GRD_SPOT_002 — Spot color fallback Delta-E validation
    GRD_SPOT_003 — Spot color naming issues
    GRD_SPOT_004 — DeviceN structural validation
    GRD_SPOT_005 — DeviceN process color consistency
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import PdfColorSpace, SemanticDocument

# Well-known spot color naming prefixes
_KNOWN_SPOT_PREFIXES = ("PANTONE", "DIC", "TOYO", "HKS")

# Process color names used in DeviceN spaces
_PROCESS_COLOR_NAMES = frozenset({"Cyan", "Magenta", "Yellow", "Black"})

# Pattern for PANTONE names (e.g., "PANTONE 485 C", "PANTONE Reflex Blue CV")
_PANTONE_PATTERN = re.compile(r"^PANTONE\s+.+$", re.IGNORECASE)


class SpotColorAnalyzer(BaseAnalyzer):
    """Analyzer for spot color and DeviceN color space validation."""

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

        return findings

    @staticmethod
    def _check_spot_inventory(  # skipcq: PY-R1000
        document: SemanticDocument,
    ) -> list[Finding]:
        """Build full spot color inventory and check consistency (GRD_SPOT_001).

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
                    inspection_id="GRD_SPOT_001",
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
                        inspection_id="GRD_SPOT_001",
                        severity=Severity.SQUALL,
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

    @staticmethod
    def _check_pantone_fallback(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Report alternate CMYK fallback values for Pantone spot colors (GRD_SPOT_002).

        For Separation colors with names matching the PANTONE pattern, report
        the alternate color space CMYK values so they can be verified against
        Pantone's expected Lab values.
        """
        findings: list[Finding] = []
        seen_pantone: set[str] = set()

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

                details: dict[str, object] = {
                    "colorant_name": colorant,
                    "alternate_space": alt_desc,
                    "page_num": page.page_num,
                }

                if cs.alternate and alt_type in ("DeviceCMYK", "ICCBased"):
                    details["alternate_type"] = alt_type

                findings.append(
                    Finding(
                        inspection_id="GRD_SPOT_002",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Pantone spot color '{colorant}' uses "
                            f"alternate space '{alt_desc}' — verify fallback CMYK "
                            f"values match Pantone color bridge expectations"
                        ),
                        page_num=page.page_num,
                        details=details,
                        iso_clause="ISO 32000-2:2020 8.6.6.4",
                    )
                )

        return findings

    @staticmethod
    def _check_spot_naming(  # skipcq: PY-R1000
        document: SemanticDocument,
    ) -> list[Finding]:
        """Check spot color naming conventions (GRD_SPOT_003).

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
                                inspection_id="GRD_SPOT_003",
                                severity=Severity.SQUALL,
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
                                    inspection_id="GRD_SPOT_003",
                                    severity=Severity.SQUALL,
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
                                    inspection_id="GRD_SPOT_003",
                                    severity=Severity.SQUALL,
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
                                inspection_id="GRD_SPOT_003",
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
        """Validate DeviceN color space structure (GRD_SPOT_004).

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
                            inspection_id="GRD_SPOT_004",
                            severity=Severity.AGROUND,
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
                            inspection_id="GRD_SPOT_004",
                            severity=Severity.AGROUND,
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
                            inspection_id="GRD_SPOT_004",
                            severity=Severity.AGROUND,
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
                                inspection_id="GRD_SPOT_004",
                                severity=Severity.SQUALL,
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
        """Check DeviceN process color consistency (GRD_SPOT_005).

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
                    inspection_id="GRD_SPOT_005",
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
                    inspection_id="GRD_SPOT_005",
                    severity=Severity.SQUALL,
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
