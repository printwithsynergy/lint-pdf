# ICC.1:2022 Tag Signature Reference

**Purpose:** Complete reference of all ICC.1:2022 tag signatures, hex codes, and basic validation info.

**Source:** ICC.1:2022 Specification, Clause 9 (Tag Definitions)

---

## All Registered ICC.1:2022 Tags (Alphabetical)

### Core Transformation Tags

| Tag Name | Signature | Hex Code | Permitted Types | Purpose | Class Required |
|---|---|---|---|---|---|
| **AToB0Tag** | 'A2B0' | 41324230h | lut8, lut16, lutAtoB | Device/Encoding → PCS (intent 0: perceptual) | Input, Display, Output, ColorSpace, Abstract (for Abstract: PCS→PCS) |
| **AToB1Tag** | 'A2B1' | 41324231h | lut8, lut16, lutAtoB | Device/Encoding → PCS (intent 1: colorimetric) | Output, (opt Input, Display, ColorSpace) |
| **AToB2Tag** | 'A2B2' | 41324232h | lut8, lut16, lutAtoB | Device/Encoding → PCS (intent 2: saturation) | Output, (opt Input, Display, ColorSpace) |
| **BToA0Tag** | 'B2A0' | 42324130h | lut8, lut16, lutBtoA | PCS → Device/Encoding (intent 0: perceptual) | Input (opt), Display (opt), Output, ColorSpace |
| **BToA1Tag** | 'B2A1' | 42324131h | lut8, lut16, lutBtoA | PCS → Device/Encoding (intent 1: colorimetric) | Output, (opt Input, Display, ColorSpace) |
| **BToA2Tag** | 'B2A2' | 42324132h | lut8, lut16, lutBtoA | PCS → Device/Encoding (intent 2: saturation) | Output, (opt Input, Display, ColorSpace) |
| **BToD0Tag** | 'B2D0' | 42324430h | multiProcessElements | PCS → Device (float32, intent 0) | Optional all |
| **BToD1Tag** | 'B2D1' | 42324431h | multiProcessElements | PCS → Device (float32, intent 1) | Optional all |
| **BToD2Tag** | 'B2D2' | 42324432h | multiProcessElements | PCS → Device (float32, intent 2) | Optional all |
| **BToD3Tag** | 'B2D3' | 42324433h | multiProcessElements | PCS → Device (float32, intent 3: absolute) | Optional all |
| **DToB0Tag** | 'D2B0' | 44324230h | multiProcessElements | Device → PCS (float32, intent 0) | Optional all |
| **DToB1Tag** | 'D2B1' | 44324231h | multiProcessElements | Device → PCS (float32, intent 1) | Optional all |
| **DToB2Tag** | 'D2B2' | 44324232h | multiProcessElements | Device → PCS (float32, intent 2) | Optional all |
| **DToB3Tag** | 'D2B3' | 44324233h | multiProcessElements | Device → PCS (float32, intent 3: absolute) | Optional all |

### Matrix/TRC Tags (Traditional RGB)

| Tag Name | Signature | Hex Code | Permitted Types | Purpose | Class Required |
|---|---|---|---|---|---|
| **redMatrixColumnTag** | 'rXYZ' | 7258595Ah | XYZ | Red matrix column (XYZ tristimulus) | Input (matrix), Display (matrix) |
| **greenMatrixColumnTag** | 'gXYZ' | 6758595Ah | XYZ | Green matrix column (XYZ tristimulus) | Input (matrix), Display (matrix) |
| **blueMatrixColumnTag** | 'bXYZ' | 6258595Ah | XYZ | Blue matrix column (XYZ tristimulus) | Input (matrix), Display (matrix) |
| **redTRCTag** | 'rTRC' | 72545243h | curve, parametricCurve | Red tone reproduction curve | Input (matrix, mono), Display (matrix, mono), Output (mono) |
| **greenTRCTag** | 'gTRC' | 67545243h | curve, parametricCurve | Green tone reproduction curve | Input (matrix), Display (matrix) |
| **blueTRCTag** | 'bTRC' | 62545243h | curve, parametricCurve | Blue tone reproduction curve | Input (matrix), Display (matrix) |
| **grayTRCTag** | 'kTRC' | 6B545243h | curve, parametricCurve | Gray/monochrome TRC | Input (mono), Display (mono), Output (mono) |

### Mandatory Metadata Tags

