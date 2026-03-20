# ICC.1:2022 Profile Validation Checklist for Preflight Engines

**Purpose:** Quick reference checklist for implementing ICC profile validation in PDF preflight detection.

**Source Document:** ICC.1:2022 (Profile version 4.4.0.0)

---

## Phase 1: Header Validation (Bytes 0-127)

### Structure Checks
- [ ] **ICC-001** Profile size field (bytes 0-3) matches actual embedded profile size
  - Failure indicates: Truncation, corruption, or size field error
  - Action: REJECT profile

- [ ] **ICC-002** Profile file signature (bytes 36-39) = 0x61637370 ('acsp')
  - Failure indicates: Invalid file format or data corruption
  - Action: REJECT profile (not an ICC profile)

- [ ] **ICC-003** Profile version (bytes 8-11)
  - Byte 8 = major version (current: 0x04)
  - Byte 9 = minor.bugfix (current: 0x40 for v4.4)
  - Bytes 10-11 must be 0x00
  - Acceptable versions: 0x02000000 (v2), 0x02040000 (v2.4), 0x04000000 (v4.0), 0x04200000 (v4.2), 0x04300000 (v4.3), 0x04400000 (v4.4)
  - Failure action: WARN if unknown version; REJECT if bytes 10-11 not zero

- [ ] **ICC-012** Reserved field (bytes 100-127) all zeros (0x00)
  - Failure action: WARN (non-critical but indicates non-compliant creation)

### Device/Color Space Definition
- [ ] **ICC-004** Device class (bytes 12-15) is one of seven valid signatures:
  - 'scnr' (input device)
  - 'mntr' (display device)
  - 'prtr' (output device/printer)
  - 'link' (devicelink)
  - 'spac' (color space)
  - 'abst' (abstract)
  - 'nmcl' (named color)
  - Action: REJECT if not in list

- [ ] **ICC-005** Data colour space (bytes 16-19) is valid signature from Table 19
  - Common: 'RGB ', 'GRAY', 'CMYK', 'XYZ ', 'Lab ', 'Luv ', 'YCbr'
  - Multi-component: '2CLR' through 'FCLR' (2-15 colours)
  - Action: REJECT if not in valid list

- [ ] **ICC-006** PCS (bytes 20-23) is valid for profile class
  - NON-DEVICELINK: Must be 'XYZ ' (PCSXYZ) or 'Lab ' (PCSLAB)
  - DEVICELINK: Any valid colour space signature (becomes output space)
  - Action: REJECT if invalid for class

### Metadata and Quality Checks
- [ ] **ICC-007** Date/time created (bytes 24-35) is plausible dateTimeNumber
  - Year: 1900-2999
  - Month: 1-12
  - Day: 1-31
  - Hour: 0-23
  - Minute: 0-59
  - Second: 0-59
  - Action: WARN if implausible; ACCEPT zeros (creation date unknown)

- [ ] **ICC-008** Platform (bytes 40-43) is zero or valid platform signature
  - Valid: 'APPL' (Apple), 'MSFT' (Microsoft), 'SGI ' (Silicon Graphics), 'SUNW' (Sun)
  - Action: WARN if unknown non-zero platform; ACCEPT zeros

- [ ] **ICC-009** Rendering intent (bytes 64-67) lower 16 bits valid
  - Valid values: 0 (perceptual), 1 (relative colorimetric), 2 (saturation), 3 (absolute colorimetric)
  - Upper 16 bits must be 0x0000
  - Action: WARN if invalid; REJECT if upper bits not zero

- [ ] **ICC-010** PCS illuminant (bytes 68-79) ≈ D50 reference white
  - Expected (rounded to 4 decimals): X ≈ 0.9642, Y ≈ 1.0, Z ≈ 0.8249
  - Tolerance: Allow ±0.005 deviation
  - Encoded as XYZNumber (s15Fixed16Number)
  - Action: WARN if significantly differs (indicates non-standard profile); REJECT if wildly off

- [ ] **ICC-011** Profile ID (bytes 84-99)
  - Either: All zeros (0x00...00) if not calculated
  - Or: Valid 16-byte MD5 hash
  - Action: INFORMATIONAL; accept either (helpful for deduplication)

---

## Phase 2: Signature Validation

- [ ] **ICC-001** Preferred CMM (bytes 4-7) is zero or ICC-registered signature
  - Action: WARN if unknown non-zero CMM signature

