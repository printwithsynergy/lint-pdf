# 03: Content Streams & Graphics State

**Research Deliverable** — Grounded Preflight Engine | Based on ISO 32000-2:2020 Chapter 8

---

## Content Streams Overview (§8.2, §7.8.2)

Per §7.8.2, a content stream contains a sequence of operators and operands describing the appearance of a page or graphical entity.

**Structure:**
- Text-based syntax: operands followed by operator name
- Postfix notation (RPN): operands on stack, operator pops and executes
- Static description (not a program): operators in fixed order

**Content Stream Sources (§7.8.1):**
- Page /Contents entry: stream or array of streams
- Form XObject /Contents entry: stream with Resource dictionary
- Annotation appearance stream (/AP)
- Type 3 font glyph descriptions

**Preflight Checks:**
- Verify Contents is stream or array of streams
- Decompress stream(s) using Filter entry
- Validate operator syntax (operator names must be ASCII)
- Check matching BT/ET (text object begin/end)

---

## Graphics State (§8.4)

**Purpose (§8.4):**
Global framework containing parameters that are implicit operands for painting operators. CTM (Current Transformation Matrix) is element of graphics state.

**Graphics State Stack (§8.4.2):**
- `q` operator: save graphics state on stack
- `Q` operator: restore most recent saved state
- Maximum depth and implementation-specific limits

**Operators (Table 56, §8.4.4):**

| Operator | Operands | Description |
|----------|----------|-------------|
| `q` | — | Save graphics state on stack (§8.4.2) |
| `Q` | — | Restore graphics state from stack |
| `cm` | a b c d e f | Concatenate CTM with matrix [a b c d e f] (§8.3.4) |
| `w` | linewidth | Set line width in user space units |
| `J` | linecap | Set line cap style: 0=butt, 1=round, 2=square |
| `j` | linejoin | Set line join style: 0=miter, 1=round, 2=bevel |
| `M` | miterlimit | Set miter limit (ratio of miter length to line width) |
| `d` | dasharray dashphase | Set line dash pattern [array] phase |
| `ri` | intent | Set rendering intent (name) |
| `i` | flatness | Set flatness tolerance |
| `gs` | dictname | Set graphics state parameter dictionary (ExtGState) |

**Preflight Checks:**
- Track q/Q stack depth (q pushes, Q pops)
- Validate line width ≥ 0
- Validate line cap in [0, 1, 2]
- Validate line join in [0, 1, 2]
- Validate miter limit ≥ 1.0
- Verify gs operator references valid ExtGState in Resources

---

## Current Transformation Matrix (CTM, §8.3.3–8.3.4)

**Purpose:**
Maps user space coordinates to device space. Initially identity matrix.

**Matrix Format:**
[a b c d e f] represents:
```
| a  b  0 |
| c  d  0 |
| e  f  1 |
```

**Accumulation (§8.3.3):**
`cm` operator concatenates: `CTM_new = Tmatrix × CTM_old`

Where Tmatrix is [a b c d e f] operands.

Mathematically:
```
| a b 0 |   | a' b' 0 |   | aa'+bc'  ab'+bd'  0 |
| c d 0 | × | c' d' 0 | = | ca'+dc'  cb'+dd'  0 |
| e f 1 |   | e' f' 1 |   | e+e'     f+f'     1 |
```

**Key Properties:**
- Scaling: `[sx 0 0 sy 0 0]`
- Rotation: `[cos θ sin θ -sin θ cos θ 0 0]`
- Translation: `[1 0 0 1 tx ty]`
- Skewing: `[1 tan α 0 1 0 0]`

**Preflight Checks:**
- Track CTM state through q/Q operations
- Detect singular matrices (determinant = ad - bc = 0) → infinite scaling
- Detect excessive scaling (very large or very small coefficients)
- Calculate effective page scale for image DPI calculation (see file 06)

---

## Path Construction Operators (§8.5.2, Table 58)

| Operator | Operands | Description |
|----------|----------|-------------|
| `m` | x y | Move to (x, y); start new subpath |
| `l` | x y | Line to (x, y) |
| `c` | x1 y1 x2 y2 x3 y3 | Cubic Bézier curve with 2 control points + endpoint |
| `v` | x2 y2 x3 y3 | Cubic Bézier with first control point = current point |
| `y` | x1 y1 x3 y3 | Cubic Bézier with second control point = endpoint |
| `h` | — | Close subpath (straight line to start) |
| `re` | x y w h | Append rectangle [x, y, width, height] |

**Path Object Rules (§8.5.1):**
- Path begins with `m` (move-to)
- Consists of subpaths (segments between moves)
- Ends with path-painting operator: `S`, `s`, `f`, `F`, `f*`, `B`, `B*`, `b`, `b*`, `n`
- May be preceded by clipping operators `W` or `W*`

