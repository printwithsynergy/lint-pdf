# lintPDF v2 Universe Enumeration (Companion File)

> **Companion to `lintpdf-check-audit-playbook-v2.md` §10.** This is the canonical, authoritative list of all 412 artifacts (84 Tier-0 primitives + 328 user-facing checks) lintPDF is targeting across v2 + EPM + BYO.
>
> **Read-only constraint applies to every entry.** Each user-facing check produces structured findings + remediation guidance, never PDF mutation.

---

## Section 1 — Tier breakdown summary

| Tier | Description | Count |
|------|-------------|------:|
| **T0** | Atomic building-block primitives (composable, not user-facing) | 84 |
| **T1** | Table stakes — every shop needs this | 62 |
| **T2** | Strong competitive — mainstream commercial preflight | 101 |
| **T3** | Dieline-focused differentiator (lintPDF wedge) | 48 |
| **T4** | Packaging-specialty (white/varnish/barcode-vs-fold/Braille) | 74 |
| **T5** | Long-tail / niche / regulatory | 43 |
| **TOTAL** |  | **412** |

## Section 2 — Category breakdown

| Category | ID prefix | Count |
|----------|-----------|------:|
| Fonts & typography | F | 41 |
| Color & ink | C | 67 |
| Images | I | 38 |
| Transparency | TR | 22 |
| Page geometry / boxes / bleed | P | 36 |
| Line art / paths / strokes | LA | 19 |
| Metadata / file structure / encryption | M | 34 |
| Layers / OCG / processing steps | L | 21 |
| Dieline & cut | D | 23 |
| White / varnish / underprint | W | 16 |
| Braille / emboss / tactile | BR | 9 |
| Barcodes & GS1 | B | 28 |
| Trapping & registration | T | 12 |
| Substrate / press / production | S | 18 |
| Variable data & VDP | V | 7 |
| Workflow / job / MIS | WF | 11 |
| Industry-specific regulatory | R | 10 |
| ISO standards (rolled-up) | ISO | 12 |
| EPM candidacy | EPM | 22 |
| **Tier-0 primitives** (separate) | (predicate names) | **84** |

---

## Section 3 — Full enumeration (user-facing checks)

Legend: **T** = tier · **D** = difficulty (E/M/H) · **DL** = dieline-adjacent · **W** = wave (0/A/B/C/D/E)

### 3.1 Fonts & Typography (F-01..F-41)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| F-01 | Font not embedded | 1 | E | N | B | Any glyph references font not embedded |
| F-02 | Font subset incomplete | 2 | M | N | D | Subset missing glyphs that text references |
| F-03 | Font fully embedded vs subset | 0 | E | N | 0 | Primitive |
| F-04 | Type 1 font present | 2 | E | N | D | Adobe sunset warning |
| F-05 | Type 3 font present | 2 | E | N | D | Disallowed in many specs |
| F-06 | TrueType font present | 0 | E | N | 0 | Primitive |
| F-07 | OpenType-CFF font present | 0 | E | N | 0 | Primitive |
| F-08 | OpenType-TrueType font present | 0 | E | N | 0 | Primitive |
| F-09 | CID font present | 0 | E | N | 0 | Primitive |
| F-10 | Multiple Master font | 2 | E | N | D | Legacy |
| F-11 | CFF / Type 1C glyph data | 0 | E | N | 0 | Primitive |
| F-12 | Font widths inconsistent / corrupt | 2 | M | N | D |  |
| F-13 | ToUnicode CMap missing | 2 | M | N | B | Text not extractable |
| F-14 | ToUnicode CMap incomplete | 2 | M | N | B |  |
| F-15 | .notdef glyph referenced | 2 | M | N | D |  |
| F-16 | Encoding inconsistent / WinAnsi mismatch | 2 | M | N | D |  |
| F-17 | Font references illegal character | 2 | M | N | D |  |
| F-18 | Artificial bold (faux bold) | 1 | M | N | B |  |
| F-19 | Artificial italic (faux oblique) | 1 | M | N | B |  |
| F-20 | Artificial outline style | 2 | M | N | D |  |
| F-21 | Artificial shadow / drop shadow on text | 2 | M | N | D |  |
| F-22 | Text below minimum size (plain) | 1 | E | N | B |  |
| F-23 | Text below min size (multi-separation/tinted) | 1 | M | Y | A |  |
| F-24 | Text below min size (reverse / knockout) | 1 | M | N | B |  |
| F-25 | Text stroke too thin | 2 | M | N | D |  |
| F-26 | White text set to overprint | 1 | E | N | B |  |
| F-27 | Light/colored text overprints | 2 | M | N | D |  |
| F-28 | Black text not overprinting | 2 | M | N | B |  |
| F-29 | Invisible text (rendering mode 3) | 2 | E | N | D |  |
| F-30 | Text below another object (hidden) | 3 | H | N | A | GWG visibility |
| F-31 | Text uses 4-color rich black | 1 | E | N | B |  |
| F-32 | Text on dieline / cut path | 3 | M | Y | A |  |
| F-33 | Text inside bleed (will be trimmed) | 3 | E | Y | A |  |
| F-34 | Text too close to trim (safe zone) | 1 | E | Y | B |  |
| F-35 | Text too close to fold | 4 | M | Y | A | Pkg differentiator |
| F-36 | Text near perforation | 4 | M | Y | A |  |
| F-37 | Text on glue flap | 4 | M | Y | A |  |
| F-38 | Font license / DRM prevents embedding | 2 | M | N | D |  |
| F-39 | Duplicate font names | 2 | M | N | D |  |
| F-40 | Font name on allow/block list | 2 | E | N | D |  |
| F-41 | Glyph differs across uses | 0 | H | N | 0 | Primitive |

