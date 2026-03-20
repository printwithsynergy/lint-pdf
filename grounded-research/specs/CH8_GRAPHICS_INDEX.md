# ISO 32000-2:2020 Chapter 8: Graphics - Complete Index

## Quick Reference

**File**: `iso32000-2-ch8-graphics.md`
**Size**: 390 KB (6,652 lines, 394,016 characters)
**Pages Extracted**: 160-307 (148 pages from the PDF)

---

## Document Structure

### 8.1 General
- Six main groups of graphics operators
- Graphics objects and their painting behavior
- Opaque vs. transparent imaging models

### 8.2 Graphics Objects
- Types: Path, Text, External Objects (XObjects), Inline images, Shadings
- Operator sequencing and postfix notation
- Graphics object nesting rules

### 8.3 Coordinate Systems
- **8.3.1** Introduction
- **8.3.2** User space vs. Device space
- **8.3.3** Transformation matrices
- **8.3.4** Common transformations

---

## 8.4 Graphics State (Complete)

### Graphics State Parameters (Two Tables)

#### **Table 51 — Device-Independent Parameters**
Essential parameters:
- CTM (Current Transformation Matrix)
- Clipping path
- Color space (stroking & non-stroking)
- Color value (stroking & non-stroking)
- Text state
- Line width
- Line cap style (0, 1, 2)
- Line join style (0, 1, 2)
- Miter limit
- Dash pattern
- Rendering intent
- Stroke adjustment
- Blend mode
- Shape
- Opacity (stroking & non-stroking)
- Text knockout
- Overprint

#### **Table 52 — Device-Dependent Parameters**
Device-specific parameters:
- **Overprint** (OP): boolean flag for color erasing
- **Overprint Mode (OPM)**: 0 (default) vs. 1 (non-zero overprint)
- Black generation (RGB to CMYK)
- Undercolor removal
- Transfer function (deprecated in PDF 2.0)
- Halftone dictionary/stream
- Flatness tolerance
- Smoothness tolerance

### Graphics State Operators

#### **Table 56 — All Graphics State Operators**

| Operator | Operation |
|----------|-----------|
| **q** | Save graphics state (push stack) |
| **Q** | Restore graphics state (pop stack) |
| **cm** | Coordinate transformation matrix |
| **w** | Set line width |
| **J** | Set line cap style |
| **j** | Set line join style |
| **M** | Set miter limit |
| **d** | Set dash pattern |
| **ri** | Set rendering intent |
| **i** | Set flatness tolerance |
| **gs** | Set graphics state dictionary |

All with complete operand specifications included.

---

## 8.5 Path Construction and Painting

### Path Construction Operators
- **m** (moveto), **l** (lineto), **c** (curveto)
- **v**, **y** (Bézier curve variants)
- **h** (closepath)
- **re** (rectangle)

### Path-Painting Operators

#### **Table 59 — Path-Painting Operators**

| Operator | Operation |
|----------|-----------|
| **S** | Stroke path (unfilled) |
| **s** | Close and stroke |
| **f** | Fill path (non-zero winding) |
| **F** | Fill path (variant) |
| **f*** | Fill path (even-odd) |
| **B** | Fill and stroke (non-zero) |
| **B*** | Fill and stroke (even-odd) |
| **b** | Close, fill, and stroke (non-zero) |
| **b*** | Close, fill, and stroke (even-odd) |
| **n** | End path without painting |

### Clipping Path Operators
- **W** (non-zero winding rule)
- **W*** (even-odd rule)

---

## 8.6 Colour Spaces (COMPLETE)

### Overview
- Three colour space families: Device, CIE-based, Special
- Each has specific use cases and rendering behavior

### 8.6.4 Device Colour Spaces

#### **DeviceGray** (8.6.4.2)
- Single component: intensity [0.0, 1.0]
- Black to white
- Default color space

#### **DeviceRGB** (8.6.4.3)
- Three components: R, G, B [0.0, 1.0]
- Additive primaries
- Primary colour space for displays

#### **DeviceCMYK** (8.6.4.4)
- Four components: C, M, Y, K [0.0, 1.0]
- Subtractive primaries
- Primary colour space for printing
- Interacts with overprint mode

### 8.6.5 CIE-Based Colour Spaces

#### **CalGray** (8.6.5.2)
- Single-component CIE color space
- Calibrated gray reference
- Uses D50 illuminant

#### **CalRGB** (8.6.5.3)
- Three-component CIE color space
- Calibrated reference white
- Gamma correction support

#### **Lab** (8.6.5.4)
- Perceptually uniform CIE color space
- L* (lightness), a*, b* (color dimensions)
- Device-independent representation

#### **ICCBased** (8.6.5.5)
- ICC color profile-based space
- Supports any input color space
- Mapping to device-independent color

### 8.6.6 Special Colour Spaces

#### **Indexed** (8.6.6.2)
- Lookup table color space
- Reduces file size for limited palettes
- Maps color indices to values

#### **Pattern** (8.6.6.3)
- Repeating graphic pattern as color
- Tiling patterns and shading patterns
- Used as paint color, not separate object

#### **Separation** (8.6.6.4)
- Single ink/colorant space
- Explicit device separations
- Alternative color
- Tint transformation function

#### **DeviceN** (8.6.6.5)
- Multiple device separations (2+)
- General ink model
- Process and spot colors
- Colorants array
- Tint transformation function

### 8.6.7 Overprint Control (CRITICAL)

**Overprint Parameter (OP)**:
- **false** (default): Unspecified colourants erased (normal painting)
- **true**: Unspecified colourants left unchanged (overprint)

