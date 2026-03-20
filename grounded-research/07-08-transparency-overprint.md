# 07-08: Transparency & Overprint Model

**Research Deliverable** — Grounded Preflight Engine | Based on ISO 32000-2:2020 Chapters 8 & 11

---

## Transparency Overview (§11.1, §8.2)

**Opaque vs. Transparent Imaging (§8.2, §11.1):**
- **PDF 1.3 & earlier**: Opaque model. Each object fully obscures objects beneath.
- **PDF 1.4+**: Transparent model. Objects can have opacity (0.0–1.0), allowing backdrop to show through via blending.

**Transparency Requires:**
1. Extended Graphics State (ExtGState) with transparency entries
2. Optional transparency group (Form XObject with /Group entry)
3. Blend modes and isolated/knockout groups

---

## Transparency Parameters (§8.4.5, Table 51–52)

**Opacity Parameters:**

| Entry | Type | Default | Range | Purpose |
|-------|------|---------|-------|---------|
| `CA` | float | 1.0 | [0.0, 1.0] | Stroking alpha (opacity) |
| `ca` | float | 1.0 | [0.0, 1.0] | Non-stroking alpha |
| `BM` | name | Normal | (16 modes) | Blend mode |
| `SMask` | stream/null | null | | Soft mask (alpha channel) |
| `AIS` | boolean | false | | Alpha is shape (vs. alpha is opacity) |
| `TK` | boolean | false | | Text knockout (PDF 1.5+) |

**Accessed via:**
- Graphics state operator: `gs /GS1` (references ExtGState named GS1)
- ExtGState dictionary in Resources /ExtGState

**Preflight Checks:**
- CA/ca in [0.0, 1.0]
- BM is valid blend mode name (see below)
- SMask (if present): valid soft mask stream
- AIS, TK: boolean

---

## 16 Blend Modes (§11.3.5, Table ...)

**All Blend Modes (§11.3.5):**

| Mode | Formula | Effect | Print Safety |
|------|---------|--------|--------------|
| `Normal` | Cb (backdrop color) | Topmost color | SAFE |
| `Multiply` | Cs × Cb | Darken (screening) | SAFE |
| `Screen` | 1 - (1 - Cs) × (1 - Cb) | Lighten | SAFE |
| `Overlay` | Mix Multiply/Screen | Increase contrast | SAFE |
| `SoftLight` | Soft Overlay variant | Subtle lighting effect | SAFE |
| `HardLight` | Overlay with source/backdrop swapped | Strong lighting | SAFE |
| `ColorDodge` | Cs / (1 - Cb) (if Cb < 1) | Lighten drastically | RISKY |
| `ColorBurn` | 1 - (1 - Cb) / Cs (if Cs > 0) | Darken drastically | RISKY |
| `Darken` | min(Cs, Cb) | Preserve darker color | SAFE |
| `Lighten` | max(Cs, Cb) | Preserve lighter color | SAFE |
| `Difference` | |Cs - Cb| | Absolute difference | RISKY |
| `Exclusion` | Cs + Cb - 2 × Cs × Cb | Soft difference | RISKY |
| `Hue` | Hue(Cs), Saturation(Cb), Luminosity(Cb) | Match hue | RISKY |
| `Saturation` | Hue(Cb), Saturation(Cs), Luminosity(Cb) | Match saturation | RISKY |
| `Color` | Hue(Cs), Saturation(Cs), Luminosity(Cb) | Match color | RISKY |
| `Luminosity` | Hue(Cb), Saturation(Cb), Luminosity(Cs) | Match luminosity | RISKY |

**Compatible Mode:**
- Special value: `/Compatible` (implementation-defined behavior)
- Preflight: Use as alternative if blend mode unsupported

**Print Safety Ratings (Preflight Concern):**
- **SAFE**: Predictable print output, compositing stable
  - Normal, Multiply, Screen, Overlay, Darken, Lighten, SoftLight, HardLight