| Tag Name | Signature | Hex Code | Permitted Types | Purpose | Class Required |
|---|---|---|---|---|---|
| **profileDescriptionTag** | 'desc' | 64657363h | multiLocalizedUnicode | Profile name/description (localizable) | All except DeviceLink |
| **copyrightTag** | 'cprt' | 63707274h | multiLocalizedUnicode or text | Copyright notice | All except DeviceLink |
| **mediaWhitePointTag** | 'wtpt' | 77747074h | XYZ | Media white point (XYZ tristimulus) | All except DeviceLink |
| **chromaticAdaptationTag** | 'chad' | 63686164h | s15Fixed16Array | Chromatic adaptation matrix (3x3) | Conditional: if white point ≠ D50 |

### Device/ColorSpace Definition Tags

| Tag Name | Signature | Hex Code | Permitted Types | Purpose | Class Required |
|---|---|---|---|---|---|
| **colorantTableTag** | 'clrt' | 636C7274h | colorantTable | Colorant names/PCS values | Output (if xCLR), DeviceLink (if input xCLR) |
| **colorantTableOutTag** | 'clro' | 636C726Fh | colorantTable | Output colorant names/values | DeviceLink (if output xCLR) |
| **colorantOrderTag** | 'clro' | 636C726Fh | colorantOrder | Colorant laydown sequence | Optional |
| **chromaticityTag** | 'chro' | 6368726Fh | chromaticity | Phosphor/colorant chromaticity | Optional Input, Display |

### Viewing/Perception Tags

| Tag Name | Signature | Hex Code | Permitted Types | Purpose | Class Required |
|---|---|---|---|---|---|
| **viewingConditionsTag** | 'view' | 76696577h | viewingConditions | PCS viewing condition parameters | Optional |
| **viewingCondDescTag** | 'vued' | 76756564h | multiLocalizedUnicode | Viewing condition description | Optional |
| **luminanceTag** | 'lumi' | 6C756D69h | XYZ | Absolute luminance (emissive devices) | Optional Display, Output |

### Measurement and Calibration Tags

| Tag Name | Signature | Hex Code | Permitted Types | Purpose | Class Required |
|---|---|---|---|---|---|
| **measurementTag** | 'meas' | 6D656173h | measurement | Measurement condition specification | Optional |
| **calibrationDateTimeTag** | 'calt' | 63616C74h | dateTime | Last calibration date/time | Optional |
| **charTargetTag** | 'targ' | 74617267h | text | Characterization target (IT8, etc.) | Optional |
| **technologyTag** | 'tech' | 74656368h | signature | Device technology (LCD, CRT, etc.) | Optional |

### Gamut and Quality Tags

| Tag Name | Signature | Hex Code | Permitted Types | Purpose | Class Required |
|---|---|---|---|---|---|
| **gamutTag** | 'gamt' | 67616D74h | lut8 or lut16 | Out-of-gamut indicator/mapping | Output (required), Input/Display/ColorSpace (optional) |
| **perceptualRenderingIntentGamutTag** | 'prig' | 70726967h | signature | Reference gamut for intent 0 (perceptual) | Optional |
| **saturationRenderingIntentGamutTag** | 'srig' | 73726967h | signature | Reference gamut for intent 2 (saturation) | Optional |

### Profile Sequence and Metadata Tags

| Tag Name | Signature | Hex Code | Permitted Types | Purpose | Class Required |
|---|---|---|---|---|---|
| **profileSequenceDescTag** | 'pseq' | 70736571h | profileSequenceDesc | Sequence of profiles (for DeviceLink) | DeviceLink (required) |
| **profileSequenceIdentifierTag** | 'psid' | 70736964h | profileSequenceIdentifier | Alternative sequence identification | Optional |
| **namedColor2Tag** | 'nc2 ' | 6E633220h | namedColor2 | Named color list with PCS + device values | NamedColor (required) |
| **metadataTag** | 'meta' | 6D657461h | dict | Flexible metadata (key-value pairs) | Optional (new in v4.4) |
| **cicpTag** | 'cicp' | 63696370h | cicp | HDR metadata (color primaries, transfer, matrix, range) | Optional (new in v4.4) |

### Display/Output-Specific Tags

| Tag Name | Signature | Hex Code | Permitted Types | Purpose | Class Required |
|---|---|---|---|---|---|
| **outputResponseTag** | 'resp' | 72657370h | responseCurveSet16 or curve | Device output response (patent-encumbered) | Optional Output |
| **preview0Tag** | 'pre0' | 70726530h | lut8 or lut16 | Preview render (intent 0) | Optional |
| **preview1Tag** | 'pre1' | 70726531h | lut8 or lut16 | Preview render (intent 1) | Optional |
| **preview2Tag** | 'pre2' | 70726532h | lut8 or lut16 | Preview render (intent 2) | Optional |

