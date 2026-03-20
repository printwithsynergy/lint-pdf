# ICC.1:2022 Specification Parsing - Complete Summary

**Date:** March 11, 2026
**Source:** ICC.1:2022-05.pdf (126 pages)
**Extraction Method:** pdfplumber text extraction + manual analysis
**Output Format:** Markdown with Grounded Inspection ID mapping
**Purpose:** Preflight validation engine reference for PDF color profile validation

---

## Deliverables Created

### 1. icc1-2022-color-profiles.md (27 KB, 714 lines)
**Comprehensive reference document covering all structural and validation aspects.**

#### Contents:
- **Section 1:** Profile Header Structure (13 validation rules: ICC-001 to ICC-012)
  - All 18 header fields detailed (bytes 0-127)
  - Data types, encoding, constraints
  - Validation rules with failure actions

- **Section 2:** Color Space Signatures
  - Table 19: Complete list of 31 color space signatures
  - ICC-013: Multi-component color space requirements

- **Section 3:** Profile Classes & Requirements
  - ICC-014 through ICC-023: 7 profile classes × 3 subtypes each
  - Required tags by class (Input, Display, Output, DeviceLink, ColorSpace, Abstract, NamedColor)

- **Section 4:** Tag Table Structure
  - ICC-024: Tag table layout and access model
  - ICC-025: Per-tag validation rules
  - ICC-026: Data element alignment and padding rules

- **Section 5:** Rendering Intents
  - ICC-027: Four rendering intents with use cases

- **Section 6:** Profile Connection Space (PCS)
  - ICC-028 through ICC-030: PCS encoding (PCSXYZ vs PCSLAB)
  - Valid value ranges and D50 illuminant reference

- **Section 7:** Version History
  - ICC-031: v4.2 / v4.3 / v4.4 compatibility
  - ICC-032: Relationship to ICC.2 (iccMAX)

- **Section 8:** Chromatic Adaptation
  - ICC-033: Adaptation tag requirements

- **Section 9-11:** Preflight Validation Rules
  - ICC-034 through ICC-039: Critical, important, and warning-level checks
  - PDF context-specific validation

- **Section 12:** Grounded Inspection ID Mapping (39 IDs)
  - Complete mapping table for all checks

- **Section 13:** Quick reference for common issues

### 2. icc1-2022-validation-checklist.md (14 KB, 357 lines)
**Step-by-step implementation checklist for preflight engines.**

#### Contents:
- **Phase 1:** Header Validation (12 checks)
- **Phase 2:** Signature Validation (4 checks)
- **Phase 3:** Tag Table Validation (8 checks)
- **Phase 4:** Class-Specific Tag Requirements (7 branches)
- **Phase 5:** PCS and Color Space Validation (3 checks)
- **Phase 6:** PDF Context Checks (3 checks)
- **Phase 7:** Version and Compatibility (2 checks)
- **Phase 8:** Summary Output
  - REJECT reasons (critical failures)
  - WARN reasons (questionable issues)
  - ACCEPT reasons (valid profile)

#### Implementation Notes:
- Tag signature format and hex codes
- Common data types and byte ordering
- Complete tag signature table

### 3. icc1-2022-tag-reference.md (14 KB, 275 lines)
**Complete tag catalog with signatures, types, and requirements.**

#### Contents:
- **Part 1:** All 40+ registered tags (alphabetical)
  - Transformation tags (A2B*, B2A*, D2B*, B2D*)
  - Matrix/TRC tags (rXYZ, gXYZ, bXYZ, rTRC, gTRC, bTRC, kTRC)
  - Mandatory metadata (desc, cprt, wtpt, chad)
  - Device definition (clrt, clro, clro, chro)
  - Viewing/perception (view, vued, lumi)
  - Measurement (meas, calt, targ, tech)
  - Gamut/quality (gamt, prig, srig)
  - Profile sequence (pseq, psid)
  - Named colors (nc2)
  - New in v4.4 (meta, cicp)

- **Part 2:** Quick lookups
  - By purpose (critical, common, per-class)
  - By hex code (44 entries)

- **Part 3:** Tag types reference
  - 14 common tag data types with examples

- **Part 4:** Private tag guidelines

---

