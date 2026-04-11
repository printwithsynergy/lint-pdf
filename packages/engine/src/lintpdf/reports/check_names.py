"""Human-friendly check name registry for preflight reports and viewer.

Maps inspection_id → plain-English name + description suitable for
non-technical users (designers, print buyers, marketing managers).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckInfo:
    """Friendly name and description for a preflight check."""

    name: str
    description: str


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
    "LPDF_IMG_001": CheckInfo("Low Image Resolution", "An image doesn't have enough detail for sharp printing."),
    "LPDF_IMG_002": CheckInfo("Excessive Resolution", "An image has far more detail than needed, increasing file size unnecessarily."),
    "LPDF_IMG_003": CheckInfo("Wrong Color Mode", "An image uses screen colors (RGB) instead of print colors (CMYK)."),
    "LPDF_IMG_004": CheckInfo("No Image Compression", "An image isn't compressed, making the file unnecessarily large."),
    "LPDF_IMG_005": CheckInfo("Inline Image", "A small image is embedded directly in the page stream instead of as a resource."),
    "LPDF_IMG_006": CheckInfo("Upscaled Image", "An image has been stretched beyond its actual size, causing visible blur."),
    "LPDF_IMG_007": CheckInfo("LZW Compression", "Image uses LZW compression which is prohibited in some print standards."),
    "LPDF_IMG_008": CheckInfo("JPEG2000 Format", "Uses JPEG2000 format which may not be supported by all RIPs."),
    "LPDF_IMG_009": CheckInfo("16-Bit Image", "Image uses 16-bit color depth, unusual for standard print workflows."),
    "LPDF_IMG_010": CheckInfo("OPI Reference", "References an external high-res image that must be available at print time."),
    "LPDF_IMG_011": CheckInfo("Alternate Image", "Contains alternate images that should be stripped before printing."),
    "LPDF_IMG_012": CheckInfo("OPI in Resources", "OPI reference found in page resources."),
    "LPDF_IMG_013": CheckInfo("Alternate in Resources", "Alternate image reference found in page resources."),
    "LPDF_IMG_014": CheckInfo("Sheared Image", "Image has a non-orthogonal transform applied (skewed)."),
    "LPDF_IMG_015": CheckInfo("Rotated Image", "Image is rotated at a non-standard angle."),
    "LPDF_IMG_016": CheckInfo("Flipped Image", "Image appears to be mirrored horizontally or vertically."),
    "LPDF_IMG_017": CheckInfo("Extreme Scaling", "Image is scaled to an extreme percentage of its original size."),

    # ── Fonts ─────────────────────────────────────────────────────────────
    "LPDF_FONT_001": CheckInfo("Missing Font", "A font is not embedded — text may display incorrectly at the printer."),
    "LPDF_FONT_002": CheckInfo("Full Font Embedded", "The entire font is embedded instead of just the characters used, increasing file size."),
    "LPDF_FONT_003": CheckInfo("System Font Used", "A standard system font is used which may render differently on other devices."),
    "LPDF_FONT_004": CheckInfo("Type 3 Font", "User-drawn Type 3 font detected — quality may vary across RIPs."),
    "LPDF_FONT_005": CheckInfo("Missing ToUnicode", "CID font is missing a ToUnicode map — text search and copy may not work."),
    "LPDF_FONT_006": CheckInfo("Missing CIDSystemInfo", "CID font is missing system information needed for correct rendering."),
    "LPDF_FONT_007": CheckInfo("No Font Encoding", "Font lacks encoding information — characters may map incorrectly."),
    "LPDF_FONT_008": CheckInfo("TrueType Not Embedded", "A TrueType font is referenced but not embedded in the file."),
    "LPDF_FONT_009": CheckInfo("OpenType Not Embedded", "An OpenType/CFF font is referenced but not embedded."),
    "LPDF_FONT_010": CheckInfo("Incomplete Font", "Font descriptor is present but the actual font data is missing."),
    "LPDF_FONT_011": CheckInfo("Multiple Master Font", "Multiple Master font detected — limited RIP support."),
    "LPDF_FONT_012": CheckInfo("Faux Bold", "Software-simulated bold detected — may not print as expected."),
    "LPDF_FONT_013": CheckInfo("Faux Italic", "Software-simulated italic detected — may not print as expected."),
    "LPDF_FONT_014": CheckInfo("Damaged Font", "The font program appears corrupt or has a type mismatch."),

    # ── Color ─────────────────────────────────────────────────────────────
    "LPDF_COLOR_001": CheckInfo("Device-Dependent Color", "Color is specified without a profile, so output will vary by device."),
    "LPDF_COLOR_002": CheckInfo("Spot Color Without Fallback", "A spot color has no process color fallback for proofing."),
    "LPDF_COLOR_003": CheckInfo("Lab Color Used", "CIE Lab color used — may require special handling at the RIP."),
    "LPDF_COLOR_004": CheckInfo("Ink Coverage Too High", "Total ink exceeds the maximum for this paper type, risking smearing or drying issues."),
    "LPDF_COLOR_005": CheckInfo("Registration Color", "All inks at 100% — only for registration marks, never for artwork."),
    "LPDF_COLOR_006": CheckInfo("No Output Intent", "No color profile is specified — colors may shift unpredictably during printing."),
    "LPDF_COLOR_007": CheckInfo("Mixed Color Spaces", "Different color spaces used on the same page may cause inconsistency."),
    "LPDF_COLOR_008": CheckInfo("CalRGB Color", "Calibrated RGB color used — should be converted to CMYK for print."),
    "LPDF_COLOR_009": CheckInfo("CalGray Color", "Calibrated gray color used — should use DeviceGray for consistency."),
    "LPDF_COLOR_010": CheckInfo("Indexed Color", "Indexed/palette color used — limited color range."),
    "LPDF_COLOR_011": CheckInfo("Pattern Color Space", "Pattern-based color used — may render differently across RIPs."),
    "LPDF_COLOR_012": CheckInfo("Separation Color", "Separation color space detected."),
    "LPDF_COLOR_013": CheckInfo("DeviceN Color", "Multi-channel DeviceN color detected."),
    "LPDF_COLOR_014": CheckInfo("Color Space Inventory", "Summary of color space types used in the document."),
    "LPDF_COLOR_015": CheckInfo("ICC Profile Mismatch", "Embedded ICC profile doesn't match the output intent."),
    "LPDF_COLOR_016": CheckInfo("RGB in CMYK Workflow", "RGB color found in a CMYK-targeted workflow."),
    "LPDF_COLOR_017": CheckInfo("Impure Black", "Black areas use unnecessary color inks, risking visible misregistration."),
    "LPDF_COLOR_018": CheckInfo("Untagged Color", "Color space used without an associated ICC profile."),
    "LPDF_COLOR_019": CheckInfo("Wide Gamut Color", "Color is outside the typical print gamut."),
    "LPDF_COLOR_020": CheckInfo("Overink Warning", "Multiple color operations accumulate high ink levels."),

    # ── Page Geometry ─────────────────────────────────────────────────────
    "LPDF_BOX_001": CheckInfo("Missing Trim/Bleed Box", "Page boundaries needed for cutting and bleed are not defined."),
    "LPDF_BOX_002": CheckInfo("Box Hierarchy Violated", "Page boxes (Media, Crop, Bleed, Trim) are not properly nested."),
    "LPDF_BOX_003": CheckInfo("Insufficient Bleed", "Not enough image extends past the trim edge — white edges may show after cutting."),
    "LPDF_BOX_004": CheckInfo("Empty Page", "Page has no visible content."),
    "LPDF_BOX_005": CheckInfo("Content in Safety Margin", "Important content is too close to the trim edge and may be cut off."),
    "LPDF_BOX_006": CheckInfo("Content Beyond Bleed", "Content extends outside the bleed box and will be clipped."),
    "LPDF_BOX_007": CheckInfo("UserUnit Scaling", "Non-standard page scaling detected which may confuse imposition."),
    "LPDF_BOX_008": CheckInfo("Non-Standard Orientation", "Page has an unusual rotation or orientation."),
    "LPDF_BOX_009": CheckInfo("Inconsistent Page Sizes", "Pages have different dimensions which may cause printing issues."),

    # ── Transparency ──────────────────────────────────────────────────────
    "LPDF_TRANS_001": CheckInfo("Transparency Used", "Page uses transparency which must be flattened for older workflows."),
    "LPDF_TRANS_002": CheckInfo("Non-Standard Blend Mode", "A blend mode other than Normal is used, which may flatten unpredictably."),
    "LPDF_TRANS_003": CheckInfo("Soft Mask", "Image uses a soft mask, increasing rendering complexity."),
    "LPDF_TRANS_004": CheckInfo("Low Opacity", "Content has very low opacity and may be nearly invisible in print."),
    "LPDF_TRANS_005": CheckInfo("Transparency Group", "A transparency group is defined on this page."),

    # ── Overprint ─────────────────────────────────────────────────────────
    "LPDF_OVER_001": CheckInfo("Overprint On", "Overprint is enabled — colors will mix where they overlap instead of knocking out."),
    "LPDF_OVER_002": CheckInfo("Overprint Off for Spot", "Overprint is disabled for a spot color, which may cause unexpected knockouts."),
    "LPDF_OVER_003": CheckInfo("Overprint Mode Mismatch", "Overprint mode setting is inconsistent."),

    # ── Document Structure ────────────────────────────────────────────────
    "LPDF_STRUCT_001": CheckInfo("JavaScript Found", "Document contains JavaScript which is not allowed in print workflows."),
    "LPDF_STRUCT_002": CheckInfo("Form Fields Present", "Interactive form fields detected — these won't print as expected."),
    "LPDF_STRUCT_003": CheckInfo("PDF Layers Detected", "Optional content layers (OCGs) are present."),
    "LPDF_STRUCT_004": CheckInfo("Embedded Files", "Document contains embedded file attachments."),

    # ── Document Info ─────────────────────────────────────────────────────
    "LPDF_DOC_001": CheckInfo("Multiple Page Sizes", "Document contains pages of different sizes which may complicate imposition."),

    # ── Metadata ──────────────────────────────────────────────────────────
    "LPDF_META_001": CheckInfo("No XMP Metadata", "XMP metadata stream is missing — may be required by some standards."),

    # ── Annotations ───────────────────────────────────────────────────────
    "LPDF_ANNOT_001": CheckInfo("Printable Annotation", "A printable annotation is inside the trim area and will appear in output."),
    "LPDF_ANNOT_003": CheckInfo("Link Annotation", "A clickable link annotation is present on this page."),

    # ── Accessibility ─────────────────────────────────────────────────────
    "LPDF_ACCESS_001": CheckInfo("Not Tagged", "Document has no structure tree — it's not accessible to screen readers."),
    "LPDF_ACCESS_002": CheckInfo("No Language Set", "Document language is not specified, reducing accessibility."),
    "LPDF_ACCESS_004": CheckInfo("Missing Document Language", "The /Lang entry is missing from the document catalog."),
    "LPDF_ACCESS_012": CheckInfo("No Output Intent for Contrast", "Cannot verify text-background contrast for accessibility without an output intent."),

    # ── Text & Hairlines ──────────────────────────────────────────────────
    "LPDF_TEXT_001": CheckInfo("Small Text", "Text is below the minimum readable size for print."),
    "LPDF_TEXT_004": CheckInfo("White Text", "White text detected — verify it's intentional and not hidden content."),
    "LPDF_HAIR_001": CheckInfo("Hairline Stroke", "A very thin line may disappear or print inconsistently."),
    "LPDF_HAIR_002": CheckInfo("Small Text on Thin Stroke", "Thin stroked text may be hard to read at small sizes."),
    "LPDF_PATH_002": CheckInfo("White Fill Path", "A white-filled path may knock out background content unintentionally."),
    "LPDF_STROKE_003": CheckInfo("Butt Cap on Thin Line", "A butt line cap on a thin stroke may cause visible gaps — round cap recommended."),

    # ── Ink & Advanced Color ──────────────────────────────────────────────
    "LPDF_INK_001": CheckInfo("TAC Heatmap", "Total Area Coverage data for this page."),
    "LPDF_INK_002": CheckInfo("Ink Separation Data", "Per-channel ink usage statistics."),
    "LPDF_INK_003": CheckInfo("Ink Channel Inventory", "Summary of all ink channels used in the document."),
    "LPDF_ADV_002": CheckInfo("Ink Savings Estimate", "Analysis of potential ink savings through GCR optimization."),
    "LPDF_ADV_004": CheckInfo("No Spectral Data", "No CxF spectral measurement data found in output intents."),
    "LPDF_ADV_005": CheckInfo("Black Composition", "Breakdown of how black is built (pure K, rich black, registration)."),

    # ── Standards Compliance ──────────────────────────────────────────────
    "LPDF_STD_001": CheckInfo("G7 Compliance", "G7 process control readiness assessment."),
    "LPDF_STD_002": CheckInfo("GRACoL Compliance", "GRACoL 2006 compliance validation."),
    "LPDF_STD_003": CheckInfo("ISO 12647 Compliance", "ISO 12647 standard compliance check."),

    # ── ICC Profiles ──────────────────────────────────────────────────────
    "LPDF_ICC_001": CheckInfo("No ICC Profile", "No ICC color profile embedded for color-managed output."),
    "LPDF_ICC_002": CheckInfo("Invalid ICC Profile", "The embedded ICC profile is corrupt or invalid."),
    "LPDF_ICC_003": CheckInfo("ICC Version Mismatch", "ICC profile version doesn't match the PDF specification."),
    "LPDF_ICC_004": CheckInfo("Wrong ICC Device Class", "ICC profile device class doesn't match usage context."),

    # ── Spot Colors ───────────────────────────────────────────────────────
    "LPDF_SPOT_001": CheckInfo("Unknown Spot Color", "A spot color is used that isn't in a standard color book."),
    "LPDF_SPOT_002": CheckInfo("Spot Color Fallback Issue", "The process color fallback for a spot color may not be accurate."),
    "LPDF_SPOT_003": CheckInfo("Similar Spot Names", "Multiple spot colors have very similar names — may be duplicates."),

    # ── Barcode ───────────────────────────────────────────────────────────
    "LPDF_BARCODE_001": CheckInfo("Barcode Detected", "A potential barcode pattern was identified on this page."),
    "LPDF_BARCODE_025": CheckInfo("Low Barcode Resolution", "The barcode area resolution is below the minimum for reliable scanning."),

    # ── Packaging ─────────────────────────────────────────────────────────
    "LPDF_PKG_001": CheckInfo("Dieline Detected", "A die line layer was identified in this packaging file."),
    "LPDF_PKG_002": CheckInfo("Missing Dieline", "No die line detected — expected for packaging artwork."),

    # ══ AI CHECKS ═════════════════════════════════════════════════════════

    # ── WCAG Contrast ─────────────────────────────────────────────────────
    "AI_WCAG_001": CheckInfo("Low Color Contrast", "Text doesn't have enough contrast against its background for comfortable reading."),
    "AI_WCAG_002": CheckInfo("Below WCAG AA", "Text-background contrast is below the WCAG AA accessibility standard."),

    # ── FDA Nutrition ─────────────────────────────────────────────────────
    "AI_FDA_001": CheckInfo("Calories Font Too Small", "The Calories declaration may be below the FDA's minimum font size requirement."),
    "AI_FDA_002": CheckInfo("NFP Text Too Small", "Nutrition Facts text is below the minimum readable size required by FDA."),
    "AI_FDA_003": CheckInfo("Missing Bold in NFP", "Required bold formatting is missing from Nutrition Facts headings."),
    "AI_FDA_004": CheckInfo("Missing Nutrients", "Required nutrients may be missing from the Nutrition Facts panel."),
    "AI_FDA_005": CheckInfo("FDA Label Warning", "A potential FDA labeling compliance issue was detected."),

    # ── EU Food Labeling ──────────────────────────────────────────────────
    "AI_EU1169_001": CheckInfo("EU Font Size Violation", "Text is below the minimum x-height required by EU Regulation 1169/2011."),
    "AI_EU1169_002": CheckInfo("Allergen Not Emphasized", "An allergen may not be properly emphasized as required by EU food labeling rules."),
    "AI_EU1169_003": CheckInfo("EU Nutrition Format", "Nutrition information format doesn't comply with EU FIR 1169/2011."),

    # ── Pharmaceutical ────────────────────────────────────────────────────
    "AI_PHARMA_001": CheckInfo("Pharma Font Too Small", "Text is below the minimum size required for pharmaceutical labeling."),

    # ── Brand Palette ─────────────────────────────────────────────────────
    "AI_BRAND_001": CheckInfo("No Brand Palette", "No brand color palette is configured for compliance checking."),
    "AI_BRAND_002": CheckInfo("Brand Color Deviation", "A color deviates from the configured brand palette."),

    # ── Spell Check ───────────────────────────────────────────────────────
    "AI_SPELL_001": CheckInfo("Misspelled Word", "A potentially misspelled word was detected in the document text."),

    # ── Language Detection ────────────────────────────────────────────────
    "AI_LANG_001": CheckInfo("Language Detected", "The document language has been identified."),

    # ── Duplicate Detection ───────────────────────────────────────────────
    "AI_DUP_001": CheckInfo("Duplicate Content", "Duplicate or near-duplicate content detected across pages."),

    # ── Image Quality (AI) ────────────────────────────────────────────────
    "AI_IQ_001": CheckInfo("Image Quality Issue", "An image quality concern was detected (blur, noise, or artifacts)."),
    "AI_SIM_001": CheckInfo("Similar Images", "Very similar or duplicate images detected in the document."),
    "AI_NSFW_001": CheckInfo("Content Safety Flag", "Potentially inappropriate content was flagged for review."),

    # ── Logo Detection ────────────────────────────────────────────────────
    "AI_LOGO_001": CheckInfo("Logo Not Found", "Expected logo was not detected on this page."),

    # ── Safe Zone ─────────────────────────────────────────────────────────
    "AI_SZ_001": CheckInfo("Safe Zone Violation", "Content is placed in a restricted bleed or safety zone area."),

    # ── Dieline Detection ─────────────────────────────────────────────────
    "AI_DIE_003": CheckInfo("No Dieline Found", "No die line detected — file does not appear to be packaging artwork."),

    # ── Regulatory Symbols ────────────────────────────────────────────────
    "AI_RSYM_001": CheckInfo("Missing Regulatory Symbol", "A required regulatory symbol may be missing from the artwork."),

    # ── Processing Steps ──────────────────────────────────────────────────
    "AI_PSTEP_001": CheckInfo("Processing Steps", "Processing step layer or instruction detected."),

    # ── Text as Outlines ──────────────────────────────────────────────────
    "AI_TAO_001": CheckInfo("Text Not Outlined", "Text has not been converted to outlines for guaranteed rendering."),

    # ── Version Comparison ────────────────────────────────────────────────
    "AI_VDIFF_001": CheckInfo("No Reference File", "No reference file provided for version comparison."),

    # ── Auto Preflight Profile ────────────────────────────────────────────
    "AI_AFP_001": CheckInfo("Auto Profile Suggestion", "An automatic preflight profile recommendation was generated."),

    # ── Document Classification ───────────────────────────────────────────
    "AI_FCLASS_001": CheckInfo("Document Classification", "The document type has been automatically classified."),

    # ── GHS Chemical Labeling ─────────────────────────────────────────────
    "AI_GHS_001": CheckInfo("Missing GHS Elements", "Required GHS hazard label elements may be missing."),

    # ── Cannabis Labeling ─────────────────────────────────────────────────
    "AI_CANN_001": CheckInfo("Cannabis Warning Missing", "Required cannabis warning symbols or statements may be missing."),

    # ── Alcohol Labeling ──────────────────────────────────────────────────
    "AI_ALC_001": CheckInfo("Alcohol Label Issue", "Required alcohol labeling elements may be missing."),

    # ── Cosmetics Labeling ────────────────────────────────────────────────
    "AI_COSM_001": CheckInfo("Cosmetics Label Issue", "Required cosmetics labeling elements may be missing."),

    # ── Organic Certification ─────────────────────────────────────────────
    "AI_ORG_001": CheckInfo("Organic Seal Issue", "Organic certification mark may be missing or incorrectly placed."),

    # ── AI Scan Marker ────────────────────────────────────────────────────
    "AI_SCAN_001": CheckInfo("AI Scan Complete", "Summary of the AI analysis pipeline run."),
}