- [ ] **ICC-048** Device manufacturer (bytes 48-51) is zero or ICC-registered signature
  - Action: WARN if unknown non-zero manufacturer code

- [ ] **ICC-049** Device model (bytes 52-55) is zero or ICC-registered signature
  - Action: WARN if unknown non-zero model code

- [ ] **ICC-050** Profile creator (bytes 80-83) is zero or ICC-registered signature
  - Action: WARN if unknown non-zero creator code

---

## Phase 3: Tag Table Validation (Bytes 128+)

### Tag Table Structure
- [ ] **ICC-024** Tag table starts immediately after header at byte offset 128

- [ ] **ICC-024a** Tag count (offset 0 in tag table, i.e., byte 128-131) > 0
  - Action: REJECT if tag count is zero

- [ ] **ICC-024b** Tag count is reasonable (typically < 100; warn if > 200)

- [ ] **ICC-025a** Tag table size = 4 + (12 × tag_count) bytes
  - Verify first tag data begins at: 128 + tag_table_size

- [ ] **ICC-025b** No duplicate tag signatures in tag table
  - Action: REJECT if duplicates found

### Individual Tag Entry Validation
- [ ] **ICC-025c** Each tag offset (tag entry bytes 8-11) is:
  - 4-byte aligned (offset & 0x3 == 0)
  - ≥ 128 + tag_table_size
  - ≤ profile_size - tag_size
  - Action: REJECT if alignment violated or offset out of bounds

- [ ] **ICC-025d** Each tag size (tag entry bytes 12-15) is:
  - Positive (> 0)
  - ≤ profile_size - tag_offset
  - Action: REJECT if invalid

- [ ] **ICC-026a** Tag data elements form contiguous sequence:
  - Sort tags by offset
  - Each tag's end (offset + size + padding to 4-byte boundary) = next tag's offset
  - No gaps allowed
  - Action: REJECT if gaps found

- [ ] **ICC-026b** Last tag element padding only extends to file end:
  - Last tag end (offset + size) ≤ profile_size
  - Last tag end + 0-3 pad bytes = profile_size
  - Action: REJECT if extra padding detected

---

## Phase 4: Class-Specific Tag Requirements

### Determine Profile Class (from ICC-004 check)

#### IF Device Class = 'scnr' (Input Device)
- [ ] **ICC-015/016/017** Required tags present:
  - [ ] `profileDescriptionTag` ('desc')
  - [ ] `copyrightTag` ('cprt')
  - [ ] `mediaWhitePointTag` ('wtpt')
  - [ ] One of:
    - [ ] `AToB0Tag` ('A2B0') for LUT-based input
    - [ ] `redMatrixColumnTag` ('rXYZ'), `greenMatrixColumnTag` ('gXYZ'), `blueMatrixColumnTag` ('bXYZ'), `redTRCTag` ('rTRC'), `greenTRCTag` ('gTRC'), `blueTRCTag` ('bTRC') for matrix-based
    - [ ] `grayTRCTag` ('kTRC') for monochrome
  - [ ] `chromaticAdaptationTag` ('chad') if white point ≠ D50 (recommended for non-D50)
  - Action: REJECT if critical tags missing

#### IF Device Class = 'mntr' (Display Device)
- [ ] **ICC-018** Required tags present:
  - [ ] `profileDescriptionTag` ('desc')
  - [ ] `copyrightTag` ('cprt')
  - [ ] `mediaWhitePointTag` ('wtpt')
  - [ ] `AToB0Tag` ('A2B0') and `BToA0Tag` ('B2A0') for LUT-based
  - [ ] OR matrix columns + TRCs for matrix-based
  - [ ] OR `grayTRCTag` for monochrome
  - [ ] `chromaticAdaptationTag` if white point ≠ D50
  - Action: REJECT if critical tags missing