## Grounded Inspection IDs (39 Total)

### Header Field Validation (ICC-001 to ICC-012)
| ID | Check | Failure Severity |
|---|---|---|
| ICC-001 | Profile size field matches actual size | REJECT |
| ICC-002 | File signature = 0x61637370 ('acsp') | REJECT |
| ICC-003 | Profile version: bytes format and range | WARN/REJECT |
| ICC-004 | Device class in seven allowed values | REJECT |
| ICC-005 | Data colour space valid signature | REJECT |
| ICC-006 | PCS valid for profile class | REJECT |
| ICC-007 | Date/time field plausible | WARN |
| ICC-008 | Platform signature valid | WARN |
| ICC-009 | Rendering intent 0-3 | WARN |
| ICC-010 | PCS illuminant ≈ D50 | WARN |
| ICC-011 | Profile ID zero or valid MD5 | INFO |
| ICC-012 | Reserved field all zeros | WARN |

### Color Space and Class Validation (ICC-013 to ICC-023)
| ID | Check | Severity |
|---|---|---|
| ICC-013 | Multi-component color space colorantTable requirement | REJECT |
| ICC-014 | Identify profile class from header signature | N/A (detection) |
| ICC-015 | Input profile (LUT) required tags present | REJECT |
| ICC-016 | Input profile (matrix-based) required tags | REJECT |
| ICC-017 | Input profile (monochrome) required tags | REJECT |
| ICC-018 | Display profile required tags | REJECT |
| ICC-019 | Output profile required tags | REJECT |
| ICC-020 | DeviceLink profile required tags | REJECT |
| ICC-021 | ColorSpace profile required tags | REJECT |
| ICC-022 | Abstract profile required tags | REJECT |
| ICC-023 | NamedColor profile required tags | REJECT |

### Tag Table and Data Validation (ICC-024 to ICC-026)
| ID | Check | Severity |
|---|---|---|
| ICC-024 | Tag table structure and location | REJECT |
| ICC-025 | Individual tag entry validation (offsets, sizes) | REJECT |
| ICC-026 | Tag data alignment, padding, contiguity | REJECT |

### Domain Validation (ICC-027 to ICC-030)
| ID | Check | Severity |
|---|---|---|
| ICC-027 | Rendering intent value 0-3, upper bits zero | WARN |
| ICC-028 | PCS encoding consistency (XYZ vs Lab) | WARN |
| ICC-029 | PCS illuminant fixed to D50 | WARN |
| ICC-030 | PCS value ranges valid | WARN |

### Version and Compatibility (ICC-031 to ICC-032)
| ID | Check | Severity |
|---|---|---|
| ICC-031 | Profile version compatible | WARN/REJECT |
| ICC-032 | ICC.2 relationship (extension, not replacement) | INFO |

### Structural and Adaptation (ICC-033)
| ID | Check | Severity |
|---|---|---|
| ICC-033 | Chromatic adaptation tag required if non-D50 | WARN |

### Preflight Rules (ICC-034 to ICC-039)
| ID | Check | Severity |
|---|---|---|
| ICC-034 | All critical validation checks pass | REJECT |
| ICC-035 | Important checks pass (complete validation) | WARN |
| ICC-036 | Warning-level checks (completeness) | WARN |
| ICC-037 | Profile class detection algorithm | N/A (detection) |
| ICC-038 | PDF context validation (class match) | WARN |
| ICC-039 | Color space compatibility with image type | WARN |

---

## Key Technical Extracts

### Profile Header (128 bytes)
```
Offset  Length  Field                    Type              Validation
0-3     4       Profile Size             uInt32Number      Must match actual size
4-7     4       Preferred CMM            Signature         Optional; ICC-registered
8-11    4       Profile Version          Binary-coded dec  Current: 04400000h
12-15   4       Device Class             Signature         Seven allowed values
16-19   4       Data Colour Space        Signature         Valid color space
20-23   4       PCS                      Signature         XYZ or Lab (non-DeviceLink)
24-35   12      Date/Time Created        dateTimeNumber    When profile created
36-39   4       Profile Signature        ASCII 'acsp'      0x61637370 (mandatory)
40-43   4       Primary Platform         Signature         APPL, MSFT, SGI, SUNW
44-47   4       Profile Flags            Bit field         Bits 0-1 defined
48-51   4       Device Manufacturer      Signature         ICC-registered
52-55   4       Device Model             Signature         ICC-registered
56-63   8       Device Attributes        Bit field         Bits 0-3 = media
64-67   4       Rendering Intent         uInt32Number      0-3 (lower 16 bits)
68-79   12      PCS Illuminant           XYZNumber         D50: X≈0.9642, Y≈1.0, Z≈0.8249
80-83   4       Profile Creator          Signature         ICC-registered
84-99   16      Profile ID               MD5 hash          RFC 1321; zero if not calculated
100-127 28      Reserved                 All zeros         Must be 0x00
```

