# T2-TRN05 — Transparency on spot page — DONE

`LPDF_TRANS_ON_SPOT` (advisory) fires once per page where Separation
/ DeviceN colour spaces are declared in resources and at least one
transparency event (alpha < 1.0 or non-Normal blend mode) was
captured. Some RIPs flatten transparency to process colour and
silently drop the spot.

Files:
- `packages/engine/src/lintpdf/analyzers/transparency.py` —
  `_check_transparency_on_spot()` + `_has_spot_color_resource()`.
- `packages/engine/tests/analyzers/test_batch10a.py` — 2 cases.
