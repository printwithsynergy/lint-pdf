# 04: Color Spaces

**Research Deliverable** — Grounded Preflight Engine | Based on ISO 32000-2:2020 Chapter 8

---

## Color Space Families (§8.6.3–8.6.6)

Per §8.6.1, color spaces define how color values are interpreted. Eleven families plus special cases.

### 1. DeviceGray (§8.6.3.1)

**Components:** 1 (gray value)
**Range:** 0.0 (black) to 1.0 (white)
**Direct Name:** `/DeviceGray`

Operators: `G` (stroking), `g` (non-stroking)

**Preflight:** Gray value in [0.0, 1.0]

### 2. DeviceRGB (§8.6.3.2)

**Components:** 3 (red, green, blue)
**Range:** 0.0 (minimum) to 1.0 (maximum intensity)
**Direct Name:** `/DeviceRGB`

Operators: `RG` (stroking), `rg` (non-stroking)

**Preflight:** Each component in [0.0, 1.0]

### 3. DeviceCMYK (§8.6.3.3)

**Components:** 4 (cyan, magenta, yellow, black)
**Range:** 0.0 (zero concentration) to 1.0 (maximum)
**Direct Name:** `/DeviceCMYK`

Operators: `K` (stroking), `k` (non-stroking)

**Overprint Mode (§8.6.7, §11.7.4):**
Behavior depends on OPM (overprint mode):
- **OPM = 0** (additive): Black (K=1.0) only prints K channel, other channels knocked out
- **OPM = 1** (subtractive): All components print independently
- Default: OPM = 0

**Preflight:** Components in [0.0, 1.0]

### 4. CalGray (§8.6.4.2)

**CIE-Based Gray (Device-Independent)**

**Dictionary Structure:**
```
[/CalGray
  <<
    /WhitePoint [Xw Yw Zw]    ; required
    /BlackPoint [Xb Yb Zb]    ; optional
    /Gamma gamma              ; optional, default 1.0
  >>
]
```

**Preflight:**
- WhitePoint required, must be [Xw, Yw, Zw] with Xw, Yw, Zw > 0
- BlackPoint (if present): [Xb, Yb, Zb] typically [0, 0, 0]
- Gamma > 0 (if present)

### 5. CalRGB (§8.6.4.3)

**CIE-Based RGB (Device-Independent)**

**Dictionary Structure:**
```
[/CalRGB
  <<
    /WhitePoint [Xw Yw Zw]           ; required
    /BlackPoint [Xb Yb Zb]           ; optional
    /Gamma [gR gG gB]                ; optional, defaults [1.0, 1.0, 1.0]
    /Matrix [xR xG xB yR yG yB zR zG zB]  ; optional, default identity
  >>
]
```

**Preflight:**
- WhitePoint required
- Gamma array (if present): 3 values, each > 0
- Matrix array (if present): 9 values

### 6. Lab (§8.6.4.4)

**CIE-Based Perceptual**

**Components:** L (lightness), a (green-red), b (blue-yellow)
**Range:** L ∈ [0, 100], a/b ∈ [amin, amax], [bmin, bmax]

**Dictionary Structure:**
```
[/Lab
  <<
    /WhitePoint [Xw Yw Zw]    ; required
    /BlackPoint [Xb Yb Zb]    ; optional
    /Range [amin amax bmin bmax]  ; optional, default [-100, 100, -100, 100]
  >>
]
```

**Preflight:**
- WhitePoint required
- Range (if present): [amin amax bmin bmax] with amin < amax, bmin < bmax

### 7. ICCBased (§8.6.5.4)

**ICC Profile (Device-Independent via ICC Color Profile)**

**Dictionary Structure:**
```
[/ICCBased stream_ref]
```

Stream contains embedded ICC color profile.

**Stream Dictionary Entries:**
- `N`: number of color components (required, 1–4 or 8)
- `Alternate`: alternate color space for non-ICC viewers
- `Range`: component ranges [c1min, c1max, c2min, c2max, ...]

**Preflight:**
- Stream present and decompressible
- N in [1, 2, 3, 4, 8]
- Alternate space (if present) must be device or CIE-based space
- ICC profile version valid (typically 2.0, 4.2, 4.3)