#### IF Device Class = 'prtr' (Output Device)
- [ ] **ICC-019** Required tags present:
  - [ ] `profileDescriptionTag` ('desc')
  - [ ] `copyrightTag` ('cprt')
  - [ ] `mediaWhitePointTag` ('wtpt')
  - [ ] For LUT-based:
    - [ ] `AToB0Tag` ('A2B0') - intent 0 (perceptual)
    - [ ] `AToB1Tag` ('A2B1') - intent 1 (colorimetric)
    - [ ] `AToB2Tag` ('A2B2') - intent 2 (saturation)
    - [ ] `BToA0Tag` ('B2A0')
    - [ ] `BToA1Tag` ('B2A1')
    - [ ] `BToA2Tag` ('B2A2')
    - [ ] `gamutTag` ('gamt')
    - [ ] `colorantTableTag` ('clrt') if data color space is xCLR
  - [ ] OR `grayTRCTag` for monochrome
  - [ ] `chromaticAdaptationTag` if white point ≠ D50
  - Action: REJECT if critical tags missing

#### IF Device Class = 'link' (DeviceLink)
- [ ] **ICC-020** Required tags present:
  - [ ] `profileDescriptionTag` ('desc')
  - [ ] `copyrightTag` ('cprt')
  - [ ] `profileSequenceDescTag` ('pseq')
  - [ ] `AToB0Tag` ('A2B0') with rendering intent from header
  - [ ] `colorantTableTag` ('clrt') if input data color space is xCLR
  - [ ] `colorantTableOutTag` ('clro') if output PCS is xCLR
  - [ ] NO `mediaWhitePointTag` required
  - [ ] NO `chromaticAdaptationTag` required
  - Action: REJECT if critical tags missing

#### IF Device Class = 'spac' (ColorSpace)
- [ ] **ICC-021** Required tags present:
  - [ ] `profileDescriptionTag` ('desc')
  - [ ] `copyrightTag` ('cprt')
  - [ ] `mediaWhitePointTag` ('wtpt')
  - [ ] `AToB0Tag` ('A2B0')
  - [ ] `BToA0Tag` ('B2A0')
  - [ ] `chromaticAdaptationTag` if white point ≠ D50
  - Action: REJECT if critical tags missing

#### IF Device Class = 'abst' (Abstract)
- [ ] **ICC-022** Required tags present:
  - [ ] `profileDescriptionTag` ('desc')
  - [ ] `copyrightTag` ('cprt')
  - [ ] `mediaWhitePointTag` ('wtpt')
  - [ ] `AToB0Tag` ('A2B0') for PCS-to-PCS transform
  - [ ] `chromaticAdaptationTag` if white point ≠ D50
  - Action: REJECT if critical tags missing

#### IF Device Class = 'nmcl' (NamedColor)
- [ ] **ICC-023** Required tags present:
  - [ ] `profileDescriptionTag` ('desc')
  - [ ] `copyrightTag` ('cprt')
  - [ ] `mediaWhitePointTag` ('wtpt')
  - [ ] `namedColor2Tag` ('nc2 ')
  - [ ] `chromaticAdaptationTag` if white point ≠ D50
  - Action: REJECT if critical tags missing

---

## Phase 5: PCS and Color Space Validation

- [ ] **ICC-028** PCS encoding consistency:
  - IF profile declares PCS = 'XYZ ': all PCS values use PCSXYZ encoding
  - IF profile declares PCS = 'Lab ': all PCS values use PCSLAB encoding
  - Action: WARN if AToB/BToA tags appear to use different encodings

- [ ] **ICC-029** PCS illuminant is fixed D50:
  - Already checked in Phase 1 (ICC-010)
  - All color transformations use D50 reference

- [ ] **ICC-030** PCS value ranges are valid:
  - PCSXYZ: -127 to +127 (can be negative; clarified in ICC.1:2022)
  - PCSLAB: L*=0-100, a*=±127, b*=±127
  - Action: WARN if tags contain out-of-range values (likely corruption)

- [ ] **ICC-013** Multi-component color spaces (xCLR):
  - IF data color space is '2CLR' through 'FCLR': `colorantTableTag` MUST be present
  - Action: REJECT if required colorantTable missing

---

## Phase 6: PDF Context Checks

- [ ] **ICC-038** Profile class matches expected use:
  - PDF color space is RGB → expect 'mntr' or 'spac' profile (not 'prtr')
  - PDF color space is CMYK → expect 'prtr' profile
  - PDF color space is Gray → expect 'prtr' or monochrome 'mntr'
  - PDF color space is Lab → expect 'spac' profile
  - Action: WARN if unexpected class for image type

- [ ] **ICC-039** Profile data color space matches image:
  - Image bytes map to profile data color space
  - IF image is RGB bytes and profile data color space ≠ 'RGB ': WARN
  - IF image is CMYK bytes and profile data color space ≠ 'CMYK': WARN
  - Action: WARN if mismatch (can cause color mis-rendering)

