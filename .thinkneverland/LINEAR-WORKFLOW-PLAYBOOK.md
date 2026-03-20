# LINEAR-WORKFLOW-PLAYBOOK.md

# Per-repo behavioral contract for Cyrus and Claude Code.

# Lives at .thinkneverland/LINEAR-WORKFLOW-PLAYBOOK.md in every repo.

---

## CARD STATES (in order)

| State       | Meaning                |
| ----------- | ---------------------- |
| Backlog     | Not yet ready          |
| AI Ready    | Pick this up next      |
| In Progress | Actively working       |
| In Review   | PR open                |
| QA Ready    | Merged, needs human QA |
| Done        | Human confirmed        |
| Cancelled   | Abandoned              |

**Cyrus controls:** AI Ready → In Progress → In Review → QA Ready
**Human controls:** Backlog → AI Ready, QA Ready → Done, any → Cancelled

---

## CARD REQUIREMENTS

Before picking up a card:

1. Clear title
2. Acceptance Criteria (numbered, verifiable)
3. State: AI Ready
4. Team: GRD

---

## MODEL ROUTING (via Linear label)

| Label    | Model             | Use For                                          |
| -------- | ----------------- | ------------------------------------------------ |
| (none)   | claude-sonnet-4-6 | Default                                          |
| `sonnet` | claude-sonnet-4-6 | Explicit                                         |
| `opus`   | claude-opus-4-6   | Architecture, security, ContentStreamInterpreter |
| `haiku`  | claude-haiku-4-5  | Quick wins, doc updates                          |

---

## BRANCH NAMING

grd/<issue-number>-<short-slug>

Examples:
grd/GRD-001-parser-adapter
grd/GRD-015-font-analyzer
grd/GRD-042-celery-worker

---

## COMMIT FORMAT

type(scope): description

Types: feat | fix | chore | docs | refactor | test | style | perf | ci

Scopes: parser | semantic | analyzers | conformance | rules | profiles | reports | api | queue | tenants | webhooks | ci | deps

---

## SCOPE RULES

1. Read card title + ALL acceptance criteria
2. If >400 lines OR touches >3 unrelated areas: STOP, comment, set to Backlog
3. Only modify files within scope
4. Bugs outside scope: create new card, don't fix in this PR

### LintPDF-specific scope guidance

- Parser module (src/parser/) changes must NOT touch analyzer code
- Analyzer changes must NOT modify the SemanticModel dataclasses
- Rule functions must be pure — no imports from api/, queue/, or tenants/
- Ruleset JSON schema changes require updating both profiles/ and the JSON schema in docs/

---

## PR REQUIREMENTS

## Summary

<1-2 sentences>

## Changes

- <what changed and why>

## Testing

- <what you tested>
- <edge cases>
- <corpus files tested against (if applicable)>

## Checklist

- [ ] mypy src/ — zero errors
- [ ] ruff check src/ — zero errors
- [ ] pytest — passing
- [ ] pytest -m corpus — corpus regression passing (if touching analyzers/rules)
- [ ] New inspection IDs documented in INSPECTION-CATALOG.md

Closes GRD-###

---

## CARDS REQUIRING HUMAN QA

Labels: `api-endpoint`, `conformance`, `ruleset-schema`, `security`

After PR merge:

1. Comment: "PR #N merged. Needs human QA on staging. Setting to QA Ready."
2. Set to QA Ready
3. STOP — do not set to Done

---

## HUMAN-ONLY CARDS

If card has `human-only` label:

1. Comment: "This card is marked human-only."
2. Do NOT write code
3. Stop

---

## LINTPDF-SPECIFIC RULES

### Inspection ID assignment

- New checks MUST get an ID: GRD*{CATEGORY}*{NNN}
- Categories: FONT, IMG, COLOR, BOX, TRANS, OVER, COMP, STRUCT, GWG
- Check INSPECTION-CATALOG.md for next available number
- Never reuse retired IDs

### Test corpus

- New analyzer/rule PRs MUST include test against at least 3 corpus files
- Corpus lives in tests/corpus/ (gitignored, downloaded by CI)
- Reference corpus files by name in test docstrings

### Finding severity

- Only use: no-fly | delay | advisory
- Default severity comes from the rule; Rulesets can override
- no-fly = PDF is non-conformant (fails spec requirement)
- delay = warning (spec recommendation or best practice)
- advisory = informational (not a violation)

### ISO clause traceability

- Every rule function MUST include iso_clause in its docstring or metadata
- Format: "ISO 32000-2:2020 §X.Y.Z" or "ISO 15930-7:2010 §X.Y"

---

## SELF-HEALING CI (up to 3 rounds)

Open draft PR
→ Poll every 30s, max 15 min
→ Read failing check annotations from GitHub API
→ Fix real issues
→ Commit "fix: CI round N — <checks>"
→ Push → wait → repeat

Round 4: stay draft, add `needs-human-review` label,
comment on card: exact failures + what tried + what needed

Never:

- Delete or skip tests
- Suppress ruff/mypy errors without fixing
- Use # type: ignore without explanation
- Mark PR ready while checks fail

---

## STUCK CARD PROTOCOL

If you cannot complete a card:

1. Comment: what attempted, what blocking, what decision needed
2. Add label `needs-human-review`
3. Leave PR as draft
4. Set card state to Backlog

Always explain exactly what happened + what to do next.
