---
title: "Service ownership contract"
description: "Ownership boundaries across loupe-pdf (display and visual inspection UX), lint-pdf (reporting, policy/rules, preflight workflow orchestration), and codex-pdf (extraction and normalized document intelligence)."
group: "Project"
order: 13
---

# Service Ownership Contract

This contract defines ownership boundaries across:

- `loupe-pdf`: display and visual inspection UX
- `lint-pdf`: reporting, policy/rules, preflight workflow orchestration
- `codex-pdf`: extraction and normalized document intelligence

## Lint ownership (this repo)

Lint owns policy and workflow semantics:

- rules/profile evaluation and pass-fail logic
- findings, reports, and customer-facing rule outcomes
- preflight workflow orchestration and execution lifecycle
- additive enrichment over upstream extraction signals when needed

Lint does **not** own:

- core extraction normalization from raw PDF internals
- viewer rendering and interaction UI concerns

## Cross-service boundaries

- Consume Codex extraction/summary outputs, then apply policy.
- Publish decisions and report semantics for UI/API consumers.
- Keep rendering in Loupe so display concerns stay reusable.

## Future offshoot rule

For new products (Forge, Trap, Impose, Marks, etc.), map each capability to one owner:

1. Display/inspection UX -> Loupe layer
2. Rules/reporting/workflow -> Lint layer
3. Extraction/normalized intelligence -> Codex layer

If a feature spans layers, split by contract. Avoid duplicated rule engines or extraction stacks in offshoot repos.
