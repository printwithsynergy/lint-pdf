"""Human-friendly check name registry for preflight reports and viewer.

Maps inspection_id → plain-English name + description suitable for
non-technical users (designers, print buyers, marketing managers).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckInfo:
    """Friendly name and description for a preflight check.

    ``v2_ids`` carries the Phase 1 v2-universe identifiers (e.g.
    ``("D-08",)``) when a v1-era LPDF code maps onto one or more
    canonical v2 IDs. The reports + dashboard surface both codes so
    operators can cross-reference the spec.
    """

    name: str
    description: str
    v2_ids: tuple[str, ...] = ()


def get_check_info(inspection_id: str) -> CheckInfo:
    """Look up friendly name for a check ID, with automatic fallback."""
    if inspection_id in CHECK_NAMES:
        return CHECK_NAMES[inspection_id]
    # Derive a reasonable name from the ID
    parts = inspection_id.replace("_", " ").replace("-", " ")
    return CheckInfo(name=parts.title(), description="")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CHECK_NAMES: dict[str, CheckInfo] = {
    # ── Image Quality ─────────────────────────────────────────────────────
    "LPDF_IMG_001": CheckInfo(
        "Low Image Resolution",
        "An image doesn't have enough detail for sharp printing — effective "
        "DPI (after the page CTM scales the image) is below the configured "
        "minimum. Fires on both colour and grayscale images.",
        v2_ids=("I-01", "I-02"),
    ),
    "LPDF_IMG_002": CheckInfo(
        "Excessive Resolution",
        "An image has far more detail than needed, inflating file size and "
        "RIP processing time without improving printed output.",
        v2_ids=("I-04",),
    ),
    "LPDF_IMG_003": CheckInfo(
        "Wrong Color Mode", "An image uses screen colors (RGB) instead of print colors (CMYK)."
    ),
    "LPDF_IMG_004": CheckInfo(
        "No Image Compression", "An image isn't compressed, making the file unnecessarily large."
    ),
    "LPDF_IMG_005": CheckInfo(
        "Inline Image",
        "A small image is embedded directly in the page stream instead of as a resource.",
    ),
    "LPDF_IMG_006": CheckInfo(
        "Upscaled Image",
        "An image has been scaled above 100% on the page, stretching it "
        "beyond its native pixel grid and causing visible blur on press.",
        v2_ids=("I-21",),
    ),
    "LPDF_IMG_007": CheckInfo(
        "LZW Compression", "Image uses LZW compression which is prohibited in some print standards."
    ),
    "LPDF_IMG_008": CheckInfo(
        "JPEG2000 Format",
        "Image uses JPEG2000 (JPX) compression, which is not supported by "
        "every RIP and is disallowed by several profiles (PDF/X-1a, "
        "GWG-Sheet-2022). Re-export with JPEG or Flate compression.",
        v2_ids=("I-11",),
    ),
    "LPDF_IMG_009": CheckInfo(
        "16-Bit Image", "Image uses 16-bit color depth, unusual for standard print workflows."
    ),
    "LPDF_IMG_010": CheckInfo(
        "OPI Reference",
        "Image carries an OPI (Open Prepress Interface) reference to an "
        "external high-resolution version. The low-res placeholder will "
        "print unless the OPI server is reachable at RIP time. PDF/X "
        "profiles disallow OPI; replace with the actual high-res image.",
        v2_ids=("I-24",),
    ),
    "LPDF_IMG_011": CheckInfo(
        "Alternate Image",
        "Image carries an alternate-images list — typically a low-resolution "
        "screen proxy alongside the print-resolution master. PDF/X profiles "
        "require alternates to be stripped before press.",
    ),
    "LPDF_IMG_012": CheckInfo(
        "OPI Reference In Image Resource",
        "OPI reference discovered while walking page-resource image XObjects "
        "(complementary to LPDF_IMG_010, which fires from content-stream "
        "events). Same remediation: substitute the high-res master.",
        v2_ids=("I-24",),
    ),
    "LPDF_IMG_013": CheckInfo(
        "Alternate Image In Page Resources",
        "Alternate-image reference discovered while walking page-resource "
        "XObjects (complementary to LPDF_IMG_011).",
    ),
    "LPDF_IMG_014": CheckInfo(
        "Sheared Image",
        "Image has a non-orthogonal CTM applied — a shear, not a pure "
        "scale + rotate. Shears compress detail along one axis and can "
        "produce moire on press.",
        v2_ids=("I-18",),
    ),
    "LPDF_IMG_015": CheckInfo(
        "Image Rotated Off-Axis",
        "Image is rotated at an angle that is not a multiple of 90° "
        "(non-orthogonal rotation). The RIP must resample at render time, "
        "softening edges. Pre-rotate the source image upstream.",
        v2_ids=("I-17",),
    ),
    "LPDF_IMG_016": CheckInfo(
        "Flipped Image",
        "Image is mirrored — the CTM has a negative determinant. Often "
        "intentional, but worth confirming on press where reflections can "
        "indicate a wrong export setting.",
        v2_ids=("I-19",),
    ),
    "LPDF_IMG_017": CheckInfo(
        "Extreme Scaling",
        "Image is scaled below 10% or above 1000% of its native pixel "
        "dimensions. At these extremes, file-size or quality is wasted — "
        "either downsample upstream (heavy upscaling) or remove the "
        "tiny-scale image entirely.",
        v2_ids=("I-22",),
    ),
    "LPDF_IMG_018": CheckInfo(
        "Dangling Image XObject Reference",
        "An image XObject in page resources resolves to a missing object (xref slot absent, null object, or cycle-detection sentinel) — the RIP will render a blank region.",
    ),
    "LPDF_IMG_019": CheckInfo(
        "Image XObject Missing /Subtype",
        "An image XObject dictionary has no /Subtype key, so the RIP can't know how to render it. The PDF is structurally malformed.",
    ),
    "LPDF_IMG_020": CheckInfo(
        "Image XObject Has Wrong /Subtype",
        "An image XObject's /Subtype is neither /Image nor /Form (e.g., deprecated /PS, or a vendor-invented subtype the RIP won't recognise).",
    ),
    # ── Fonts ─────────────────────────────────────────────────────────────
    "LPDF_FONT_001": CheckInfo(
        "Missing Font", "A font is not embedded — text may display incorrectly at the printer."
    ),
    "LPDF_FONT_002": CheckInfo(
        "Full Font Embedded",
        "The entire font is embedded instead of just the characters used, increasing file size.",
    ),
    "LPDF_FONT_003": CheckInfo(
        "System Font Used",
        "A standard system font is used which may render differently on other devices.",
    ),
    "LPDF_FONT_004": CheckInfo(
        "Type 3 Font",
        "User-drawn Type 3 font detected — quality may vary across RIPs.",
        v2_ids=("F-05",),
    ),
    "LPDF_FONT_005": CheckInfo(
        "Missing ToUnicode",
        "CID font is missing a ToUnicode map — text search and copy may not "
        "work. Currently fires on CID fonts only; the broader F-13 case "
        "(ToUnicode missing on any font subtype) is partially covered here.",
        v2_ids=("F-13",),
    ),
    "LPDF_FONT_006": CheckInfo(
        "Missing CIDSystemInfo",
        "CID font is missing system information needed for correct rendering.",
    ),
    "LPDF_FONT_007": CheckInfo(
        "No Font Encoding", "Font lacks encoding information — characters may map incorrectly."
    ),
    "LPDF_FONT_008": CheckInfo(
        "TrueType Not Embedded", "A TrueType font is referenced but not embedded in the file."
    ),
    "LPDF_FONT_009": CheckInfo(
        "OpenType Not Embedded", "An OpenType/CFF font is referenced but not embedded."
    ),
    "LPDF_FONT_010": CheckInfo(
        "Incomplete Font", "Font descriptor is present but the actual font data is missing."
    ),
    "LPDF_FONT_011": CheckInfo(
        "Multiple Master Font",
        "Multiple Master font detected — limited RIP support.",
        v2_ids=("F-10",),
    ),
    "LPDF_FONT_012": CheckInfo(
        "Faux Bold",
        "Software-simulated bold detected — the renderer is synthesising "
        "weight from a non-bold font variant rather than using a real bold "
        "weight, so glyphs print thinner and less consistently than expected. "
        "Replace with the actual bold variant or accept the design choice.",
        v2_ids=("F-18",),
    ),
    "LPDF_FONT_013": CheckInfo(
        "Faux Italic",
        "Software-simulated italic detected — the renderer is shearing the "
        "upright glyph rather than using a true italic variant. Glyph forms "
        "are not the designer's italic intent. Replace with the actual italic "
        "variant or accept the design choice.",
        v2_ids=("F-19",),
    ),
    "LPDF_FONT_014": CheckInfo(
        "Damaged Font", "The font program appears corrupt or has a type mismatch."
    ),
    "LPDF_FONT_015": CheckInfo(
        "Restricted Font Embedding Licence",
        "Font's OS/2 fsType bit advertises a licence restriction (restricted / preview-and-print / editable embedding). Verify vendor licensing before distributing this PDF.",
        v2_ids=("F-38",),
    ),
    "LPDF_FONT_016": CheckInfo(
        "Font Subset Violates No-Subsetting Policy",
        "Font vendor set the OS/2 no_subsetting bit, but the PDF subsetted this font anyway. Disabled by default; enable for licensed-font-only workflows.",
    ),
    "LPDF_FONT_017": CheckInfo(
        "Outline Embed Violates Bitmap-Only Policy",
        "Font vendor set the OS/2 bitmap_only bit, but the PDF embedded outline data. Disabled by default; enable for licensed-font-only workflows.",
    ),
    # ── Color ─────────────────────────────────────────────────────────────
    "LPDF_COLOR_001": CheckInfo(
        "Device-Dependent Color",
        "Color is specified without a profile, so output will vary by device.",
    ),
    "LPDF_COLOR_002": CheckInfo(
        "Spot Color Without Fallback", "A spot color has no process color fallback for proofing."
    ),
    "LPDF_COLOR_003": CheckInfo(
        "Lab Color Used", "CIE Lab color used — may require special handling at the RIP."
    ),
    "LPDF_COLOR_004": CheckInfo(
        "Ink Coverage Too High",
        "Total ink exceeds the maximum for this paper type, risking smearing or drying issues.",
    ),
    "LPDF_COLOR_005": CheckInfo(
        "Registration Colour Used As Artwork Fill",
        "Registration colour (100% on every CMYK channel) is reserved for "
        "crop marks and trapping guides, never artwork. Fires when "
        "registration is used as a fill — typically a registration-only "
        "swatch picked up by mistake during design.",
        v2_ids=("C-51",),
    ),
    "LPDF_COLOR_006": CheckInfo(
        "No Output Intent",
        "Document declares no Output Intent. Without one, every downstream "
        "tool guesses at the destination colour space — proofs and press "
        "output drift unpredictably. Add an Output Intent ICC referencing "
        "the target press condition.",
        v2_ids=("C-19",),
    ),
    "LPDF_COLOR_007": CheckInfo(
        "Mixed Color Spaces",
        "Different color spaces used on the same page may cause inconsistency.",
    ),
    "LPDF_COLOR_008": CheckInfo(
        "CalRGB Color", "Calibrated RGB color used — should be converted to CMYK for print."
    ),
    "LPDF_COLOR_009": CheckInfo(
        "CalGray Color", "Calibrated gray color used — should use DeviceGray for consistency."
    ),
    "LPDF_COLOR_010": CheckInfo(
        "Indexed Color", "Indexed/palette color used — limited color range."
    ),
    "LPDF_COLOR_011": CheckInfo(
        "Pattern Color Space", "Pattern-based color used — may render differently across RIPs."
    ),
    "LPDF_COLOR_012": CheckInfo("Separation Color", "Separation color space detected."),
    "LPDF_COLOR_013": CheckInfo("DeviceN Color", "Multi-channel DeviceN color detected."),
    "LPDF_COLOR_014": CheckInfo(
        "Color Space Inventory", "Summary of color space types used in the document."
    ),
    "LPDF_COLOR_015": CheckInfo(
        "Device-Dependent Colour With OutputIntent",
        "A device-dependent colour space (DeviceRGB / DeviceCMYK / "
        "DeviceGray) is used while an OutputIntent is present. The "
        "DeviceRGB branch is disallowed under PDF/X-4 entirely; "
        "DeviceCMYK and DeviceGray are allowed but ICC-based alternatives "
        "are recommended for predictable colour. Re-tag with an ICCBased "
        "alternative.",
        v2_ids=("C-01",),
    ),
    "LPDF_COLOR_016": CheckInfo(
        "Impure Gray",
        "Object uses a CMY-built gray (C ≈ M ≈ Y, components within 5% of "
        "each other) rather than a single-channel DeviceGray or pure K. "
        "Multi-ink grays drift on press and waste ink — convert to "
        "DeviceGray or pure K.",
        v2_ids=("C-53",),
    ),
    "LPDF_COLOR_017": CheckInfo(
        "Impure Black",
        "Black areas use C, M, or Y in addition to K. Multi-ink blacks "
        "are sensitive to press registration and produce visible fringes "
        "where neighbouring colours overprint. Replace with pure K or a "
        "controlled rich-black recipe.",
        v2_ids=("C-52",),
    ),
    "LPDF_COLOR_018": CheckInfo(
        "Untagged Color", "Color space used without an associated ICC profile."
    ),
    "LPDF_COLOR_019": CheckInfo("Wide Gamut Color", "Color is outside the typical print gamut."),
    "LPDF_COLOR_020": CheckInfo(
        "Overink Warning", "Multiple color operations accumulate high ink levels."
    ),
    "LPDF_COLOR_021": CheckInfo(
        "Rich Black Text",
        "Text uses more than one CMYK ink — pure K (100/0/0/0) is recommended "
        "at every size to avoid misregistration.",
        v2_ids=("C-50",),
    ),
    # ── Page Geometry ─────────────────────────────────────────────────────
    "LPDF_BOX_001": CheckInfo(
        "Missing Trim/Bleed Box",
        "Page boundaries needed for cutting and bleed are not defined. The "
        "analyzer emits one finding per missing box; the discriminator lives "
        "in `details.missing_box` (`TrimBox` or `BleedBox`).",
        v2_ids=("P-03", "P-04"),
    ),
    "LPDF_BOX_002": CheckInfo(
        "Box Hierarchy Violated",
        "Page boxes (Media, Crop, Bleed, Trim) are not properly nested per "
        "ISO 32000-2 §14.11.2. Fires on three conditions discriminated by "
        "`details.violation`: CropBox extends outside MediaBox, BleedBox "
        "extends outside CropBox, or TrimBox extends outside BleedBox.",
        v2_ids=("P-07",),
    ),
    "LPDF_BOX_003": CheckInfo(
        "Insufficient Bleed",
        "One or more sides have less bleed allowance than the configured "
        "minimum. White edges may show after cutting if the image doesn't "
        "extend far enough past the trim edge.",
        v2_ids=("P-09",),
    ),
    "LPDF_BOX_004": CheckInfo("Empty Page", "Page has no visible content."),
    "LPDF_BOX_005": CheckInfo(
        "Content In Safety Margin",
        "Critical content sits within the configured safety margin of the "
        "trim edge. Movement during finishing can shift this content into "
        "the cut zone — pull it inward upstream.",
        v2_ids=("P-33",),
    ),
    "LPDF_BOX_006": CheckInfo(
        "Content Beyond Bleed",
        "Content extends outside the BleedBox. Anything past the bleed will "
        "be clipped by the RIP and is wasted file size at best, or evidence "
        "of a misconfigured export at worst.",
        v2_ids=("P-28",),
    ),
    "LPDF_BOX_007": CheckInfo(
        "UserUnit Scaling Active",
        "Page uses a UserUnit other than 1.0 — coordinates are scaled "
        "globally. Common in large-format work but can confuse imposition "
        "and downstream measurements that assume default units.",
        v2_ids=("P-16",),
    ),
    "LPDF_BOX_008": CheckInfo(
        "Non-Standard Page Rotation",
        "Page has a /Rotate value other than 0° (typically 90°/180°/270°). "
        "RIPs honour rotation, but imposition tools and operator workflows "
        "expect upright pages by default.",
        v2_ids=("P-14",),
    ),
    "LPDF_BOX_009": CheckInfo(
        "Inconsistent Page Sizes",
        "Document contains pages of different sizes. Mixed-size jobs need "
        "explicit handling at imposition; verify this is intentional.",
        v2_ids=("P-13",),
    ),
    "LPDF_BOX_010": CheckInfo(
        "Page Size Mismatch",
        "Page dimensions don't match the product size declared on the "
        "profile (`expected_page_width_mm` / `expected_page_height_mm`). "
        "Tolerance defaults to 0.5mm; either orientation is accepted.",
        v2_ids=("P-12",),
    ),
    # ── Transparency ──────────────────────────────────────────────────────
    "LPDF_TRANS_001": CheckInfo(
        "Transparency Used", "Page uses transparency which must be flattened for older workflows."
    ),
    "LPDF_TRANS_002": CheckInfo(
        "Transparency × Overprint Interaction",
        "Both transparency and overprint are active on the same page. The "
        "interaction between alpha-blended objects and overprinted spot "
        "colours is RIP-specific — flattening behaviour can swap colours "
        "or drop objects unpredictably. Verify on a proof.",
        v2_ids=("TR-19",),
    ),
    "LPDF_TRANS_003": CheckInfo(
        "Soft Mask", "Image uses a soft mask, increasing rendering complexity."
    ),
    "LPDF_TRANS_004": CheckInfo(
        "Low Opacity", "Content has very low opacity and may be nearly invisible in print."
    ),
    "LPDF_TRANS_005": CheckInfo(
        "Transparency Group", "A transparency group is defined on this page."
    ),
    # ── Overprint ─────────────────────────────────────────────────────────
    "LPDF_OVER_001": CheckInfo(
        "Overprint On",
        "Overprint is enabled — colors will mix where they overlap instead of knocking out.",
    ),
    "LPDF_OVER_002": CheckInfo(
        "Overprint Off for Spot",
        "Overprint is disabled for a spot color, which may cause unexpected knockouts.",
    ),
    "LPDF_OVER_003": CheckInfo(
        "Overprint Mode Mismatch", "Overprint mode setting is inconsistent."
    ),
    # ── Document Structure ────────────────────────────────────────────────
    "LPDF_STRUCT_001": CheckInfo(
        "JavaScript Found",
        "Document contains JavaScript actions. Print workflows strip JS; "
        "PDF/X profiles prohibit it outright. Remove before press.",
        v2_ids=("M-17",),
    ),
    "LPDF_STRUCT_002": CheckInfo(
        "Form Fields Present",
        "Interactive form fields (text inputs, buttons, dropdowns, "
        "signatures) detected. Forms are stripped at press time and may "
        "indicate the wrong file was uploaded.",
    ),
    "LPDF_STRUCT_003": CheckInfo(
        "PDF Layers Detected",
        "Optional Content Groups (OCGs / layers) are present. Layers are "
        "valid in PDF/X-4 and later, but verify the intended layers are "
        "marked printable and the rest are hidden — RIPs honour OCG "
        "visibility.",
    ),
    "LPDF_STRUCT_004": CheckInfo(
        "Embedded Files",
        "Document carries embedded file attachments. Strip before press: "
        "attachments inflate file size, complicate auditing, and are "
        "disallowed by most PDF/X profiles.",
        v2_ids=("M-19",),
    ),
    # ── Document Info ─────────────────────────────────────────────────────
    "LPDF_DOC_001": CheckInfo(
        "Multiple Page Sizes",
        "Document contains pages of different sizes which may complicate imposition.",
    ),
    # ── Metadata ──────────────────────────────────────────────────────────
    "LPDF_META_001": CheckInfo(
        "No XMP Metadata",
        "Document has no XMP metadata stream. Required by PDF/X-4 and "
        "GWG-2022 packaging profiles, and used by most MIS systems for "
        "automation. Add an XMP block at export time.",
        v2_ids=("M-06",),
    ),
    # ── Annotations ───────────────────────────────────────────────────────
    "LPDF_ANNOT_001": CheckInfo(
        "Printable Annotation",
        "A printable annotation is inside the trim area and will appear in output.",
    ),
    "LPDF_ANNOT_003": CheckInfo(
        "Link Annotation", "A clickable link annotation is present on this page."
    ),
    # ── Accessibility ─────────────────────────────────────────────────────
    "LPDF_ACCESS_001": CheckInfo(
        "Not Tagged", "Document has no structure tree — it's not accessible to screen readers."
    ),
    "LPDF_ACCESS_002": CheckInfo(
        "No Language Set", "Document language is not specified, reducing accessibility."
    ),
    "LPDF_ACCESS_004": CheckInfo(
        "Missing Document Language", "The /Lang entry is missing from the document catalog."
    ),
    "LPDF_ACCESS_012": CheckInfo(
        "No Output Intent for Contrast",
        "Cannot verify text-background contrast for accessibility without an output intent.",
    ),
    # ── Text & Hairlines ──────────────────────────────────────────────────
    "LPDF_TEXT_001": CheckInfo(
        "Small Text",
        "Text is below the configured minimum readable size for print "
        "(default 6pt). Below this threshold, ink spread on press makes "
        "letterforms close up and lose legibility — especially on "
        "uncoated stocks.",
        v2_ids=("F-22",),
    ),
    "LPDF_TEXT_004": CheckInfo(
        "White Text Detected",
        "White text instance(s) found on page. White text only renders if "
        "the underlying inks knock out — verify the intent is correct and "
        "isn't accidentally invisible content.",
    ),
    "LPDF_HAIR_001": CheckInfo(
        "Hairline Stroke",
        "Stroke width is below the configured minimum (typically 0.25pt). "
        "Hairlines may disappear entirely on offset presses or print "
        "inconsistently across plates. Increase the stroke weight upstream.",
        v2_ids=("LA-01",),
    ),
    "LPDF_HAIR_002": CheckInfo(
        "Small Text Built With Thin Stroke",
        "Stroked text below the minimum size with a thin stroke. The "
        "combination is a double legibility risk — small glyphs with "
        "fragile stroke widths.",
    ),
    "LPDF_PATH_002": CheckInfo(
        "White Fill Path", "A white-filled path may knock out background content unintentionally."
    ),
    "LPDF_STROKE_003": CheckInfo(
        "Butt Cap on Thin Line",
        "A butt line cap on a thin stroke may cause visible gaps — round cap recommended.",
    ),
    "LPDF_STROKE_007": CheckInfo(
        "Rich Black Stroke",
        "A thin stroke (0.5-1.0pt) uses more than one CMYK ink - pure K or a "
        "single spot is recommended on fine line work.",
    ),
    # ── Ink & Advanced Color ──────────────────────────────────────────────
    "LPDF_INK_001": CheckInfo("TAC Heatmap", "Total Area Coverage data for this page."),
    "LPDF_INK_002": CheckInfo("Ink Separation Data", "Per-channel ink usage statistics."),
    "LPDF_INK_003": CheckInfo(
        "Ink Channel Inventory", "Summary of all ink channels used in the document."
    ),
    "LPDF_ADV_002": CheckInfo(
        "Ink Savings Estimate", "Analysis of potential ink savings through GCR optimization."
    ),
    "LPDF_ADV_004": CheckInfo(
        "No Spectral Data", "No CxF spectral measurement data found in output intents."
    ),
    "LPDF_ADV_005": CheckInfo(
        "Black Composition", "Breakdown of how black is built (pure K, rich black, registration)."
    ),
    # ── Standards Compliance ──────────────────────────────────────────────
    "LPDF_STD_001": CheckInfo("G7 Compliance", "G7 process control readiness assessment."),
    "LPDF_STD_002": CheckInfo("GRACoL Compliance", "GRACoL 2006 compliance validation."),
    "LPDF_STD_003": CheckInfo("ISO 12647 Compliance", "ISO 12647 standard compliance check."),
    # ── ICC Profiles ──────────────────────────────────────────────────────
    "LPDF_ICC_001": CheckInfo(
        "No ICC Profile", "No ICC color profile embedded for color-managed output."
    ),
    "LPDF_ICC_002": CheckInfo(
        "Invalid ICC Profile", "The embedded ICC profile is corrupt or invalid."
    ),
    "LPDF_ICC_003": CheckInfo(
        "ICC Version Mismatch", "ICC profile version doesn't match the PDF specification."
    ),
    "LPDF_ICC_004": CheckInfo(
        "Wrong ICC Device Class", "ICC profile device class doesn't match usage context."
    ),
    # ── Spot Colors ───────────────────────────────────────────────────────
    "LPDF_SPOT_001": CheckInfo(
        "Unknown Spot Color", "A spot color is used that isn't in a standard color book."
    ),
    "LPDF_SPOT_002": CheckInfo(
        "Spot Color Fallback Issue",
        "The process color fallback for a spot color may not be accurate.",
    ),
    "LPDF_SPOT_003": CheckInfo(
        "Similar Spot Names", "Multiple spot colors have very similar names — may be duplicates."
    ),
    # ── Barcode ───────────────────────────────────────────────────────────
    "LPDF_BARCODE_001": CheckInfo(
        "Barcode Detected", "A potential barcode pattern was identified on this page."
    ),
    "LPDF_BARCODE_025": CheckInfo(
        "Low Barcode Resolution",
        "The barcode area resolution is below the minimum for reliable scanning.",
    ),
    # ── Packaging ─────────────────────────────────────────────────────────
    "LPDF_PKG_001": CheckInfo(
        "Dieline Detected", "A die line layer was identified in this packaging file."
    ),
    "LPDF_PKG_002": CheckInfo(
        "Missing Dieline", "No die line detected — expected for packaging artwork."
    ),
    # ══ AI CHECKS ═════════════════════════════════════════════════════════
    # ── WCAG Contrast ─────────────────────────────────────────────────────
    "AI_WCAG_001": CheckInfo(
        "Low Color Contrast",
        "Text doesn't have enough contrast against its background for comfortable reading.",
    ),
    "AI_WCAG_002": CheckInfo(
        "Below WCAG AA", "Text-background contrast is below the WCAG AA accessibility standard."
    ),
    # ── FDA Nutrition ─────────────────────────────────────────────────────
    "AI_FDA_001": CheckInfo(
        "Calories Font Too Small",
        "The Calories declaration may be below the FDA's minimum font size requirement.",
    ),
    "AI_FDA_002": CheckInfo(
        "NFP Text Too Small",
        "Nutrition Facts text is below the minimum readable size required by FDA.",
    ),
    "AI_FDA_003": CheckInfo(
        "Missing Bold in NFP", "Required bold formatting is missing from Nutrition Facts headings."
    ),
    "AI_FDA_004": CheckInfo(
        "Missing Nutrients", "Required nutrients may be missing from the Nutrition Facts panel."
    ),
    "AI_FDA_005": CheckInfo(
        "FDA Label Warning", "A potential FDA labeling compliance issue was detected."
    ),
    # ── EU Food Labeling ──────────────────────────────────────────────────
    "AI_EU1169_001": CheckInfo(
        "EU Font Size Violation",
        "Text is below the minimum x-height required by EU Regulation 1169/2011.",
    ),
    "AI_EU1169_002": CheckInfo(
        "Allergen Not Emphasized",
        "An allergen may not be properly emphasized as required by EU food labeling rules.",
    ),
    "AI_EU1169_003": CheckInfo(
        "EU Nutrition Format", "Nutrition information format doesn't comply with EU FIR 1169/2011."
    ),
    # ── Pharmaceutical ────────────────────────────────────────────────────
    "AI_PHARMA_001": CheckInfo(
        "Pharma Font Too Small",
        "Text is below the minimum size required for pharmaceutical labeling.",
    ),
    # ── Brand Palette ─────────────────────────────────────────────────────
    "AI_BRAND_001": CheckInfo(
        "No Brand Palette", "No brand color palette is configured for compliance checking."
    ),
    "AI_BRAND_002": CheckInfo(
        "Brand Color Deviation", "A color deviates from the configured brand palette."
    ),
    # ── Spell Check ───────────────────────────────────────────────────────
    "AI_SPELL_001": CheckInfo(
        "Misspelled Word", "A potentially misspelled word was detected in the document text."
    ),
    # ── Language Detection ────────────────────────────────────────────────
    "AI_LANG_001": CheckInfo("Language Detected", "The document language has been identified."),
    # ── Duplicate Detection ───────────────────────────────────────────────
    "AI_DUP_001": CheckInfo(
        "Duplicate Content", "Duplicate or near-duplicate content detected across pages."
    ),
    # ── Image Quality (AI) ────────────────────────────────────────────────
    "AI_IQ_001": CheckInfo(
        "Image Quality Issue", "An image quality concern was detected (blur, noise, or artifacts)."
    ),
    "AI_SIM_001": CheckInfo(
        "Similar Images", "Very similar or duplicate images detected in the document."
    ),
    "AI_NSFW_001": CheckInfo(
        "Content Safety Flag", "Potentially inappropriate content was flagged for review."
    ),
    # ── Logo Detection ────────────────────────────────────────────────────
    "AI_LOGO_001": CheckInfo("Logo Not Found", "Expected logo was not detected on this page."),
    # ── Safe Zone ─────────────────────────────────────────────────────────
    "AI_SZ_001": CheckInfo(
        "Safe Zone Violation", "Content is placed in a restricted bleed or safety zone area."
    ),
    # ── Dieline Detection ─────────────────────────────────────────────────
    "AI_DIE_003": CheckInfo(
        "No Dieline Found", "No die line detected — file does not appear to be packaging artwork."
    ),
    # ── Regulatory Symbols ────────────────────────────────────────────────
    "AI_RSYM_001": CheckInfo(
        "Missing Regulatory Symbol", "A required regulatory symbol may be missing from the artwork."
    ),
    # ── Processing Steps ──────────────────────────────────────────────────
    "AI_PSTEP_001": CheckInfo("Processing Steps", "Processing step layer or instruction detected."),
    # ── Text as Outlines ──────────────────────────────────────────────────
    "AI_TAO_001": CheckInfo(
        "Text Not Outlined", "Text has not been converted to outlines for guaranteed rendering."
    ),
    # ── Version Comparison ────────────────────────────────────────────────
    "AI_VDIFF_001": CheckInfo(
        "No Reference File", "No reference file provided for version comparison."
    ),
    # ── Auto Preflight Profile ────────────────────────────────────────────
    "AI_AFP_001": CheckInfo(
        "Auto Profile Suggestion", "An automatic preflight profile recommendation was generated."
    ),
    # ── Document Classification ───────────────────────────────────────────
    "AI_FCLASS_001": CheckInfo(
        "Document Classification", "The document type has been automatically classified."
    ),
    # ── GHS Chemical Labeling ─────────────────────────────────────────────
    "AI_GHS_001": CheckInfo(
        "Missing GHS Elements", "Required GHS hazard label elements may be missing."
    ),
    # ── Cannabis Labeling ─────────────────────────────────────────────────
    "AI_CANN_001": CheckInfo(
        "Cannabis Warning Missing",
        "Required cannabis warning symbols or statements may be missing.",
    ),
    # ── Alcohol Labeling ──────────────────────────────────────────────────
    "AI_ALC_001": CheckInfo(
        "Alcohol Label Issue", "Required alcohol labeling elements may be missing."
    ),
    # ── Cosmetics Labeling ────────────────────────────────────────────────
    "AI_COSM_001": CheckInfo(
        "Cosmetics Label Issue", "Required cosmetics labeling elements may be missing."
    ),
    # ── Organic Certification ─────────────────────────────────────────────
    "AI_ORG_001": CheckInfo(
        "Organic Seal Issue", "Organic certification mark may be missing or incorrectly placed."
    ),
    # ── AI Scan Marker ────────────────────────────────────────────────────
    "AI_SCAN_001": CheckInfo("AI Scan Complete", "Summary of the AI analysis pipeline run."),
    # ══════════════════════════════════════════════════════════════════════
    # Auto-filled entries — derived from analyzer emit-site messages
    # via audit/phase-1/fill-names. Hand-polished names for AI checks.
    # Grouped by prefix in original-registry style.
    # ══════════════════════════════════════════════════════════════════════
    # ── AI Auto Preflight Profile ───────────────────────────────────────────
    "AI_AFP_002": CheckInfo(
        "Recommended Preflight Profile",
        "Preflight profile recommendation emitted with confidence score.",
    ),
    "AI_AFP_003": CheckInfo(
        "Preflight profile recommendation has low confidence",
        "Preflight profile recommendation has low confidence (N). Manual selection may be more appropriate.",
    ),
    # ── AI Alcohol ──────────────────────────────────────────────────────────
    "AI_ALC_002": CheckInfo(
        "TTB/EU Alcohol Label Format",
        "Alcohol label format deviates from TTB COLA or EU wine/spirits requirements.",
    ),
    # ── AI Brand Specification ──────────────────────────────────────────────
    "AI_BRAND_003": CheckInfo(
        "Brand Spec Deviation",
        "Artwork deviates from the active brand specification.",
    ),
    # ── AI Cannabis ─────────────────────────────────────────────────────────
    "AI_CANN_002": CheckInfo(
        "Cannabis Potency/Dosage Issue",
        "Potency or dosage labeling deviates from state cannabis requirements.",
    ),
    # ── AI Cosmetics ────────────────────────────────────────────────────────
    "AI_COSM_002": CheckInfo(
        "Cosmetic Ingredient List Issue",
        "Cosmetic ingredient list deviates from INCI ordering or minimum-type-size rules.",
    ),
    # ── AI Dieline Detection ────────────────────────────────────────────────
    "AI_DIE_001": CheckInfo(
        "Dieline Detected",
        "A dieline was detected via spot name, layer name, or AI vision fallback.",
        v2_ids=("D-01",),
    ),
    "AI_DIE_002": CheckInfo(
        "No Dieline Detected",
        "Expected dieline not found in a packaging file. Verify spot naming or AI detection availability.",
    ),
    # ── Dieline Quality (Batch 4 — T3) ─────────────────────────────────────
    "LPDF_DIE_MISSING": CheckInfo(
        "Dieline Missing",
        "Expected dieline not present in a packaging file. Neither name-match nor vision fallback detected a cut contour.",
    ),
    "LPDF_DIE_MULTI_COLOR": CheckInfo(
        "Dieline Multi-Colour",
        "Dieline layer / spot contains multiple stroke colours — a clean cut path should be exactly one ink.",
    ),
    "LPDF_DIE_ZORDER": CheckInfo(
        "Dieline Below Artwork",
        "Dieline is painted before artwork in the content stream — the cutter marker should sit on top of all content. Move the dieline layer to the top of the layer stack before exporting.",
        v2_ids=("D-06",),
    ),
    "LPDF_DIE_KNOCKOUT": CheckInfo(
        "Dieline Set To Knockout",
        "Dieline stroke is set to knockout (OP=false) — underlying inks will have gaps along cut lines. Enable 'Overprint Stroke' on the dieline layer in Illustrator / InDesign.",
        v2_ids=("D-07",),
    ),
    "LPDF_DIE_BLEND_MODE": CheckInfo(
        "Dieline Has Non-Normal Blend Mode",
        "Dieline spot is painted with a blend mode other than Normal (Multiply, Darken, etc.). Cutter spots are layer-extracted process controls, not artwork — non-Normal blend modes are silently dropped or composited by the RIP, leaving the cut plate missing or in the wrong colour. Set blend mode to Normal on the dieline layer.",
        v2_ids=("D-08",),
    ),
    "LPDF_DIE_OPACITY_LOW": CheckInfo(
        "Dieline Has Reduced Opacity",
        "Dieline spot is painted with alpha < 100% (semi-transparent). Cutter spots are layer-extracted process controls, not artwork — partial transparency does not survive RIP separation, so the cut plate either drops to zero coverage or composites into the substrate. Set opacity to 100% on the dieline layer in Illustrator / InDesign.",
        v2_ids=("D-09",),
    ),
    "LPDF_PAGE_BLEED_PAST_DIELINE": CheckInfo(
        "Page BleedBox Extends Past Dieline",
        "The page's declared /BleedBox extends past the dieline polygon envelope. The press-side bleed allowance does not fit within the cutter region — imposition will waste paper or clip adjacent units on a multi-up sheet. Either tighten the BleedBox in the export profile or expand the dieline so the bleed sits inside it.",
        v2_ids=("P-30",),
    ),
    "LPDF_TEXT_ON_DIELINE_PATH": CheckInfo(
        "Text Overlaps Dieline Cut Path",
        "Text region overlaps the dieline cut path. At the cutter, glyphs will be physically sliced — the printed product reads as a typo even though the source artwork is correct. Distinct from text-near-fold (clearance) — this fires on actual intersection. Reposition the text or move the dieline before re-exporting.",
        v2_ids=("F-32",),
    ),
    "LPDF_DIE_AS_ART": CheckInfo(
        "Dieline Spot Used As Fill",
        "Dieline spot colour is applied as a fill, not just a stroke. The cutter will follow the filled region as a closed path. Change the fill to the intended print ink (common Canva-export bug).",
        v2_ids=("D-15",),
    ),
    "LPDF_DIE_LAYER_CONTENT": CheckInfo(
        "Foreign Content On Dieline Layer",
        "Non-dieline paint operation(s) found inside a dieline-named OCG marked-content block. Artwork on the cutter plate will print on every copy — move it to a non-dieline layer.",
        v2_ids=("D-04",),
    ),
    "LPDF_DIE_CONTENT_OUTSIDE": CheckInfo(
        "Content Outside Dieline",
        "Paint bbox extends beyond the dieline polygon envelope by more than the configured tolerance. Content may be clipped or trimmed in production.",
        v2_ids=("D-15",),
    ),
    "LPDF_DIE_VARNISH_COLLISION": CheckInfo(
        "Varnish Applied Inside VarnishFree Region",
        "Varnish / coating spot overlaps a VarnishFree (no-coating) region. Remove varnish from the marked region in the source file before exporting.",
    ),
    "LPDF_DIE_EXCESSIVE_BLEED": CheckInfo(
        "Excessive Bleed Past Dieline",
        "Artwork extends past the dieline polygon by more than the configured max_bleed_mm. Excessive bleed wastes paper and may complicate multi-up imposition.",
    ),
    "LPDF_INK_SUBSTRATE": CheckInfo(
        "TAC Exceeds Substrate Limit",
        "Observed max Total Area Coverage exceeds the limit typical for the declared substrate (uncoated offset 280%, coated 300%, newsprint 240%, digital 320%, flexo 260%, gravure 300%, large-format 280%).",
        v2_ids=("C-48",),
    ),
    "LPDF_SPOT_NONCANONICAL": CheckInfo(
        "Non-Canonical Spot Name",
        "Spot colour name doesn't match the lintPDF canonical taxonomy (CutContour, Crease, Perforation, KissCut, ThroughCut, White, Varnish, VarnishFree). Renaming to canonical names improves cross-vendor compatibility (Esko, PackZ, ArtiosCAD).",
    ),
    "LPDF_PSTEP_SUGGEST": CheckInfo(
        "ISO 19593-1 Processing Step Suggestion",
        "Spot ink with a recognised production-process name (cut, crease, perforation, varnish, white) should be tagged with the matching ISO 19593-1 ProcessingSteps group so finishing equipment treats it as a process rather than a printable ink.",
    ),
    "LPDF_PSTEP_POSITIONS": CheckInfo(
        "ISO 19593-1 Positions Suggestion",
        "Spot ink whose name suggests a positioning aid (registration / trim mark / colour bar) should be tagged under the ISO 19593-1 'Positions' ProcessingSteps group so prepress strips it before plating.",
    ),
    "LPDF_PSTEP_WHITE_SUBTYPE": CheckInfo(
        "ISO 19593-1 White Subtype Suggestion",
        "White spot whose name carries a hint (Underprint / Overprint / Print / Knockout) should be tagged with the matching ISO 19593-1 White subtype.",
    ),
    "LPDF_SPOT_DEPRECATED_PANTONE": CheckInfo(
        "Deprecated Pantone Suffix",
        "Spot name uses a legacy Pantone suffix (CV, CVC, CVU, CVP, CVUX) that was retired with the post-2008 Pantone book; verify the spot still maps to the intended colour.",
        v2_ids=("C-32",),
    ),
    "LPDF_VIEWER_DISPLAY_TITLE": CheckInfo(
        "Viewer DisplayDocTitle",
        "Catalog /ViewerPreferences /DisplayDocTitle should be true so PDF readers show the document's metadata title rather than its filename. Required by WCAG 2.1 SC 2.4.2 when the title is the meaningful identifier.",
    ),
    "LPDF_XMP_GWG_TRAIL": CheckInfo(
        "GWG Audit Trail Missing",
        "No GWG audit-trail namespace was found in XMP metadata. The PDF has not been through a Ghent Workgroup-aware preflight tool.",
    ),
    "LPDF_TRANS_BLEND_CS_MISMATCH": CheckInfo(
        "Transparency Blend / OutputIntent CS Mismatch",
        "Transparency-group blending colour space differs from the OutputIntent destination colour space. Flatteners may render the page colour-shifted relative to the printed proof.",
    ),
    "LPDF_TRANS_ON_SPOT": CheckInfo(
        "Transparency on Spot Page",
        "Page declares Separation / DeviceN spot colour spaces and also has transparency events. Some RIPs flatten transparency to process colour and lose the spot.",
    ),
    "LPDF_TEXT_REVERSE_THIN": CheckInfo(
        "Reverse Text Minimum Stroke",
        "Small white (reverse / knockout) text was rendered without a stroke. Add a ≥0.5pt stroke or use ≥12pt for legibility on press.",
        v2_ids=("F-24",),
    ),
    "LPDF_PDFVT_STRUCTURE": CheckInfo(
        "PDF/VT Structural Issue",
        "Document declares PDF/VT (variable-data printing per ISO 16612-2) but lacks the required structural elements such as /Catalog /DPartRoot.",
    ),
    "LPDF_TOBACCO_WARNING_AREA": CheckInfo(
        "Tobacco Warning Area Below Threshold",
        "Tobacco / cigarette artwork's health warning covers less than the regulator-required fraction of the page surface (EU TPD2 65%, US FDA 50%, AU/NZ 75%).",
    ),
    "LPDF_BARCODE_GS1_AI": CheckInfo(
        "Invalid GS1 AI Syntax",
        "Decoded barcode payload contains a GS1 Application Identifier whose value does not satisfy its expected syntax (length / character set).",
    ),
    "LPDF_BARCODE_UDI": CheckInfo(
        "UDI Barcode Issues",
        "UDI (Unique Device Identifier) barcode is missing required AIs (e.g. AI 01 GTIN) or none of the recommended production AIs (17 / 10 / 21) are present.",
    ),
    "LPDF_BARCODE_EU_DPP": CheckInfo(
        "EU DPP URL Issues",
        "EU Digital Product Passport URL in a decoded barcode payload is not HTTPS or contains malformed characters.",
    ),
    "LPDF_DIGIMARC_HINT": CheckInfo(
        "Digimarc Watermark Hint",
        "XMP metadata contains a Digimarc namespace or URL token. The actual watermark requires the licensed Digimarc SDK to verify.",
    ),
    "LPDF_GRAIN_MISSING": CheckInfo(
        "Grain Direction Missing",
        "XMP metadata carries no grain-direction key. Downstream press / finishing operations may not get the substrate orientation from this PDF.",
    ),
    "LPDF_TEXT_SOFT_MASK": CheckInfo(
        "Text Under Soft Mask",
        "Text rendered on a page that declares a soft-mask ExtGState. Some RIPs lose legibility on text under a soft mask; verify rendering at production resolution.",
        v2_ids=("TR-13",),
    ),
    "AI_ALC_003": CheckInfo(
        "Wine / Spirits Specific Compliance",
        "Wine or spirits labelling has issues per TTB 27 CFR 4 / 5 or EU 1308/2013 — missing 'Contains Sulfites', vintage / estate-bottled without an appellation, or spirits without a proof statement.",
    ),
    "LPDF_DIE_TOO_SMALL": CheckInfo(
        "Dieline Feature Below Cutter Resolution",
        "Dieline polygon's bbox or perimeter is smaller than the cutting machine can track cleanly (default 1.0mm threshold). Tiny features tear surrounding stock or crumble during die-cutting.",
    ),
    "LPDF_DIE_WHITE_GAP": CheckInfo(
        "White Underprint Gap",
        "White / OpaqueWhite underprint covers less than the configured fraction of the dieline area (default 95%). On clear or foil substrates, gaps in white underprint let the substrate show through colour artwork.",
    ),
    "LPDF_BARCODE_QUIET_ZONE": CheckInfo(
        "Barcode Quiet Zone Conflict",
        "An image XObject (likely a barcode) sits closer than the configured quiet zone (default 2.5mm) to a dieline / fold / crease line. The cut blade or fold crease may pass through the barcode quiet zone and break scanability.",
    ),
    "LPDF_TEXT_NEAR_FOLD": CheckInfo(
        "Text Near Fold Line",
        "Text region within the configured clearance (default 3.0mm) of a fold / crease / score line. Text that crosses or hugs a fold gets bent and becomes hard to read.",
        v2_ids=("F-35",),
    ),
    "LPDF_BRAILLE_INTEGRITY": CheckInfo(
        "Braille Zone Integrity",
        "Pharma-packaging Braille spot detected. Severity escalates to warning when other inks paint inside the Braille zone (dots fill in and become unreadable).",
    ),
    # ── AI File Classification ──────────────────────────────────────────────
    "AI_FCLASS_002": CheckInfo(
        "Document Classified",
        "Document classification result with confidence score.",
    ),
    "AI_FCLASS_003": CheckInfo(
        "Low Document Classification Confidence",
        "Document classification confidence is low. Manual review recommended.",
    ),
    # ── AI GHS / CLP ────────────────────────────────────────────────────────
    "AI_GHS_002": CheckInfo(
        "GHS Mutual Exclusion Violation",
        "Two mutually-exclusive GHS elements detected on the same label.",
    ),
    "AI_GHS_003": CheckInfo(
        "GHS Statement Without Pictogram",
        "H-statements or signal words detected but no GHS pictogram is present.",
    ),
    "AI_GHS_004": CheckInfo("GHS H-Statements Detected", "H-statements detected on the label."),
    "AI_GHS_005": CheckInfo("GHS P-Statements Detected", "P-statements detected on the label."),
    "AI_GHS_006": CheckInfo(
        "Multiple GHS Signal Words",
        "Multiple signal words detected. CLP allows only one signal word per label.",
    ),
    "AI_GHS_007": CheckInfo("GHS Signal Word Detected", "A GHS signal word is present."),
    "AI_GHS_008": CheckInfo(
        "GHS Pictogram Below Minimum Size",
        "GHS pictogram below minimum size for the package dimensions.",
    ),
    # ── AI Image Quality ────────────────────────────────────────────────────
    "AI_IQ_002": CheckInfo(
        "Image Quality Below Minimum",
        "Page image quality score is below the configured minimum threshold.",
    ),
    "AI_IQ_003": CheckInfo(
        "Image Quality Score", "Page image quality score reported with threshold."
    ),
    # ── AI Language ─────────────────────────────────────────────────────────
    "AI_LANG_002": CheckInfo(
        "Page Language Mismatch",
        "Page language differs from the document-level language metadata.",
    ),
    "AI_LANG_003": CheckInfo(
        "Translation Service Unavailable",
        "GPU inference service unavailable for translation of the target language.",
    ),
    "AI_LANG_004": CheckInfo(
        "Document Translated",
        "Document text translated from one language to another (informational).",
    ),
    # ── AI Logo Detection ───────────────────────────────────────────────────
    "AI_LOGO_002": CheckInfo(
        "Logo Detected",
        "A logo was detected on this page with an associated confidence score.",
    ),
    "AI_LOGO_003": CheckInfo(
        "Expected Logo Missing",
        "An expected brand logo was not detected in the document.",
    ),
    # ── AI NSFW Detection ───────────────────────────────────────────────────
    "AI_NSFW_002": CheckInfo(
        "Explicit Content Detected", "Explicit content detected on this page."
    ),
    "AI_NSFW_003": CheckInfo(
        "Suggestive Content Detected", "Suggestive content detected on this page."
    ),
    # ── AI Organic Certification ────────────────────────────────────────────
    "AI_ORG_002": CheckInfo(
        "USDA Organic Seal Misuse",
        "USDA organic seal used on a product below the required organic-content threshold.",
    ),
    # ── AI Pharma Labeling ──────────────────────────────────────────────────
    "AI_PHARMA_002": CheckInfo(
        "FDA Body Text Below Minimum",
        "FDA Drug Facts body text point size is below the required minimum.",
    ),
    "AI_PHARMA_003": CheckInfo(
        "FDA Heading Below Minimum",
        "FDA Drug Facts heading point size is below the required minimum.",
    ),
    "AI_PHARMA_004": CheckInfo(
        "FDA Text Density Excessive",
        "FDA Drug Facts text exceeds the maximum characters-per-inch readability threshold.",
    ),
    # ── AI Processing Step (ISO 19593-1) ────────────────────────────────────
    "AI_PSTEP_002": CheckInfo(
        "Processing step detected source detail",
        "Processing step detected: 'N' (source: N, detail: 'N')",
    ),
    "AI_PSTEP_003": CheckInfo(
        "No processing steps detected in document",
        "No processing steps detected in document.",
    ),
    # ── AI_RSYM ─────────────────────────────────────────────────────────────
    "AI_RSYM_002": CheckInfo(
        "Regulatory symbol",
        "Regulatory symbol 'N' on page N is undersized (Nmm, minimum: Nmm)",
    ),
    "AI_RSYM_003": CheckInfo(
        "Regulatory symbol detected",
        "Regulatory symbol 'N' detected on page N (confidence: N, size: Nmm)",
    ),
    "AI_RSYM_004": CheckInfo(
        "Expected regulatory symbol was not detected",
        "Expected regulatory symbol 'N' was not detected in the document",
    ),
    # ── AI_SIM ──────────────────────────────────────────────────────────────
    "AI_SIM_002": CheckInfo(
        "Generated visual embedding for page -dimensional",
        "Generated visual embedding for page N (N-dimensional, model: N)",
    ),
    # ── AI Submission Quality SPC ───────────────────────────────────────────
    "AI_SPC_001": CheckInfo(
        "Only historical submissions available need",
        "Only N historical submissions available (need N for SPC). Trend analysis will improve with more data.",
    ),
    "AI_SPC_002": CheckInfo(
        "All historical submissions have identical finding",
        "All historical submissions have identical finding counts — no variation to analyze.",
    ),
    "AI_SPC_003": CheckInfo(
        "Quality trend summary submissions pass rate",
        "Quality trend summary: N submissions, pass rate N%, mean findings N (sigma=N), N control chart violation(s)",
    ),
    "AI_SPC_004": CheckInfo(
        "Western Electric Rule violation", "Western Electric Rule N violation: N"
    ),
    # ── AI_SPELL ────────────────────────────────────────────────────────────
    "AI_SPELL_002": CheckInfo("Suspicious text", "Suspicious text on page N: 'N' (N)"),
    # ── AI_SZ ───────────────────────────────────────────────────────────────
    "AI_SZ_002": CheckInfo(
        "On page encroaches the safe", "'N' on page N encroaches the safe zone (Nmm)"
    ),
    # ── AI_TAO ──────────────────────────────────────────────────────────────
    "AI_TAO_002": CheckInfo(
        "Page contains text converted to outlines",
        "Page N contains text converted to outlines. OCR detected N characters of visible text but only N characters are extractable as live text.",
    ),
    "AI_TAO_003": CheckInfo("Outlined text region", "Outlined text region on page N: 'N'"),
    # ── AI Version Diff ─────────────────────────────────────────────────────
    "AI_VDIFF_002": CheckInfo(
        "Page Count Changed vs Reference",
        "The reference document and the current document have different "
        "page counts. Verify the version compared against is correct.",
    ),
    "AI_VDIFF_003": CheckInfo(
        "Page Differs From Reference",
        "A page differs from the reference version (SSIM below threshold or "
        "non-trivial pixel-change percentage). Visually inspect to confirm "
        "the change is intentional.",
    ),
    # ── Accessibility (extended) ────────────────────────────────────────────
    "LPDF_ACCESS_003": CheckInfo(
        "Document is a tagged PDF StructTreeRoot",
        "Document is a tagged PDF (StructTreeRoot and MarkInfo present)",
    ),
    "LPDF_ACCESS_005": CheckInfo(
        "Image on page may lack",
        "Image 'N' on page N may lack alternative text (/Alt)",
    ),
    "LPDF_ACCESS_006": CheckInfo(
        "No heading structure found in document missing",
        "No heading structure found in document (missing /H1../H6 tags)",
    ),
    "LPDF_ACCESS_007": CheckInfo(
        "Table structure found but no table header",
        "Table structure found but no table header (/TH) elements present",
    ),
    "LPDF_ACCESS_008": CheckInfo(
        "List items found without proper list container",
        "List items found without proper list container (/L) structure",
    ),
    "LPDF_ACCESS_009": CheckInfo(
        "No Artifact markings found in structure tree",
        "No Artifact markings found in structure tree; decorative elements may not be properly excluded",
    ),
    "LPDF_ACCESS_010": CheckInfo(
        "Reading order undefined /StructTreeRoot has no /K",
        "Reading order undefined (/StructTreeRoot has no /K children)",
    ),
    "LPDF_ACCESS_011": CheckInfo(
        "No structural emphasis tags /Em /Strong found",
        "No structural emphasis tags (/Em, /Strong) found; information may be conveyed by color alone",
    ),
    "LPDF_ACCESS_013": CheckInfo(
        "Tab order not specified",
        "Tab order not specified on page N (/Tabs missing)",
    ),
    "LPDF_ACCESS_TABLE_STRUCTURE": CheckInfo(
        "Table Header Cell Missing /Scope or /Headers",
        "Table /TH cell lacks /Scope or /Headers attribute — screen readers can't associate data cells with their headers (WCAG 1.3.1).",
    ),
    "LPDF_ACCESS_HEADING_SKIP": CheckInfo(
        "Heading Hierarchy Skip",
        "Heading hierarchy skips a level (e.g., H1 → H3 without H2). Breaks screen-reader navigation and outline browsing (WCAG 1.3.1).",
    ),
    "LPDF_ACCESS_SCREEN_READER": CheckInfo(
        "Encryption Denies Screen Reader",
        "Encryption /P permission bit 10 is cleared — screen readers can't extract text or graphics for accessibility (ISO 32000-2 §7.6.4.2 Table 22).",
    ),
    # ── Advanced Colour ─────────────────────────────────────────────────────
    "LPDF_ADV_001": CheckInfo(
        "CMYK image on page xpx",
        "CMYK image 'N' on page N (NxNpx) could be analyzed for GCR/UCR black generation strategy",
    ),
    "LPDF_ADV_003": CheckInfo(
        "Trapping risk small text",
        "Trapping risk: small text (Npt) on page N uses N non-K process colors (misregistration risk without trapping)",
    ),
    "LPDF_ADV_006": CheckInfo(
        "CxF defines spot color but no",
        "CxF defines spot color 'N' but no matching Separation space found in document",
    ),
    "LPDF_ADV_007": CheckInfo(
        "CxF spectral data is embedded",
        "CxF spectral data is embedded in the document",
    ),
    "LPDF_ADV_008": CheckInfo(
        "CxF spectral range for is -nm",
        "CxF spectral range for 'N' is N-Nnm, does not cover required 380-730nm",
    ),
    "LPDF_ADV_009": CheckInfo(
        "CxF spectral data does not specify measurement",
        "CxF spectral data does not specify measurement geometry (e.g., 45/0, d/8)",
    ),
    "LPDF_ADV_010": CheckInfo(
        "CxF illuminant does not match output",
        "CxF illuminant 'N' does not match output intent illuminant 'N'",
    ),
    "LPDF_ADV_011": CheckInfo(
        "CxF observer angle ° is non-standard expected",
        "CxF observer angle N° is non-standard (expected 2° or 10°)",
    ),
    "LPDF_ADV_012": CheckInfo(
        "CxF spot spectral vs colorimetric Delta-E",
        "CxF spot 'N' spectral vs colorimetric Delta-E = N exceeds threshold N",
    ),
    "LPDF_ADV_013": CheckInfo(
        "CxF spectral data references library color",
        "CxF spectral data references N library color 'N'",
    ),
    "LPDF_ADV_014": CheckInfo(
        "CxF spectral data includes substrate paper white",
        "CxF spectral data includes substrate (paper white) measurement",
    ),
    "LPDF_ADV_015": CheckInfo(
        "CxF version may not be fully",
        "CxF version 'N' may not be fully compatible (supported: N)",
    ),
    # ── AI Helper ───────────────────────────────────────────────────────────
    "LPDF_AI_BAND_001": CheckInfo(
        "Visible banding detected on page CAMBI",
        "Visible banding detected on page N: CAMBI score N exceeds threshold (N)",
    ),
    "LPDF_AI_CAST_001": CheckInfo(
        "Significant color cast detected",
        "Significant color cast detected on page N: N cast (deviation N, CLIP-IQA score N)",
    ),
    "LPDF_AI_CDCC_001": CheckInfo(
        "Spot color inventory for cross-document tracking",
        "Spot color inventory for cross-document tracking: N (N spot color(s) found)",
    ),
    "LPDF_AI_DIEL_002": CheckInfo(
        "Dieline spot color detected color space",
        "Dieline spot color detected: 'N' (color space 'N', type N) on page N",
    ),
    "LPDF_AI_SKIN_001": CheckInfo("Skin tone analysis", "Skin tone analysis for page N: N"),
    # ── Annotations (extended) ──────────────────────────────────────────────
    "LPDF_ANNOT_002": CheckInfo("Multimedia annotation", "Multimedia annotation (N) on page N"),
    "LPDF_ANNOT_004": CheckInfo("Stamp annotation", "Stamp annotation on page N"),
    "LPDF_ANNOT_005": CheckInfo(
        "Non-printing annotation in trim area",
        "Non-printing N annotation in trim area on page N",
    ),
    "LPDF_ANNOT_006": CheckInfo(
        "TrapNet annotation on page embedded trapping",
        "TrapNet annotation on page N (embedded trapping may conflict with RIP trapping settings)",
    ),
    # ── Barcodes ────────────────────────────────────────────────────────────
    "LPDF_BARCODE_004": CheckInfo(
        "Barcode decode failed",
        "Barcode decode failed on page N — candidate region could not be decoded",
    ),
    "LPDF_BARCODE_005": CheckInfo(
        "Barcode grade", "Barcode grade 'N' on page N is below minimum 'N'"
    ),
    "LPDF_BARCODE_006": CheckInfo(
        "Barcode quiet zone",
        "Barcode quiet zone on page N is Nmm, below required Nmm",
    ),
    "LPDF_BARCODE_007": CheckInfo(
        "Barcode symbol contrast below B grade",
        "Barcode symbol contrast N below B grade on page N",
    ),
    "LPDF_BARCODE_008": CheckInfo(
        "Poor barcode edge contrast CV=",
        "Poor barcode edge contrast (CV=N) on page N",
    ),
    "LPDF_BARCODE_009": CheckInfo(
        "Barcode quiet zone mm below ISO minimum",
        "Barcode quiet zone Nmm below ISO minimum Nmm on page N",
    ),
    "LPDF_BARCODE_010": CheckInfo(
        "Barcode Bar-Width Deviation",
        "Measured bar widths deviate from the nominal X-dimension by more "
        "than the ISO 15416 tolerance. Excessive deviation lowers the print "
        "grade and risks scanner read failures.",
    ),
    "LPDF_BARCODE_011": CheckInfo(
        "Possible barcode defect",
        "Possible barcode defect on page N — only N strokes detected",
    ),
    "LPDF_BARCODE_012": CheckInfo(
        "Barcode modulation below C grade",
        "Barcode modulation N below C grade on page N",
    ),
    "LPDF_BARCODE_013": CheckInfo(
        "Barcode decodability below C grade",
        "Barcode decodability N below C grade on page N",
    ),
    "LPDF_BARCODE_014": CheckInfo(
        "Potential 2D barcode detected",
        "Potential 2D barcode detected on page N (N modules in NxNpt region)",
    ),
    "LPDF_BARCODE_015": CheckInfo(
        "2D barcode grid irregularity",
        "2D barcode grid irregularity on page N (width CV=N, height CV=N)",
    ),
    "LPDF_BARCODE_016": CheckInfo(
        "2D barcode on page contains", "2D barcode on page N contains N modules"
    ),
    "LPDF_BARCODE_017": CheckInfo(
        "2D barcode aspect ratio",
        "2D barcode aspect ratio N on page N (expected near 1.0 for most 2D symbologies)",
    ),
    "LPDF_BARCODE_018": CheckInfo("2D barcode size xmm", "2D barcode size NxNmm on page N"),
    "LPDF_BARCODE_019": CheckInfo(
        "Barcode candidate on page — verify",
        "Barcode candidate on page N — verify GS1 format compliance if applicable",
    ),
    "LPDF_BARCODE_020": CheckInfo(
        "Barcode candidate on page — verify",
        "Barcode candidate on page N — verify application identifier if applicable",
    ),
    "LPDF_BARCODE_021": CheckInfo(
        "Barcode placement on page — center",
        "Barcode placement on page N — center at (N, N)pt",
    ),
    "LPDF_BARCODE_022": CheckInfo(
        "Barcode symbology on page — verify",
        "Barcode symbology on page N — verify symbology meets specification requirements",
    ),
    "LPDF_BARCODE_023": CheckInfo(
        "Barcode data length",
        "Barcode data length on page N — verify encoded data length meets requirements",
    ),
    "LPDF_BARCODE_024": CheckInfo(
        "Barcode color compliance",
        "Barcode color compliance on page N — verify dark bars (K>0.7 or Gray<0.3) on light background",
    ),
    "LPDF_BARCODE_026": CheckInfo(
        "Barcode in portrait orientation",
        "Barcode in portrait orientation on page N (may affect scanning)",
    ),
    "LPDF_BARCODE_027": CheckInfo(
        "Multiple barcode candidates", "Multiple barcode candidates (N) on page N"
    ),
    "LPDF_BARCODE_028": CheckInfo(
        "Barcode extends beyond trim box",
        "Barcode extends beyond trim box on page N (will be trimmed)",
    ),
    "LPDF_BARCODE_029": CheckInfo(
        "Barcode center is mm from page center",
        "Barcode center is Nmm from page center on page N — may be near a fold",
    ),
    "LPDF_BARCODE_030": CheckInfo(
        "Barcode height mm below ISO minimum",
        "Barcode height Nmm below ISO minimum on page N",
    ),
    # ── LPDF_BC ─────────────────────────────────────────────────────────────
    "LPDF_BC_001": CheckInfo(
        "Decoded DataMatrix barcode", "Decoded DataMatrix barcode on page N: 'N'"
    ),
    # ── Barcode Content QR Match ────────────────────────────────────────────
    "LPDF_BCQM_001": CheckInfo(
        "DataMatrix on page GTIN",
        "DataMatrix on page N: GTIN N has invalid check digit (expected N, got N)",
    ),
    "LPDF_BCQM_002": CheckInfo(
        "QR code on page contains invalid",
        "QR code on page N contains invalid URL: N",
    ),
    "LPDF_BCQM_003": CheckInfo(
        "No human-readable text detected near QR code",
        "No human-readable text detected near QR code on page N",
    ),
    "LPDF_BCQM_004": CheckInfo(
        "QR code on page human-readable text",
        "QR code on page N: human-readable text does not match decoded data (similarity N)",
    ),
    # ── Barcode Content Validation ──────────────────────────────────────────
    "LPDF_BCV_001": CheckInfo(
        "DataMatrix on page GTIN",
        "DataMatrix on page N: GTIN N has invalid check digit (expected N, got N)",
    ),
    "LPDF_BCV_002": CheckInfo(
        "QR code on page contains invalid",
        "QR code on page N contains invalid URL: N — 'N'",
    ),
    "LPDF_BCV_003": CheckInfo(
        "DataMatrix on page GS1 AI",
        "DataMatrix on page N: GS1 AI (N) has invalid value 'N'",
    ),
    # ── Barcode Dimensions ──────────────────────────────────────────────────
    "LPDF_BD_001": CheckInfo(
        "Barcode on page X-dimension",
        "N barcode on page N: X-dimension N mm is below absolute minimum N mm (80% magnification)",
    ),
    "LPDF_BD_002": CheckInfo(
        "Barcode on page magnification",
        "N barcode on page N: magnification N is below absolute minimum N",
    ),
    "LPDF_BD_003": CheckInfo(
        "Barcode on page height",
        "N barcode on page N: height N mm is critically below minimum N mm",
    ),
    "LPDF_BD_004": CheckInfo(
        "Barcode on page right quiet zone",
        "N barcode on page N: right quiet zone ~N modules, minimum N required",
    ),
    # ── Document (extended) ─────────────────────────────────────────────────
    "LPDF_DOC_002": CheckInfo(
        "Inconsistent Page Rotations",
        "Pages declare differing /Rotate values — the document mixes "
        "upright and rotated pages. Imposition tools and operator "
        "workflows expect consistent orientation; verify this is "
        "intentional.",
        v2_ids=("P-15",),
    ),
    "LPDF_DOC_003": CheckInfo(
        "Missing Document Title",
        "Document Info dictionary has no /Title entry. Some MIS / "
        "tracking systems display the filename instead, which loses "
        "context after rename. Set /Title at export time.",
        v2_ids=("M-03",),
    ),
    "LPDF_DOC_004": CheckInfo(
        "Document Is Encrypted",
        "Document is password-protected or otherwise encrypted. RIPs "
        "and prepress automation cannot reliably parse encrypted PDFs; "
        "all PDF/X profiles prohibit encryption. Re-export without a "
        "password.",
        v2_ids=("M-12",),
    ),
    "LPDF_DOC_005": CheckInfo(
        "Linearized PDF",
        "PDF is linearized (web-optimised — fast-web-view layout with a "
        "linearization dictionary at the start). Harmless on press, but "
        "many production tools re-save without linearization; flagged "
        "for awareness.",
    ),
    "LPDF_DOC_006": CheckInfo(
        "Incremental Updates Present",
        "Trailer dictionary carries a /Prev reference — the file has "
        "been incrementally updated rather than rewritten cleanly. Old "
        "object versions remain in the file and may carry stale ink, "
        "spot, or metadata data the RIP could pick up. Re-save with a "
        "full rewrite.",
    ),
    "LPDF_DOC_007": CheckInfo(
        "File Size Exceeds Threshold",
        "File size exceeds the configured maximum. Large files slow "
        "ingest, RIP processing, and operator tools — verify embedded "
        "images aren't oversized and consider sub-setting fonts.",
        v2_ids=("M-34",),
    ),
    "LPDF_DOC_008": CheckInfo(
        "Pre-Separated Pages Detected",
        "One or more pages use a single Separation colour space — i.e. "
        "the document is pre-separated rather than composite. Composite "
        "PDF/X is the standard for press-side workflows; pre-separated "
        "files require special handling.",
        v2_ids=("M-28",),
    ),
    "LPDF_DOC_009": CheckInfo(
        "PDF Version Outside Profile Range",
        "The PDF header version sits outside the range the active preflight profile expects (below min_pdf_version or above max_pdf_version). Re-save with a matching compatibility setting.",
        v2_ids=("M-01",),
    ),
    # ── veraPDF-backed Conformance ─────────────────────────────────────────
    "LPDF_PDFX_CONF": CheckInfo(
        "PDF/X Non-Conformant",
        "veraPDF reported one or more PDF/X rule failures (X-1a / X-3 / X-4 / X-6). See details.failures for the clause + test-number list.",
    ),
    "LPDF_PDFA_CONF": CheckInfo(
        "PDF/A Non-Conformant",
        "veraPDF reported one or more PDF/A rule failures (1b / 2b / 2u / 3b / 3u / 4). See details.failures for the clause + test-number list.",
    ),
    "LPDF_UA_CONF": CheckInfo(
        "PDF/UA Non-Conformant",
        "veraPDF Matterhorn reported one or more PDF/UA-1 checkpoint failures (accessibility). See details.failures for the list.",
    ),
    # ── Extended Colour Gamut ───────────────────────────────────────────────
    "LPDF_ECG_001": CheckInfo(
        "ECG Readiness Assessment",
        "Reports whether the document is structured for Expanded Colour "
        "Gamut (CMYKOGV) reproduction: spot-colour count, presence of "
        "CMYKOGV-like DeviceN spaces, and overall ECG-appropriateness.",
    ),
    "LPDF_ECG_002": CheckInfo(
        "ECG achievability Spot color could not",
        "ECG achievability: Spot color 'N' could not be mapped to a Lab value for gamut testing (found on page(s) N). Provide an ICC profile or…",
    ),
    "LPDF_ECG_003": CheckInfo(
        "ECG TAC Exceeds Limit",
        "Total Area Coverage on a multi-channel (DeviceN) ECG separation "
        "exceeds the configured limit. ECG presses tolerate higher TAC than "
        "CMYK but still have a substrate-specific ceiling — exceeding it "
        "causes drying, finishing, and trapping problems.",
    ),
    "LPDF_ECG_004": CheckInfo(
        "DeviceN 7-colorant space",
        "DeviceN 7-colorant space 'N' on page N has inconsistent naming: N. NN",
    ),
    "LPDF_ECG_005": CheckInfo(
        "ECG Ink-Build Exceeds 3-Ink Maximum",
        "More than three inks are active simultaneously above the "
        "significance threshold. ECG prefers a maximum 3-ink build for "
        "colour stability — additional inks create gray-balance drift and "
        "compound dot-gain.",
    ),
    "LPDF_ECG_006": CheckInfo(
        "Spot color could be replaced",
        "Spot color 'N' could be replaced by ECG process color 'N' on page(s) N",
    ),
    "LPDF_ECG_007": CheckInfo(
        "ECG color out of build range CMYK+OGV",
        "ECG color out of build range: CMYK+OGV TAC N% exceeds maximum allowable 400% on page N",
    ),
    "LPDF_ECG_008": CheckInfo(
        "ECG Gray-Balance Drift Risk",
        "Objects use a near-equal C / M / Y mix above the high-ink "
        "threshold. In ECG workflows these neutrals depend on cross-press "
        "consistency that single-pass orange / green / violet inks rarely "
        "deliver — colour shift is likely. Convert critical neutrals to a "
        "K-anchored recipe.",
    ),
    "LPDF_ECG_009": CheckInfo(
        "ECG Overinking",
        "Total Area Coverage exceeds the ECG-specific threshold. Excess "
        "ink on an ECG press produces drying problems, ink trapping issues, "
        "and back-of-sheet contamination on multi-pass jobs.",
    ),
    "LPDF_ECG_010": CheckInfo(
        "Missing ECG characterization data no ECG-specific",
        "Missing ECG characterization data: no ECG-specific output intent or characterization reference (e.g., FOGRA55) found in document metadata",
    ),
    "LPDF_ECG_011": CheckInfo(
        "ECG ink channel limit exceeded channel(s",
        "ECG ink channel limit exceeded: channel(s) N above N% on page N",
    ),
    "LPDF_ECG_012": CheckInfo(
        "Gamut boundary mapping required spot color",
        "Gamut boundary mapping required: spot color 'N' on page(s) N may be out of ECG gamut and would need gamut mapping for accurate reproduction",
    ),
    "LPDF_ECG_013": CheckInfo(
        "ECG Small Text Built From Multiple Inks",
        "Small text below the legibility threshold is built from multiple "
        "inks instead of K-only. Multi-ink small text is fragile to "
        "registration error on ECG presses — convert to K-only or enlarge "
        "the type.",
    ),
    "LPDF_ECG_014": CheckInfo(
        "ECG Non-Standard Rich-Black Recipe",
        "Objects use a rich-black recipe outside the configured ECG "
        "default (typically C=60, M=40, Y=40, K=100). Non-standard recipes "
        "may shift colour or produce inconsistent neutrals across press "
        "runs.",
    ),
    "LPDF_ECG_015": CheckInfo(
        "ECG trap zone warning path element(s",
        "ECG trap zone warning: N path element(s) with stroke width below Npt across N page(s) may need special trapping in ECG workflow",
    ),
    "LPDF_ECG_016": CheckInfo(
        "ECG ICC profile version",
        "ECG ICC profile version N is below v4.0; ECG workflows require ICC v4 or later for accurate multicolor profiling",
    ),
    "LPDF_ECG_017": CheckInfo(
        "DeviceN colorant order",
        "DeviceN colorant order N on page N does not follow CMYKOGV convention N",
    ),
    "LPDF_ECG_018": CheckInfo(
        "ECG high ink per channel channel(s",
        "ECG high ink per channel: channel(s) N exceed N% on page N",
    ),
    # ── Equivalent Process Match ────────────────────────────────────────────
    "LPDF_EPM_001": CheckInfo(
        "EPM K-Channel Usage",
        "Objects use the K (black) channel. In HP Indigo EPM (Enhanced "
        "Productivity Mode) only C, M, Y print, so K-bearing objects either "
        "drop to white or fall back to a CMY composite — neither is what the "
        "designer asked for. Move pure-black to a CMY composite, or route the "
        "job to standard CMYK instead of EPM.",
    ),
    "LPDF_EPM_002": CheckInfo(
        "EPM Pure-Black Text",
        "Text uses pure K-only or DeviceGray and will not print in EPM mode "
        "(C, M, Y only). Convert pure black text to a CMY composite black "
        "before press, or route the job to CMYK rather than EPM.",
        v2_ids=("EPM-A4",),
    ),
    "LPDF_EPM_003": CheckInfo(
        "EPM Weak CMY Composite Black",
        "Objects with K=0 and C+M+Y under 200% will produce a weak, washed-out "
        "black on press in CMY-only mode. Good density requires roughly "
        "C≥80%, M≥70%, Y≥70%.",
    ),
    "LPDF_EPM_004": CheckInfo(
        "EPM CMY TAC Exceeds Threshold",
        "Maximum CMY-only Total Area Coverage (K excluded) exceeds the "
        "configured EPM threshold. Excess CMY ink overprints, smears, and "
        "slows press throughput. Either reduce coverage upstream or route the "
        "job to standard CMYK.",
        v2_ids=("EPM-A5",),
    ),
    "LPDF_EPM_005": CheckInfo(
        "EPM Spot Color K-Dependent Fallback",
        "A spot color's CMYK alternate values include the K channel. When the "
        "spot is unavailable on press and the RIP falls back to alternate "
        "values, EPM mode strips K and shifts the rendered colour. Re-author "
        "the spot's alternate values to a CMY-only mix.",
    ),
    "LPDF_EPM_006": CheckInfo(
        "EPM Image K-Channel Dependency",
        "CMYK image(s) carry significant K-channel data. In EPM mode the K "
        "plate is dropped, so images either lose density or are silently "
        "re-separated by the RIP. Re-export images as CMY composite or route "
        "to CMYK.",
    ),
    "LPDF_EPM_007": CheckInfo(
        "EPM Registration Color In Artwork",
        "Objects are painted in registration colour (all CMYK ≥ ~90%) — a "
        "marks-and-bleeds-only ink. In EPM mode the K component is dropped "
        "and the object reads as 100% C+M+Y. Replace registration with the "
        "intended process or spot ink.",
        v2_ids=("EPM-B2",),
    ),
    "LPDF_EPM_008": CheckInfo(
        "EPM Gray Balance Risk",
        "Objects use a neutral CMY mix (C ≈ M ≈ Y, all above the gray-balance "
        "threshold) with K=0. Without K to anchor the neutral, EPM-mode "
        "presses are at high risk of a colour shift. Convert critical neutrals "
        "to a recipe that includes K, or route to CMYK.",
        v2_ids=("EPM-A7", "EPM-C4"),
    ),
    "LPDF_EPM_009": CheckInfo(
        "EPM Toner Limit Exceeded",
        "Total toner area coverage (C + M + Y + K) exceeds the configured EPM "
        "device limit (default 280%). Excess toner causes drying, finishing, "
        "and registration problems on digital presses.",
        v2_ids=("EPM-A5",),
    ),
    "LPDF_EPM_010": CheckInfo(
        "EPM Per-Channel Ink Limit",
        "One or more individual ink channels exceeds 95% coverage. Even when "
        "total TAC is acceptable, single-channel saturation can exceed "
        "substrate-specific limits on digital presses (especially synthetic "
        "and uncoated stocks).",
    ),
    "LPDF_EPM_011": CheckInfo(
        "EPM Spot Color Fidelity Risk",
        "Spot colour may not reproduce accurately on digital devices. Verify "
        "the proof on the target press, or convert to a process build with "
        "documented gamut coverage.",
    ),
    "LPDF_EPM_012": CheckInfo(
        "EPM Variable-Data Indicators",
        "Document carries variable-data indicators (PDF/VT MarkInfo or "
        "associated files). EPM throughput gains may not apply to VDP runs; "
        "check press configuration before scheduling.",
    ),
    "LPDF_EPM_013": CheckInfo(
        "EPM Custom Halftone In ExtGState",
        "ExtGState carries a custom halftone dictionary. Digital presses use "
        "their own internal screening; custom halftones are typically ignored "
        "and may flag a workflow incompatibility.",
    ),
    "LPDF_EPM_014": CheckInfo(
        "EPM Output Intent Profile-Class Mismatch",
        "Output Intent ICC profile class is not 'prtr' (printer) or 'mntr' "
        "(monitor) — digital presses need a device-specific output profile to "
        "render correctly. Re-tag the document with the press's calibrated ICC.",
        v2_ids=("EPM-C8",),
    ),
    "LPDF_EPM_015": CheckInfo(
        "EPM White-Ink Underlayer Detected",
        "A Separation color space resembling white ink was detected. White "
        "underlayers are used for dark substrate printing and are typically "
        "not part of an EPM workflow — confirm the press supports the "
        "white-ink station before proceeding.",
    ),
    "LPDF_EPM_016": CheckInfo(
        "EPM Overprint Simulation Mode",
        "ExtGState has overprint enabled (OP=true) with a non-default OPM. "
        "Digital presses simulate rather than physically overprint, so the "
        "rendered result depends on RIP behaviour — verify on a proof.",
    ),
    "LPDF_EPM_017": CheckInfo(
        "EPM High Object Count",
        "A page has more drawn objects than the advisory threshold (default "
        "5,000). High object counts can slow digital-press RIP processing — "
        "consider flattening, simplifying, or rasterising heavy regions "
        "upstream.",
    ),
    "LPDF_EPM_018": CheckInfo(
        "EPM Thin Stroke Below Digital Press Threshold",
        "Stroked path(s) have line width below the configured digital-press "
        "minimum (default 0.35pt). Thin strokes may break or print "
        "inconsistently on digital substrates.",
        v2_ids=("EPM-A4",),
    ),
    # ── LPDF_GAMUT ──────────────────────────────────────────────────────────
    "LPDF_GAMUT_001": CheckInfo(
        "CMYK color",
        "CMYK color (N, N, N, N) is out of gamut for N (Lab N, N, N, distance N, N conversion)",
    ),
    "LPDF_GAMUT_002": CheckInfo(
        "Target gamut volume for Lab^3", "Target gamut volume for N: N Lab^3 units"
    ),
    "LPDF_GAMUT_003": CheckInfo(
        "Gamut summary for / colors out",
        "Gamut summary for N: N/N colors out of gamut (N RGB, N CMYK)",
    ),
    # ── ICC Profiles ────────────────────────────────────────────────────────
    "LPDF_ICC_005": CheckInfo(
        "Output intent # has unrecognized condition",
        "Output intent #N has unrecognized condition 'N'",
    ),
    "LPDF_ICC_006": CheckInfo(
        "Multiple output intents have inconsistent color space",
        "Multiple output intents have inconsistent color space types: N",
    ),
    "LPDF_ICC_007": CheckInfo(
        "ICC profile", "ICC profile 'N' on page N is missing required tag(s): N"
    ),
    "LPDF_ICC_008": CheckInfo(
        "Document uses ICC profiles with different rendering",
        "Document uses ICC profiles with different rendering intents: N",
    ),
    "LPDF_ICC_009": CheckInfo(
        "ICC profile has non-D50 PCS illuminant",
        "ICC profile 'N' has non-D50 PCS illuminant: X=N, Y=N, Z=N (expected X=0.9642, Y=1.0, Z=0.8249)",
    ),
    # ── Metadata (extended) ─────────────────────────────────────────────────
    "LPDF_META_002": CheckInfo(
        "Title mismatch Info dict vs XMP", "Title mismatch: Info dict 'N' vs XMP 'N'"
    ),
    "LPDF_META_003": CheckInfo(
        "Trapped key is in XMP metadata", "Trapped key is N in XMP metadata"
    ),
    "LPDF_META_004": CheckInfo(
        "PDF version mismatch header vs XMP",
        "PDF version mismatch: header 'N' vs XMP 'N'",
    ),
    # ── Overprint (extended) ────────────────────────────────────────────────
    "LPDF_OVER_004": CheckInfo(
        "White Fill Painted With Overprint",
        "An object filled with white (or process white) has overprint "
        "active. White-overprint is a special-cases-only setting: the white "
        "fill becomes invisible because overprint preserves the underlying "
        "ink instead of knocking it out. Either remove the overprint or "
        "switch to knockout.",
        v2_ids=("C-36",),
    ),
    "LPDF_OVER_005": CheckInfo(
        "Overprint Inventory",
        "Informational summary of every object that has overprint enabled, "
        "broken down by colour space. Useful for comparing overprint "
        "behaviour against the production proof and the operator's "
        "expectations.",
    ),
    "LPDF_OVER_006": CheckInfo(
        "Overprint Active With DeviceRGB",
        "Overprint is active on a DeviceRGB-coloured object. Overprint is "
        "fundamentally a separation-time concept (per-channel knock-out vs "
        "preserve), but DeviceRGB has no separation model. Press behaviour "
        "is undefined and varies by RIP. Convert to CMYK or remove the "
        "overprint flag.",
    ),
    "LPDF_OVER_007": CheckInfo(
        "Small Black Text In Knockout Mode",
        "Small black text is painted with overprint disabled (knockout). "
        "Without overprint the press must register the K plate against any "
        "non-K underlying inks within a few thousandths of an inch — small "
        "type breaks visually as soon as registration drifts. Enable "
        "overprint on small black text.",
        v2_ids=("F-28",),
    ),
    "LPDF_OVER_008": CheckInfo(
        "Registration Colour With Overprint Active",
        "An object painted in registration colour (all CMYK ≥ ~90%) has "
        "overprint enabled. Registration colour is reserved for marks; "
        "overprinting it onto artwork lays a heavy ink load over whatever "
        "sits below. Remove the overprint or switch to the intended "
        "process / spot ink.",
        v2_ids=("C-38",),
    ),
    # ── Paths ───────────────────────────────────────────────────────────────
    "LPDF_PATH_001": CheckInfo(
        "Excessive path points",
        "Excessive path points (N) on page N (may cause RIP slowdown or failure)",
    ),
    # ── Packaging ───────────────────────────────────────────────────────────
    "LPDF_PKG_003": CheckInfo(
        "Dieline layer is on a non-printing",
        "Dieline layer 'N' is on a non-printing layer. Verify this is intentional for your packaging workflow.",
    ),
    "LPDF_PKG_004": CheckInfo(
        "Content on page is positioned significantly",
        "Content on page N is positioned significantly outside the trim box — may be outside the dieline boundary",
    ),
    "LPDF_PKG_005": CheckInfo(
        "Content within mm packaging safe zone",
        "Content within Nmm packaging safe zone on page N",
    ),
    "LPDF_PKG_006": CheckInfo(
        "Packaging bleed insufficient on page minimum",
        "Packaging bleed insufficient on page N: (minimum Npt / Nmm for packaging)",
    ),
    "LPDF_PKG_007": CheckInfo(
        "Multiple distinct panel sizes detected across",
        "Multiple distinct panel sizes detected across N pages (N unique sizes) — common in multi-panel packaging",
    ),
    "LPDF_PKG_008": CheckInfo(
        "Multi-page packaging layout detected Verify crossover",
        "Multi-page packaging layout detected. Verify crossover alignment between adjacent panels to ensure seamless print across fold/cut lines.",
    ),
    "LPDF_PKG_009": CheckInfo(
        "Varnish/coating layer detected", "Varnish/coating layer detected: N"
    ),
    "LPDF_PKG_010": CheckInfo(
        "White ink separation detected Ensure white ink",
        "White ink separation detected. Ensure white ink layer is correctly configured for your substrate and print process.",
    ),
    # ── Prepress ────────────────────────────────────────────────────────────
    "LPDF_PRESS_001": CheckInfo(
        "Custom halftone dictionary detected",
        "Custom halftone dictionary detected on page N",
    ),
    "LPDF_PRESS_002": CheckInfo(
        "Transfer function detected on page prohibited",
        "Transfer function detected on page N (prohibited in PDF/X)",
    ),
    "LPDF_PRESS_003": CheckInfo(
        "Custom BG/UCR function detected",
        "Custom BG/UCR function detected on page N",
    ),
    "LPDF_PRESS_004": CheckInfo(
        "Custom halftone HalftoneType detected in ExtGState",
        "Custom halftone (HalftoneType N) detected in ExtGState 'N' on page N",
    ),
    "LPDF_PRESS_005": CheckInfo(
        "Custom transfer curve detected in ExtGState",
        "Custom transfer curve (N) detected in ExtGState 'N' on page N",
    ),
    # ── Processing ──────────────────────────────────────────────────────────
    "LPDF_PROC_001": CheckInfo(
        "Processing step layers detected", "Processing step layers detected: N"
    ),
    "LPDF_PROC_002": CheckInfo("White ink layer detected", "White ink layer detected: N"),
    # ── Pharma Serialization ────────────────────────────────────────────────
    "LPDF_PS_001": CheckInfo(
        "Pharma DataMatrix on page is missing",
        "Pharma DataMatrix on page N is missing required EU FMD fields: N",
    ),
    "LPDF_PS_002": CheckInfo(
        "Pharma DataMatrix on page GTIN",
        "Pharma DataMatrix on page N: GTIN N has invalid check digit (expected N, got N)",
    ),
    "LPDF_PS_003": CheckInfo(
        "Pharma DataMatrix on page invalid expiry",
        "Pharma DataMatrix on page N: invalid expiry date format 'N' (expected YYMMDD)",
    ),
    "LPDF_PS_004": CheckInfo(
        "Pharma DataMatrix on page all EU",
        "Pharma DataMatrix on page N: all EU FMD fields present — GTIN N, Serial N, Batch N, Expiry N",
    ),
    "LPDF_PS_005": CheckInfo(
        "No DataMatrix barcode found — EU FMD",
        "No DataMatrix barcode found — EU FMD requires a GS1 DataMatrix (ECC200) on pharmaceutical packaging",
    ),
    "LPDF_PS_006": CheckInfo(
        "Conflicting 2D Barcodes Alongside Pharma DataMatrix",
        "Non-DataMatrix 2D barcode(s) (QR, Aztec, etc.) appear on the same "
        "page as a pharma GS1 DataMatrix. Scanners may pick the wrong "
        "symbol and cause traceability failures — remove or relocate the "
        "secondary barcodes.",
    ),
    # ── QR Human-Readable ───────────────────────────────────────────────────
    "LPDF_QHR_001": CheckInfo(
        "No human-readable text detected near QR code",
        "No human-readable text detected near QR code on page N",
    ),
    "LPDF_QHR_002": CheckInfo(
        "QR code on page human-readable text",
        "QR code on page N: human-readable text matches decoded data (similarity N)",
    ),
    "LPDF_QHR_003": CheckInfo(
        "QR code on page human-readable text",
        "QR code on page N: human-readable text does not match decoded data (similarity N). QR contains 'NN', nearby text: 'NN'",
    ),
    # ── QR Validation ───────────────────────────────────────────────────────
    "LPDF_QR_001": CheckInfo(
        "QR code on page has insufficient",
        "QR code on page N has insufficient left quiet zone: N modules (minimum N per ISO 18004)",
    ),
    "LPDF_QR_002": CheckInfo(
        "QR code on page module size",
        "QR code on page N: module size N mm (N px at N DPI)",
    ),
    "LPDF_QR_003": CheckInfo(
        "QR code on page contains GS1",
        "QR code on page N contains GS1 Digital Link with GTIN N",
    ),
    "LPDF_QR_004": CheckInfo(
        "Duplicate QR code found on pages", "Duplicate QR code found on pages N: 'NN'"
    ),
    # ── Spot Colours (extended) ─────────────────────────────────────────────
    "LPDF_SPOT_004": CheckInfo(
        "DeviceN on page colorant count",
        "DeviceN 'N' on page N: colorant count (N) does not match components (N)",
    ),
    "LPDF_SPOT_005": CheckInfo(
        "DeviceN on page includes process",
        "DeviceN 'N' on page N includes process colors: N",
    ),
    "LPDF_SPOT_006": CheckInfo(
        "Pantone spot color not found",
        "Pantone spot color 'N' not found in reference database — upload custom Pantone data for Delta-E validation",
    ),
    "LPDF_SPOT_007": CheckInfo(
        "Unknown spot color does not match",
        "Unknown spot color 'N' does not match any known color library (PANTONE, HKS, TOYO, DIC, RAL)",
    ),
    "LPDF_SPOT_008": CheckInfo(
        "Spot color library has alternate",
        "Spot color 'N' (N library) has alternate space 'N' which is not expected (expected: N)",
    ),
    "LPDF_SPOT_009": CheckInfo(
        "Duplicate spot color",
        "Duplicate spot color 'N' on page N defined N time(s) with different parameters: N",
    ),
    "LPDF_SPOT_010": CheckInfo(
        "Spot Color Count Exceeds Maximum",
        "The document declares more spot colours than the configured "
        "maximum allowed by the active profile. Excess spots inflate plate "
        "counts and press time — consolidate or convert to process where "
        "possible.",
    ),
    "LPDF_SPOT_011": CheckInfo(
        "Spot Color Used At 0% Tint",
        "A spot colour is referenced at 0% tint and contributes nothing to "
        "the rendered output, but it still allocates a separation plate. "
        "Either remove the reference or apply a non-zero tint.",
    ),
    # ── Strokes (extended) ──────────────────────────────────────────────────
    "LPDF_STROKE_001": CheckInfo(
        "Hairline Stroke (Below Minimum)",
        "Stroke width is below the configured minimum. Effectively the same "
        "check as LPDF_HAIR_001; both fire for thin strokes detected by "
        "different code paths (event-stream vs analyzer pass).",
        v2_ids=("LA-01",),
    ),
    "LPDF_STROKE_002": CheckInfo(
        "Zero-Width Stroke",
        "A stroke is declared with zero width. Zero-width strokes render "
        "device-pixel-thin in some RIPs and not at all in others — "
        "behaviour is undefined. Set an explicit width upstream.",
        v2_ids=("LA-03",),
    ),
    "LPDF_STROKE_004": CheckInfo(
        "Multi-Ink Thin Stroke",
        "A thin stroke is built from more than one CMYK ink. Thin strokes "
        "are highly sensitive to press registration; multi-ink builds "
        "fringe visibly when plates drift. Convert to pure K or a single "
        "spot ink.",
        v2_ids=("LA-02",),
    ),
    "LPDF_STROKE_005": CheckInfo(
        "Invisible Stroke",
        "Stroke is white or has zero opacity, rendering invisibly on press. "
        "Likely an export error (the source app intended a knockout "
        "between two filled regions). Verify the design intent.",
        v2_ids=("LA-04",),
    ),
    "LPDF_STROKE_006": CheckInfo(
        "Non-Default Flatness Tolerance",
        "Stroke or fill uses a non-default flatness tolerance. Higher "
        "tolerances coarsen curve approximations — for fine artwork, "
        "leave at the default (1.0). May affect press-side curve "
        "rendering quality.",
    ),
    # ── Structure ───────────────────────────────────────────────────────────
    "LPDF_STRUCT_005": CheckInfo(
        "3D Annotation Found",
        "Page contains a 3D annotation (Acrobat 3D model). 3D annotations "
        "have no print representation and are stripped at press; flagged "
        "for awareness in case the file was uploaded by mistake.",
    ),
    "LPDF_STRUCT_006": CheckInfo(
        "Document contains XFA forms not supported",
        "Document contains XFA forms (not supported in print workflows)",
    ),
    "LPDF_STRUCT_007": CheckInfo(
        "Document is a tagged PDF structure tree",
        "Document is a tagged PDF (structure tree present)",
    ),
    "LPDF_STRUCT_008": CheckInfo(
        "JavaScript action detected in page actions",
        "JavaScript action detected in page N actions (security and print workflow risk)",
    ),
    "LPDF_STRUCT_009": CheckInfo(
        "Interactive Form Fields Present",
        "The document contains interactive form fields (text inputs, "
        "buttons, dropdowns, signatures). Form fields are usually stripped "
        "for press output and may indicate the wrong file was uploaded.",
    ),
    "LPDF_STRUCT_010": CheckInfo(
        "Layer configuration has print-specific visibility",
        "Layer configuration has print-specific visibility rules for N layer(s)",
    ),
    "LPDF_STRUCT_011": CheckInfo(
        "PostScript fragment Type 1 XObject detected",
        "PostScript fragment (Type 1 XObject) detected on page N (prohibited in modern PDF/X workflows)",
    ),
    "LPDF_STRUCT_012": CheckInfo(
        "Document contains bookmarks/outlines entries",
        "Document contains bookmarks/outlines (N entries)",
    ),
    "LPDF_STRUCT_013": CheckInfo(
        "Embedded page thumbnails detected starting",
        "Embedded page thumbnails detected (starting on page N — increases file size unnecessarily)",
    ),
    "LPDF_STRUCT_014": CheckInfo(
        "Non-JavaScript action detected in document catalog",
        "Non-JavaScript action 'N' detected in document catalog (may cause unexpected behavior in print workflow)",
    ),
    # ── Text (extended) ─────────────────────────────────────────────────────
    "LPDF_TEXT_002": CheckInfo(
        "Very Small Text Below Effective Minimum",
        "Effective text size (after the page CTM scales the type) is "
        "below the configured minimum. Same defect class as LPDF_TEXT_001 "
        "but expressed in CTM-effective points rather than nominal "
        "points — catches tiny text that looks larger in source.",
        v2_ids=("F-22",),
    ),
    "LPDF_TEXT_003": CheckInfo(
        "Invisible Text (Rendering Mode 3)",
        "Text is rendered with mode 3 — neither filled nor stroked. Used to "
        "make text searchable but invisible (overlay on a scanned image, for "
        "instance). On press the text won't print but it still occupies the "
        "object stream and may confuse RIPs that expect every text object to "
        "render.",
        v2_ids=("F-29",),
    ),
    "LPDF_TEXT_005": CheckInfo(
        "Text Painted In Registration Colour",
        "Text is painted in registration colour (100% on every CMYK "
        "channel). Registration is reserved for crop marks and trapping "
        "guides — text in registration overprints heavily and bleeds when "
        "ink trapping fails. Re-tag with the intended ink.",
    ),
    "LPDF_TEXT_006": CheckInfo(
        "Small Multi-Ink Text",
        "Small text is built from more than one CMYK ink. At small sizes "
        "even a half-pixel of plate misregistration shows as a fringe — "
        "convert to pure K or enlarge the type.",
        v2_ids=("F-23",),
    ),
    # ── Transparency (extended) ─────────────────────────────────────────────
    "LPDF_TRANS_006": CheckInfo(
        "Knockout transparency group on page may",
        "Knockout transparency group on page N (may cause unexpected rendering)",
    ),
    "LPDF_TRANS_007": CheckInfo(
        "Shading pattern detected",
        "Shading pattern detected on page N (N shadingN, potential gradient banding risk)",
    ),
}
