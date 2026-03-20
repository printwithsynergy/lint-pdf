# ICC.1:2022 Color Profile Specification - Preflight Validation Reference

**Source:** ICC.1:2022 (Profile version 4.4.0.0) - International Color Consortium Specification
**Scope:** This document extracts preflight-relevant content for PDF color profile validation.
**Version:** ICC.1:2022 (updated from ICC.1:2010)
**Backward Compatibility:** Revision 4.4 is fully backward compatible with earlier versions (4.2, 4.3)

---

## Overview

ICC color profiles are embedded in PDFs to specify color transformations and color space relationships. A preflight detection engine must validate profile structure, integrity, and compatibility without performing color management itself.

---

## 1. Profile Header Structure (Bytes 0-127)

**Critical for Validation:** The profile header is fixed-length (128 bytes) and contains essential metadata for profile identification and validation.

### Header Field Layout (Table 17 from Spec)

| Byte Range | Field Length | Field Name | Data Type | Purpose | Validation Rules |
|---|---|---|---|---|---|
| 0-3 | 4 | Profile Size | uInt32Number | Total profile size in bytes | Must match actual file size |
| 4-7 | 4 | Preferred CMM | Signature | Preferred Color Management Module | Optional; if used, must be ICC-registered; can be 0x00000000 |
| 8-11 | 4 | Profile Version | BCD | Major.Minor.BugFix.Reserved | Current: 04400000h (v4.4.0.0); bytes 10-11 must be 0x00 |
| 12-15 | 4 | Device Class | Signature | Profile type/class | Must be one of 7 defined classes (scnr, mntr, prtr, link, spac, abst, nmcl) |
| 16-19 | 4 | Data Colour Space | Signature | A-side (device) color space | Must match valid signature from color space table |
| 20-23 | 4 | PCS | Signature | B-side (PCS) color space | For non-DeviceLink: must be XYZ or Lab; for DeviceLink: any valid color space |
| 24-35 | 12 | Date/Time Created | dateTimeNumber | Profile creation timestamp | When profile was first created |
| 36-39 | 4 | Profile Signature | ASCII 'acsp' | File signature | Must be exactly 0x61637370 (acsp) |
| 40-43 | 4 | Platform | Signature | Primary OS/platform | Optional (APPL, MSFT, SGI, SUNW); can be 0x00000000 |
| 44-47 | 4 | Profile Flags | Bit field | CMM hints, embedding info | Bits 0-1 defined; bits 2-15 reserved; bits 16-31 vendor-specific |
| 48-51 | 4 | Device Manufacturer | Signature | Device manufacturer code | ICC-registered signature; optional (0x00000000 if unused) |
| 52-55 | 4 | Device Model | Signature | Device model code | ICC-registered signature; optional (0x00000000 if unused) |
| 56-63 | 8 | Device Attributes | Bit field | Media/device properties | Bits 0-3 describe media; bits 4-31 reserved (set to 0); bits 32-63 vendor-specific |
| 64-67 | 4 | Rendering Intent | uInt32Number | Default rendering intent | Lower 16 bits used (0=Perceptual, 1=Colorimetric-relative, 2=Saturation, 3=Absolute) |
| 68-79 | 12 | PCS Illuminant | XYZNumber | D50 illuminant tristimulus | Must be X≈0.9642, Y≈1.0, Z≈0.8249 |
| 80-83 | 4 | Profile Creator | Signature | Software creator signature | ICC-registered signature; optional (0x00000000 if unused) |
| 84-99 | 16 | Profile ID | MD5 hash | Profile fingerprint | Calculated per RFC 1321; zero if not calculated |
| 100-127 | 28 | Reserved | All zeros | Future expansion | Must be all 0x00 bytes |

### Header Validation Checks (ICC-001 to ICC-012)

