# T4-A02 — PDF/A-1b..4 verification

## What the check detects

Runs veraPDF against the profile's declared PDF/A flavour and emits
`LPDF_PDFA_CONF` on non-conformance.

Supported flavours (veraPDF 1.26+):
- `PDFA_1_B` — pdfa1b
- `PDFA_2_B` — pdfa2b
- `PDFA_2_U` — pdfa2u
- `PDFA_3_B` — pdfa3b
- `PDFA_3_U` — pdfa3u
- `PDFA_4` — pdfa4

## Interaction with the existing PdfAValidator

The engine already has a built-in `PdfAValidator` (
`packages/engine/src/lintpdf/conformance/pdfa/*`). That validator
emits its own IDs. LPDF_PDFA_CONF is the veraPDF-backed
**augmentation** — it catches rules the built-in validator doesn't
implement (veraPDF is the reference implementation; ours is a subset).

Both checks coexist without conflict:
- Built-in: emits several per-rule IDs like LPDF_PDFA_COLOR_001.
- veraPDF: emits one summary finding with ≤25 failures in details.

## Read-only / Gating / Tests

Same shape as T1-CMP01. Tests at `TestPdfAFinding` (2 cases) plus the
map-completeness assertion.