### 3.2 Color & Ink (C-01..C-67)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| C-01 | DeviceRGB used | 1 | E | N | B |  |
| C-02..C-13 | Color-space primitives | 0 | E | N | 0 | DeviceCMYK/Gray/CalRGB/CalGray/Lab/ICCBased/DeviceN/NChannel/Separation/Indexed/Pattern/Shading |
| C-14 | RGB images present | 1 | E | N | B |  |
| C-15 | Lab images present | 2 | E | N | D |  |
| C-16 | Indexed images present | 2 | E | N | D |  |
| C-17 | Image with embedded ICC | 0 | E | N | 0 | Primitive |
| C-18 | Image ICC differs from doc OI | 2 | M | N | D |  |
| C-19 | OutputIntent missing | 1 | E | N | B |  |
| C-20 | OutputIntent ICC mismatched | 2 | M | N | D |  |
| C-21 | OutputIntent ICC v2 vs v4 | 0 | E | N | 0 | Primitive |
| C-22 | OutputIntent embedded vs reference | 2 | E | N | D |  |
| C-23 | Spot color count > N | 1 | E | N | B |  |
| C-24 | Spot color allow/block list | 1 | E | N | B |  |
| C-25 | Spot color regex / suffix | 2 | M | N | D |  |
| C-26 | Spot alternate space inappropriate | 2 | M | N | D |  |
| C-27 | Spot alternate values zero | 2 | M | N | D |  |
| C-28 | Spot tint below min dot | 4 | M | N | C | Flexo |
| C-29 | Spot above max dot | 4 | M | N | C |  |
| C-30 | Spot ≈ process color (use CMYK instead) | 3 | H | N | A |  |
| C-31 | Spot not in reference library | 2 | M | N | D |  |
| C-32 | Deprecated Pantone naming | 2 | E | N | D |  |
| C-33 | Ambiguous spot definition | 2 | M | N | D |  |
| C-34 | Object overprint set | 0 | E | N | 0 | Primitive |
| C-35 | OPM 0 vs OPM 1 | 2 | M | N | D |  |
| C-36 | Overprint of process white | 1 | E | N | B |  |
| C-37 | Overprint of light tints | 2 | M | N | D |  |
| C-38 | Overprint of registration color | 1 | E | N | B |  |
| C-39 | Overprint on dieline / cut spot | 3 | M | Y | A | ISO 19593 |
| C-40 | Overprint on white-ink layer | 4 | M | Y | C |  |
| C-41 | Overprint on varnish layer | 4 | M | Y | C |  |
| C-42 | Knockout where overprint expected (black) | 2 | M | N | D |  |
| C-43 | TAC > limit (page max) | 1 | M | N | B |  |
| C-44 | Average TAC per region | 2 | H | N | D |  |
| C-45 | Per-page TAC max | 2 | M | N | D |  |
| C-46 | Per-separation coverage % | 2 | M | N | D |  |
| C-47 | Ink-on-pixel max | 2 | M | N | D |  |
| C-48 | Substrate-aware TAC | 4 | M | N | C |  |
| C-49 | Area above min-dot threshold | 4 | M | N | C |  |
| C-50 | 4-color rich black on small text | 1 | E | N | B |  |
| C-51 | Registration pseudo-color as fill | 1 | E | N | B |  |
| C-52 | Impure black (CMY > 0 in K-only intent) | 2 | M | N | D |  |
| C-53 | Impure gray | 2 | M | N | D |  |
| C-54 | Transfer function present | 2 | E | N | D |  |
| C-55 | Halftone dictionary present | 2 | E | N | D |  |
| C-56 | UCR/BG function | 0 | M | N | 0 | Primitive |
| C-57 | Rendering Intent set per object | 2 | E | N | D |  |
| C-58 | Blending CS at page level | 2 | M | N | D |  |
| C-59 | Blending CS wrong (RGB on CMYK) | 2 | M | N | D |  |
| C-60 | Inks list extraction | 0 | E | N | 0 | Primitive |
| C-61 | Ink ordering / printing sequence | 4 | M | N | C |  |
| C-62 | Technical ink correctly tagged ISO 19593 | 3 | M | Y | A |  |
| C-63 | Multiple PS inks on same plate | 3 | H | Y | A |  |
| C-64 | Color-managed vs untagged image mix | 2 | M | N | D |  |
| C-65 | Mixed CMYK + RGB on same page | 2 | E | N | D |  |
| C-66 | Single black plate when non-black expected | 2 | M | N | D |  |
| C-67 | Forbidden ink names (Cyan/All) as spot | 2 | E | N | B | ISO violation |

### 3.3 Images (I-01..I-38)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| I-01 | Color image effective resolution < min | 1 | E | N | B |  |
| I-02 | Grayscale resolution < min | 1 | E | N | B |  |
| I-03 | 1-bit (line art) resolution < min | 2 | E | N | D |  |
| I-04 | Color image resolution > max | 2 | E | N | D |  |
| I-05 | Image PPI before scaling | 0 | E | N | 0 | Primitive |
| I-06 | Image PPI after CTM scale | 0 | E | N | 0 | Primitive |
| I-07 | Image bit depth | 0 | E | N | 0 | Primitive |
| I-08 | 16-bit images in non-PDF/X-4 | 2 | E | N | D |  |
| I-09 | JPEG compression detected | 2 | E | N | D |  |
| I-10 | JPEG quality below threshold | 2 | M | N | D |  |
| I-11 | JPEG2000 detected | 2 | E | N | D |  |
| I-12 | LZW in PDF/X-1a context | 2 | E | N | D |  |
| I-13..I-15 | CCITT/Flate/JBIG2/disallowed-filter primitives | 0 | E | N | 0 | Primitives |
| I-16 | Image rotated 90/180/270 | 2 | E | N | D |  |
| I-17 | Image rotated non-orthogonally | 2 | M | N | D |  |
| I-18 | Image sheared / skewed | 2 | M | N | D |  |
| I-19 | Image mirrored / flipped | 2 | E | N | D |  |
| I-20 | Image scaled non-uniformly | 2 | E | N | D |  |
| I-21 | Image scale > 100% | 2 | E | N | D |  |
| I-22 | Image scale < 25% (downscale waste) | 2 | E | N | D |  |
| I-23 | Image interpolation flag | 0 | E | N | 0 | Primitive |
| I-24 | OPI link present | 2 | E | N | D |  |
| I-25 | OPI link broken | 2 | M | N | D |  |
| I-26 | Image embedded vs linked | 0 | E | N | 0 | Primitive |
| I-27 | Duplicate image streams | 2 | M | N | D |  |
| I-28 | Image inside clipping path | 0 | E | N | 0 | Primitive |
| I-29 | Image fully outside crop / trim | 2 | E | N | D |  |
| I-30 | Image partially outside trim (no bleed) | 1 | E | Y | B |  |
| I-31..I-33 | Inline / soft mask / alternate image primitives | 0 | E | N | 0 | Primitives |
| I-34 | EXIF metadata present | 2 | M | N | D |  |
| I-35 | Web format (WebP/HEIC/AVIF) embedded | 2 | M | N | D |  |
| I-36 | Image alpha channel present | 0 | E | N | 0 | Primitive |
| I-37 | Image color profile vs page profile mismatch | 2 | M | N | D |  |
| I-38 | Banding-prone gradient | 2 | H | N | D |  |