**ICC-001: Profile Size Field**
- Check: Profile size in bytes 0-3 must equal actual file/data size
- Type: Critical structural validation
- Impact: Size mismatch indicates corruption or truncation
- Action: Reject if mismatch

**ICC-002: Profile File Signature**
- Check: Bytes 36-39 must contain exactly 0x61637370 (ASCII "acsp")
- Type: Mandatory
- Impact: Confirms this is an ICC profile
- Action: Reject if not "acsp"

**ICC-003: Profile Version**
- Check: Byte 8 = major version (current 0x04), Byte 9 = minor/bugfix (current 0x40), Bytes 10-11 must be 0x00
- Type: Validation + compatibility
- Current valid: 0x04400000 (v4.4.0.0)
- Backward compatible: v4.2, v4.3, v4.4
- Action: Warn if version > 4.4; reject if bytes 10-11 not zero

**ICC-004: Device Class**
- Check: Bytes 12-15 must contain exactly one of seven profile class signatures
- Valid signatures and hex codes:
  - 'scnr' (73636E72h) = Input device profile
  - 'mntr' (6D6E7472h) = Display device profile
  - 'prtr' (70727472h) = Output device profile
  - 'link' (6C696E6Bh) = DeviceLink profile
  - 'spac' (73706163h) = ColorSpace profile
  - 'abst' (61627374h) = Abstract profile
  - 'nmcl' (6E6D636Ch) = NamedColor profile
- Type: Critical
- Impact: Determines which tags are required
- Action: Reject if not in list

**ICC-005: Data Colour Space**
- Check: Bytes 16-19 must contain valid color space signature from Table 19
- Purpose: Specifies the device-side color space (A-side)
- Type: Critical
- Action: Reject if not in valid list

**ICC-006: PCS (Profile Connection Space)**
- Check: Bytes 20-23 must contain valid PCS signature
- Rules:
  - For non-DeviceLink profiles: must be 'XYZ ' or 'Lab ' (PCSXYZ or PCSLAB)
  - For DeviceLink profiles: any valid data color space signature
  - 'XYZ ' = 58595A20h (PCSXYZ)
  - 'Lab ' = 4C616220h (PCSLAB)
- Type: Critical
- Impact: Determines how B-side (PCS) data is encoded
- Action: Reject if invalid for profile class

**ICC-007: Date/Time Field**
- Check: Bytes 24-35 are valid dateTimeNumber (year: 1900-2999, month 1-12, day 1-31, hour 0-23, min 0-59, sec 0-59)
- Type: Validation
- Action: Warn if invalid; note: may be all zeros (0x000000000000)

**ICC-008: Platform Signature**
- Check: Bytes 40-43 contain optional platform code
- Valid values:
  - 'APPL' (4150504Ch) = Apple
  - 'MSFT' (4D534654h) = Microsoft
  - 'SGI ' (53474920h) = Silicon Graphics
  - 'SUNW' (53554E57h) = Sun
  - 0x00000000 = No platform specified
- Type: Optional
- Impact: Indicates target platform; informational only

**ICC-009: Rendering Intent Field**
- Check: Bytes 64-67 lower 16 bits contain valid intent (upper 16 bits must be 0x0000)
- Valid values:
  - 0 = Perceptual
  - 1 = Media-relative colorimetric
  - 2 = Saturation
  - 3 = ICC-absolute colorimetric
- Type: Important for usage
- Action: Warn if invalid value

**ICC-010: PCS Illuminant**
- Check: Bytes 68-79 (XYZNumber) must match D50 illuminant when rounded to 4 decimals
- Expected values:
  - X ≈ 0.9642 (hex: 7B6Bh in s15Fixed16Number)
  - Y = 1.0 (hex: 00010000h)
  - Z ≈ 0.8249
- Type: Important
- Impact: Defines PCS white point reference
- Action: Warn if significantly differs from D50

