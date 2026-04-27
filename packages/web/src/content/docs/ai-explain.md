---
title: "AI-Explain"
description: "Generate human-readable explanations for preflight findings via Claude Haiku 4.5, with built-in cost-cap protection."
section: "ai"
order: 90
---

# AI-Explain

AI-Explain turns a terse preflight finding (e.g. *"LPDF_FONT_001 — Helvetica is not embedded"*) into a human-readable sentence your operators and customers can act on. It uses Claude Haiku 4.5 under the hood, caches every result on the finding row, and is gated by a per-tenant monthly cost cap so the line item is predictable.

## Endpoint

```
POST /api/v1/jobs/{job_id}/findings/{finding_id}/explain
Authorization: Bearer lpdf_live_...
```

The response body:

```json
{
  "finding_id": "xyz",
  "explanation": "This font is not embedded; the press will substitute Helvetica.",
  "model": "claude-haiku-4-5",
  "cached": false,
  "cost_cents": 0.04
}
```

`cached: true` means the engine already had a cached explanation for this finding and skipped the API call. Cached responses are free.

## Where it shows up

- **Dashboard preflight report** (`/dashboard/preflight/{jobId}/report`) — every finding card shows an **✦ Explain** button. Clicking it makes the call and renders the result inline. Subsequent visits to the page show the cached explanation immediately.
- **Reports** — every HTML, PDF, and JSON report renderer hydrates the cached explanation onto each finding card before rendering. If a report was generated *before* an explanation was created, regenerate the report (or the next render will pick it up automatically).
- **Desktop + SDK + plugin** — all four consumers expose `explainFinding(jobId, findingId)` that hits the same endpoint and returns the same shape.

## Cost-cap behavior (Q-C5)

A monthly per-tenant LLM cost cap protects you from runaway spend. When the cap is exhausted:

```
HTTP/1.1 402 Payment Required
Content-Type: application/json

{
  "detail": "Cost cap exceeded — raise the cap in Account → Billing.",
  "used_cents": 9987,
  "monthly_cap_cents": 10000
}
```

- Preflight + reports + analyzers **keep working**. Only LLM features pause.
- The dashboard surfaces a "raise the cap" CTA inline on the finding row.
- Cached explanations remain available — only fresh calls return 402.
- The cap resets at the start of each calendar month.

Configure the cap on **Account → Billing → AI Credits**. Three knobs:

- **Enabled** — turn the cap on/off (off = unlimited).
- **Monthly cap (cents)** — hard ceiling per calendar month.
- **Alert threshold (%)** — emit a webhook + dashboard banner when usage crosses this percentage.

## Live-AI verification (release-tag time)

The smoke test stubs Claude so it runs offline + free in CI. Before tagging a release, run the optional **live-AI** verification path:

```bash
# via the make target
cd packages/engine && make smoke-live-ai

# or directly
uv run --package engine pytest -m live_ai
```

This requires `ANTHROPIC_API_KEY` and costs ~$0.01 per run. It exercises the real Claude path against a 2-finding fixture and confirms:

- The fresh API call returns a non-empty explanation.
- The explanation is cached on `JobFinding.ai_explanation` / `_model` / `_at`.
- The second call short-circuits to the cache (no new spend).

If the live-AI test fails after a passing smoke run, an upstream change broke the Claude path — investigate before shipping the release tag.

The `live_ai` marker is registered in `packages/engine/pyproject.toml` so the test is **only** collected when you pass `-m live_ai`. Default `pytest` runs skip it entirely.

## Why Haiku 4.5

Haiku 4.5 is the right size for a per-finding explanation — fast (~500ms p50), cheap (~$0.04 per call), and good enough at the writing task that operators don't need to edit the output. Opus and Sonnet would be overkill; the explanation is short and the input is highly structured.
