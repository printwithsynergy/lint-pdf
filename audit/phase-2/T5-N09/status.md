# T5-N09 — Digimarc / anti-counterfeit watermark hint — DONE

`LPDF_DIGIMARC_HINT` (advisory) fires when XMP metadata contains
a Digimarc namespace token or `digimarc.com` URL. The check is
intentionally **best-effort**: actual Digimarc watermark detection
requires the licensed Digimarc Discover SDK, which the engine
does not bundle. The advisory tells operators a Digimarc watermark
*may* be present; the watermark itself can only be verified
through Digimarc's tooling.

The check carries the matching hint tokens in
`details.hints` so the operator can investigate.

Files:
- `packages/engine/src/lintpdf/analyzers/metadata.py` —
  `_check_digimarc_hint()`.
- `packages/engine/tests/analyzers/test_batch10b.py` — 2 cases.

## Out of scope

Real Digimarc watermark detection is gated on a paid Digimarc
licence. We document the metadata heuristic as the closest
read-only signal lintPDF can produce.