**ICC-011: Profile ID**
- Check: Bytes 84-99 contain 16-byte MD5 hash or all zeros
- Calculation: MD5 of entire profile with ID field, flags field, and rendering intent field set to 0x00
- Type: Optional (validation aid)
- Action: Informational; allow zero value

**ICC-012: Reserved Field**
- Check: Bytes 100-127 must all be 0x00
- Type: Mandatory
- Action: Warn if any non-zero bytes found (corrupted/non-compliant)

---

## 2. Color Space Signatures

**Table 19 - Valid Data Colour Space and PCS Signatures**

### Common Colour Spaces

| Colour Space | Signature | Hex Encoding | Context |
|---|---|---|---|
| nCIEXYZ / PCSXYZ | 'XYZ ' | 58595A20h | Can be device space or PCS |
| CIELAB / PCSLAB | 'Lab ' | 4C616220h | Can be device space or PCS |
| CIELUV | 'Luv ' | 4C757620h | Device space only |
| YCbCr | 'YCbr' | 59436272h | Device space (video) |
| CIEYxy | 'Yxy ' | 59787920h | Device space |
| RGB | 'RGB ' | 52474220h | Device space (common) |
| Gray/Monochrome | 'GRAY' | 47524159h | Device space |
| HSV | 'HSV ' | 48535620h | Device space |
| HLS | 'HLS ' | 484C5320h | Device space |
| CMYK | 'CMYK' | 434D594Bh | Device space (print) |
| CMY | 'CMY ' | 434D5920h | Device space (print) |

### Multi-Colour Spaces (N-Component)

| Colour Space | Signature | Hex Encoding | Meaning |
|---|---|---|---|
| 2 colour | '2CLR' | 32434C52h | 2-component custom |
| 3 colour (other) | '3CLR' | 33434C52h | 3-component custom (non-standard) |
| 4 colour (non-CMYK) | '4CLR' | 34434C52h | 4-component custom |
| 5 colour | '5CLR' | 35434C52h | 5-component custom |
| ... | ... | ... | ... |
| 15 colour | 'FCLR' | 46434C52h | 15-component custom |

**Validation Rule ICC-013:** For xCLR color spaces (custom multi-component), output profiles and DeviceLink profiles MUST have a colorantTableTag specifying names and PCS values.

---

## 3. Profile Classes and Requirements

### ICC-014: Profile Class Validation

**Input Device Profile ('scnr')**
- Used for: Scanners, cameras, digital capture devices
- Transform direction: Device → PCS
- Subtypes:
  - N-component LUT-based (supports PCSXYZ or PCSLAB)
  - Three-component matrix-based (PCSXYZ only)
  - Monochrome

**Display Device Profile ('mntr')**
- Used for: Monitors, screens, displays
- Transform direction: Device ↔ PCS (bidirectional)
- Subtypes:
  - N-component LUT-based
  - Three-component matrix-based (PCSXYZ only)
  - Monochrome

**Output Device Profile ('prtr')**
- Used for: Printers, film recorders, output devices
- Transform direction: PCS → Device (and optionally Device → PCS)
- Subtypes:
  - N-component LUT-based (most common for print)
  - Monochrome
- Note: Most important for preflight validation

**DeviceLink Profile ('link')**
- Used for: Direct Device1 → Device2 transformation
- Transform direction: Device1 → Device2 (one-way)
- Special rules:
  - Does not have mediaWhitePointTag or chromaticAdaptationTag requirements
  - Cannot be embedded in images
  - Preset rendering intent in header applies
  - PCS field contains output device color space (not PCSXYZ/PCSLAB)

**ColorSpace Profile ('spac')**
- Used for: Standard color encoding transformations
- Transform direction: Encoding ↔ PCS
- Note: Can be embedded; device-dependent fields may be zero

**Abstract Profile ('abst')**
- Used for: PCS-to-PCS color effects/transformations
- Transform direction: PCS → PCS only
- Note: Cannot be embedded in images

