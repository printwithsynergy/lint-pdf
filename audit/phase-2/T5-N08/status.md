# T5-N08 — GS1 AI syntax inside GS1-128 / DataMatrix / QR — DONE

`LPDF_BARCODE_GS1_AI` (warning) fires when a decoded barcode
payload looks like a GS1 element string (starts with AI 01 or
contains FNC1 separators) and one or more AIs fail their
expected syntax (length / character set / unknown AI code).

The schema covers ~20 of the most-used GS1 AIs (GTIN, dates,
lot/serial, weights, URL AIs 8200-8202). Each AI has a regex +
fixed-or-variable length spec; the walker iterates the payload
and records `(ai, value, error)` triples.

Pure-python, no external dependencies. Silent on non-GS1 payloads.

Files:
- `packages/engine/src/lintpdf/analyzers/barcode_validation.py`
  — `GS1_AI_SCHEMA`, `validate_gs1_ai_payload`.
- `packages/engine/src/lintpdf/analyzers/barcode.py` — invokes
  the validator on every decoded payload.
- `packages/engine/tests/analyzers/test_batch10b.py` — 4 cases.
