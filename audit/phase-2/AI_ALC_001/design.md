# AI_ALC_001 / AI_ALC_002 — Alcohol labeling compliance

## What the checks detect

When the document is an alcoholic-beverage label (auto-detected),
verify required TTB / EU elements are present.

**Auto-detection** — the analyzer fires only when at least one of:

- An ABV pattern: `\d{1,2}(\.\d+)?\s*%\s*(ALC|ABV|VOL|ALC/VOL|ALC\.?\s*BY\s*VOL)`.
- An alcohol-class keyword in the page text: `beer`, `ale`, `lager`,
  `stout`, `porter`, `wine`, `champagne`, `prosecco`, `cava`, `cider`,
  `mead`, `sake`, `vodka`, `gin`, `rum`, `tequila`, `mezcal`, `whisky`,
  `whiskey`, `bourbon`, `scotch`, `cognac`, `brandy`, `liqueur`,
  `vermouth`, `absinthe`.

If neither is present, no findings emit (silent on non-alcohol files).

**AI_ALC_001 — Missing required alcohol labeling elements** (severity warning)

When the document looks like an alcohol label, verify:

1. **ABV declaration** present (per TTB 27 CFR 4.36 / 5.37 / 7.71 and
   EU Regulation 1169/2011 Article 9). Missing → finding.
2. **TTB Government Warning** (27 CFR 16.21) — required for US alcohol
   labels. Look for phrase `GOVERNMENT WARNING` (case-insensitive).
   When absent on a TTB-jurisdiction product, emit finding.
3. **Country of origin / "Product of"** (TTB COLA, EU labelling
   regulations). Look for `Product of`, `Imported from`, `Made in`.
   When absent, emit finding (advisory severity downgrade per locale).

A single AI_ALC_001 finding aggregates all missing elements via a
`missing_elements` list in details (not three separate findings —
keeps finding count manageable on labels missing multiple elements).

**AI_ALC_002 — Format violations** (severity advisory)

When ABV is detected, verify it follows TTB format:

- Format: `X% ALC/VOL` or `X% ABV` (TTB 27 CFR 4.36 prefers the former).
- Number range plausible (0.5%–95% — outside this is a typo).
- Decimal precision ≤ 1 place (e.g. `5.5%` ok; `5.55%` flagged).

## Detection

```py
abv_match = _ABV_PATTERN.search(text)
class_match = _ALC_CLASS_PATTERN.search(text)
is_alcohol = bool(abv_match or class_match)

if not is_alcohol:
    return []

missing: list[str] = []
if not abv_match:
    missing.append("abv_declaration")
if not _GOV_WARNING_PATTERN.search(text):
    missing.append("ttb_government_warning")
if not _ORIGIN_PATTERN.search(text):
    missing.append("country_of_origin")
```

## Output

```
Finding(
    inspection_id="AI_ALC_001",
    severity=Severity.WARNING,
    message="Alcohol label is missing required elements: <list>",
    details={
        "missing_elements": ["ttb_government_warning", "country_of_origin"],
        "detected_class": "wine",
        "abv_pct": 13.5,
        "regulation": "TTB 27 CFR 4.36 / 16.21",
    },
)
```

## Read-only / category gating

Read-only. Universal warning-tier rule. Skips when neither ABV nor
alcohol-class keywords detected — no false positives on non-alcohol
labels.
