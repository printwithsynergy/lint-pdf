# lint-pdf — STOP-Gate Approvals (mirror)

Authoritative source: `/Users/macadmin/synergy-agents/approvals.md`. This
file mirrors the entries that affect `lint-pdf` for in-repo discoverability.

## Entries

### Parity-corpus baseline (criterion 4)
- gate: Parity-corpus baseline (lint-pdf criterion 4)
- decision: Approved
- date: 2026-05-07T15:08:00Z
- source: Quincy authorization in Multi-Agent Cutover Prompt — "Treat user approvals received in chat as Quincy-authoritative for STOP-gates."
- evidence: `reports/parity/criterion4_corpus_baseline.json`, `reports/parity/criterion4_corpus_report.json`, `reports/parity/criterion4_corpus_report.diff.json`, `reports/parity/parser_surface_audit.json`

### Codex contract changes (additive analysis side-channel)
- gate: Codex contract changes (additive analysis side-channel)
- decision: Approved
- date: 2026-05-07T00:00:00Z
- source: Quincy authorization + QUESTIONABLE-DECISIONS.md 2026-05-07 codex analysis side-channel for dieline parity
- evidence: lint-pdf migrated analyzers (`dieline.py`, `dieline_quality.py`, `spot_name_normaliser.py`) consume `lintpdf.codex_adapter`; `tests/criterion4_parity_validation.json`
