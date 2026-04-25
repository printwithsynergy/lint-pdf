# AI_COSM_001 / AI_COSM_002 — Cosmetics labeling compliance

## What the checks detect

When the document is a cosmetic-product label (auto-detected), verify
EU Cosmetics Regulation 1223/2009 + FDA 21 CFR 700-740 required
elements.

**Auto-detection** — fires when at least one of:

- An `INGREDIENTS:` / `INGRÉDIENTS:` / `INCI:` header followed by
  multiple INCI-style tokens (CAPS, often comma-separated).
- A PAO-symbol-related token: `12M`, `6M`, `3M`, `24M` followed by
  the keyword `month` or simply embedded in a panel labelled
  `period after opening`.
- A cosmetics product class keyword: `shampoo`, `conditioner`,
  `lotion`, `moisturiser`, `moisturizer`, `serum`, `cream`, `balm`,
  `mascara`, `lipstick`, `foundation`, `concealer`, `blush`,
  `eyeshadow`, `eyeliner`, `cleanser`, `toner`, `deodorant`,
  `antiperspirant`, `perfume`, `eau de toilette`, `eau de parfum`,
  `cologne`, with at least one ingredient-list token nearby.

If neither indicator is present, no findings emit.

**AI_COSM_001 — Missing required cosmetics labeling elements** (warning)

Required by EU 1223/2009 Article 19 + FDA 21 CFR 701:

1. **Ingredient list** — the INCI list itself (header + tokens).
2. **Net quantity** — weight (`g`, `oz`) or volume (`ml`, `fl oz`).
   Must be present in declared form.
3. **PAO symbol** — for non-shelf-stable products (lotions, creams,
   eye products) — text presence of `12M`, `6M` etc.
4. **Batch / lot code** — text reference to `Batch`, `Lot`, `LOT`
   followed by an alphanumeric identifier.
5. **Responsible person address** (EU only) — pattern `\b\d{4,5}\s+
   [A-Z][a-z]+\b` near a country/EU mention.

Aggregated AI_COSM_001 with `missing_elements` list.

**AI_COSM_002 — INCI nomenclature/ordering violations** (advisory)

When an ingredient list is detected:

1. Tokens > 1% by weight should appear in descending order. We can't
   verify weight from text alone, but we *can* flag pure violations:
   - First non-water token must be either `AQUA`, `WATER`, `EAU`,
     or absent. Cosmetic labels nearly always start with water — when
     the first token is `PARABEN` / `FRAGRANCE` / etc, that's a
     reorder violation.
2. Token format — INCI uses upper-case English/Latin nomenclature.
   When > 30 % of tokens contain lowercase letters, the list isn't
   following INCI conventions.

## Detection

```py
ingredient_match = _INGREDIENTS_HEADER.search(text)
class_match = _COSM_CLASS_PATTERN.search(text)
is_cosmetic = bool(ingredient_match or class_match)

if not is_cosmetic:
    return []

missing = []
if not ingredient_match:
    missing.append("ingredient_list")
if not _NET_QTY_PATTERN.search(text):
    missing.append("net_quantity")
if not _PAO_PATTERN.search(text):
    missing.append("pao_symbol")
if not _BATCH_PATTERN.search(text):
    missing.append("batch_code")
```

## Output

```
Finding(
    inspection_id="AI_COSM_001",
    severity=Severity.WARNING,
    message="Cosmetic label missing required elements: <list>",
    details={
        "missing_elements": ["pao_symbol", "batch_code"],
        "regulation": "EU 1223/2009 Article 19 / FDA 21 CFR 701",
    },
)
```

## Read-only / category gating

Read-only. Universal warning-tier rule. Auto-skips when no cosmetic
indicator detected — silent on non-cosmetic files.