### Profile Classes (7 Types)
```
Class          Signature  Hex        Device Type      Transform
Input          'scnr'     73636E72h  Scanner/Camera   Device → PCS
Display        'mntr'     6D6E7472h  Monitor/Screen   Device ↔ PCS
Output         'prtr'     70727472h  Printer          PCS → Device (+ reverse)
DeviceLink     'link'     6C696E6Bh  Device1 → Device Device1 → Device2
ColorSpace     'spac'     73706163h  Encoding         Encoding ↔ PCS
Abstract       'abst'     61627374h  Effect           PCS → PCS
NamedColor     'nmcl'     6E6D636Ch  Named colors     Name → PCS + device
```

### Rendering Intents (4 Types)
```
Intent                           Value  Use Case              Profile Location
Perceptual                       0      Natural images        AToB0, BToA0
Media-relative colorimetric      1      Proofing              AToB1, BToA1
Saturation                       2      Graphics/charts       AToB2, BToA2
ICC-absolute colorimetric        3      Exact match           DToB3, BToD3
```

### Color Spaces (31 Signatures)
```
Primary:        RGB, CMYK, GRAY, XYZ, Lab, HSV, HLS, CMY, etc.
Multi-component: 2CLR through FCLR (2-15 color components)
Video:          YCbCr
CIE:            Luv, Yxy
```

### Tag Categories by Frequency in PDFs
```
CRITICAL (always check):
  - A2B0 (Device → PCS)
  - B2A0 (PCS → Device)
  - desc (Profile name)
  - cprt (Copyright)
  - wtpt (White point)

COMMON (output profiles):
  - A2B1, A2B2, B2A1, B2A2 (Intent transforms)
  - gamt (Gamut)
  - clrt (Colorants for CMYK)

OPTIONAL (may or may not exist):
  - meta, cicp (new in v4.4)
  - chad (Chromatic adaptation)
  - view, vued (Viewing conditions)
```

---

## Validation Logic Flow

### Recommended Implementation Order

```
1. READ HEADER (bytes 0-127)
   ↓ Check profile size (ICC-001)
   ↓ Check 'acsp' signature (ICC-002)
   ↓ Check version format (ICC-003)
   ↓ Identify device class (ICC-004)
   ↓ Validate color spaces (ICC-005, ICC-006)

2. READ TAG TABLE (128+ bytes)
   ↓ Verify tag count > 0 (ICC-024a)
   ↓ Verify tag table size = 4 + 12n bytes
   ↓ For each tag:
      ↓ Validate offset (4-byte aligned, within bounds) (ICC-025c)
      ↓ Validate size (positive, within bounds) (ICC-025d)
   ↓ Check tag contiguity/no gaps (ICC-026)
   ↓ Check no duplicate tags (ICC-025b)

3. VERIFY REQUIRED TAGS FOR CLASS (ICC-015 to ICC-023)
   ↓ Based on device class from step 1
   ↓ Verify each mandatory tag present
   ↓ Verify critical mandatory tags (profileDescription, copyright)

4. OUTPUT VALIDATION RESULT
   ↓ REJECT if any critical check fails
   ↓ WARN if important checks fail
   ↓ ACCEPT with warnings if all critical pass
```

---

## Common Failure Scenarios

### Scenario 1: Corrupted/Truncated Profile
- **Indicator:** Size field doesn't match actual data
- **Check:** ICC-001
- **Action:** REJECT - Profile is corrupt

