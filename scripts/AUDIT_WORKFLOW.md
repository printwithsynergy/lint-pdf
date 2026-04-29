# Engine audit workflow

Two scripts, two purposes. Use the right one.

## `scripts/audit-engine.py` — routine internal audit

**When**: after every engine PR, before push. Cost: $0, ~2 minutes.

```sh
python3 scripts/audit-engine.py
```

What it does:
- Runs the local engine against the 12 baseline fixtures
- Diffs current findings against `packages/engine/tests/fixtures/expected_findings_baseline.json`
- Reports **regressions** (lost check IDs), **new findings** (added coverage), and **count drift** per fixture
- Exit code `1` on regressions, `0` on clean / improvements

Output is human-readable per fixture + a detail section listing exactly which check IDs gained/lost coverage.

## Updating the baseline

After a batch of intentional engine improvements (and ideally an Opus
sign-off — see below), rebase the baseline:

```sh
python3 scripts/audit-engine.py --update-baseline
```

Commit the updated `expected_findings_baseline.json` so the regression
guard tracks the new floor.

## `scripts/audit-opus.py` — discovery audit

**When**: occasional. Cost: ~$10 + ~10 minutes per run.

```sh
ANTHROPIC_API_KEY=$CLAUDE_API_TOKEN python3 scripts/audit-opus.py /tmp/smoke-batch-<ts>
```

Use cases:
- Release-time sign-off on a batch of engine changes
- Discovering NEW miss categories the engine doesn't yet catch
- Re-baselining once major engine improvements land

Don't run per-PR — the cost adds up and Opus's per-run variance creates noise. The internal audit catches regressions cheaply; Opus is for finding gaps.

## Baseline provenance

The current baseline (`expected_findings_baseline.json`) was captured 2026-04-29 from `/tmp/smoke-batch-1777483978/` after PRs S–HH merged to main. Last Opus audit at `/tmp/audit-opus-1777484*` showed: 1423 findings, 88.2% agree, 0.8% disagree, 53 misses.