### 3.4 Transparency (TR-01..TR-22)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| TR-01 | Transparency present (live) | 1 | E | N | B |  |
| TR-02..TR-09 | Blend mode primitives | 0 | E | N | 0 | Normal/Multiply/Screen/Overlay/Darken/Lighten/Dodge/Burn/HardLight/SoftLight/Difference/Exclusion |
| TR-10 | Non-separable blend mode (Hue/Sat/Color/Lum) | 2 | E | N | D |  |
| TR-11 | ExtGState alpha < 1.0 | 0 | E | N | 0 | Primitive |
| TR-12 | Soft mask in use | 0 | E | N | 0 | Primitive |
| TR-13 | Soft mask on text | 2 | M | N | D |  |
| TR-14 | Knockout group | 0 | E | N | 0 | Primitive |
| TR-15 | Isolated group | 0 | E | N | 0 | Primitive |
| TR-16 | Page-level transparency group missing | 2 | M | N | D |  |
| TR-17 | Blending CS missing on transparent page | 2 | M | N | D |  |
| TR-18 | Transparency on spot color | 2 | M | Y | D |  |
| TR-19 | Transparency × overprint interaction | 2 | H | Y | D |  |
| TR-20 | Transparency requires flattening | 2 | M | N | D |  |
| TR-21 | Flattener preset detected (rasterized) | 2 | M | N | D |  |
| TR-22 | Transparency on processing-step / cut layer | 3 | M | Y | A | Pkg wedge |

### 3.5 Page Geometry / Boxes / Bleed (P-01..P-36)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| P-01..P-02 | MediaBox/CropBox present (primitives) | 0 | E | N | 0 |  |
| P-03 | TrimBox missing | 1 | E | Y | B |  |
| P-04 | BleedBox missing | 1 | E | Y | B |  |
| P-05 | ArtBox present | 0 | E | N | 0 | Primitive |
| P-06 | TrimBox = MediaBox (no bleed possible) | 1 | E | Y | B |  |
| P-07 | TrimBox not nested in BleedBox | 1 | E | Y | B |  |
| P-08 | BleedBox not nested in MediaBox | 1 | E | Y | B |  |
| P-09 | Bleed amount < required | 1 | E | Y | B |  |
| P-10 | Bleed asymmetric per side | 2 | M | Y | B |  |
| P-11 | Bleed > maximum | 2 | E | Y | D |  |
| P-12 | Trim size mismatch vs job ticket | 2 | M | N | D |  |
| P-13 | Page size differs across pages | 2 | E | N | D |  |
| P-14 | Page rotated (90/180/270) | 2 | E | N | D |  |
| P-15 | Mixed page orientation | 2 | E | N | D |  |
| P-16 | UserUnit ≠ 1.0 | 2 | E | N | D | Large-format |
| P-17 | Page count expected vs actual | 1 | E | N | B |  |
| P-18 | Multi-up / step-and-repeat detected | 2 | H | Y | D |  |
| P-19 | Empty (blank) page | 2 | E | N | D |  |
| P-20 | Blank separation on page | 2 | M | N | D |  |
| P-21 | All-white content / no inked objects | 2 | M | N | D |  |
| P-22 | Only non-printing layers contain content | 3 | M | Y | A | All design on cut/varnish |
| P-23 | Object completely outside trimbox | 2 | E | Y | D |  |
| P-24 | Object partially crossing trimbox | 2 | E | Y | D |  |
| P-25 | Object overlapping other objects | 0 | E | N | 0 | Primitive |
| P-26 | Object hidden under another (GWG visibility) | 3 | H | N | A | False-positive killer |
| P-27 | White-on-white invisible content | 2 | M | N | D |  |
| P-28 | Content beyond bleed (will get cut) | 2 | E | Y | D |  |
| P-29 | Content too close to spine (book jobs) | 5 | M | N | E |  |
| P-30 | Bleed beyond dieline | 3 | M | Y | A | Pkg key |
| P-31 | Bleed inside dieline (insufficient) | 3 | M | Y | A | Pkg key |
| P-32 | Content too close to dieline (X mm) | 3 | M | Y | A | Brand-killer |
| P-33 | Safety/text-zone violation | 2 | E | Y | D |  |
| P-34 | Page boxes have non-zero offset origin | 2 | E | N | D |  |
| P-35 | Two pages overlap (reader-spreads) | 2 | M | N | D |  |
| P-36 | TrimBox larger than logical product | 2 | M | N | D |  |