**Preflight Checks:**
- All paths properly terminated
- No orphaned path construction operators (without painting)
- BezierCurves have valid control points

---

## Path-Painting Operators (§8.5.3, Table 59)

| Operator | Operands | Description |
|----------|----------|-------------|
| `S` | — | Stroke path with current line width, color, dash pattern |
| `s` | — | Close and stroke path |
| `f` | — | Fill path using nonzero winding rule |
| `F` | — | Equivalent to `f` (deprecated) |
| `f*` | — | Fill path using even-odd rule |
| `B` | — | Fill then stroke path (nonzero winding) |
| `B*` | — | Fill then stroke path (even-odd winding) |
| `b` | — | Close, fill, then stroke path (nonzero) |
| `b*` | — | Close, fill, then stroke path (even-odd) |
| `n` | — | End path (no-op; used to define clipping paths) |

**Stroking Parameters (§8.5.3.2, Table 56):**
- Line width: `w` operator
- Line cap: `J` operator (butt, round, square)
- Line join: `j` operator (miter, round, bevel)
- Miter limit: `M` operator (§8.4.3.5)
- Dash pattern: `d` operator (array of on/off lengths + phase)

**Clipping Paths (§8.5.4, Table 60):**

| Operator | Rule | Description |
|----------|------|-------------|
| `W` | nonzero | Set clipping path to current path (nonzero winding) |
| `W*` | even-odd | Set clipping path to current path (even-odd winding) |

Must precede path-painting operator. Only one clipping path active (new W/W* replaces previous).

**Preflight Checks:**
- Verify fill color set before fill operators
- Verify stroke color set before stroke operators
- Check line width ≥ 0
- Clipping paths properly defined before use

---

## Text Objects (§8.2, Table 105–107)

**Text Object Delimiters:**
- `BT`: Begin text object
- `ET`: End text object

**Text State Operators (Table 103, §9.3):**

| Operator | Operands | Purpose |
|----------|----------|---------|
| `Tc` | charspace | Character spacing |
| `Tw` | wordspace | Word spacing |
| `Tz` | scale | Horizontal scaling (100 = normal) |
| `TL` | leading | Text leading (line spacing) |
| `Tf` | font size | Set font + size |
| `Tr` | mode | Text rendering mode (0–7) |
| `Ts` | rise | Text rise (superscript/subscript) |

**Text Positioning (Table 106):**

| Operator | Operands | Description |
|----------|----------|-------------|
| `Td` | tx ty | Text matrix: translate by (tx, ty) |
| `TD` | tx ty | Text matrix: translate, set leading = -ty |
| `Tm` | a b c d e f | Set text matrix = [a b c d e f] |
| `T*` | — | Move to start of next line (Td with x=0, y=-TL) |

**Text Showing (Table 107, §9.4):**

| Operator | Operands | Description |
|----------|----------|-------------|
| `Tj` | string | Show string using current font + state |
| `TJ` | array | Show strings with positioning adjustments in array |
| `'` | string | Move to next line, show string |
| `"` | wx wy string | Set spacing, move to next line, show string |

**Preflight Checks (§9.3):**
- Font must be set before showing text (Tf operator)
- Valid text rendering mode: 0–7
- Text scaling within reasonable range (not 0, not excessive)
- Valid character/word spacing
- BT/ET matched

---

## Inline Images (§8.9.7, Table 104–105)

**Syntax:**
```
BI ... ID image_data EI
```

Where:
- `BI`: Begin inline image
- Dictionary entries (image parameters)
- `ID`: Image data delimiter
- image_data: raw binary image pixels
- `EI`: End inline image

**Dictionary Keys:**
- `W`: width in pixels
- `H`: height in pixels
- `CS`: color space name
- `BPC`: bits per component (1, 2, 4, 8, 16)
- `F`: filter (optional, filter name)
- `IM`: intent (optional)
- `I`: intent (short form of Intent)
- `IM`: intent (short form)
- `Decode`: decode array
- `DP`: decode parameters

**Preflight Checks:**
- W, H valid positive integers
- BPC valid: 1, 2, 4, 8, or 16
- CS valid color space name
- Image data size matches W × H × BPC ÷ 8 (bytes)
- ID followed by newline/whitespace before image data
- EI properly terminated

---

## Form XObjects (§8.10, Table 96)

**Purpose:**
Self-contained content stream with its own Resources dictionary. Can be invoked multiple times with `Do` operator.

**Dictionary Entries (Table 96, §8.10.2):**
- `Type`: XObject (required)
- `Subtype`: Form (required)
- `Contents`: stream containing content stream (required)
- `Resources`: resource dictionary (optional, inherited from page if absent)
- `BBox`: [llx lly urx ury] bounding box in form space (required)
- `Matrix`: transformation matrix [a b c d e f] (optional, default identity)
- `Group`: transparency group attributes (optional, PDF 1.4+)
- `Parent`: parent Form XObject (optional)
- `Metadata`: metadata stream (optional)