**NamedColor Profile ('nmcl')**
- Used for: Named color specifications
- Contains: Named color → PCS + optional device representation
- Note: Device-specific

---

## 4. Required Tags by Profile Class

### ICC-015: Input Profile (N-component LUT)

**Mandatory tags:**
- `profileDescriptionTag` - Profile name/description
- `copyrightTag` - Copyright notice
- `mediaWhitePointTag` - Media white point (XYZ)
- `AToB0Tag` - Device → PCS transformation (required)
- `chromaticAdaptationTag` - Chromatic adaptation (required only if white point differs from D50)

**Optional tags:**
- `AToB1Tag`, `AToB2Tag` - Alternative rendering intents
- `BToA0Tag`, `BToA1Tag`, `BToA2Tag` - Reverse transforms
- `DToB0Tag`, `DToB1Tag`, `DToB2Tag`, `DToB3Tag` - Float-based transforms
- `BToD0Tag`, `BToD1Tag`, `BToD2Tag`, `BToD3Tag` - Float-based reverse
- `gamutTag` - Gamut boundary

### ICC-016: Input Profile (Matrix-based RGB)

**Mandatory tags:**
- `profileDescriptionTag`
- `copyrightTag`
- `mediaWhitePointTag`
- `redMatrixColumnTag` - Red matrix column (XYZ)
- `greenMatrixColumnTag` - Green matrix column (XYZ)
- `blueMatrixColumnTag` - Blue matrix column (XYZ)
- `redTRCTag` - Red TRC curve
- `greenTRCTag` - Green TRC curve
- `blueTRCTag` - Blue TRC curve
- `chromaticAdaptationTag` - If white point differs from D50

**Constraint:** PCSXYZ encoding only (not PCSLAB)

### ICC-017: Input Profile (Monochrome)

**Mandatory tags:**
- `profileDescriptionTag`
- `copyrightTag`
- `mediaWhitePointTag`
- `grayTRCTag` - Gray tone reproduction curve
- `chromaticAdaptationTag` - If white point differs from D50

### ICC-018: Display Profile (N-component LUT)

**Mandatory tags:**
- `profileDescriptionTag`
- `copyrightTag`
- `mediaWhitePointTag`
- `AToB0Tag` - Device → PCS (perceptual, intent 0)
- `BToA0Tag` - PCS → Device (perceptual, intent 0)
- `chromaticAdaptationTag` - If white point differs from D50

**Optional:**
- `AToB1Tag`, `AToB2Tag` - Colorimetric and saturation intents
- `BToA1Tag`, `BToA2Tag`

### ICC-019: Output Profile (N-component LUT)

**Mandatory tags:**
- `profileDescriptionTag`
- `copyrightTag`
- `mediaWhitePointTag`
- `AToB0Tag` - Device → PCS (intent 0, perceptual)
- `AToB1Tag` - Device → PCS (intent 1, colorimetric)
- `AToB2Tag` - Device → PCS (intent 2, saturation)
- `BToA0Tag` - PCS → Device (intent 0)
- `BToA1Tag` - PCS → Device (intent 1)
- `BToA2Tag` - PCS → Device (intent 2)
- `gamutTag` - Out-of-gamut indicator
- `colorantTableTag` - Required only for xCLR color spaces
- `chromaticAdaptationTag` - If white point differs from D50

**Note:** Output profiles are most complex; all three rendering intents must be present

### ICC-020: DeviceLink Profile

**Mandatory tags:**
- `profileDescriptionTag`
- `copyrightTag`
- `profileSequenceDescTag` - Sequence of profiles used to build link
- `AToB0Tag` - Device1 → Device2 (rendering intent from header)
- `colorantTableTag` - If data color space is xCLR
- `colorantTableOutTag` - If PCS field is xCLR

**Special rules:**
- No `mediaWhitePointTag` required
- No `chromaticAdaptationTag` required
- One rendering intent in header applies to AToB0Tag
- Cannot be embedded in images