**Overprint Mode (OPM)** (PDF 1.3+):
- Only affects DeviceCMYK when overprinting enabled
- **OPM = 0** (default): Source components replace previous (standard)
- **OPM = 1**: Zero source components leave previous unchanged (non-zero overprint)

Device-dependent behavior; not all devices support overprinting.

---

## 8.7 Patterns

### Pattern Types
- Tiling patterns: Regular repeating graphic
- Shading patterns: Geometric color gradients
- Pattern colour spaces: Use patterns as paint colors

---

## 8.8 Shadings

### Shading Types
- Type 1: Function-based shading
- Type 2: Axial shading (gradient)
- Type 3: Radial shading (circular gradient)
- Type 4-7: Free-form and lattice shadings

---

## 8.9 Images (COMPLETE)

### Image Types
- Sampled images: Rectangular arrays of color samples
- Inline images: Small images within content stream

### Image Dictionary (8.9.3)

#### **Table 87 — Image Dictionary Entries**

**Required entries:**
- **Type**: /XObject
- **Subtype**: /Image
- **Width**: integer (samples per row)
- **Height**: integer (rows)
- **ColorSpace**: name or array

**Content description:**
- **BitsPerComponent**: 1, 2, 4, 8, or 16
- **Intent**: Rendering intent
- **ImageMask**: boolean (mask vs. color image)
- **Decode**: [min max] array pairs per component
- **DecodeParms**: Filter parameters

**Image processing:**
- **Interpolate**: boolean (smooth vs. blocky)
- **Name**: name (XObject name in resource)
- **SMask**: Soft mask (transparency)
- **SMaskInData**: Mask data in content stream
- **Alternates**: Alternate image versions

**Color-related:**
- **Intent**: Rendering intent specification

### Inline Images (8.9.7)

#### **Table 90 — Inline Image Operators**

| Operator | Purpose |
|----------|---------|
| **BI** | Begin inline image (start marker) |
| **ID** | Image data (data stream delimiter) |
| **EI** | End image (terminator) |

**Inline image dictionary**: Subset of image dictionary entries
- Abbreviations supported: W (Width), H (Height), CS (ColorSpace), BPC (BitsPerComponent)
- Data between ID and EI: Raw binary image data
- Restrictions: No nesting; limited image size; no DCTDecode or JPXDecode

---

## 8.10 Form XObjects

### Form XObject Structure
- Type: /XObject, Subtype: /Form
- Self-contained content stream
- Treatable as single graphics object
- Provides encapsulation and reusability

### Form Types
- Type 1: Standard form XObject (PDF 1.1+)

### Special Form Types
- Reference XObjects: Import content from other PDFs
- Group XObjects: Transparency groups for composite effects

---

## 8.11 Optional Content

### Optional Content Groups (OCGs)
- Layer-like functionality
- Visibility control
- Print/Export specific behavior
- Configuration dictionaries

---

## Critical Information Summary

### For Preflight Analyzers

1. **Graphics State Validation**
   - Reference Table 51 & 52 for all parameters
   - Verify graphics state stack operations
   - Check rendering intent and overprint settings

2. **Color Space Interpretation**
   - Identify all 10 color space types
   - Validate color component counts
   - Check overprint mode (OPM 0 vs 1) for CMYK
   - Verify ICC profile presence for ICCBased

3. **Operator Validation**
   - Use Table 50 for operator categorization
   - Table 56 for graphics state operators
   - Table 59 for path-painting operators
   - Table 90 for inline image operators

4. **Image/XObject Analysis**
   - Table 87 for complete image dictionary specification
   - Validate image data encoding (Filter parameter)
   - Check interpolation settings
   - Verify soft mask (SMask) presence

5. **Path and Clipping**
   - Validate path operator sequences
   - Check clipping path definitions
   - Verify coordinate transformations

---

## Table Reference Quick Access

| Table | Subject | Key Content |
|-------|---------|------------|
| 50 | Operator categories | Classification of 73+ PDF operators |
| 51 | Device-independent parameters | CTM, clipping, color, text state, etc. |
| 52 | Device-dependent parameters | Overprint, OPM, halftone, transfer, etc. |
| 56 | Graphics state operators | q, Q, cm, w, J, j, M, d, ri, i, gs |
| 59 | Path-painting operators | S, s, f, F, f*, B, B*, b, b*, n |
| 87 | Image dictionary entries | Type, Width, Height, BitsPerComponent, Decode, etc. |
| 90 | Inline image operators | BI, ID, EI |

---

## Operator Quick Reference

### Graphics State (Table 56)
```
q           — Save state (push)
Q           — Restore state (pop)
cm a b c d e f — Transform matrix [a b c d e f]
w n         — Line width (n units)
J n         — Line cap (0=butt, 1=round, 2=projecting)
j n         — Line join (0=miter, 1=round, 2=bevel)
M n         — Miter limit
d array n   — Dash pattern [array] phase n
ri name     — Rendering intent
i n         — Flatness tolerance
gs name     — Set graphics state dictionary
```

### Path Painting (Table 59)
```
S           — Stroke path (no fill)
s           — Close and stroke
f           — Fill (non-zero rule)
F           — Fill (variant)
f*          — Fill (even-odd rule)
B           — Fill and stroke (non-zero)
B*          — Fill and stroke (even-odd)
b           — Close, fill, and stroke (non-zero)
b*          — Close, fill, and stroke (even-odd)
n           — End path (no-op)
```

### Inline Images (Table 90)
```
BI          — Begin inline image
ID          — Image data (binary stream follows)
EI          — End inline image
```

---

## Notes

- All page numbers in the extracted file reference original PDF pages (160-307)
- Examples and code snippets preserved for operator usage
- Device-dependent behavior noted for output device considerations
- Deprecated features (PDF 1.x) marked with version numbers

