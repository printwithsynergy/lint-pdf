---
title: "Rulesets and profiles"
description: "Built-in profiles (GWG 2022, PDF/X-4, ECG, HP Indigo EPM, ISO 12647) and the JSON schema for authoring custom rulesets — enabled / disabled checks, severity overrides, and tunable thresholds."
group: "Reference"
order: 7
---

# Rulesets and profiles

A profile is a JSON document that names a check set, conformance
target, workflow assumption (`CMYK` vs `auto`), and threshold knobs
(min DPI, TAC limit, bleed, …). Submit a job with `profile_id=<id>`
and the engine resolves that profile from the catalogue, applies it
to every analyzer, and emits the resulting findings.

## Built-in catalogue

The engine ships 62 built-in profiles under
[`src/lintpdf/profiles/builtin/`](../src/lintpdf/profiles/builtin/).
They split into three families:

| Family            | Coverage                                     | Examples                                           |
|-------------------|----------------------------------------------|----------------------------------------------------|
| **GWG 2022**      | Sheetfed offset, digital, packaging, magazine, newspaper, large format | `gwg-2022-sheetfed-offset-coated`, `gwg-2022-packaging-folding-carton-offset`, `gwg-2022-magazine-glossy` |
| **LintPDF native**| Default / strict / advisory presets used by the hosted SaaS and self-hosters | `lintpdf-default`, `lintpdf-strict`, `lintpdf-advisory-only` |
| **Conformance**   | Industry-standard PDF and color targets      | `pdfx1a-magazine-ads`, `pdfx3-european`, `iso-12647-compliance`, `ecg-readiness`, `hp-indigo-epm` |

The catalogue resolver lives at
[`src/lintpdf/profiles/resolver.py`](../src/lintpdf/profiles/resolver.py);
the registry that loads and validates the JSON files lives at
[`src/lintpdf/profiles/registry.py`](../src/lintpdf/profiles/registry.py).

## Profile schema

Every profile JSON conforms to the schema enforced by
[`src/lintpdf/profiles/schema.py`](../src/lintpdf/profiles/schema.py).
The shape:

```json
{
  "name": "LintPDF Default",
  "description": "Comprehensive preflight with all engine checks, PDF/X-4 conformance, and AI analysis.",
  "version": "1.3",
  "conformance": "pdfx4",
  "workflow": "CMYK",
  "checks": {
    "enabled": ["LPDF_*", "PDFX4-*", "PDFX1A-*", "PDFA-*", "AI_*"],
    "disabled": ["LPDF_FONT_016", "LPDF_FONT_017"],
    "severity_overrides": {}
  },
  "thresholds": {
    "min_dpi": 150.0,
    "max_dpi": 600.0,
    "tac_limit": 300.0,
    "min_bleed_mm": 3.0
  }
}
```

Field reference:

- **`conformance`** — one of `pdfx4`, `pdfx3`, `pdfx1a`, or omitted /
  empty for "no conformance gate." Picks which conformance validators
  run.
- **`workflow`** — `CMYK` or `auto`. Drives color-space expectations
  (e.g., warn on RGB images in a `CMYK` workflow).
- **`checks.enabled`** — glob-style list of inspection IDs. `LPDF_*`
  matches every native LintPDF check; `PDFX4-*` matches every PDF/X-4
  conformance check; `AI_*` matches every AI-assisted check.
- **`checks.disabled`** — explicit deny list applied after `enabled`.
  Use this to opt out of specific checks within a wildcard match.
- **`checks.severity_overrides`** — `{ "LPDF_IMG_001": "info" }` to
  downgrade or upgrade individual findings.
- **`thresholds`** — numeric knobs read by analyzers. The keys above
  are illustrative; analyzers document which thresholds they consume
  in their manifests.

## Submitting with a profile

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -F "file=@artwork.pdf" \
  -F "profile_id=lintpdf-default"
```

If `profile_id` is omitted the engine falls back to `lintpdf-default`.

## Custom profiles

You can register your own profile JSON via `POST /api/v1/profiles` (or
seed it on disk and let the registry pick it up at boot). The schema
validator rejects unknown top-level keys and out-of-range thresholds,
so a malformed profile fails at load time rather than producing
silently wrong findings.

For analyzer-side details (how a check decides whether it's `enabled`
under a given profile, and how thresholds flow into
[`AnalyzerContext.config`](./plugin-api.md)), see
[Plugin API](./plugin-api.md).
