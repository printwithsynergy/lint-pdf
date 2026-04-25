# AI_CANN_001 / AI_CANN_002 — Cannabis labeling compliance

## What the checks detect

When the document is cannabis-product packaging, verify required
warning statements + symbols.

**Auto-detection** — fires when at least one of:

- A THC/CBD potency phrase: `\b\d+(\.\d+)?\s*mg\s*(THC|CBD)\b` (or
  reversed: `\b(THC|CBD)\s*\d+\s*mg\b`).
- An explicit cannabis term: `cannabis`, `marijuana`, `medical
  marijuana`, `recreational marijuana`, `THC`, `delta-9`, `delta-8`,
  `cannabidiol`, with at least one supporting context token
  (`%`, `mg`, `g`, `oz`, `infused`, `dispensary`, `licensed`).

Hemp-only / CBD-only products without THC mention skip cannabis
warnings (regulated as supplements in most US jurisdictions).

**AI_CANN_001 — Missing required cannabis warnings/symbols** (warning)

Required across nearly all US cannabis-legal states:

1. **"Keep out of reach of children"** statement (verbatim or
   regex-relaxed match).
2. **Cannabis warning symbol** declaration — text reference to a
   universal symbol (CA: "Universal Symbol"; CO: "THC"; OR/WA: triangle
   warning). Look for `universal symbol`, `cannabis symbol`,
   `THC stamp`.
3. **Potency declaration** (mg per serving + total mg) — required on
   edibles/extracts.
4. **State-specific operator/license phrase** — `licensed by`,
   `dispensary`, or `cultivated by` (presence indicates intent).

Aggregated: one AI_CANN_001 with `missing_elements` list.

**AI_CANN_002 — Potency/dosage formatting violations** (advisory)

When potency declared:

- Total mg should match servings × per-serving mg within ±10 %.
  Mismatch → finding.
- Per-serving mg ≤ 10 mg recommended in CO (`> 10mg per serving`
  → advisory).

## Detection

```py
thc_mg = list(_THC_PATTERN.finditer(text))
cbd_mg = list(_CBD_PATTERN.finditer(text))
is_cannabis = bool(thc_mg or _CANNABIS_KEYWORD_PATTERN.search(text))

if not is_cannabis:
    return []

missing = []
if not _KEEP_OUT_PATTERN.search(text):
    missing.append("keep_out_of_reach_of_children")
if not _SYMBOL_PATTERN.search(text):
    missing.append("cannabis_warning_symbol")
if not (thc_mg or cbd_mg):
    missing.append("potency_declaration")
```

## Output

```
Finding(
    inspection_id="AI_CANN_001",
    severity=Severity.WARNING,
    message="Cannabis label missing required elements: <list>",
    details={
        "missing_elements": ["keep_out_of_reach_of_children",
                             "cannabis_warning_symbol"],
        "thc_mentions": 3,
        "cbd_mentions": 0,
        "regulation": "Multi-state cannabis labeling (CA/CO/OR/WA/etc.)",
    },
)
```

## Read-only / category gating

Read-only. Universal warning-tier rule. Auto-skips when no cannabis
indicators detected — silent on non-cannabis files.