### ICC-021: ColorSpace Profile

**Mandatory tags:**
- `profileDescriptionTag`
- `copyrightTag`
- `mediaWhitePointTag`
- `AToB0Tag` - Encoding → PCS
- `BToA0Tag` - PCS → Encoding
- `chromaticAdaptationTag` - If white point differs from D50

### ICC-022: Abstract Profile

**Mandatory tags:**
- `profileDescriptionTag`
- `copyrightTag`
- `mediaWhitePointTag`
- `AToB0Tag` - PCS → PCS transformation
- `chromaticAdaptationTag` - If white point differs from D50

### ICC-023: NamedColor Profile

**Mandatory tags:**
- `profileDescriptionTag`
- `copyrightTag`
- `mediaWhitePointTag`
- `namedColor2Tag` - Named color definitions
- `chromaticAdaptationTag` - If white point differs from D50

---

## 5. Tag Table Structure

### ICC-024: Tag Table Layout

The tag table immediately follows the 128-byte header and provides random access to tagged data elements.

**Structure:**
```
Offset 0-3:   Tag count (n) as uInt32Number
Offset 4-7:   First tag signature (4 bytes)
Offset 8-11:  First tag data offset (uInt32Number)
Offset 12-15: First tag data size (uInt32Number)
Offset 16+:   Repeat entries for remaining (n-1) tags
```

**Total tag table size:** 4 + (12 × n) bytes

### ICC-025: Tag Entry Validation

For each tag entry:
- **Tag Signature:** 4-byte ASCII signature (e.g., 'desc', 'cprt', 'A2B0')
- **Offset:** Must be multiple of 4 bytes; must be ≥ 128 + tag table size
- **Size:** Actual tag data size in bytes (padding not included)
- **Uniqueness:** Each signature must be unique within tag table (no duplicates)
- **No gaps:** Tag data must form contiguous sequence with no gaps
- **Alignment:** All tag data must start on 4-byte boundary

### ICC-026: Tag Data Element Rules

- Tag data elements must not partially overlap
- Multiple tags may reference the same data offset (reuse)
- When reused, both offset and size must be identical
- All tag data (except last) padded to 4-byte boundary with 0x00 bytes (0-3 bytes padding)
- Last tag data padded only as needed to reach file end

---

## 6. Rendering Intents

### ICC-027: Rendering Intent Field Validation

**Location:** Bytes 64-67 in profile header

**Valid values (lower 16 bits of uInt32Number):**

| Intent Name | Value | Use Case | Application |
|---|---|---|---|
| Perceptual | 0 | General photography | Natural images, perceptual appearance |
| Media-relative colorimetric | 1 | Proofing accuracy | Preserve in-gamut colors relative to media white |
| Saturation | 2 | Graphics/charts | Preserve color saturation/vividness |
| ICC-absolute colorimetric | 3 | Exact match | Match absolute color to reference white |

**Rules:**
- Upper 16 bits (bits 16-31) must be 0x0000
- All three rendering intents required in output profiles (separate AToB0, AToB1, AToB2)
- Display profiles typically support intent 0 (perceptual)
- Input profiles typically support intent 0
- Intent in header may be default/recommended value
- DeviceLink profiles store the rendering intent used during linking

---

## 7. Profile Connection Space (PCS)

### ICC-028: PCS Encoding Options

Two encodings are supported; profile declares which in header (bytes 20-23):

**PCSXYZ (nCIEXYZ encoded)**
- Signature: 'XYZ ' (58595A20h)
- Encoding: 16-bit signed fixed-point per component or 32-bit float
- Range: Encoded to represent typical visible color range
- White point: X≈0.9642, Y≈1.0, Z≈0.8249 (D50 illuminant)
- Used by: Traditional profiles, matrix-based profiles, some LUT profiles

