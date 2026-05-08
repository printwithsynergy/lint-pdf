---
trigger: always_on
description: "Service ownership boundary: Lint rules, Codex extraction, Loupe display"
---

# Service Ownership Boundary

- Lint owns policy/rule evaluation, reporting, and preflight workflow semantics.
- Codex owns extraction and normalized reusable data signals.
- Loupe owns rendering and visual inspection UX.
- Do not move viewer concerns into this repo; do not fork extraction logic without a clear additive contract need.
- New offshoots (Forge, Trap, Impose, Marks, etc.) must map capabilities to one owner layer.