### Device Description Tags

| Tag Name | Signature | Hex Code | Permitted Types | Purpose | Class Required |
|---|---|---|---|---|---|
| **deviceMfgDescTag** | 'dmnd' | 646D6E64h | multiLocalizedUnicode | Device manufacturer description (human-readable) | Optional |
| **deviceModelDescTag** | 'dmdd' | 646D6464h | multiLocalizedUnicode | Device model description (human-readable) | Optional |

### Intent/Image State Tags

| Tag Name | Signature | Hex Code | Permitted Types | Purpose | Class Required |
|---|---|---|---|---|---|
| **colorimetricIntentImageStateTag** | 'ciis' | 63696973h | signature | Image state for colorimetric transforms (picture-referred vs scene-referred) | Optional |

---

## Quick Tag Lookup by Purpose

### Most Critical Tags (for Preflight)
1. **profileDescriptionTag** ('desc') - Profile identity
2. **AToB0Tag** ('A2B0') - Core device→PCS transformation
3. **BToA0Tag** ('B2A0') - Core PCS→device transformation
4. **mediaWhitePointTag** ('wtpt') - White point reference
5. **copyrightTag** ('cprt') - Legal metadata
6. **gamutTag** ('gamt') - Gamut warning (print)

### Most Common Tags in PDFs
- 'A2B0' (AToB0Tag) - Device → PCS
- 'B2A0' (BToA0Tag) - PCS → Device
- 'desc' (profileDescriptionTag) - Name
- 'cprt' (copyrightTag) - Copyright
- 'wtpt' (mediaWhitePointTag) - White point
- 'gamt' (gamutTag) - Gamut (in output profiles)

### Tags by Profile Class

#### Input Profile Tags
| Mandatory | Optional |
|---|---|
| desc, cprt, wtpt, A2B0, chad (if non-D50) | A2B1, A2B2, B2A0, B2A1, B2A2, D2B*, B2D*, gamt |

#### Display Profile Tags
| Mandatory | Optional |
|---|---|
| desc, cprt, wtpt, A2B0, B2A0, chad (if non-D50) | A2B1, A2B2, B2A1, B2A2, D2B*, B2D*, gamt |

#### Output Profile Tags (Most Complete)
| Mandatory | Optional |
|---|---|
| desc, cprt, wtpt, A2B0, A2B1, A2B2, B2A0, B2A1, B2A2, gamt, clrt (if xCLR), chad (if non-D50) | D2B*, B2D*, resp, pre* |

#### DeviceLink Tags
| Mandatory | Optional |
|---|---|
| desc, cprt, pseq, A2B0, clrt (if input xCLR), clro (if output xCLR) | D2B0 |

#### ColorSpace Tags
| Mandatory | Optional |
|---|---|
| desc, cprt, wtpt, A2B0, B2A0, chad (if non-D50) | A2B1, A2B2, B2A1, B2A2, D2B*, B2D*, gamt |

#### Abstract Tags
| Mandatory | Optional |
|---|---|
| desc, cprt, wtpt, A2B0, chad (if non-D50) | D2B0 |

#### NamedColor Tags
| Mandatory | Optional |
|---|---|
| desc, cprt, wtpt, nc2, chad (if non-D50) | |

---

## Hex Lookup (by Hex Code)