### 3.6 Line Art / Paths / Strokes (LA-01..LA-19)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| LA-01 | Hairline below min (single sep) | 1 | E | N | B |  |
| LA-02 | Hairline below min (multi-sep / colored) | 1 | M | N | B |  |
| LA-03 | Zero-width stroke | 2 | E | N | D |  |
| LA-04 | Invisible stroke (None color) | 0 | E | N | 0 | Primitive |
| LA-05 | Dashed stroke (where solid expected) | 0 | E | N | 0 | Primitive |
| LA-06 | Negative dash phase | 2 | E | N | D |  |
| LA-07 | Miter limit excessive | 0 | E | N | 0 | Primitive |
| LA-08 | Line cap / join style | 0 | E | N | 0 | Primitive |
| LA-09 | Path with too many nodes | 2 | M | N | D |  |
| LA-10 | Subsequent duplicate path points | 2 | M | N | D |  |
| LA-11 | Self-intersecting path | 0 | M | N | 0 | Primitive |
| LA-12 | Path has zero area | 0 | E | N | 0 | Primitive |
| LA-13 | Clipping path complexity excessive | 2 | M | N | D |  |
| LA-14 | Clipping path nesting depth | 2 | M | N | D |  |
| LA-15..LA-17 | Open path / stroke None / fill None primitives | 0 | E | N | 0 | Primitives |
| LA-18 | Cut path is dashed (should be solid) | 3 | M | Y | A |  |
| LA-19 | Cut path has tint < 100% | 3 | E | Y | A |  |

### 3.7 Metadata / File Structure / Encryption (M-01..M-34)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| M-01 | PDF version | 1 | E | N | B |  |
| M-02 | PDF 2.0 features in 1.x file | 2 | M | N | D |  |
| M-03 | Document Title present | 2 | E | N | D |  |
| M-04 | Author / Creator / Producer | 2 | E | N | D |  |
| M-05 | CreationDate / ModDate | 0 | E | N | 0 | Primitive |
| M-06 | XMP metadata present | 1 | E | N | B |  |
| M-07 | XMP well-formed | 2 | M | N | D |  |
| M-08 | XMP namespace required | 2 | M | N | D |  |
| M-09 | XMP audit trail / history | 2 | M | N | D |  |
| M-10 | Document ID match | 0 | E | N | 0 | Primitive |
| M-11 | Info dict vs XMP inconsistency | 2 | M | N | D |  |
| M-12 | Encryption present | 1 | E | N | B |  |
| M-13 | Owner password set | 2 | E | N | D |  |
| M-14 | Permission flags restrict printing | 2 | E | N | D |  |
| M-15 | Permission flags restrict modify | 0 | E | N | 0 | Primitive |
| M-16 | Digital signature present | 0 | E | N | 0 | Primitive |
| M-17 | JavaScript present | 2 | E | N | D |  |
| M-18 | Action dictionaries / additional actions | 2 | E | N | D |  |
| M-19 | Embedded files (attachments) | 2 | E | N | D |  |
| M-20 | XFA forms present | 2 | E | N | D |  |
| M-21 | Alternate presentations | 0 | E | N | 0 | Primitive |
| M-22 | External streams | 0 | E | N | 0 | Primitive |
| M-23 | Reference XObjects | 2 | M | N | D |  |
| M-24 | PostScript fragments / passthrough | 2 | E | N | D |  |
| M-25 | Article threads | 0 | E | N | 0 | Primitive |
| M-26 | Bookmarks / destinations | 0 | E | N | 0 | Primitive |
| M-27 | Marked content / structure tree | 0 | E | N | 0 | Primitive |
| M-28 | Pre-separated pages detected | 2 | M | N | D |  |
| M-29 | Trapped flag (True/False/Unknown) | 1 | E | N | B |  |
| M-30 | Compressed object streams | 0 | E | N | 0 | Primitive |
| M-31 | Data after EOF | 2 | M | N | D |  |
| M-32 | Malformed xref / linearization | 2 | M | N | D |  |
| M-33 | Unused objects / file bloat | 2 | M | N | D |  |
| M-34 | File size > limit | 2 | E | N | D |  |

### 3.8 Layers / OCG / Processing Steps (L-01..L-21)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| L-01 | OCG / layers present | 0 | E | N | 0 | Primitive |
| L-02 | Empty layer | 2 | E | N | D |  |
| L-03 | Hidden layer with printable content | 2 | M | N | D |  |
| L-04 | Layer initial state | 0 | E | N | 0 | Primitive |
| L-05 | OCG config not PDF/X-4 conformant | 2 | M | N | D |  |
| L-06 | ISO 19593-1 GTS_Metadata key on OCG | 3 | M | Y | A |  |
| L-07..L-13 | Processing-step group/type detection | 3-4 | E-M | Y | A-C | Cutting/Folding-Creasing/Glueing/Perforating/Braille/Information/Positions |
| L-14 | PS group: White / Underprint | 4 | M | Y | C |  |
| L-15 | PS group: Varnish | 4 | M | Y | C |  |
| L-16 | PS group: Dimensions (legacy) | 5 | M | Y | E |  |
| L-17 | PS group: Custom (user-defined) | 4 | M | Y | C |  |
| L-18 | Reserved ink names on PS layer | 4 | E | Y | C | ISO violation |
| L-19 | PS object not in spot color | 4 | E | Y | C |  |
| L-20 | PS object not set to overprint | 4 | E | Y | C | Required by ISO |
| L-21 | PS layer also contains design content | 4 | M | Y | C | Layer purity |