**PCSLAB (CIELAB encoded)**
- Signature: 'Lab ' (4C616220h)
- Encoding: 8-bit or 16-bit per component or 32-bit float
- Range: L* = 0-100, a* = ±127, b* = ±127
- White point: L* = 100, a* = 0, b* = 0 (D50)
- Perceptually uniform
- Used by: LUT-based profiles, especially with gamut mapping

### ICC-029: PCS Illuminant (D50)

D50 is the fixed reference white point for all ICC.1 profiles:
- nCIEXYZ tristimulus: X ≈ 0.9642, Y ≈ 1.0, Z ≈ 0.8249
- Encoded in header bytes 68-79
- All color transformations reference this illuminant
- When source measurement white differs, chromaticAdaptationTag indicates adaptation used

### ICC-030: PCS Values and Valid Ranges

**PCSXYZ 16-bit encoding:**
- Range: -127.0 to +127.0 per component
- Encoding: s15Fixed16Number (signed 15.16 fixed-point)
- Special note: ICC.1:2022 clarifies that negative PCSXYZ values are valid

**PCSLAB encoding:**
- L* range: 0.0 to 100.0 (16-bit: 0-65535 maps to 0-100)
- a* range: -127.0 to +127.0
- b* range: -127.0 to +127.0
- Note: Values >100 for L* are technically representable but invalid per PCS spec

---

## 8. Version History and Compatibility

### ICC-031: Version Identification and Backward Compatibility

**Current Version: 4.4.0.0**
- Encoded in header bytes 8-11: 0x04400000
- Byte 8 = major version (0x04)
- Byte 9 = minor/bugfix version (0x40 = minor 4, bugfix 0)
- Bytes 10-11 = reserved (must be 0x00)

**Version Timeline:**
- v4.2 - Original ISO 15076-1:2005 version
- v4.3 - Minor revision, fully backward compatible with v4.2
- v4.4 - Current ICC.1:2022 (fully backward compatible with v4.2 and v4.3)

**Backward Compatibility Rules:**
- v4.4 is fully backward compatible (no changes breaking v4.2/v4.3 interpretation)
- Profiles created by v4.2/v4.3 implementations can be read by v4.4
- v4.4 introduces optional new tags (metadataTag, dictType, cicpTag) but doesn't change core structure
- CMMs supporting v4.4 can process v4.2 and v4.3 profiles

**Key changes in ICC.1:2022 (v4.4) vs. ICC.1:2010 (v4.3):**
1. Clarification that PCSXYZ values can be negative
2. metadataTag added for flexible metadata
3. dictType added for key-value metadata
4. cicpTag added for HDR metadata
5. Tag tables now required to define contiguous sequence (no gaps)
6. Parametric curve functions corrected in Table 68

### ICC-032: Relationship to ICC.2 (iccMAX)

ICC.2 (iccMAX) is NOT a replacement for ICC.1 but an extension:
- Backward compatible with ICC.1 (ICC.2 CMM can read ICC.1)
- Not forward compatible (ICC.1 CMM cannot read most ICC.2 profiles)
- ICC.2 supports alternative PCS (D65, spectral, bi-spectral, multiplex)
- ICC.1 fixed to D50 PCS only
- ICC.2 profiles can be embedded in ICC.1 profiles per Technical Note 04-2018

---

## 9. Chromatic Adaptation

### ICC-033: Chromatic Adaptation Tag

**When required:**
If measurement data was obtained relative to a white point with different chromaticity than D50 (PCS adopted white), chromaticAdaptationTag must be present.

**Transformation:**
Converts measured XYZ values from actual adopted white to PCS adopted white (D50).

**Recommended method:** Linear Bradford model (described in Annex E)

**Header rule:** If chromaticAdaptationTag is absent, color data is assumed already adapted to D50.

---

## 10. Profile Validation Rules for Preflight

### ICC-034: Mandatory Validation Checks

**CRITICAL - Must be present for valid profile:**

