# T4-A01 — PDF/UA-1 Matterhorn verification

## What the check detects

Runs veraPDF's `PDFUA_1` profile (the Matterhorn Protocol test set)
and emits `LPDF_UA_CONF` when any Matterhorn checkpoint fails.

## Gating

Fires only when the active profile's `checks.enabled` includes
`LPDF_UA_*` (or equivalent pattern) AND `LPDF_UA_CONF` isn't in
`checks.disabled`. Most tenants won't have UA checks enabled — this
is an accessibility-first opt-in, not a default-on check.

When running a PDF/A-2u / 3u / 4 profile, tenants should also enable
LPDF_UA_* since PDF/A-compliant docs meant for archival often share
the accessibility-tagging requirements with UA.

## Output

Severity: warning (below error — non-compliant UA is less severe than
non-compliant PDF/A from a print-workflow perspective, but still
worth flagging).

`details.failures` carries the Matterhorn checkpoint list (e.g.
clause 01-003, 06-002, 14-002) so assistive-tech specialists can go
straight to the failing test instead of re-running veraPDF.

## Read-only

Confirmed. Same validate_with_verapdf path as T1-CMP01.

## Tests

`TestUaFinding::test_non_conformant_ua_fires_when_enabled` — fires on
failures when enabled_ua=True.

`TestUaFinding::test_ua_silent_when_not_enabled` — skips the veraPDF
call entirely when enabled_ua=False (saves latency for tenants not on
UA workflows).

`TestCombinedFlavours::test_pdfa_and_ua_together` — PDF/A + UA profile
invokes veraPDF twice, emits both LPDF_PDFA_CONF and LPDF_UA_CONF.
