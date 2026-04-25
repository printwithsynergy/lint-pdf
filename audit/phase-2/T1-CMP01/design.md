# T1-CMP01 — PDF/X conformance verify (X-1a..X-6)

## What the check detects

Runs veraPDF against the profile's declared PDF/X flavour and emits a
stable finding (`LPDF_PDFX_CONF`) when veraPDF reports any failures.

Supported veraPDF profiles (per veraPDF 1.26+):
- `PDFX_1A` — covers `pdfx1a` and `pdfx1a2003`
- `PDFX_3` — covers `pdfx3` and `pdfx32003`
- `PDFX_4` — covers `pdfx4` and `pdfx6` (X-6 builds on X-4)
- `PDFX_4P` — covers `pdfx4p`
- `PDFX_5` — covers `pdfx5`

## Input / Output

Gated by `PreflightProfile.conformance` — the check runs only when
that field is in the PDF/X family. Silent otherwise.

`LPDF_PDFX_CONF` emits once per document with severity=error.
`details.failures` carries up to 25 deduped rule summaries
`{clause, test_number, description, failed_checks}` so tenants see
the exact veraPDF clauses without needing the raw XML report.

## Sidecar behaviour

veraPDF is already deployed as `railway.verapdf.toml`. The existing
`verapdf_client.py` handles wake-from-sleep, timeouts, connect errors.
All failure paths silently no-op — `run_verapdf_checks()` never blocks
the preflight run on veraPDF unavailability.

## Read-only

Confirmed. `validate_with_verapdf()` uploads bytes to the sidecar for
validation and parses the JSON response. No writes back to the PDF
from either lintPDF or veraPDF (veraPDF is a validator, not a fixer
— the existing engine already uses it that way).

## Verification

`tests/conformance/test_verapdf_runner.py::TestPdfXFinding` — 2 cases:
non-conformant fires with correct details; compliant is silent.

Plus the shared map tests (`TestConformanceMaps::test_pdfx_family_complete`)
assert every `pdfx*` conformance value the engine recognises maps to a
veraPDF profile.