**Device-Independent Rendering:**
Accurate color via ICC profile. Alternate space used if viewer doesn't support ICC.

### 8. Indexed (§8.6.5.3)

**Color Lookup Table**

**Dictionary Structure:**
```
[/Indexed base hival lookup]
```

Where:
- `base`: base color space (DeviceRGB, DeviceGray, etc.)
- `hival`: maximum index value (0–255 typically)
- `lookup`: string or stream containing color table

**Index Values:** 0 to hival (inclusive) map to base color space values

**Preflight:**
- Base space is valid device or CIE-based space (NOT Indexed, Separation, DeviceN, Pattern)
- hival >= 0
- Lookup table: string or stream with length = (hival+1) × (base color components)
  - DeviceRGB base: lookup length = (hival+1) × 3
  - DeviceGray base: lookup length = (hival+1) × 1

### 9. Separation (§8.6.6.3)

**Single Spot Color**

**Dictionary Structure:**
```
[/Separation colorantName alternateSpace tintTransform]
```

Where:
- `colorantName`: name object identifying color (e.g., `/LogoGreen`)
- `alternateSpace`: fallback color space if separation unavailable
- `tintTransform`: function mapping tint [0.0, 1.0] to alternate space values

**Tint Value:** 0.0 = no color, 1.0 = full color

**Preflight:**
- colorantName is name
- alternateSpace is device or CIE-based (not Indexed/Separation/DeviceN/Pattern)
- tintTransform is valid function (FunctionType 0, 2, 3, 4)

**Special Name:** `/All` = all process colors (rarely used)

**RGB Exception (§8.6.6.3 NOTE 7):**
Separation on RGB device should use alternate space, not device colorant (additive behavior unexpected).

### 10. DeviceN (§8.6.6.5)

**Multiple Spot Colors (Arbitrary Components)**

**Dictionary Structure (Basic):**
```
[/DeviceN names alternateSpace tintTransform]
```

**Dictionary Structure (Extended, PDF 1.6):**
```
[/DeviceN names alternateSpace tintTransform attributes]
```

Where:
- `names`: array of color component names [/Cyan, /Magenta, /Yellow, /Black, /Spot1, ...]
- `alternateSpace`: fallback space
- `tintTransform`: function mapping all components to alternate space
- `attributes`: optional dictionary with Subtype, Colorants, etc.

**Component Names:**
- Cyan, Magenta, Yellow, Black: standard CMYK (reserved)
- Other names: custom spot colors
- Special name: `/None` (component ignored)

**Preflight:**
- names array: all different (except /None can repeat)
- alternateSpace valid
- tintTransform valid function
- attributes (if present): valid dictionary

**Subtype Values (§8.6.6.5):**
- (absent or `DeviceN`): standard DeviceN
- `NChannel`: PDF 1.6+ with additional features (process vs. spot distinction)

### 11. Pattern (§8.7)

**Color via Tiling or Shading Pattern**

**Colored Pattern:**
```
[/Pattern]
```
References Pattern in Resources /Pattern subdictionary.

**Uncolored Pattern:**
```
[/Pattern base]
```
Uses base color space; pattern supplies color.

**Preflight:** Pattern object exists in Resources /Pattern

---

## Overprint Control (§8.6.7)

**Overprint Modes (OPM):**

| Mode | Behavior | Use |
|------|----------|-----|
| 0 | Black knockout: K=1.0 knocks out other colors | Screen, proofs |
| 1 | All colors print independently | Separation simulation |

**Operators:**
- `OP` (stroking overprint): boolean
- `op` (non-stroking overprint): boolean
- `OPM` (overprint mode): 0 or 1

**Dictionary Entries (ExtGState):**
- `OP`: boolean
- `op`: boolean
- `OPM`: integer (0 or 1)

**Non-Zero OPM Rules (§8.6.7):**
Applied only to:
- Current color in graphics state when color space is DeviceCMYK
- NOT to images or shadings
- NOT if device native color space != CMYK

**Preflight Checks:**
- OP/op boolean values
- OPM in [0, 1]
- Overprint usage consistent with color space
- Warning if OPM=0 with CMYK colors (destructive)

---

## Color Space Operators (§8.6.8, Table 73)