### 3.9 Dieline & Cut (D-01..D-23)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| D-01 | Dieline detection by spot name | 3 | E | Y | A | "CutContour", "Die", "Cut" |
| D-02 | Dieline detection by ISO 19593 layer | 3 | E | Y | A |  |
| D-03 | Dieline detection by tech-ink mapping | 3 | M | Y | A | Custom mapping |
| D-04 | Dieline detection by layer name pattern | 3 | E | Y | A |  |
| D-05 | Multiple competing dieline definitions | 3 | M | Y | A | Cutter ambiguity |
| D-06 | Dieline z-order is below content | 3 | M | Y | A | UNCLAIMED wedge |
| D-07 | Dieline is set to knockout (should overprint) | 3 | E | Y | A |  |
| D-08 | Dieline blend mode ≠ Normal | 3 | E | Y | A |  |
| D-09 | Dieline opacity < 100% | 3 | E | Y | A |  |
| D-10 | Dieline tint < 100% | 3 | E | Y | A |  |
| D-11 | Dieline has soft mask | 3 | E | Y | A |  |
| D-12 | Dieline closure (closed path) | 3 | M | Y | A |  |
| D-13 | Dieline self-intersects | 3 | M | Y | A | Cutter problems |
| D-14 | Dieline unit / scale matches CAD | 3 | H | Y | A |  |
| D-15 | Content extends beyond dieline | 3 | E | Y | A |  |
| D-16 | Content fails to reach dieline (white edge) | 3 | E | Y | A |  |
| D-17 | Critical content within X mm of dieline | 3 | M | Y | A | Trim safety |
| D-18 | Fold-line distance: content too close | 3 | M | Y | A | Wedge |
| D-19 | Fold-line direction (mountain/valley tag) | 4 | H | Y | C |  |
| D-20 | Multi-fold parallelism (tri-fold) | 4 | H | Y | C |  |
| D-21 | Perforation tooth pattern | 4 | M | Y | C |  |
| D-22 | Glue-flap content present | 4 | M | Y | A |  |
| D-23 | Registration on glue flap | 4 | M | Y | A |  |

### 3.10 White / Varnish / Underprint (W-01..W-16)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| W-01 | White-ink layer presence | 4 | E | Y | C |  |
| W-02 | White underprint coverage matches color above | 4 | H | Y | C | UNCLAIMED |
| W-03 | White underprint choke (X µm shrink) | 4 | H | Y | C |  |
| W-04 | White underprint spread | 4 | H | Y | C |  |
| W-05 | White is set to overprint | 4 | E | Y | C |  |
| W-06 | White covers transparent substrate | 4 | H | Y | C |  |
| W-07 | Missing white where colored ink is laid | 4 | H | Y | C | UNCLAIMED |
| W-08 | White marked opaque vs transparent | 4 | M | Y | C |  |
| W-09 | Varnish coverage area | 4 | E | Y | C |  |
| W-10 | Varnish-free / ink-free zones | 4 | M | Y | C |  |
| W-11 | Matte vs Gloss varnish tagging | 4 | M | Y | C |  |
| W-12 | Varnish overlaps non-printable areas | 4 | M | Y | C | UNCLAIMED |
| W-13 | Selective spot UV registers to design | 4 | M | Y | C |  |
| W-14 | Foil layer (cold/hot) tagged correctly | 4 | M | Y | C |  |
| W-15 | Embossing / debossing tagged | 4 | M | Y | C |  |
| W-16 | Emboss content matches design content | 5 | H | Y | E |  |

### 3.11 Braille / Tactile (BR-01..BR-09)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| BR-01 | Braille layer present (ISO 19593) | 4 | E | Y | C |  |
| BR-02 | Braille dot diameter (Marburg Medium 1.3 mm) | 4 | M | Y | C |  |
| BR-03 | Braille dot spacing (intra-cell 2.5 mm) | 4 | M | Y | C |  |
| BR-04 | Braille line spacing (inter-cell 6.0 mm) | 4 | M | Y | C |  |
| BR-05 | Braille decode (translates to expected text) | 4 | H | Y | C | Pharma req |
| BR-06 | Braille language / alphabet | 4 | M | Y | C |  |
| BR-07 | Braille not on cut/fold | 4 | M | Y | C |  |
| BR-08 | Braille count (per pharma SKU) | 5 | M | Y | E |  |
| BR-09 | Braille overlaps print content | 4 | M | Y | C |  |

### 3.12 Barcodes & GS1 (B-01..B-28)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| B-01 | Barcode presence | 1 | E | N | B |  |
| B-02 | Barcode decoded | 2 | M | N | D |  |
| B-03 | Barcode value matches expected | 2 | M | N | D | MIS check |
| B-04 | Barcode quiet zone width | 2 | M | N | D | 7x or 10x rule |
| B-05 | Bar Width Reduction applied | 4 | M | N | C | Press-spec |
| B-06 | Barcode magnification factor | 4 | E | N | C |  |
| B-07 | Barcode X-dimension | 4 | E | N | C |  |
| B-08 | ISO 15416 grade (linear) | 4 | H | N | C |  |
| B-09 | ISO 15415 grade (2D) | 4 | H | N | C |  |
| B-10 | GS1 AI syntax inside GS1-128 / DataMatrix | 4 | M | N | C |  |
| B-11 | GS1 check digit valid | 2 | E | N | D |  |
| B-12 | Barcode rotation | 2 | E | N | D |  |
| B-13 | Barcode sheared/skewed | 2 | M | N | D |  |
| B-14 | Barcode scaled non-uniformly | 2 | M | N | D |  |
| B-15 | Barcode placed near fold | 4 | M | Y | A | UNCLAIMED |
| B-16 | Barcode placed near die / cut | 4 | M | Y | A | UNCLAIMED |
| B-17 | Barcode on non-printing layer | 4 | E | Y | A | Won't print |
| B-18 | Barcode color contrast | 2 | M | N | D |  |
| B-19 | Barcode in single ink (not built from process) | 2 | M | N | D |  |
| B-20..B-28 | Symbology detection primitives | 0 | E | N | 0 | EAN/UPC/ITF/Code128/Code39/QR/DataMatrix/PDF417/Aztec/Maxicode/DataBar |

