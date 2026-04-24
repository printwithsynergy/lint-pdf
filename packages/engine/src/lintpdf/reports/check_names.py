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
    "LPDF_IMG_001": CheckInfo(
        "Low Image Resolution", "An image doesn't have enough detail for sharp printing."
    ),
    "LPDF_IMG_002": CheckInfo(
        "Excessive Resolution",
        "An image has far more detail than needed, increasing file size unnecessarily.",
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
        "An image has been stretched beyond its actual size, causing visible blur.",
    ),
    "LPDF_IMG_007": CheckInfo(
        "LZW Compression", "Image uses LZW compression which is prohibited in some print standards."
    ),
    "LPDF_IMG_008": CheckInfo(
        "JPEG2000 Format", "Uses JPEG2000 format which may not be supported by all RIPs."
    ),
    "LPDF_IMG_009": CheckInfo(
        "16-Bit Image", "Image uses 16-bit color depth, unusual for standard print workflows."
    ),
    "LPDF_IMG_010": CheckInfo(
        "OPI Reference",
        "References an external high-res image that must be available at print time.",
    ),
    "LPDF_IMG_011": CheckInfo(
        "Alternate Image", "Contains alternate images that should be stripped before printing."
    ),
    "LPDF_IMG_012": CheckInfo("OPI in Resources", "OPI reference found in page resources."),
    "LPDF_IMG_013": CheckInfo(
        "Alternate in Resources", "Alternate image reference found in page resources."
    ),
    "LPDF_IMG_014": CheckInfo(
        "Sheared Image", "Image has a non-orthogonal transform applied (skewed)."
    ),
    "LPDF_IMG_015": CheckInfo("Rotated Image", "Image is rotated at a non-standard angle."),
    "LPDF_IMG_016": CheckInfo(
        "Flipped Image", "Image appears to be mirrored horizontally or vertically."
    ),
    "LPDF_IMG_017": CheckInfo(
        "Extreme Scaling", "Image is scaled to an extreme percentage of its original size."
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
        "Type 3 Font", "User-drawn Type 3 font detected — quality may vary across RIPs."
    ),
    "LPDF_FONT_005": CheckInfo(
        "Missing ToUnicode",
        "CID font is missing a ToUnicode map — text search and copy may not work.",
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
        "Multiple Master Font", "Multiple Master font detected — limited RIP support."
    ),
    "LPDF_FONT_012": CheckInfo(
        "Faux Bold", "Software-simulated bold detected — may not print as expected."
    ),
    "LPDF_FONT_013": CheckInfo(
        "Faux Italic", "Software-simulated italic detected — may not print as expected."
    ),
    "LPDF_FONT_014": CheckInfo(
        "Damaged Font", "The font program appears corrupt or has a type mismatch."
    ),
    "LPDF_FONT_015": CheckInfo(
        "Restricted Font Embedding Licence",
        "Font's OS/2 fsType bit advertises a licence restriction (restricted / preview-and-print / editable embedding). Verify vendor licensing before distributing this PDF.",
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
        "Registration Color", "All inks at 100% — only for registration marks, never for artwork."
    ),
    "LPDF_COLOR_006": CheckInfo(
        "No Output Intent",
        "No color profile is specified — colors may shift unpredictably during printing.",
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
        "ICC Profile Mismatch", "Embedded ICC profile doesn't match the output intent."
    ),
    "LPDF_COLOR_016": CheckInfo(
        "RGB in CMYK Workflow", "RGB color found in a CMYK-targeted workflow."
    ),
    "LPDF_COLOR_017": CheckInfo(
        "Impure Black", "Black areas use unnecessary color inks, risking visible misregistration."
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
    ),
    # ── Page Geometry ─────────────────────────────────────────────────────
    "LPDF_BOX_001": CheckInfo(
        "Missing Trim/Bleed Box", "Page boundaries needed for cutting and bleed are not defined."
    ),
    "LPDF_BOX_002": CheckInfo(
        "Box Hierarchy Violated", "Page boxes (Media, Crop, Bleed, Trim) are not properly nested."
    ),
    "LPDF_BOX_003": CheckInfo(
        "Insufficient Bleed",
        "Not enough image extends past the trim edge — white edges may show after cutting.",
    ),
    "LPDF_BOX_004": CheckInfo("Empty Page", "Page has no visible content."),
    "LPDF_BOX_005": CheckInfo(
        "Content in Safety Margin",
        "Important content is too close to the trim edge and may be cut off.",
    ),
    "LPDF_BOX_006": CheckInfo(
        "Content Beyond Bleed", "Content extends outside the bleed box and will be clipped."
    ),
    "LPDF_BOX_007": CheckInfo(
        "UserUnit Scaling", "Non-standard page scaling detected which may confuse imposition."
    ),
    "LPDF_BOX_008": CheckInfo(
        "Non-Standard Orientation", "Page has an unusual rotation or orientation."
    ),
    "LPDF_BOX_009": CheckInfo(
        "Inconsistent Page Sizes",
        "Pages have different dimensions which may cause printing issues.",
    ),
    "LPDF_BOX_010": CheckInfo(
        "Page Size Mismatch",
        "Page dimensions don't match the product size declared on the profile (expected_page_width_mm / expected_page_height_mm). Tolerance defaults to 0.5mm; either orientation is accepted.",
    ),
    # ── Transparency ──────────────────────────────────────────────────────
    "LPDF_TRANS_001": CheckInfo(
        "Transparency Used", "Page uses transparency which must be flattened for older workflows."
    ),
    "LPDF_TRANS_002": CheckInfo(
        "Non-Standard Blend Mode",
        "A blend mode other than Normal is used, which may flatten unpredictably.",
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
        "JavaScript Found", "Document contains JavaScript which is not allowed in print workflows."
    ),
    "LPDF_STRUCT_002": CheckInfo(
        "Form Fields Present", "Interactive form fields detected — these won't print as expected."
    ),
    "LPDF_STRUCT_003": CheckInfo(
        "PDF Layers Detected", "Optional content layers (OCGs) are present."
    ),
    "LPDF_STRUCT_004": CheckInfo("Embedded Files", "Document contains embedded file attachments."),
    # ── Document Info ─────────────────────────────────────────────────────
    "LPDF_DOC_001": CheckInfo(
        "Multiple Page Sizes",
        "Document contains pages of different sizes which may complicate imposition.",
    ),
    # ── Metadata ──────────────────────────────────────────────────────────
    "LPDF_META_001": CheckInfo(
        "No XMP Metadata", "XMP metadata stream is missing — may be required by some standards."
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
    "LPDF_TEXT_001": CheckInfo("Small Text", "Text is below the minimum readable size for print."),
    "LPDF_TEXT_004": CheckInfo(
        "White Text", "White text detected — verify it's intentional and not hidden content."
    ),
    "LPDF_HAIR_001": CheckInfo(
        "Hairline Stroke", "A very thin line may disappear or print inconsistently."
    ),
    "LPDF_HAIR_002": CheckInfo(
        "Small Text on Thin Stroke", "Thin stroked text may be hard to read at small sizes."
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
    ),
    "AI_DIE_002": CheckInfo(
        "No Dieline Detected",
        "Expected dieline not found in a packaging file. Verify spot naming or AI detection availability.",
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
        "Page count changed reference has page(s",
        "Page count changed: reference has N page(s), current has N page(s)",
    ),
    "AI_VDIFF_003": CheckInfo(
        "Page differs from reference SSIM= %",
        "Page N differs from reference (SSIM=N, N% pixels changed)",
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
        "Barcode bar width deviation %",
        "Barcode bar width deviation N% on page N",
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
        "Document has inconsistent page rotations",
        "Document has inconsistent page rotations: N",
    ),
    "LPDF_DOC_003": CheckInfo(
        "Document has no title in Info dictionary",
        "Document has no title in Info dictionary",
    ),
    "LPDF_DOC_004": CheckInfo(
        "Document is encrypted not allowed in print",
        "Document is encrypted (not allowed in print workflows)",
    ),
    "LPDF_DOC_005": CheckInfo(
        "Linearized PDF detected web-optimized may need",
        "Linearized PDF detected (web-optimized, may need re-saving for print)",
    ),
    "LPDF_DOC_006": CheckInfo(
        "Incremental updates detected trailer has /Prev",
        "Incremental updates detected (trailer has /Prev reference, file may contain stale data)",
    ),
    "LPDF_DOC_007": CheckInfo(
        "File size MB exceeds threshold", "File size (N MB) exceeds threshold (N MB)"
    ),
    "LPDF_DOC_008": CheckInfo(
        "Pre-separated pages detected pages with single",
        "Pre-separated pages detected (N pages with single Separation color space)",
    ),
    "LPDF_DOC_009": CheckInfo(
        "PDF Version Outside Profile Range",
        "The PDF header version sits outside the range the active preflight profile expects (below min_pdf_version or above max_pdf_version). Re-save with a matching compatibility setting.",
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
        "ECG readiness spot color(s found",
        "ECG readiness: N spot color(s) found, N CMYKOGV-like DeviceN space(s) detected. N",
    ),
    "LPDF_ECG_002": CheckInfo(
        "ECG achievability Spot color could not",
        "ECG achievability: Spot color 'N' could not be mapped to a Lab value for gamut testing (found on page(s) N). Provide an ICC profile or…",
    ),
    "LPDF_ECG_003": CheckInfo(
        "ECG TAC % exceeds % limit",
        "ECG TAC N% exceeds N% limit on page N (N-channel DeviceN)",
    ),
    "LPDF_ECG_004": CheckInfo(
        "DeviceN 7-colorant space",
        "DeviceN 7-colorant space 'N' on page N has inconsistent naming: N. NN",
    ),
    "LPDF_ECG_005": CheckInfo(
        "ECG ink build active inks >%",
        "ECG ink build: N active inks (>N%) on page N exceeds 3-ink maximum for color stability",
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
        "ECG gray balance drift risk object(s",
        "ECG gray balance drift risk: N object(s) with near-equal C/M/Y components above N% across N page(s) may exhibit gray balance instability in…",
    ),
    "LPDF_ECG_009": CheckInfo(
        "ECG overinking TAC % exceeds ECG threshold",
        "ECG overinking: TAC N% exceeds ECG threshold N% on page N",
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
        "ECG multi-ink small text text object(s",
        "ECG multi-ink small text: N text object(s) below Npt use multi-ink instead of K-only across N page(s)",
    ),
    "LPDF_ECG_014": CheckInfo(
        "ECG rich black recipe object(s use",
        "ECG rich black recipe: N object(s) use non-standard rich black recipe across N page(s). ECG recommends C=N% M=N% Y=N% K=N%",
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
        "EPM K-channel dependency object(s use K",
        "EPM K-channel dependency: N object(s) use K across N page(s)",
    ),
    "LPDF_EPM_002": CheckInfo(
        "EPM pure black text text object(s",
        "EPM pure black text: N text object(s) use pure K-only or DeviceGray black and will not print in EPM mode (CMY-only) across N page(s)",
    ),
    "LPDF_EPM_003": CheckInfo(
        "EPM weak CMY black object(s",
        "EPM weak CMY black: N object(s) with K=0 and C+M+Y < 200% may produce weak blacks in CMY-only mode across N page(s) (good density requires…",
    ),
    "LPDF_EPM_004": CheckInfo(
        "EPM CMY TAC % exceeds % threshold",
        "EPM CMY TAC N% exceeds N% threshold on page N (K excluded)",
    ),
    "LPDF_EPM_005": CheckInfo(
        "EPM spot color K-dependency Spot color",
        "EPM spot color K-dependency: Spot color 'N' has a CMYK fallback (alternate: N) which may include K channel",
    ),
    "LPDF_EPM_006": CheckInfo(
        "EPM image K-dependency CMYK image(s across",
        "EPM image K-dependency: N CMYK image(s) across N page(s) have K channel dependency that affects EPM output",
    ),
    "LPDF_EPM_007": CheckInfo(
        "EPM registration color object(s use registration",
        "EPM registration color: N object(s) use registration color (all CMYK components >=N%) across N page(s); in EPM mode only CMY channels will…",
    ),
    "LPDF_EPM_008": CheckInfo(
        "EPM gray balance risk object(s",
        "EPM gray balance risk: N object(s) with neutral CMY mix (CNMNY within N%, all >N%) across N page(s) are high risk for color shift without K…",
    ),
    "LPDF_EPM_009": CheckInfo(
        "EPM toner limit exceeded total toner area",
        "EPM toner limit exceeded: total toner area coverage N% exceeds EPM device limit N% on page N",
    ),
    "LPDF_EPM_010": CheckInfo(
        "EPM substrate ink limit object(s",
        "EPM substrate ink limit: N object(s) with individual ink channel >95% across N page(s) may exceed substrate-specific limits for digital…",
    ),
    "LPDF_EPM_011": CheckInfo(
        "EPM spot color fidelity spot color",
        "EPM spot color fidelity: spot color 'N' may not reproduce accurately on digital devices",
    ),
    "LPDF_EPM_012": CheckInfo(
        "EPM variable data document contains variable data",
        "EPM variable data: document contains variable data indicators (N)",
    ),
    "LPDF_EPM_013": CheckInfo(
        "EPM halftone incompatibility custom halftone",
        "EPM halftone incompatibility: custom halftone in ExtGState 'N' on page N; digital presses use their own screening",
    ),
    "LPDF_EPM_014": CheckInfo(
        "EPM ICC profile class mismatch output intent",
        "EPM ICC profile class mismatch: output intent has profile class 'N' (expected 'prtr' or 'mntr'); digital presses need device-specific…",
    ),
    "LPDF_EPM_015": CheckInfo(
        "EPM white ink underlayer Separation color space",
        "EPM white ink underlayer: Separation color space with colorant 'N' detected on page N; white ink separations are used for dark substrate…",
    ),
    "LPDF_EPM_016": CheckInfo(
        "EPM overprint simulation ExtGState",
        "EPM overprint simulation: ExtGState 'N' on page N has overprint enabled (OP=true, OPM=N); digital presses simulate overprint",
    ),
    "LPDF_EPM_017": CheckInfo(
        "EPM high object count",
        "EPM high object count: page N has N objects (threshold N) which may slow digital press RIP processing",
    ),
    "LPDF_EPM_018": CheckInfo(
        "EPM thin line weight stroked path(s",
        "EPM thin line weight: N stroked path(s) have line width below Npt across N page(s)",
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
        "White overprint on page fill",
        "White overprint on page N (fill is white with overprint active — content underneath will show through)",
    ),
    "LPDF_OVER_005": CheckInfo(
        "Overprint inventory object(s with overprint enabled",
        "Overprint inventory: N object(s) with overprint enabled across N color space type(s)",
    ),
    "LPDF_OVER_006": CheckInfo(
        "Overprint active with DeviceRGB",
        "Overprint active with DeviceRGB on page N (undefined behavior on press)",
    ),
    "LPDF_OVER_007": CheckInfo(
        "Small black text instance min",
        "N small black text instanceN (min Npt) in knockout mode on page N (overprint not active — risk of misregistration)",
    ),
    "LPDF_OVER_008": CheckInfo(
        "Registration color with overprint active",
        "Registration color with overprint active on page N (registration color outside marks is dangerous)",
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
        "Found non-DataMatrix 2D barcode(s alongside pharma",
        "Found N non-DataMatrix 2D barcode(s) alongside pharma DataMatrix — may cause scanning confusion",
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
        "Document uses spot color(s exceeding",
        "Document uses N spot color(s), exceeding the maximum of N: N",
    ),
    "LPDF_SPOT_011": CheckInfo(
        "Spot color used at 0% tint",
        "Spot color 'N' used at 0% tint on page N (invisible)",
    ),
    # ── Strokes (extended) ──────────────────────────────────────────────────
    "LPDF_STROKE_001": CheckInfo(
        "Hairline stroke", "Hairline stroke (Npt) on page N (below Npt minimum)"
    ),
    "LPDF_STROKE_002": CheckInfo(
        "Zero-width stroke on page will not",
        "Zero-width stroke on page N (will not render in print)",
    ),
    "LPDF_STROKE_004": CheckInfo(
        "Multi-ink thin stroke pt inks",
        "Multi-ink thin stroke (Npt, N inks) on page N (risk of misregistration on thin lines)",
    ),
    "LPDF_STROKE_005": CheckInfo(
        "Invisible stroke white/zero-opacity on page renders",
        "Invisible stroke (white/zero-opacity) on page N (renders as white line art)",
    ),
    "LPDF_STROKE_006": CheckInfo(
        "Non-default flatness tolerance",
        "Non-default flatness tolerance (N) on page N (may affect curve rendering quality)",
    ),
    # ── Structure ───────────────────────────────────────────────────────────
    "LPDF_STRUCT_005": CheckInfo("3D annotation found", "3D annotation found on page N"),
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
        "Document contains interactive form field(s text",
        "Document contains N interactive form field(s) (text inputs, buttons, dropdowns, or signatures)",
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
        "Very small text pt effective",
        "Very small text (Npt effective) on page N (below Npt)",
    ),
    "LPDF_TEXT_003": CheckInfo(
        "Invisible text rendering mode 3",
        "Invisible text (rendering mode 3) on page N (text is neither filled nor stroked)",
    ),
    "LPDF_TEXT_005": CheckInfo(
        "Text on registration color 100% all CMYK",
        "Text on registration color (100% all CMYK) on page N",
    ),
    "LPDF_TEXT_006": CheckInfo(
        "Small multi-ink text pt inks",
        "Small multi-ink text (Npt, N inks) on page N (risk of misregistration)",
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
