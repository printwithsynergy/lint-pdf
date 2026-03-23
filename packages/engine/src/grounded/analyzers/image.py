"""ImageAnalyzer — DPI calculation, color space, and compression checks.

Processes ImagePlacedEvent events to calculate effective DPI and detect
image-related preflight issues.

DPI formula (ISO 32000-2:2020 section 8.9):
    display_width_pts = sqrt(a^2 + c^2)
    display_height_pts = sqrt(b^2 + d^2)
    dpi_x = pixel_width / (display_width_pts / 72)
    dpi_y = pixel_height / (display_height_pts / 72)

Check IDs:
    GRD_IMG_001 — Low resolution (below minimum DPI threshold)
    GRD_IMG_002 — Excessive resolution (above maximum DPI threshold)
    GRD_IMG_003 — Color space mismatch (e.g., RGB image in CMYK workflow)
    GRD_IMG_004 — No effective compression
    GRD_IMG_005 — Inline image detected
    GRD_IMG_006 — Image upscaled >150%
    GRD_IMG_007 — LZW compression (prohibited in PDF/X)
    GRD_IMG_008 — JPEG2000 image detected
    GRD_IMG_009 — 16-bit image (bits_per_component > 8)
    GRD_IMG_010 — OPI reference detected (prohibited in PDF/X)
    GRD_IMG_011 — Alternate images detected (prohibited in PDF/X)
    GRD_IMG_012 — OPI reference detected in page resources (advisory)
    GRD_IMG_013 — Alternate image detected in page resources (advisory)
    GRD_IMG_014 — Image is sheared (non-orthogonal CTM transform)
    GRD_IMG_015 — Image is significantly rotated (non-90-degree rotation)
    GRD_IMG_016 — Image is flipped (mirrored)
    GRD_IMG_017 — Image precise scaling percentage (extreme scaling detected)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent, ImagePlacedEvent
    from grounded.semantic.graphics_state import TransformationMatrix
    from grounded.semantic.model import SemanticDocument

# Default DPI thresholds (configurable via Voyage Plan)
DEFAULT_MIN_DPI = 150.0
DEFAULT_MAX_DPI = 600.0

# Filters that provide no actual compression
_NO_COMPRESSION_FILTERS = frozenset({"ASCIIHexDecode", "ASCII85Decode"})


@dataclass(frozen=True)
class ImageAnalysisResult:
    """Result of DPI analysis for a single image.

    Attributes:
        page_num: 1-indexed page number.
        image_name: XObject resource name.
        pixel_width: Image width in pixels.
        pixel_height: Image height in pixels.
        dpi_x: Effective horizontal DPI.
        dpi_y: Effective vertical DPI.
        dpi_effective: Conservative DPI (minimum of x and y).
        color_space: Image color space.
        is_valid: Whether the CTM produced valid DPI values.
    """

    page_num: int
    image_name: str
    pixel_width: int
    pixel_height: int
    dpi_x: float
    dpi_y: float
    dpi_effective: float
    color_space: str
    is_valid: bool


class ImageAnalyzer(BaseAnalyzer):
    """Analyzer for image DPI, color space, and compression.

    Args:
        min_dpi: Minimum acceptable DPI (default 150 for print).
        max_dpi: Maximum useful DPI (default 600).
    """

    def __init__(
        self,
        min_dpi: float = DEFAULT_MIN_DPI,
        max_dpi: float = DEFAULT_MAX_DPI,
    ) -> None:
        self.min_dpi = min_dpi
        self.max_dpi = max_dpi

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze all image events and return findings."""
        from grounded.semantic.events import ImagePlacedEvent

        findings: list[Finding] = []

        for event in events:
            if isinstance(event, ImagePlacedEvent):
                findings.extend(self._analyze_image(event))

        # GRD_IMG_012: OPI references in page XObject resources
        findings.extend(self._check_opi_in_resources(document))

        # GRD_IMG_013: Alternate images in page XObject resources
        findings.extend(self._check_alternates_in_resources(document))

        return findings

    def _analyze_image(self, event: ImagePlacedEvent) -> list[Finding]:  # skipcq: PY-R1000
        """Analyze a single image placement."""
        findings: list[Finding] = []

        # Calculate DPI
        result = self.calculate_dpi(event)

        if result.is_valid:
            # GRD_IMG_001: Low resolution
            if result.dpi_effective < self.min_dpi:
                findings.append(
                    Finding(
                        inspection_id="GRD_IMG_001",
                        severity=Severity.WARNING,
                        message=(
                            f"Image '{result.image_name}' has low resolution: "
                            f"{result.dpi_effective:.0f} DPI "
                            f"(minimum {self.min_dpi:.0f} DPI)"
                        ),
                        page_num=event.page_num,
                        details={
                            "image_name": result.image_name,
                            "dpi_x": result.dpi_x,
                            "dpi_y": result.dpi_y,
                            "dpi_effective": result.dpi_effective,
                            "pixel_width": result.pixel_width,
                            "pixel_height": result.pixel_height,
                            "min_dpi": self.min_dpi,
                        },
                        iso_clause="ISO 32000-2:2020 8.9",
                        object_id=event.image_name,
                        object_type="image",
                    )
                )

            # GRD_IMG_002: Excessive resolution
            if result.dpi_effective > self.max_dpi:
                findings.append(
                    Finding(
                        inspection_id="GRD_IMG_002",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Image '{result.image_name}' has excessive resolution: "
                            f"{result.dpi_effective:.0f} DPI "
                            f"(maximum useful {self.max_dpi:.0f} DPI)"
                        ),
                        page_num=event.page_num,
                        details={
                            "image_name": result.image_name,
                            "dpi_effective": result.dpi_effective,
                            "max_dpi": self.max_dpi,
                        },
                        iso_clause="ISO 32000-2:2020 8.9",
                        object_id=event.image_name,
                        object_type="image",
                    )
                )

            # GRD_IMG_006: Image upscaled >150%
            # Upscale ratio = display size / pixel size
            ctm = event.ctm
            sx, sy = _extract_ctm_scale(ctm)
            if sx > 1e-10 and sy > 1e-10:
                display_w_inches = sx / 72.0
                display_h_inches = sy / 72.0
                if event.pixel_width > 0 and event.pixel_height > 0:
                    scale_x = display_w_inches / (event.pixel_width / 72.0)
                    scale_y = display_h_inches / (event.pixel_height / 72.0)
                    upscale_pct = max(scale_x, scale_y) * 100.0
                    if upscale_pct > 150.0:
                        findings.append(
                            Finding(
                                inspection_id="GRD_IMG_006",
                                severity=Severity.WARNING,
                                message=(
                                    f"Image '{event.image_name}' is upscaled "
                                    f"{upscale_pct:.0f}% on page {event.page_num} "
                                    f"(>150% causes visible quality loss)"
                                ),
                                page_num=event.page_num,
                                details={
                                    "image_name": event.image_name,
                                    "upscale_percent": upscale_pct,
                                    "pixel_width": event.pixel_width,
                                    "pixel_height": event.pixel_height,
                                },
                                object_id=event.image_name,
                                object_type="image",
                            )
                        )

        # GRD_IMG_004: No effective compression
        if event.filters:
            filter_set = set(event.filters)
            if filter_set and filter_set.issubset(_NO_COMPRESSION_FILTERS):
                findings.append(
                    Finding(
                        inspection_id="GRD_IMG_004",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Image '{event.image_name}' uses no effective compression "
                            f"(filters: {', '.join(event.filters)})"
                        ),
                        page_num=event.page_num,
                        details={
                            "image_name": event.image_name,
                            "filters": list(event.filters),
                        },
                        iso_clause="ISO 32000-2:2020 7.4",
                    )
                )

        # GRD_IMG_005: Inline image
        if event.is_inline:
            findings.append(
                Finding(
                    inspection_id="GRD_IMG_005",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Inline image detected on page {event.page_num} "
                        f"(inline images are less efficient than XObject images)"
                    ),
                    page_num=event.page_num,
                    details={"image_name": event.image_name},
                    iso_clause="ISO 32000-2:2020 8.9.7",
                )
            )

        # GRD_IMG_007: LZW compression (prohibited in PDF/X)
        if event.filters and "LZWDecode" in event.filters:
            findings.append(
                Finding(
                    inspection_id="GRD_IMG_007",
                    severity=Severity.WARNING,
                    message=(
                        f"Image '{event.image_name}' uses LZW compression "
                        f"on page {event.page_num} (prohibited in PDF/X)"
                    ),
                    page_num=event.page_num,
                    details={
                        "image_name": event.image_name,
                        "filters": list(event.filters),
                    },
                    iso_clause="ISO 15930-7:2010 6.2.5",
                    object_id=event.image_name,
                    object_type="image",
                )
            )

        # GRD_IMG_008: JPEG2000 image detected
        if event.filters and "JPXDecode" in event.filters:
            findings.append(
                Finding(
                    inspection_id="GRD_IMG_008",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Image '{event.image_name}' uses JPEG2000 compression "
                        f"on page {event.page_num}"
                    ),
                    page_num=event.page_num,
                    details={
                        "image_name": event.image_name,
                        "filters": list(event.filters),
                    },
                    iso_clause="ISO 32000-2:2020 7.4.9",
                    object_id=event.image_name,
                    object_type="image",
                )
            )

        # GRD_IMG_009: 16-bit image (bits_per_component > 8)
        if event.bits_per_component > 8:
            findings.append(
                Finding(
                    inspection_id="GRD_IMG_009",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Image '{event.image_name}' is {event.bits_per_component}-bit "
                        f"on page {event.page_num} (may cause processing issues)"
                    ),
                    page_num=event.page_num,
                    details={
                        "image_name": event.image_name,
                        "bits_per_component": event.bits_per_component,
                    },
                    iso_clause="ISO 32000-2:2020 8.9.5.1",
                    object_id=event.image_name,
                    object_type="image",
                )
            )

        # GRD_IMG_010: OPI reference detected (prohibited in PDF/X)
        if event.has_opi:
            findings.append(
                Finding(
                    inspection_id="GRD_IMG_010",
                    severity=Severity.ERROR,
                    message=(
                        f"Image '{event.image_name}' contains OPI reference "
                        f"on page {event.page_num} (prohibited in PDF/X)"
                    ),
                    page_num=event.page_num,
                    details={"image_name": event.image_name},
                    iso_clause="ISO 15930-7:2010 6.2.7",
                    object_id=event.image_name,
                    object_type="image",
                )
            )

        # GRD_IMG_011: Alternate images detected (prohibited in PDF/X)
        if event.has_alternate:
            findings.append(
                Finding(
                    inspection_id="GRD_IMG_011",
                    severity=Severity.WARNING,
                    message=(
                        f"Image '{event.image_name}' has alternate images "
                        f"on page {event.page_num} (prohibited in PDF/X)"
                    ),
                    page_num=event.page_num,
                    details={"image_name": event.image_name},
                    iso_clause="ISO 15930-7:2010 6.2.5",
                    object_id=event.image_name,
                    object_type="image",
                )
            )

        # GRD_IMG_014: Image is sheared (non-orthogonal CTM)
        findings.extend(self._check_image_shear(event))

        # GRD_IMG_015: Image is significantly rotated (non-90-degree)
        findings.extend(self._check_image_rotation(event))

        # GRD_IMG_016: Image is flipped (mirrored)
        findings.extend(self._check_image_flip(event))

        # GRD_IMG_017: Image extreme scaling
        findings.extend(self._check_image_scaling(event))

        return findings

    @staticmethod
    def _check_image_shear(event: ImagePlacedEvent) -> list[Finding]:
        """Check for non-orthogonal CTM transform on an image (GRD_IMG_014).

        A sheared image has a CTM where the off-diagonal elements (b, c)
        do not correspond to a pure rotation. This indicates a skew/shear
        transform that may cause unexpected output.
        """
        findings: list[Finding] = []
        ctm = event.ctm

        # For a pure scale+rotation, the matrix satisfies:
        # a*b + c*d = 0 (orthogonality condition)
        # and |a*d - b*c| = sx * sy (determinant = product of scales)
        dot_product = ctm.a * ctm.b + ctm.c * ctm.d
        determinant = abs(ctm.a * ctm.d - ctm.b * ctm.c)

        # If determinant is near zero, image is degenerate — skip
        if determinant < 1e-10:
            return findings

        # Normalize dot product by the determinant for a scale-independent check
        shear_metric = abs(dot_product) / determinant

        # Threshold: anything above ~0.01 is a noticeable shear
        if shear_metric > 0.01:
            findings.append(
                Finding(
                    inspection_id="GRD_IMG_014",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Image '{event.image_name}' is sheared on page {event.page_num} "
                        f"(non-orthogonal transform detected)"
                    ),
                    page_num=event.page_num,
                    details={
                        "image_name": event.image_name,
                        "ctm": [ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f],
                        "shear_metric": shear_metric,
                    },
                    object_id=event.image_name,
                    object_type="image",
                    iso_clause="ISO 32000-2:2020 8.3.4",
                )
            )

        return findings

    @staticmethod
    def _check_image_rotation(event: ImagePlacedEvent) -> list[Finding]:
        """Check for non-90-degree rotation on an image (GRD_IMG_015).

        Detects images that are rotated by angles other than 0, 90, 180, 270
        degrees, which may indicate unintended transforms or quality issues.
        """
        findings: list[Finding] = []
        ctm = event.ctm

        # Extract rotation angle from CTM
        # For a rotation matrix: a=cos(t), b=sin(t), c=-sin(t), d=cos(t)
        # We use atan2 on the (b, a) pair to extract the angle
        angle_rad = math.atan2(ctm.b, ctm.a)
        angle_deg = math.degrees(angle_rad) % 360

        # Check if the angle is close to a multiple of 90 degrees
        remainder = angle_deg % 90
        if remainder > 45:
            remainder = 90 - remainder

        # If more than 0.5 degrees away from a 90-degree multiple, flag it
        if remainder > 0.5:
            # Also verify the CTM isn't just a pure scale (b=0, c=0)
            if abs(ctm.b) < 1e-10 and abs(ctm.c) < 1e-10:
                return findings  # Pure scale, no rotation

            findings.append(
                Finding(
                    inspection_id="GRD_IMG_015",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Image '{event.image_name}' is rotated {angle_deg:.1f} degrees "
                        f"on page {event.page_num} (non-90-degree rotation detected)"
                    ),
                    page_num=event.page_num,
                    details={
                        "image_name": event.image_name,
                        "rotation_degrees": round(angle_deg, 1),
                        "ctm": [ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f],
                    },
                    object_id=event.image_name,
                    object_type="image",
                    iso_clause="ISO 32000-2:2020 8.3.4",
                )
            )

        return findings

    @staticmethod
    def _check_image_flip(event: ImagePlacedEvent) -> list[Finding]:
        """Check for reflection (mirror/flip) in the CTM (GRD_IMG_016).

        A negative determinant (a*d - b*c < 0) indicates that one axis
        has been reflected, meaning the image is flipped/mirrored.
        """
        findings: list[Finding] = []
        ctm = event.ctm

        determinant = ctm.a * ctm.d - ctm.b * ctm.c

        # A negative determinant means a reflection transform is present
        if determinant < -1e-10:
            findings.append(
                Finding(
                    inspection_id="GRD_IMG_016",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Image '{event.image_name}' is flipped (mirrored) "
                        f"on page {event.page_num} (reflection transform detected)"
                    ),
                    page_num=event.page_num,
                    details={
                        "image_name": event.image_name,
                        "ctm": [ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f],
                        "determinant": determinant,
                    },
                    object_id=event.image_name,
                    object_type="image",
                    iso_clause="ISO 32000-2:2020 8.3.4",
                )
            )

        return findings

    @staticmethod
    def _check_image_scaling(event: ImagePlacedEvent) -> list[Finding]:
        """Check for extreme scaling of an image (GRD_IMG_017).

        Flags images scaled to less than 10% or more than 1000% of their
        original size, as these are likely errors.
        """
        findings: list[Finding] = []
        ctm = event.ctm
        sx, sy = _extract_ctm_scale(ctm)

        if sx < 1e-10 or sy < 1e-10:
            return findings

        if event.pixel_width <= 0 or event.pixel_height <= 0:
            return findings

        # Scale percentage: display size vs pixel size
        # display_inches = sx / 72, pixel_inches = pixel_width / 72
        # scale = display_inches / pixel_inches = sx / pixel_width
        scale_x_pct = (sx / event.pixel_width) * 100.0
        scale_y_pct = (sy / event.pixel_height) * 100.0
        scale_pct = max(scale_x_pct, scale_y_pct)

        if scale_pct < 10.0 or scale_pct > 1000.0:
            findings.append(
                Finding(
                    inspection_id="GRD_IMG_017",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Image '{event.image_name}' is scaled to {scale_pct:.0f}% "
                        f"on page {event.page_num} (extreme scaling detected)"
                    ),
                    page_num=event.page_num,
                    details={
                        "image_name": event.image_name,
                        "scale_x_percent": round(scale_x_pct, 1),
                        "scale_y_percent": round(scale_y_pct, 1),
                        "scale_percent": round(scale_pct, 1),
                        "pixel_width": event.pixel_width,
                        "pixel_height": event.pixel_height,
                    },
                    object_id=event.image_name,
                    object_type="image",
                    iso_clause="ISO 32000-2:2020 8.3.4",
                )
            )

        return findings

    @staticmethod
    def _check_opi_in_resources(document: SemanticDocument) -> list[Finding]:
        """Check for /OPI in image XObject dictionaries (GRD_IMG_012).

        Scans page resources for image XObjects containing OPI references,
        which indicate low-resolution placeholders meant for OPI server
        replacement.
        """
        findings: list[Finding] = []
        for page in document.pages:
            xobjects = page.resources.get("/XObject", {})
            if not isinstance(xobjects, dict):
                continue
            for xobj_name, xobj_dict in xobjects.items():
                if not isinstance(xobj_dict, dict):
                    continue
                if xobj_dict.get("/Subtype") != "/Image":
                    continue
                if "/OPI" in xobj_dict:
                    findings.append(
                        Finding(
                            inspection_id="GRD_IMG_012",
                            severity=Severity.ADVISORY,
                            message=(
                                f"OPI reference found in image '{xobj_name}' "
                                f"on page {page.page_num} "
                                f"(low-resolution placeholder for OPI server)"
                            ),
                            page_num=page.page_num,
                            details={"image_name": xobj_name},
                            object_id=xobj_name,
                            object_type="image",
                            iso_clause="ISO 32000-2:2020 14.11.7",
                        )
                    )
                    return findings  # One finding is enough
        return findings

    @staticmethod
    def _check_alternates_in_resources(document: SemanticDocument) -> list[Finding]:
        """Check for /Alternates in image XObject dictionaries (GRD_IMG_013).

        Scans page resources for image XObjects containing alternate image
        entries, which may cause unexpected output if the wrong alternate
        is selected.
        """
        findings: list[Finding] = []
        for page in document.pages:
            xobjects = page.resources.get("/XObject", {})
            if not isinstance(xobjects, dict):
                continue
            for xobj_name, xobj_dict in xobjects.items():
                if not isinstance(xobj_dict, dict):
                    continue
                if xobj_dict.get("/Subtype") != "/Image":
                    continue
                if "/Alternates" in xobj_dict:
                    findings.append(
                        Finding(
                            inspection_id="GRD_IMG_013",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Alternate image found for '{xobj_name}' "
                                f"on page {page.page_num} "
                                f"(may cause unexpected output selection)"
                            ),
                            page_num=page.page_num,
                            details={"image_name": xobj_name},
                            object_id=xobj_name,
                            object_type="image",
                            iso_clause="ISO 32000-2:2020 8.9.5.4",
                        )
                    )
                    return findings  # One finding is enough
        return findings

    @staticmethod
    def check_color_space_mismatch(
        event: ImagePlacedEvent,
        workflow: str,
    ) -> Finding | None:
        """Check if image color space mismatches the document workflow.

        Args:
            event: Image placement event.
            workflow: Target workflow ("CMYK" or "RGB").

        Returns:
            Finding if mismatch detected, None otherwise.
        """
        cs = event.color_space

        if workflow == "CMYK" and cs in ("DeviceRGB", "CalRGB"):
            return Finding(
                inspection_id="GRD_IMG_003",
                severity=Severity.WARNING,
                message=(f"Image '{event.image_name}' uses {cs} in a CMYK workflow"),
                page_num=event.page_num,
                details={
                    "image_name": event.image_name,
                    "color_space": cs,
                    "workflow": workflow,
                },
                iso_clause="ISO 15930-7:2010 6.2.4",
            )

        if workflow == "RGB" and cs in ("DeviceCMYK",):
            return Finding(
                inspection_id="GRD_IMG_003",
                severity=Severity.WARNING,
                message=(f"Image '{event.image_name}' uses {cs} in an RGB workflow"),
                page_num=event.page_num,
                details={
                    "image_name": event.image_name,
                    "color_space": cs,
                    "workflow": workflow,
                },
                iso_clause="ISO 15930-7:2010 6.2.4",
            )

        return None

    @staticmethod
    def calculate_dpi(event: ImagePlacedEvent) -> ImageAnalysisResult:
        """Calculate effective DPI from an image placement event.

        Uses CTM scale factors to determine display size, then
        computes DPI = pixels / (display_points / 72).
        """
        ctm = event.ctm
        sx, sy = _extract_ctm_scale(ctm)

        if sx < 1e-10 or sy < 1e-10:
            return ImageAnalysisResult(
                page_num=event.page_num,
                image_name=event.image_name,
                pixel_width=event.pixel_width,
                pixel_height=event.pixel_height,
                dpi_x=float("inf"),
                dpi_y=float("inf"),
                dpi_effective=float("inf"),
                color_space=event.color_space,
                is_valid=False,
            )

        dpi_x = event.pixel_width / (sx / 72.0)
        dpi_y = event.pixel_height / (sy / 72.0)
        dpi_effective = min(dpi_x, dpi_y)

        return ImageAnalysisResult(
            page_num=event.page_num,
            image_name=event.image_name,
            pixel_width=event.pixel_width,
            pixel_height=event.pixel_height,
            dpi_x=dpi_x,
            dpi_y=dpi_y,
            dpi_effective=dpi_effective,
            color_space=event.color_space,
            is_valid=True,
        )


def _extract_ctm_scale(ctm: TransformationMatrix) -> tuple[float, float]:
    """Extract horizontal and vertical scale factors from CTM.

    Returns:
        (sx, sy) where sx = sqrt(a^2 + c^2), sy = sqrt(b^2 + d^2).
    """
    sx = math.sqrt(ctm.a * ctm.a + ctm.c * ctm.c)
    sy = math.sqrt(ctm.b * ctm.b + ctm.d * ctm.d)
    return sx, sy
