# Preflight accuracy scoreboard

One row per tightening commit. Numbers are measured by
`scripts/replay_audit_dataset.py` against the committed
2026-04-23 Opus verdicts in `docs/audits/raw/*.json`.

| date (UTC) | sha | label | rules touched | baseline findings | baseline disputed | fresh findings | fresh disputed | disputed Δ | regressions |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 2026-04-23 15:45 | `3d8b284` | 2026-04-23 baseline | — | 3946 | 86 | 3946 | 86 | +0 | 0 |