1. Profile size field matches actual size
2. File signature = 0x61637370 ('acsp')
3. Profile version bytes 10-11 = 0x00
4. Device class is one of seven allowed values
5. Data color space signature is valid
6. PCS signature matches device class rules
7. Tag table immediately follows header (at byte 128)
8. Tag count is valid (> 0)
9. All tag offsets are 4-byte aligned and within file
10. All tag sizes are positive and within file
11. Tags form contiguous sequence with no gaps
12. No duplicate tag signatures
13. All required tags for profile class are present

### ICC-035: Important Validation Checks

**IMPORTANT - Should check; warn if missing:**

1. Profile ID is valid (zero or valid MD5)
2. Date/time field is plausible
3. PCS illuminant equals D50 (within tolerance)
4. Reserved header field (bytes 100-127) is all zeros
5. Rendering intent is valid (0-3)
6. All tags have registered signatures

### ICC-036: Warning-Level Checks

**INFORMATIONAL - Log but don't reject:**

1. Preferred CMM is registered
2. Device manufacturer is registered
3. Device model is registered
4. Profile creator is registered
5. Platform field matches actual platform
6. Profile flags are plausible
7. Device attributes describe reasonable media

---

## 11. Preflight Detection Rules

### ICC-037: Profile Class Detection

From header bytes 12-15, determine:

```
IF device_class = 'scnr' THEN "Input Profile (Scanner/Camera)"
IF device_class = 'mntr' THEN "Display Profile (Monitor)"
IF device_class = 'prtr' THEN "Output Profile (Printer)"
IF device_class = 'link' THEN "DeviceLink Profile (Direct Device Transform)"
IF device_class = 'spac' THEN "ColorSpace Profile (Encoding Conversion)"
IF device_class = 'abst' THEN "Abstract Profile (PCS Effect)"
IF device_class = 'nmcl' THEN "NamedColor Profile (Named Colors)"
```

### ICC-038: PDF-Specific Validation

When profile is embedded in PDF:

**Must check:**
1. Profile size in header ≤ actual embedded data size
2. For print workflows: expect 'prtr' (output) profiles
3. For screen display: may have 'mntr' (display) profiles
4. Color space in PDF document definition matches profile data color space

**Should flag:**
1. Input ('scnr') profiles embedded (unusual in PDFs)
2. Abstract ('abst') profiles used as working spaces
3. DeviceLink ('link') profiles limiting to preset transform

### ICC-039: Color Space Compatibility

**For PDF RGB image + embedded profile:**
- Expected data color space: 'RGB ' (52474220h)
- Typical PCS: 'XYZ ' or 'Lab '
- Common class: 'mntr' (display) or 'spac' (RGB ColorSpace)

**For PDF CMYK image + embedded profile:**
- Expected data color space: 'CMYK' (434D594Bh)
- Typical PCS: 'XYZ ' or 'Lab '
- Expected class: 'prtr' (output)
- MUST have colorantTableTag if multi-component

**For PDF Lab image + embedded profile:**
- Expected data color space: 'Lab ' (4C616220h)
- Expected PCS: 'Lab ' or 'XYZ '
- Expected class: 'spac' (ColorSpace)

---

## 12. Grounded Inspection ID Mapping

All validation rules and checks map to Grounded Inspection IDs:

