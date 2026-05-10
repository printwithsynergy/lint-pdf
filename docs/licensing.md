---
title: "Licensing"
description: "AGPL-3.0+ terms for the LintPDF OSS engine, what self-hosting and modification mean in practice, and how to obtain a commercial license for proprietary or embedded use."
group: "Project"
order: 1
---

# Licensing

LintPDF is licensed under the
[GNU Affero General Public License v3.0 or later](https://github.com/printwithsynergy/lint-pdf/blob/main/LICENSE)
(AGPL-3.0+). The full license text lives at the repository root.

Copyright © 2024–2026 Think Neverland LLC.

## What that means in practice

### Self-hosting

You can self-host LintPDF for any use — commercial or otherwise — at no
charge, with no per-tenant cap and no notify-us clause. Run the engine on
your own infrastructure and ship reports to your customers. Pull builds
from the public registry, edit configuration, deploy across as many
nodes as you need.

### Modifications

If you modify the engine, your modifications must be made available
under the same AGPL-3.0+ license to anyone who interacts with your
modified version — **including over a network**. That's the "A" in
AGPL: the network-use trigger. If you patch LintPDF and operate the
result as a hosted service, your patches are AGPL too. There's no
"private SaaS" loophole.

In practice that means: if you fork, you publish your fork. The
threshold is interaction over a network, not just redistribution of
binaries.

### What counts as "interacting over a network"

Anyone who can submit a job to your modified engine and receive a
report has interacted with it over a network. That includes:

- End-users using your hosted product.
- Backend services calling your modified engine via HTTP / RPC.
- Browser clients receiving rendered reports from your modified engine.

It does **not** include:

- Internal CI runs that don't expose the engine to anyone outside
  your build infrastructure.
- Local-only test harnesses.

If you're unsure where the line falls for your deployment, ask before
shipping.

## Commercial license

If you need to embed LintPDF inside a proprietary product, distribute
modifications without disclosing them, or bundle the engine with
software under an incompatible license, contact Think Neverland LLC
about a commercial license.

The hosted SaaS at [lintpdf.com](https://lintpdf.com) runs under such
an arrangement with itself — the engine code is identical to this OSS
release, but the hosted operator holds a commercial license that
relaxes the AGPL distribution clauses for the SaaS multi-tenant
layers (billing, admin console, white-label reports).

To request a commercial license, email
[hello@printwithsynergy.com](mailto:hello@printwithsynergy.com) with:

- Intended use case (embedded, OEM, hosted, on-premise).
- Expected scale (per-month preflight volume, number of tenants).
- Whether you need indemnification, SLAs, or priority support.

## Third-party components

LintPDF depends on a number of permissively-licensed third-party
libraries (BSD, MIT, Apache-2.0, MPL-2.0). The full attribution list
is generated at build time via `pip-licenses`; see the project's CI
artifacts for the per-release inventory.

A handful of optional integrations have stricter requirements:

- **VeraPDF** (`Dockerfile.verapdf`) is dual-licensed under MPL-2.0
  and GPL-3.0. When LintPDF embeds VeraPDF for PDF/A conformance,
  the GPL-3.0 obligations apply to that container image — see the
  VeraPDF project for redistribution terms.
- **Ghostscript** (used by codex-pdf, the rendering sidecar) is
  AGPL-3.0; the same self-hosting / modification rules apply.

## Trademark

"LintPDF" is a trademark of Think Neverland LLC. The AGPL covers
copyright, not trademark. You can run, modify, and redistribute the
software, but you can't pass off your fork as the official LintPDF
product without a separate trademark license.

## Questions

For licensing questions that aren't answered here, email
[hello@printwithsynergy.com](mailto:hello@printwithsynergy.com).
For day-to-day OSS questions (how to self-host, how to extend, how
to contribute), use the GitHub Discussions or Issues on the
repository — those don't need a commercial conversation.
