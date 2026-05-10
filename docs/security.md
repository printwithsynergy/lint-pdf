---
title: "Security"
description: "Vulnerability disclosure process, supported versions, the engine's security model (sandboxing, untrusted PDF handling, AGPL-aware reporting), and where to send a security report."
group: "Project"
order: 2
---

# Security

LintPDF processes untrusted PDF input from end-users. The engine
treats every input as adversarial and runs analyzers inside the
process boundary the operator chooses (single Python process,
forked workers, or container-isolated workers depending on
deployment topology).

This page documents how we handle vulnerability reports, which
versions receive security fixes, and the assumptions the engine
relies on at the trust boundary.

## Reporting a vulnerability

If you find a security issue in the LintPDF engine, the
codex-pdf rendering sidecar, or the loupe-pdf viewer, **do not
open a public GitHub issue**. Send the report to:

> **security@printwithsynergy.com**

Include:

- The affected version(s) (output of `lintpdf --version` or the
  Docker image tag).
- A minimal reproducer — ideally a sample PDF or a curl invocation
  against the HTTP API.
- The impact you observed (crash, RCE, info-leak, DoS, etc.).
- Any temporary mitigations you applied.

We acknowledge receipt within **2 business days** and aim for a
fix or a credible mitigation plan within **14 days** for
high-severity reports. Lower-severity reports follow the normal
release cadence.

PGP encryption is available on request — email and we'll send our
current public key.

## Disclosure policy

We follow coordinated disclosure:

1. You report → we acknowledge within 2 business days.
2. We confirm and triage; we share a draft advisory with you for
   review.
3. We ship a fix and bump the patch version. The hosted SaaS at
   lintpdf.com is upgraded first, then the OSS Docker image and
   Python package, then the GitHub release with the advisory.
4. We credit you in the advisory unless you ask us not to.

We do not currently run a paid bug bounty. If your finding leads
to a CVE, we coordinate with MITRE on assignment.

## Supported versions

| Version line | Status            | Security fixes |
| ------------ | ----------------- | -------------- |
| `0.x` (current) | Active development | Yes            |
| pre-`0.1`    | Unsupported       | No             |

Once a `1.0` lands, we'll move to a two-line LTS policy (current
major + previous major). Until then every fix targets the latest
release.

## Engine security model

### Trust boundary

The engine assumes the **HTTP front end** is the trust boundary.
Everything past `/v1/jobs` is treated as untrusted user input until
proven otherwise:

- Uploaded PDF bytes are scanned for malformed structure before
  any analyzer touches the parsed object tree.
- Analyzer plugins must declare their imports in their manifest;
  the **engine-purity tripwire** (see [Plugin API](/docs/plugin-api))
  fails plugins that import anything outside the allowed list.
- Worker processes don't share state across jobs by default;
  per-job temp directories are wiped on completion.
- The hosted SaaS additionally runs ClamAV in front of the engine;
  self-hosters can opt in by setting `CLAMAV_HOST` (see
  [Deployment](/docs/deployment)).

### Sandboxing

The OSS engine itself does **not** sandbox analyzer plugins beyond
the engine-purity tripwire. Operators that need stronger isolation
should run analyzer workers inside a process-isolated container
(the recommended Railway / Kubernetes topology in
[Deployment](/docs/deployment) does this).

### Network egress

Analyzers MUST NOT make outbound network calls. The engine-purity
tripwire policies this — any plugin that imports `requests`,
`httpx`, `urllib`, etc. fails to load. The only egress paths are
the operator-configured webhook destinations and the optional
external-AI tier (which calls a single configured upstream).

### Storage

Job inputs and outputs are stored under a configurable directory
(default `./reports/`). The engine does not encrypt files at rest —
that's the operator's responsibility (encrypted volumes, KMS-wrapped
S3 buckets, etc.). Job records carry a TTL and the engine GCs
expired payloads on a configurable schedule.

## Threat model — what we defend against

- **Malicious PDF inputs** — bombs, malformed structure, infinite
  recursion in object streams. The parser layer (pikepdf,
  PyMuPDF) is hardened against these; analyzers run on already-parsed
  objects. PDFs that fail the parser layer return a structured error,
  not a crash.
- **Plugin-supply-chain attacks** — see "engine-purity tripwire"
  above. Operators install plugins explicitly via the
  `lintpdf.plugins` entry point; auto-discovery from PyPI is
  disabled.
- **Webhook spoofing** — webhook payloads are signed with HMAC-SHA256
  using a per-tenant secret. Receivers should verify the signature
  before trusting the payload.

## Threat model — what we don't defend against

- **Compromised host OS / hypervisor** — out of scope. Operators
  are responsible for the underlying infrastructure.
- **Side-channel attacks across tenants on the same node** — the
  OSS engine is single-tenant by design. Multi-tenant operators
  should run a separate engine instance per tenant or rely on the
  hosted SaaS (which uses additional tenant-isolation controls
  not present in the OSS package).
- **Denial-of-service via resource exhaustion** — the engine
  enforces a configurable `MAX_FILE_BYTES` and per-job timeout,
  but a sufficiently large fleet of legitimate-looking jobs can
  saturate any operator's worker pool. Rate-limiting at the HTTP
  edge is the operator's responsibility.

## AGPL-aware reporting

If a vulnerability affects how the engine handles operator
configuration or webhook secrets — anything where a fix is in the
engine but the deployment also leaks state — the advisory will
call out both the upstream patch and the recommended operator
action (rotate the leaked secret, re-issue tenant tokens, etc.).

Modified forks subject to AGPL must publish their patches the
same way. If you're carrying out-of-tree security patches, please
also report them upstream so other operators can benefit.

## See also

- [Licensing](/docs/licensing) — AGPL terms that govern security
  patches in modified forks.
- [Deployment](/docs/deployment) — `CLAMAV_HOST`, network policies,
  per-job isolation in production topologies.
- [Plugin API](/docs/plugin-api) — engine-purity tripwire and
  plugin manifest rules.