- [ ] **ICC-038a** Embedded profile restrictions:
  - IF Device Class = 'link' or 'abst': WARN (these cannot be embedded per spec)
  - IF Profile flags bit 1 = 1 ("cannot be used independently"): WARN (dependent profile)

---

## Phase 7: Version and Compatibility

- [ ] **ICC-031** Version is compatible:
  - v4.4 (0x04400000) ✓ fully compatible
  - v4.3 (0x04300000) ✓ compatible
  - v4.2 (0x04200000) ✓ compatible
  - v4.0 (0x04000000) ✓ compatible
  - v2.x (0x02xxxxxx) ✓ compatible (older, but readable)
  - Other: WARN or REJECT depending on tolerance

- [ ] **ICC-031a** Major version mismatches:
  - v5.0+ would indicate unknown future format
  - Action: REJECT if major version > 4

---

## Phase 8: Summary Output

### REJECT Reasons (Profile Invalid)
- [ ] Profile size mismatch (ICC-001)
- [ ] Missing file signature (ICC-002)
- [ ] Invalid device class (ICC-004)
- [ ] Invalid data color space (ICC-005)
- [ ] Invalid PCS for profile class (ICC-006)
- [ ] Critical tag missing for profile class (ICC-015-023)
- [ ] Tag offset not 4-byte aligned (ICC-025c)
- [ ] Tag data overlap or gaps (ICC-026)
- [ ] Tag count zero (ICC-024a)
- [ ] Invalid major version (ICC-031a)

### WARN Reasons (Profile Questionable)
- [ ] Unknown version (ICC-003)
- [ ] PCS illuminant not D50 (ICC-010)
- [ ] Unknown platform (ICC-008)
- [ ] Invalid rendering intent (ICC-009)
- [ ] Reserved field non-zero (ICC-012)
- [ ] Unknown CMM/manufacturer/creator (ICC-048-050)
- [ ] Multi-component color space without colorantTable (ICC-013)
- [ ] Class mismatch for PDF context (ICC-038)
- [ ] Data color space mismatch with image (ICC-039)
- [ ] DeviceLink or Abstract profile embedded (ICC-038a)

### ACCEPT Reasons
- [ ] All critical checks pass
- [ ] All required tags present for profile class
- [ ] No structural corruption detected
- [ ] Version is 4.2, 4.3, or 4.4 (or 2.x with tolerance)

---

## Implementation Notes

### Tag Signature Format
- All 4-byte signatures are ASCII characters padded to 4 bytes (e.g., 'desc' = 0x64657363)
- Some signatures have trailing spaces: 'XYZ ' = 0x58595A20

### Data Types Commonly Used
- **uInt32Number:** 4-byte unsigned integer (big-endian)
- **s15Fixed16Number:** 16.16 fixed-point signed (for XYZ tristimulus)
- **dateTimeNumber:** 12 bytes (year, month, day, hour, minute, second as uInt16s)
- **Signature:** 4-byte ASCII string

### Common Tag Signatures (Hex)
| Tag Name | Signature | Hex |
|---|---|---|
| Profile Description | 'desc' | 64657363h |
| Copyright | 'cprt' | 63707274h |
| Device to PCS (intent 0) | 'A2B0' | 41324230h |
| Device to PCS (intent 1) | 'A2B1' | 41324231h |
| Device to PCS (intent 2) | 'A2B2' | 41324232h |
| PCS to Device (intent 0) | 'B2A0' | 42324130h |
| PCS to Device (intent 1) | 'B2A1' | 42324131h |
| PCS to Device (intent 2) | 'B2A2' | 42324132h |
| Gamut | 'gamt' | 67616D74h |
| Media White Point | 'wtpt' | 77747074h |
| Chromatic Adaptation | 'chad' | 63686164h |
| Colorant Table | 'clrt' | 636C7274h |
| Gray TRC | 'kTRC' | 6B545243h |
| Red TRC | 'rTRC' | 72545243h |
| Green TRC | 'gTRC' | 67545243h |
| Blue TRC | 'bTRC' | 62545243h |
| Profile Sequence Desc | 'pseq' | 70736571h |

---

**Revision:** 1.0
**Date:** 2026-03-11
**Reference:** ICC.1:2022 specification (126 pages)