| Operator | Operands | Description |
|----------|----------|-------------|
| `CS` | name | Set current stroking color space |
| `cs` | name | Set current non-stroking color space |
| `SC` / `SCN` | c1 ... cn | Set stroking color values |
| `sc` / `scn` | c1 ... cn | Set non-stroking color values |
| `G` | gray | Set stroking color space to DeviceGray |
| `g` | gray | Set non-stroking color space to DeviceGray |
| `RG` | r g b | Set stroking color space to DeviceRGB |
| `rg` | r g b | Set non-stroking color space to DeviceRGB |
| `K` | c m y k | Set stroking color space to DeviceCMYK |
| `k` | c m y k | Set non-stroking color space to DeviceCMYK |

**Color Restrictions (§8.6.8):**
Inside uncolored tiling patterns and Type 3 font glyph definitions (d1 operator), color-setting operators are ignored:
- CS, cs, SC, SCN, sc, scn, G, g, RG, rg, K, k, ri (rendering intent)

**Preflight:**
- Verify CS/cs operators reference valid color space in Resources /ColorSpace
- Verify color value operand count matches color space components
- Check value ranges per color space

---

## Initial Color Values (§8.6.8)

When color space changed with CS/cs, stroking/non-stroking color initialized:

| Color Space | Initial Value |
|-----------|---------------|
| DeviceGray, CalGray | 0.0 (black) |
| DeviceRGB, CalRGB, Lab | [0.0, 0.0, 0.0] |
| DeviceCMYK | [0.0, 0.0, 0.0, 1.0] (black) |
| Indexed | 0 (first index) |
| Separation, DeviceN | 1.0 for all components (no color) |
| Pattern | special null pattern (no-op) |
| ICCBased | 0.0 for all components (black) |

---

## TAC Calculation (Total Area Coverage)

**Purpose:**
Limit ink density in print; prevent oversat uration.

**Formula (per §8.6.7):**
```
TAC = sum of all separations (C + M + Y + K + spot colors) at given point
```

**Preflight Approach:**
- Track color operators in content stream
- For CMYK objects: sum C, M, Y, K values (0.0–4.0 range)
- For spot colors: include in TAC calculation
- Common TAC limits: 300% (0.0–3.0), 280%, 240%

**Implementation Note:**
Full TAC calculation requires decomposing all colors to CMYK via ICC profiles (complex). Preflight can warn if colors appear heavy-saturated or if overprint is enabled without explicit OPM handling.

---

## Special Rendering (§8.6.5.8, §8.6.5.9)

**Rendering Intent (ri operator):**
- `AbsoluteColorimetric`
- `RelativeColorimetric`
- `Saturation`
- `Perceptual`

**Black Point Compensation (UseBlackPtComp):**
Boolean flag in ExtGState. Adjusts rendering of near-black colors.

---

## Table References

| Table | Section | Content |
|-------|---------|---------|
| Table 63–72 | 8.6.3–8.6.6 | Color space definitions |
| Table 70 | 8.6.6.5 | DeviceN attributes dictionary |
| Table 73 | 8.6.8 | Color operators |
| Table 51 | 8.4.5 | ExtGState color entries (CA, ca, OPM, BM) |

---

## Feed to AI

Use this research to design Grounded's **Color Space Validator Module**:

1. **Color Space Parser**: Identify all 11 families (DeviceGray/RGB/CMYK, CalGray/RGB, Lab, ICC, Indexed, Separation, DeviceN, Pattern)
2. **Dictionary Validator**: For each family, validate required/optional entries per spec
3. **ICC Profile Analyzer**: Decompress ICC stream, validate profile version, extract component count
4. **Separation Resolver**: Find base color, verify tint transform function
5. **DeviceN Analyzer**: Check component names, validate Subtype, check Colorants
6. **Component Range Checker**: Verify operator operands match color space component count
7. **Overprint Tracker**: Monitor OPM, OP/op flags, warn of unsafe patterns (OPM=0 + CMYK)
8. **TAC Estimator**: Sum color components, flag potential oversat uration

Generate violation reports citing §8.6.x sections and Table numbers.

---

**Specification Version:** ISO 32000-2:2020 Chapter 8
**Date Generated:** 2026-03-11