- **RISKY**: May produce unexpected print results, device-dependent
  - ColorDodge, ColorBurn, Difference, Exclusion, Hue, Saturation, Color, Luminosity

---

## Soft Mask (SMask, §11.2.5)

**Soft Mask Dictionary:**
Referenced via `SMask` entry in ExtGState.

**Structure:**
- Type: XObject
- Subtype: Image
- ColorSpace: DeviceGray (1-component image)
- Data: grayscale image (0=transparent, 255=opaque)

**Matte Color:**
Optional `/Matte` entry specifies color composited at mask edges.

**Preflight:**
- SMask is XObject with Type=/Image, Subtype=/Image
- ColorSpace = DeviceGray
- Width/Height match painted content
- Matte (if present): array of color values

---

## Transparency Groups (§11.4, §8.10.4)

**Form XObject with Group Entry (§11.4.1):**

```
[Form XObject Dictionary]
  /Type /XObject
  /Subtype /Form
  /Group <<
    /Type /Group
    /S /Transparency
    /CS colorspace
    /I isolated
    /K knockout
  >>
```

**Group Dictionary Entries (§11.4.1):**

| Entry | Type | Default | Purpose |
|-------|------|---------|---------|
| Type | name | Group | /Group |
| S | name | (required) | /Transparency (for transparency groups) |
| CS | name/array | (varies) | Color space for group composition |
| I | boolean | false | Isolated group (don't blend with backdrop) |
| K | boolean | false | Knockout group (opaque content knocks out backdrop) |

**Isolated (I) Flag (§11.4.3):**
- I=false: Group blends normally with backdrop
- I=true: Group composed independently, result composited as unit

**Knockout (K) Flag (§11.4.4):**
- K=false: Opaque content inside group partially transparent (normal)
- K=true: Opaque content is fully opaque (knocks out backdrop)

**Preflight Checks:**
- Group /Type = /Group
- Group /S = /Transparency
- CS (if present): valid color space
- I, K: boolean values

---

## Overprint Control (§8.6.7, §11.7.4)

**Overprinting (Spot Colors):**
When overprinting enabled, painting an object doesn't knockout colors beneath—instead, colors composite via additive/subtractive rules.

**Overprint Mode (OPM, §8.6.7):**

| Mode | Color Space | Behavior |
|------|-------------|----------|
| 0 | DeviceCMYK | K component at 1.0 knocks out C/M/Y |
| 0 | (other) | Normal (no special behavior) |
| 1 | DeviceCMYK | All components print independently |
| 1 | (other) | Normal |

**Operators:**
- `OP` (stroking overprint): boolean
- `op` (non-stroking overprint): boolean
- `OPM` (overprint mode): 0 or 1

**ExtGState Entries:**
- `OP`: boolean
- `op`: boolean
- `OPM`: 0 or 1

**Overprinting Dangerous Patterns (§11.7.4, Preflight Warning):**
1. OPM=0 + Black knockout: K=1.0 erases C/M/Y beneath
   - Risk: Unintended color loss if not carefully controlled
2. OPM=1 + Spot colors: All components print
   - Risk: Spot color saturates plate, TAC exceeds limits
3. Overprint + Transparency: Complex interaction (see §11.7.4)
   - Risk: Rendering device-dependent, may fail on older devices

**Preflight Checks:**
- Track OP/op flags through content stream
- Monitor OPM mode (0 vs. 1)
- Warning if OPM=0 with heavy CMYK colors
- Warning if overprint + transparency used together
- Check DeviceCMYK color values for saturation

---

## Blend Mode & Overprint Interaction (§11.7.4)

**Complex Case:**
If transparency (blend mode != Normal) AND overprinting both active:

Per §11.7.4:
- Non-zero OPM applies only to current color in graphics state
- NOT to images or shadings
- NOT if device native color space != CMYK

**Preflight Alert:**
Warn if both `BM != Normal` AND `OP=true/OPM` active in same ExtGState.

---

## Non-Knockout Groups vs. Knockout Groups (§11.4.4)

**Non-Knockout (K=false, default):**
```
Backdrop color = Color behind group
Result = Group composited normally
```

**Knockout (K=true):**
```
Result = Group opaque (ignores backdrop)
Objects behind group invisible
```

---

## Rendering Implications

**Device Support (§11.1):**
Not all devices support transparency. Fallback behavior:
1. Flatten transparency (convert to opaque graphics)
2. Ignore transparency (render with knockout)
3. Use alternate color space

**Preflight Warnings:**
- Transparency in PS Level 3 output (unsupported, needs flattening)
- Complex blend modes (ColorDodge, ColorBurn, etc.) may render device-dependently
- Soft masks on older devices
- Isolated groups on very old devices

---

## Extended Graphics State (ExtGState) Validation

**Complete ExtGState Validation (§8.4.5, Table 51–52):**

| Entry | Type | Valid Values | Preflight |
|-------|------|--------------|-----------|
| Type | name | GS | verify |
| LW | number | ≥ 0 | check range |
| LC | integer | 0, 1, 2 | check enum |
| LJ | integer | 0, 1, 2 | check enum |
| ML | number | ≥ 1 | check >= 1 |
| D | array | [array, number] | check format |
| RI | name | (4 intents) | check valid |
| OP | boolean | true/false | check type |
| op | boolean | true/false | check type |
| OPM | integer | 0, 1 | check enum |
| Font | array | [font_ref, size] | check both |
| CA | number | [0.0, 1.0] | check range |
| ca | number | [0.0, 1.0] | check range |
| BM | name | (16 modes + Compatible) | check valid |
| SMask | stream/null | valid XObject | verify stream |
| AIS | boolean | true/false | check type |
| TK | boolean | true/false | check type |
| BG/BG2 | function | (function) | validate |
| UCR/UCR2 | function | (function) | validate |
| TR/TR2 | function/name | (function or Standard) | validate |
| HT | dict/stream/name | (halftone) | validate |
| FL | number | > 0 | check > 0 |
| SM | number | > 0 | check > 0 |
| SA | boolean | true/false | check type |

---

## Table References

| Section | Content |
|---------|---------|
| §8.4.5, Table 51 | Graphics state parameter dictionary (core entries) |
| §8.4.5, Table 52 | Graphics state parameter dictionary (additional) |
| §11.3.5 | Blend mode formulas and definitions |
| §11.4 | Transparency groups |
| §11.4.1 | Group dictionary |
| §11.7 | Spot colors and transparency |
| §11.7.4 | Overprinting and transparency |

---

## Feed to AI

Use this research to design Grounded's **Transparency & Overprint Validator Module**:

1. **ExtGState Parser**: Extract all /ExtGState dictionaries from Resources
2. **Transparency Detector**: Identify CA/ca values < 1.0 (transparent objects)
3. **Blend Mode Validator**: Check BM values against 16 valid modes
4. **Soft Mask Handler**: Validate SMask XObject streams
5. **Group Analyzer**: Identify Form XObjects with /Group entry, validate I/K flags
6. **Overprint Detector**: Track OP/op flags and OPM mode
7. **Dangerous Pattern Identifier**: Flag OPM=0 + heavy CMYK, BM + overprint, etc.
8. **Blend Mode Safety Classifier**: Categorize modes as SAFE vs. RISKY
9. **Compatibility Checker**: Warn if transparency in old PDF versions (<1.4)
10. **Rendering Risk Assessor**: Flag complex transparency patterns, blend modes

Generate reports citing:
- §11.x.x sections for transparency
- §8.6.7 for overprinting
- Table 51–52 entries
- Print safety implications (device-dependent, risky blending, etc.)

---

**Specification Version:** ISO 32000-2:2020 Chapters 8 & 11
**Date Generated:** 2026-03-11