### 3.13 Trapping & Registration (T-01..T-12)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| T-01 | Trapped flag set in PDF | 1 | E | N | B |  |
| T-02 | Trapping marks present in slug | 2 | M | N | D |  |
| T-03 | Reverse trap (color spread wrong dir) | 4 | H | N | C |  |
| T-04 | Trap width consistent | 4 | M | N | C |  |
| T-05 | Trap on wrong plate | 4 | H | N | C | UNCLAIMED read-only |
| T-06 | Registration marks present | 2 | E | N | D |  |
| T-07 | Registration marks outside trim | 2 | E | Y | D |  |
| T-08 | Registration marks rotated/wrong color | 2 | E | N | D |  |
| T-09 | Slug area / cropmark zone present | 2 | E | N | D |  |
| T-10 | Mark resolvability | 3 | M | Y | A |  |
| T-11 | Trap-free zone respected (over barcode) | 4 | M | N | C |  |
| T-12 | Trap interaction with white underprint | 4 | H | Y | C |  |

### 3.14 Substrate / Press / Production (S-01..S-18)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| S-01 | Min dot per substrate (flexo) | 4 | M | N | C |  |
| S-02 | Max dot / shadow break per substrate | 4 | M | N | C |  |
| S-03 | Ink limit per substrate | 4 | M | N | C |  |
| S-04 | Plate count vs press capability | 2 | E | N | D |  |
| S-05 | Common knife / common cut alignment | 4 | M | Y | C |  |
| S-06 | Grain direction tagged | 4 | M | N | C |  |
| S-07 | Press signature size match | 2 | M | N | D |  |
| S-08 | Step-and-repeat overlap | 3 | M | Y | A |  |
| S-09 | Step-and-repeat gutter < min | 3 | M | Y | A |  |
| S-10 | Output Intent matches target press | 2 | M | N | D |  |
| S-11 | CIP3/PPF data presence | 5 | M | N | E |  |
| S-12 | JDF / XJDF metadata presence | 5 | M | N | E |  |
| S-13 | Print method per separation tagged | 4 | M | N | C |  |
| S-14 | Anti-mixing customer tag (combo runs) | 5 | M | N | E |  |
| S-15 | File naming convention compliance | 1 | E | N | B |  |
| S-16 | Per-page ink coverage report | 2 | M | N | D |  |
| S-17 | Total ink consumption estimation | 2 | M | N | D |  |
| S-18 | Per-substrate ink-limit flag | 4 | M | N | C |  |

### 3.15 Variable Data (V-01..V-07)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| V-01 | PDF/VT conformance | 5 | M | N | E | Roll-up |
| V-02..V-07 | DPart hierarchy / DPM / encapsulation / repeating BG / overset / variable barcode | 5 | M | N | E |  |

### 3.16 Workflow / Job-Level (WF-01..WF-11)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| WF-01 | Filename matches MIS pattern | 1 | E | N | B |  |
| WF-02 | File size within limits | 1 | E | N | B |  |
| WF-03 | Page count == expected | 1 | E | N | B |  |
| WF-04 | Single vs multi-page expected | 2 | E | N | D |  |
| WF-05 | Run length appropriate (digital vs offset) | 5 | M | N | E |  |
| WF-06 | Output Intent matches job ticket | 2 | M | N | D |  |
| WF-07 | Page labels present / correct | 0 | E | N | 0 | Primitive |
| WF-08 | Color strategy declared in XMP | 2 | M | N | D |  |
| WF-09 | Customer brand profile applied | 2 | M | N | D |  |
| WF-10 | Job ticket attached (XJDF/JDF/JMF) | 5 | M | N | E |  |
| WF-11 | Certified PDF status / signatures | 5 | M | N | E |  |

### 3.17 Industry-Specific Regulatory (R-01..R-10)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| R-01 | Pharma min text size (e.g. 7 pt EU) | 5 | M | Y | E |  |
| R-02 | Pharma leaflet folding awareness | 5 | H | Y | E |  |
| R-03 | Wine/spirits gov-warning area | 5 | M | Y | E |  |
| R-04 | Cosmetics INCI min 1 mm type | 5 | M | N | E |  |
| R-05 | Tobacco warning area % calc | 5 | H | Y | E | UNCLAIMED |
| R-06 | Medical Device UDI presence | 5 | M | N | E |  |
| R-07 | EU Digital Product Passport QR validation | 5 | M | N | E | UNCLAIMED, emerging mandate |
| R-08 | Food-contact ink warning in metadata | 5 | E | N | E |  |
| R-09 | Allergen-label minimum size | 5 | M | N | E |  |
| R-10 | Lot / batch placeholder area present | 5 | M | Y | E |  |

### 3.18 ISO Standards (ISO-01..ISO-12)

| ID | Check | T | D | DL | W | Description |
|----|-------|--:|---|:--:|---|-------------|
| ISO-01 | PDF/X-1a conformance | 1 | E | N | B | Delegate to validator |
| ISO-02 | PDF/X-3 conformance | 2 | E | N | D |  |
| ISO-03 | PDF/X-4 conformance | 1 | E | N | B | GWG default |
| ISO-04 | PDF/X-5 conformance | 2 | E | N | D |  |
| ISO-05 | PDF/X-6 conformance | 2 | E | N | D |  |
| ISO-06 | PDF/A-1/2/3/4 conformance | 5 | E | N | E |  |
| ISO-07 | PDF/E conformance | 5 | E | N | E |  |
| ISO-08 | PDF/VT conformance | 5 | M | N | E |  |
| ISO-09 | PDF 2.0 base validity | 2 | E | N | D |  |
| ISO-10 | ISO 19593-1 conformance overall | 3 | M | Y | A |  |
| ISO-11 | GWG 2022 specification (relevant variant) | 1 | E | N | B |  |
| ISO-12 | ISO 15416 / 15415 barcode grading | 4 | H | N | C |  |

### 3.19 EPM Candidacy (EPM-A1..A8, EPM-B1..B6, EPM-C1..C8)

