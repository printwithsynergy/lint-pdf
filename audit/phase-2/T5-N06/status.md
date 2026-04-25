# T5-N06 — UDI / EU DPP barcode content — DONE

Two checks emit when the barcode analyzer decodes a payload with
zxing-cpp and the content matches:

- `LPDF_BARCODE_UDI` (warning) — payload contains a GS1 GTIN
  (AI 01) but is missing required UDI elements per FDA 21 CFR 801
  / EU MDR 2017/745. Currently flags absence of the required AI
  set (AI 01) plus all of the recommended production AIs
  (17 / 10 / 21).
- `LPDF_BARCODE_EU_DPP` (warning) — payload is a URL targeting
  the EU Digital Product Passport (matches `dpp` /
  `digitalproductpassport` / `europa.eu/dpp`) but uses non-HTTPS
  or contains malformed whitespace.

Both validators are pure-python and silent on payloads that don't
match the relevant format.

Files:
- `packages/engine/src/lintpdf/analyzers/barcode_validation.py`
  (new module — also implements T5-N08).
- `packages/engine/src/lintpdf/analyzers/barcode.py` — invokes
  the validators inside `_decode_and_grade` after a successful
  zxing decode.
- `packages/engine/tests/analyzers/test_batch10b.py` — 5 cases
  covering UDI + EU DPP.
