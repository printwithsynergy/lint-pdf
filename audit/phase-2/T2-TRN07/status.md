# T2-TRN07 — Page-level transparency group knockout flag — DONE

Already covered by the existing `LPDF_TRANS_006` check in
`transparency.py`. The check fires when a page's transparency-
group dictionary has `/K=true`, which is exactly the
"knockout flag" T2-TRN07 calls out. Promoted partial → present
in the gap mapping; no new code required.

Files:
- `packages/engine/src/lintpdf/analyzers/transparency.py`
  (`LPDF_TRANS_006` — pre-existing).