| ID | Category | Check |
|---|---|---|
| ICC-001 | Header | Profile size consistency |
| ICC-002 | Header | File signature ('acsp') |
| ICC-003 | Header | Version field validation |
| ICC-004 | Header | Device class validation |
| ICC-005 | Header | Data color space validation |
| ICC-006 | Header | PCS field validation |
| ICC-007 | Header | Date/time field |
| ICC-008 | Header | Platform signature |
| ICC-009 | Header | Rendering intent |
| ICC-010 | Header | PCS illuminant (D50) |
| ICC-011 | Header | Profile ID (MD5) |
| ICC-012 | Header | Reserved field (zeros) |
| ICC-013 | ColorSpace | Multi-component color space requirements |
| ICC-014 | ClassTypes | Profile class identification |
| ICC-015 | RequiredTags | Input profile (LUT) requirements |
| ICC-016 | RequiredTags | Input profile (matrix) requirements |
| ICC-017 | RequiredTags | Input profile (monochrome) requirements |
| ICC-018 | RequiredTags | Display profile requirements |
| ICC-019 | RequiredTags | Output profile requirements |
| ICC-020 | RequiredTags | DeviceLink profile requirements |
| ICC-021 | RequiredTags | ColorSpace profile requirements |
| ICC-022 | RequiredTags | Abstract profile requirements |
| ICC-023 | RequiredTags | NamedColor profile requirements |
| ICC-024 | TagTable | Tag table structure |
| ICC-025 | TagTable | Tag entry validation |
| ICC-026 | TagTable | Tag data alignment and padding |
| ICC-027 | RenderingIntent | Intent value validation |
| ICC-028 | PCS | PCS encoding selection (XYZ vs Lab) |
| ICC-029 | PCS | PCS illuminant (D50) reference |
| ICC-030 | PCS | Valid PCS value ranges |
| ICC-031 | Version | Version identification and compatibility |
| ICC-032 | Version | ICC.2 relationship |
| ICC-033 | Adaptation | Chromatic adaptation requirements |
| ICC-034 | Validation | Critical validation checks |
| ICC-035 | Validation | Important validation checks |
| ICC-036 | Validation | Warning-level checks |
| ICC-037 | Detection | Profile class detection from header |
| ICC-038 | PDFContext | PDF-specific profile validation |
| ICC-039 | ColorSpaceMatch | Color space compatibility for images |

---

## 13. Quick Reference: Common Issues and Fixes

### Corrupted Profile Header
- **Symptom:** Size field doesn't match actual data
- **Check:** ICC-001
- **Action:** Reject profile; report truncation/corruption

### Invalid Device Class
- **Symptom:** Bytes 12-15 don't match seven allowed signatures
- **Check:** ICC-004
- **Action:** Reject; log unknown class code

### Missing Required Tags
- **Symptom:** Expected tags for profile class not in tag table
- **Check:** ICC-015 to ICC-023
- **Action:** Reject; report missing tag(s) and class type

### Color Space Mismatch
- **Symptom:** Profile data color space doesn't match image color space
- **Check:** ICC-039
- **Action:** Warn; may result in incorrect color rendering

### Invalid PCS for Profile Type
- **Symptom:** Display profile has PCS='CMYK' instead of 'XYZ ' or 'Lab '
- **Check:** ICC-006
- **Action:** Reject; invalid PCS for non-DeviceLink profile

### Tag Offset Not 4-byte Aligned
- **Symptom:** Tag offset lower 2 bits not zero
- **Check:** ICC-025
- **Action:** Reject; alignment violation indicates corruption

### PCS Illuminant Not D50
- **Symptom:** Bytes 68-79 don't match D50 tristimulus values
- **Check:** ICC-010
- **Action:** Warn if significantly different; major deviation indicates non-standard profile

---

## References

- **ICC.1:2022:** International Color Consortium Specification (Profile version 4.4.0.0)
- **ISO 15076-1:2010:** ISO version (technically identical to ICC.1:2010)
- **ISO 13655:** Spectral measurement and colorimetric computation
- **ISO 3664:** Viewing conditions
- **RFC 1321:** MD5 Message-Digest Algorithm
- **ICC Technical Note 10-2021:** Embedding ICC Profiles
- **ICC Technical Note 04-2018:** Embedding ICC.2 in ICC.1 profiles
- **ICC Tag Registry:** www.color.org/registry/

---

**Document generated:** 2026-03-11
**Extraction source:** ICC.1:2022-05.pdf (126 pages)
**Purpose:** Preflight color profile validation engine reference