### Scenario 2: Invalid Output Profile for Print
- **Indicator:** Device class = 'mntr' or 'scnr' instead of 'prtr'
- **Check:** ICC-004, ICC-038
- **Action:** WARN - May not work correctly for CMYK output

### Scenario 3: Missing Critical Tags
- **Indicator:** AToB0 or BToA0 missing from output profile
- **Check:** ICC-019
- **Action:** REJECT - Cannot perform color transformation

### Scenario 4: Color Space Mismatch
- **Indicator:** Image is CMYK but profile data color space = 'RGB '
- **Check:** ICC-039
- **Action:** WARN - Color transformation will be incorrect

### Scenario 5: Non-D50 White Point
- **Indicator:** PCS illuminant bytes 68-79 ≠ D50 values
- **Check:** ICC-010
- **Action:** WARN - Non-standard profile (may work but unusual)

### Scenario 6: Misaligned Tag Data
- **Indicator:** Tag offset lower 2 bits ≠ 0
- **Check:** ICC-025c
- **Action:** REJECT - Structural violation; indicates corruption or non-compliance

---

## Statistics from Parsed Specification

| Item | Count | Notes |
|---|---|---|
| Total pages | 126 | PDF extraction complete |
| Profile header fields | 18 | Bytes 0-127 |
| Valid device classes | 7 | Input, Display, Output, DeviceLink, ColorSpace, Abstract, NamedColor |
| Valid color spaces | 31 | Including 14 multi-component (2CLR-FCLR) |
| Rendering intents | 4 | Perceptual, Colorimetric-rel, Saturation, Absolute |
| Registered tags | 40+ | From Clause 9 (Tag Definitions) |
| Grounded inspection IDs | 39 | Full validation coverage |
| Required tag sets | 7 | One per profile class |
| Key validation rules | 40+ | REJECT/WARN/INFO severity |

---

## Implementation Checklist

- [x] Extract all 126 pages via pdfplumber
- [x] Parse header structure (bytes 0-127)
- [x] Document color space signatures (Table 19)
- [x] Extract profile class definitions and requirements
- [x] Map required tags per class (Annex G)
- [x] Document tag table structure and validation
- [x] Extract rendering intent definitions
- [x] Document PCS encoding rules
- [x] Capture version history and compatibility
- [x] Create 39-point Grounded Inspection ID mapping
- [x] Generate validation checklist (8 phases)
- [x] Create tag reference (40+ tags with hex codes)
- [x] Provide quick-lookup tables and references

---

## Files Generated

1. **icc1-2022-color-profiles.md** (27 KB)
   - Comprehensive structural reference
   - All validation rules with ICC-IDs
   - Detailed field descriptions

2. **icc1-2022-validation-checklist.md** (14 KB)
   - Step-by-step implementation guide
   - Phase-based validation
   - Common issues and fixes

3. **icc1-2022-tag-reference.md** (14 KB)
   - Complete tag catalog
   - Hex code lookup table
   - Tag type reference

4. **ICC-PARSING-SUMMARY.md** (This file)
   - Overview of deliverables
   - Grounded ID mapping
   - Implementation guidance

---

## How to Use These Documents

### For Preflight Engine Development
1. **Start with:** icc1-2022-validation-checklist.md
   - Use phases 1-8 as implementation guide
   - Each checkpoint maps to ICC-IDs for logging

2. **Reference:** icc1-2022-color-profiles.md
   - Detailed technical explanation for each ICC-ID
   - Background on PCS, rendering intents, classes

3. **Lookup:** icc1-2022-tag-reference.md
   - Tag signature validation
   - Expected tags per profile class
   - Hex code conversion

### For PDF Preflight/Validation
- **Profile validation flow:** icc1-2022-validation-checklist.md Phases 1-6
- **Color space compatibility:** Section on ICC-039
- **Common issues:** Quick reference section

### For Quality Assurance
- **Test vectors:** Use the validation rules to create test profiles
- **Edge cases:** Refer to version compatibility (ICC-031) and PCS rules (ICC-028 to ICC-030)
- **Regression testing:** Use the 39 ICC-IDs as test case reference

---

**Specification Parsing Complete**
**Ready for Grounded Integration**
**All preflight-relevant content extracted and organized**