22 checks. See playbook §2.EPM for full detail.

**Hard disqualifiers (Tier A):**
- EPM-A1: Job has no color pages (100% B&W)
- EPM-A2: Unwanted spot color present (whitelist/blacklist)
- EPM-A3: Rich-black coverage exceeds page % threshold
- EPM-A4: Small black text / thin black lines below threshold
- EPM-A5: Maximum ink coverage exceeds EPM TAC
- EPM-A6: ΔE to EPM gamut exceeds threshold (Advanced)
- EPM-A7: ΔC (neutral gray deviation) exceeds threshold (Advanced)
- EPM-A8: PDF rendering / parse error

**Strong negative signals (Tier B):**
- EPM-B1: High % of pure-K pages (route to EPM+ instead)
- EPM-B2: Registration color ("All") in artwork (not marks)
- EPM-B3: Skin-tone heavy photography (>15% pixels) (Advanced)
- EPM-B4: Brand-critical PANTONE with K≥15% in alternate
- EPM-B5: Deep-shadow imagery (>50% area at L*<25) (Advanced)
- EPM-B6: RGB source with no output intent defined

**Soft signals (Tier C):**
- EPM-C1: Number of distinct K tints
- EPM-C2: Maximum K value
- EPM-C3: K-only page-area % in color pages
- EPM-C4: Neutral gray fills (C=M=Y)
- EPM-C5: Untagged objects (no color space)
- EPM-C6: PDF/X-4 non-compliant
- EPM-C7: Transparency flattening with K
- EPM-C8: OI mismatched to press ICC

---

## Section 4 — Tier-0 atomic primitives (84)

These are low-level predicates against the PDF object graph. Not user-facing. Compose all Tier 1–5 user-facing checks.

### 4.1 Object-class predicates
- `object.is_text` / `object.is_image` / `object.is_path` / `object.is_form_xobject` / `object.is_shading`
- `object.is_inline_image`
- `object.is_clipping_path`
- `object.is_pattern`

### 4.2 Color-space predicates
- `cs.is_DeviceCMYK` / `cs.is_DeviceRGB` / `cs.is_DeviceGray`
- `cs.is_CalRGB` / `cs.is_CalGray` / `cs.is_Lab`
- `cs.is_ICCBased`
- `cs.is_Separation` / `cs.is_DeviceN` / `cs.is_NChannel`
- `cs.is_Indexed` / `cs.is_Pattern` / `cs.is_Shading`
- `cs.alternate_space()`
- `cs.tint_transform_is_zero()`
- `cs.icc_profile_version()` (v2/v4)
- `cs.icc_profile_class()` (input/display/output)

### 4.3 Ink predicates
- `ink.name(spot)` / `ink.is_process()` / `ink.is_spot()`
- `ink.lab_value()` / `ink.alt_cmyk()` / `ink.alt_lab()`
- `ink.matches_library(Pantone, HKS, Roland, custom)`
- `ink.is_reserved_name()` (Cyan, All, None, Registration, Black)
- `ink.is_processing_step()` (per ISO 19593)
- `ink.processing_step_group()` / `ink.processing_step_type()`

### 4.4 Geometry / page-box predicates
- `box.media() / .crop() / .trim() / .bleed() / .art()`
- `box.contains(other_box)` / `box.equals(other_box)`
- `obj.bbox()` / `obj.intersects(box)` / `obj.outside(box)` / `obj.within(box, margin)`
- `path.is_closed()` / `path.self_intersects()` / `path.node_count()`
- `path.is_dashed()` / `path.dash_phase()` / `path.miter_limit()` / `path.line_cap()`
- `obj.ctm()` / `obj.rotation()` / `obj.scale_xy()` / `obj.is_mirrored()` / `obj.is_skewed()`

### 4.5 Stroke / fill predicates
- `obj.has_fill()` / `obj.has_stroke()`
- `obj.fill_color()` / `obj.stroke_color()`
- `stroke.width()` / `stroke.effective_width(ctm)`
- `obj.opacity()` (CA/ca)
- `obj.blend_mode()`

### 4.6 Transparency-stack predicates
- `obj.in_isolated_group()` / `obj.in_knockout_group()`
- `obj.has_smask()` / `smask.is_alpha()` / `smask.is_luminosity()`
- `page.transparency_group_present()` / `page.blending_color_space()`
- `extgstate.alpha()` / `extgstate.blend_mode()`

### 4.7 Text predicates
- `text.font_name()` / `text.font_subtype()` / `text.font_is_embedded()` / `text.font_is_subset()`
- `text.font_has_to_unicode()` / `text.font_to_unicode_complete()`
- `text.font_widths_consistent()`
- `text.glyph_uses_notdef()`
- `text.is_artificial_bold()` / `text.is_artificial_italic()` / `text.is_artificial_outline()`
- `text.rendering_mode()`
- `text.size_pt()` / `text.effective_size_pt(ctm)`
- `text.color_space()` / `text.is_white()` / `text.is_rich_black()`

### 4.8 Image predicates
- `image.color_space()` / `image.bit_depth()`
- `image.filter()` / `image.has_jpeg()` / `image.has_jpeg2000()` / `image.has_jbig2()`
- `image.dpi_native()` / `image.dpi_effective(ctm)`
- `image.has_icc_profile()` / `image.icc_matches_oi()`
- `image.has_alpha()` / `image.has_smask()`
- `image.is_inline()` / `image.is_linked_opi()`

### 4.9 Page / structure predicates
- `page.has_layers()` / `layer.is_empty()` / `layer.has_metadata_GTS()`
- `layer.processing_step_group()` / `layer.processing_step_type()`
- `page.has_transparency()` / `page.has_overprint()`
- `page.is_blank()` / `page.empty_separation(ink)`
- `page.user_unit()`

