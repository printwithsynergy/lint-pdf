# LintPDF Preflight Stress Test Results

- Tenant: `d92bce15-df0d-43f8-8d02-ba3a4dae999a` (throwaway)
- Profile: `lintpdf-default`   AI preset: `full-ai-scan`
- Source dir: `preflight-test-files`
- Count: **15**   Workers: 15   Clone factor: 1
- Wall clock: **180.8s** (2026-04-21T17:24:31+00:00 → 2026-04-21T17:27:31+00:00)
- Terminal: **0 complete** · 0 failed · 0 timed out · 15 never submitted

## Report links (click for manual audit)

| # | File | Duration | Findings (E/W/A) | Verdict | Viewer | HTML | PDF | JSON |
|---|---|---|---|---|---|---|---|---|
| 1 | `Amalgam_Catalyst_9_5x3_5.pdf` | 0.0s | — | ? | — | — | — | — |
| 2 | `Pavette_Pride_v99.pdf` | 0.0s | — | ? | — | — | — | — |
| 3 | `GFS0073-01_Nutrops10ctPouchLS030926.pdf` | 0.0s | — | ? | — | — | — | — |
| 4 | `GFS0073-01_Nutrops10ctPouchLS030926_OT.pdf` | 0.0s | — | ? | — | — | — | — |
| 5 | `GFS0080-01_Nutrops10ctPouchSF030926.pdf` | 0.0s | — | ? | — | — | — | — |
| 6 | `GFS0080-01_Nutrops10ctPouchSF030926_OT.pdf` | 0.0s | — | ? | — | — | — | — |
| 7 | `GFS0080-01_Nutrops10ctPouchSF030926.pdf` | 0.0s | — | ? | — | — | — | — |
| 8 | `GFS0080-01_Nutrops10ctPouchSF030926_OT.pdf` | 0.0s | — | ? | — | — | — | — |
| 9 | `AN-Energy_StickPack_CA_Pink-Slush_P2_OL.pdf` | 0.0s | — | ? | — | — | — | — |
| 10 | `AN_Energy_StickPack_CA_HSI_ADM_P1_OL.pdf` | 0.0s | — | ? | — | — | — | — |
| 11 | `PKG-DSP-STL-AC(10 Lane, Dieline 114511).pdf` | 0.0s | — | ? | — | — | — | — |
| 12 | `AN-Energy_StickPack_CA_Cherry-Twist_OUTLINED.pdf` | 0.0s | — | ? | — | — | — | — |
| 13 | `AN-Energy_StickPack_CA_Pink-Slush_OUTLINED.pdf` | 0.0s | — | ? | — | — | — | — |
| 14 | `AN_Energy_StickPack_CA_HSI_OUTLINED.pdf` | 0.0s | — | ? | — | — | — | — |
| 15 | `AN_Energy_StickPack_CA_Orange Kiss_OUTLINED.pdf` | 0.0s | — | ? | — | — | — | — |

## Bugs & Slowdowns

- `Amalgam_Catalyst_9_5x3_5.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}
- `Pavette_Pride_v99.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}
- `GFS0073-01_Nutrops10ctPouchLS030926.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}
- `GFS0073-01_Nutrops10ctPouchLS030926_OT.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}
- `GFS0080-01_Nutrops10ctPouchSF030926.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}
- `GFS0080-01_Nutrops10ctPouchSF030926_OT.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}
- `GFS0080-01_Nutrops10ctPouchSF030926.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}
- `GFS0080-01_Nutrops10ctPouchSF030926_OT.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}
- `AN-Energy_StickPack_CA_Pink-Slush_P2_OL.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}
- `AN_Energy_StickPack_CA_HSI_ADM_P1_OL.pdf` — 503: b'DNS cache overflow'
- `PKG-DSP-STL-AC(10 Lane, Dieline 114511).pdf` — 0: {'error': 'EOF occurred in violation of protocol (_ssl.c:2437)'}
- `AN-Energy_StickPack_CA_Cherry-Twist_OUTLINED.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}
- `AN-Energy_StickPack_CA_Pink-Slush_OUTLINED.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}
- `AN_Energy_StickPack_CA_HSI_OUTLINED.pdf` — 503: b'DNS cache overflow'
- `AN_Energy_StickPack_CA_Orange Kiss_OUTLINED.pdf` — -1: {'error': "TimeoutError('The read operation timed out')"}

## Scaling defects (prior-known caps that may have fired)

See `preflight-stress-metrics.csv` for queue-depth/worker-count time-series captured during the run. Cross-reference spikes with the known ceilings: Modal `max_containers=5`, Celery pool 20, Postgres `max_connections=100`.