**Do Operator (Table 86, §8.2):**
```
/FormName Do
```
Invokes form XObject named FormName from current Resources /XObject dictionary.

**Preflight Checks:**
- Type = XObject, Subtype = Form
- Contents is stream
- BBox is array [x1 y1 x2 y2] with x1 < x2, y1 < y2
- Resources (if present) is valid resource dictionary
- Form content stream is valid

---

## Graphics State Parameter Dictionary (§8.4.5, Table 51–52)

Referenced via `gs` operator. Contains parameters not directly settable by operators.

**Common Entries:**
- `Type`: GS (optional)
- `LW`: line width
- `LC`: line cap
- `LJ`: line join
- `ML`: miter limit
- `D`: dash pattern [array, phase]
- `RI`: rendering intent
- `OP` / `op`: overprint flags (stroking / non-stroking)
- `OPM`: overprint mode (0 or 1, §8.6.7)
- `Font`: [font_dict, size]
- `CA` / `ca`: alpha (stroking / non-stroking), 0.0–1.0
- `BM`: blend mode (16 blend modes, §11.3.5)
- `SMask`: soft mask dictionary
- `BG` / `BG2`: black generation functions
- `UCR` / `UCR2`: undercolor removal functions
- `TR` / `TR2`: transfer functions
- `HT`: halftone dictionary
- `FL`: flatness tolerance
- `SM`: smoothness tolerance
- `SA`: stroke adjustment (boolean)
- `AIS`: alpha is shape (boolean)
- `TK`: text knockout (boolean)

**Preflight Checks:**
- CA/ca in range [0.0, 1.0]
- OPM in [0, 1]
- BM is valid blend mode name
- Font entry (if present) is [font_ref, size]

---

## Operator Table Summary (Table 50, §8.2)

| Category | Operators | Section |
|----------|-----------|---------|
| General graphics state | w, J, j, M, d, ri, i, gs, q, Q | Table 56 |
| Special graphics state (CTM) | cm | Table 56 |
| Path construction | m, l, c, v, y, h, re | Table 58 |
| Path painting | S, s, f, F, f*, B, B*, b, b*, n | Table 59 |
| Clipping paths | W, W* | Table 60 |
| Text objects | BT, ET | Table 105 |
| Text state | Tc, Tw, Tz, TL, Tf, Tr, Ts | Table 103 |
| Text positioning | Td, TD, Tm, T* | Table 106 |
| Text showing | Tj, TJ, ', " | Table 107 |
| Type 3 fonts | d0, d1 | Table 111 |
| Color operators | CS, cs, SC, SCN, sc, scn, G, g, RG, rg, K, k | Table 73 |
| Shading | sh | Table 74 |
| Inline images | BI, ID, EI | Table 104–105 |
| XObject | Do | Table 86 |
| Marked content | BDC, BMC, EMC | Table 320 |

---

## Table References

| Table | Section | Content |
|-------|---------|---------|
| Table 50 | 8.2 | Operator categories |
| Table 51 | 8.4.5 | Graphics state parameter dictionary |
| Table 56 | 8.4.4 | Graphics state operators |
| Table 58 | 8.5.2 | Path construction operators |
| Table 59 | 8.5.3 | Path-painting operators |
| Table 60 | 8.5.4 | Clipping path operators |
| Table 73 | 8.6.8 | Color operators |
| Table 86 | 8.2 | Do operator |
| Table 96 | 8.10 | Form XObject entries |
| Table 103 | 9.3 | Text state operators |
| Table 104–105 | 8.9.7 | Inline image syntax |
| Table 105 | 8.2 | Text object operators |
| Table 106 | 9.4 | Text positioning operators |
| Table 107 | 9.4 | Text showing operators |

---

## Feed to AI

Use this research to design Grounded's **Content Stream & Graphics State Validator Module**:

1. **Operator Parser**: Tokenize content stream, recognize all operator names from Table 50
2. **Stack Validator**: Track operand stack, verify operator has correct operand count
3. **Graphics State Tracker**: Maintain q/Q stack, track CTM, color, line params per §8.4
4. **Path Constructor**: Build path objects, validate m/l/c/v/y/h/re operators, check termination
5. **Text Object Handler**: Match BT/ET pairs, validate Tf/Tj operators, track text matrix
6. **CTM Accumulator**: Apply cm operators, track cumulative transformation matrix
7. **Resource Resolver**: Resolve gs, Do operators to Resources dictionary entries
8. **Inline Image Parser**: Parse BI...ID...EI blocks, validate dimensions and data size

Generate violation reports citing specific Table and §8.x.y clause numbers.

---

**Specification Version:** ISO 32000-2:2020 Chapter 8
**Date Generated:** 2026-03-11