| Hex Code | Signature | Tag Name |
|---|---|---|
| 41324230h | 'A2B0' | AToB0Tag |
| 41324231h | 'A2B1' | AToB1Tag |
| 41324232h | 'A2B2' | AToB2Tag |
| 42324130h | 'B2A0' | BToA0Tag |
| 42324131h | 'B2A1' | BToA1Tag |
| 42324132h | 'B2A2' | BToA2Tag |
| 42324430h | 'B2D0' | BToD0Tag |
| 42324431h | 'B2D1' | BToD1Tag |
| 42324432h | 'B2D2' | BToD2Tag |
| 42324433h | 'B2D3' | BToD3Tag |
| 44324230h | 'D2B0' | DToB0Tag |
| 44324231h | 'D2B1' | DToB1Tag |
| 44324232h | 'D2B2' | DToB2Tag |
| 44324233h | 'D2B3' | DToB3Tag |
| 62545243h | 'bTRC' | blueTRCTag |
| 6258595Ah | 'bXYZ' | blueMatrixColumnTag |
| 63616C74h | 'calt' | calibrationDateTimeTag |
| 63686164h | 'chad' | chromaticAdaptationTag |
| 636869624Ah | 'chicp' | cicpTag (may appear as alternate) |
| 63696370h | 'cicp' | cicpTag |
| 636C726Fh | 'clro' | colorantOrderTag / colorantTableOutTag |
| 636C7274h | 'clrt' | colorantTableTag |
| 63707274h | 'cprt' | copyrightTag |
| 64657363h | 'desc' | profileDescriptionTag |
| 646D6464h | 'dmdd' | deviceModelDescTag |
| 646D6E64h | 'dmnd' | deviceMfgDescTag |
| 67545243h | 'gTRC' | greenTRCTag |
| 67616D74h | 'gamt' | gamutTag |
| 6758595Ah | 'gXYZ' | greenMatrixColumnTag |
| 6B545243h | 'kTRC' | grayTRCTag |
| 6C756D69h | 'lumi' | luminanceTag |
| 6D656173h | 'meas' | measurementTag |
| 6D657461h | 'meta' | metadataTag |
| 6E633220h | 'nc2 ' | namedColor2Tag |
| 70726530h | 'pre0' | preview0Tag |
| 70726531h | 'pre1' | preview1Tag |
| 70726532h | 'pre2' | preview2Tag |
| 70726967h | 'prig' | perceptualRenderingIntentGamutTag |
| 70736571h | 'pseq' | profileSequenceDescTag |
| 70736964h | 'psid' | profileSequenceIdentifierTag |
| 72545243h | 'rTRC' | redTRCTag |
| 7258595Ah | 'rXYZ' | redMatrixColumnTag |
| 72657370h | 'resp' | outputResponseTag |
| 73726967h | 'srig' | saturationRenderingIntentGamutTag |
| 74617267h | 'targ' | charTargetTag |
| 74656368h | 'tech' | technologyTag |
| 76696577h | 'view' | viewingConditionsTag |
| 76756564h | 'vued' | viewingCondDescTag |
| 77747074h | 'wtpt' | mediaWhitePointTag |

---

## Tag Type Reference

### Common Tag Data Types

| Type Name | Purpose | Example |
|---|---|---|
| **XYZType** | Tristimulus values (color) | Media white point, matrix columns |
| **curveType** | TRC or response curve | Red/Green/Blue/Gray TRC |
| **parametricCurveType** | Mathematical curve definition | Alternative TRC |
| **lut8Type** | 8-bit LUT transformation | A2B0, B2A0 (lower precision) |
| **lut16Type** | 16-bit LUT transformation | A2B0, B2A0 (standard precision) |
| **lutAToBType** | Advanced A→B LUT with matrices | A2B0, A2B1, A2B2 (flexible) |
| **lutBToAType** | Advanced B→A LUT with matrices | B2A0, B2A1, B2A2 (flexible) |
| **multiProcessElementsType** | Chained processing elements (float32) | D2B*, B2D* (highest precision) |
| **multiLocalizedUnicodeType** | Localizable text (multiple languages) | profileDescriptionTag |
| **textType** | Simple ASCII text | charTargetTag |
| **dateTimeType** | Date and time stamp | calibrationDateTimeTag |
| **namedColor2Type** | Named color definitions | namedColor2Tag |
| **profileSequenceDescType** | Profile sequence info | profileSequenceDescTag |
| **colorantTableType** | Colorant names and PCS values | colorantTableTag |
| **measurementType** | Measurement conditions | measurementTag |
| **viewingConditionsType** | Viewing environment parameters | viewingConditionsTag |
| **dictType** | Key-value dictionary (metadata) | metadataTag |
| **cicpType** | HDR/color signal metadata | cicpTag |

---

## Private Tag Guidelines

### Registering Private Tags

For vendor-specific/proprietary tags:
1. Register tag signature with ICC
2. Register tag type signature with ICC
3. Use 4-byte ASCII signature (e.g., 'xyz1', 'abc_')
4. Include in tag table like any standard tag
5. CMMs ignoring unregistered signatures will skip tag
6. Unknown tags should not break profile functionality

---

**Reference Date:** March 11, 2026
**Specification:** ICC.1:2022 (Profile version 4.4.0.0)
**Applicable versions:** Also compatible with ICC.1:2010 (v4.3) and ICC.1:2004 (v4.2)