### 4.10 Document / metadata predicates
- `doc.pdf_version()`
- `doc.has_xmp()` / `doc.xmp_well_formed()` / `doc.xmp_has_namespace(ns)`
- `doc.info_dict_matches_xmp()`
- `doc.is_encrypted()` / `doc.permission(flag)`
- `doc.has_signatures()` / `doc.has_javascript()` / `doc.has_embedded_files()`
- `doc.has_xfa_forms()` / `doc.has_action_dicts()`
- `doc.has_post_eof_data()` / `doc.has_unused_objects()`
- `doc.trapped_flag()`
- `doc.output_intent()` / `doc.output_intent_icc()`

### 4.11 Barcode predicates (extension)
- `barcode.detect()` → list
- `barcode.symbology()` / `barcode.value()` / `barcode.x_dimension()` / `barcode.magnification()`
- `barcode.quiet_zone(left/right/top/bottom)`
- `barcode.iso_15416_grade()` / `barcode.iso_15415_grade()`
- `barcode.gs1_ai_parse()` / `barcode.gs1_check_digit()`
- `barcode.bbox()` / `barcode.rotation()`

**Total: 84 primitives.**

---

## Section 5 — Genuinely unclaimed checks (lintPDF wedge)

These checks have no clear incumbent doing them well in a read-only diagnostic mode. **They are the marketing-defensible differentiators.** Bold = highest-leverage.

| ID | Check | Why unclaimed |
|----|-------|---------------|
| **D-06** | Dieline z-order analysis | Esko enforces but doesn't *report*; lintPDF can show "your cut path is on top of the design" |
| **P-30/P-31** | Bleed-vs-dieline geometric verdict (per-side) | PS adds bleed; nobody *reports* per-side shortfall against an irregular die |
| **D-17** | Critical-content clearance from die (mm) | Brand-killer; lintPDF natural fit |
| D-20 | Multi-fold parallelism for tri-folds | Phoenix imposition only; not a preflight |
| D-19 | Fold-line direction tag (mountain/valley) | Not enforced anywhere but Esko Studio |
| **W-02/W-03/W-04** | White underprint coverage choke/spread | PKZ does it as fixup; lintPDF read-only verdict is unique |
| **W-07** | Missing-white-where-color-laid detection | Massive support-ticket reducer |
| **W-12** | Varnish/foil overlaps non-printable | Pkg specialty unclaimed |
| W-13 | Selective spot UV register-to-design | Geometric overlap |
| **B-15/B-16** | Barcode placed near fold/die clearance | No incumbent reports this |
| B-17 | Barcode on non-printing layer | Common error, no current alarm |
| BR-07 | Braille not on cut/fold | Pharma must-have |
| L-18 | Reserved ink on PS layer | ISO 19593 cleanup |
| L-21 | PS layer purity (also contains design) | Cleanup wedge |
| **T-05** | Trap-on-wrong-plate diagnostic (read-only) | AP+ traps but as fixup; diagnostic is novel |
| **R-05** | Tobacco / pharma % warning-area calc | Niche but high-margin |
| R-07 | DPP QR validation against EU spec | Emerging mandatory |
| W-16 | Embossing content vs design content geometric match | Nobody auto-reports |
| C-63 | Multi-PS-ink on same plate | ISO 19593 violation, unflagged |
| D-12/D-13 | Cut path closure / self-intersection verdict | AP+ mutates; lintPDF reports |
| **EPM-Core / Advanced / AI-Explain** |  | No read-only EPM candidacy preflight on the market |
| **BYO viewer-only mode** |  | No incumbent ingests pre-computed RIP data as preflight input |

---

## Section 6 — Wave assignment reference

### 6.1 Wave A — T3 Dieline Wedge (~24 checks, 3.5 EM)

`D-01, D-02, D-04, D-06, D-07, D-08, D-09, D-10, D-11, D-12, D-13, D-15, D-16, D-17, D-18, D-22, D-23, F-32, F-33, F-35, F-36, F-37, P-22, P-26, P-30, P-31, P-32, C-39, C-62, C-63, ISO-10, L-06, L-07, L-08, LA-18, LA-19, T-10, TR-22, S-08, S-09`

### 6.2 Wave B — T1 Catch-up (~12 checks, 1.0 EM)

`F-13, F-14, F-22, F-26, F-28, C-50, C-51, C-67, M-12, M-29, P-07, P-08, P-10, WF-01, WF-03, M-06, ISO-03, ISO-11`

### 6.3 Wave D — T2 Parity (~95 checks, 2.0 EM)

All Tier-2 entries not assigned to Wave A or B. Includes most font, color, image, transparency, line-art, metadata, page-geometry T2 items.

### 6.4 Wave C — T4 Packaging Specialty (~74 checks, 4.0 EM)

`L-09, L-10, L-14, L-15, L-17, L-18, L-19, L-20, L-21, W-01..W-15, BR-01..BR-07, BR-09, B-05..B-10, B-15, B-16, B-17, T-03, T-04, T-05, T-11, T-12, S-01..S-03, S-05, S-06, S-13, S-18, C-28, C-29, C-40, C-41, C-48, C-49, C-61, ISO-12`

### 6.5 Wave E — T5 Regulatory paid add-ons (~43 checks, 2.0 EM)

All Tier-5 entries: `R-01..R-10`, `V-01..V-07`, `S-11, S-12, S-14`, `WF-05, WF-10, WF-11`, `ISO-06, ISO-07, ISO-08`, `BR-08`, `D-19, D-20, P-29, W-16, L-16, L-17 (custom)`

### 6.6 Phase 2.EPM — EPM module (22 EPM checks, 2.5 EM)

`EPM-A1..EPM-A8` (hard disqualifiers), `EPM-B1..EPM-B6` (strong negative signals), `EPM-C1..EPM-C8` (soft signals). Plus the scoring algorithm, BYO schema integration, optional LLM explanation layer.

---

*End of v2 universe enumeration. 412 artifacts canonical. Read-only constraint applies throughout.*
