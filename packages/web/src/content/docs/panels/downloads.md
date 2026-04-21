---
title: "Downloads"
description: "Desktop app, CLI, and SDK binaries."
section: "panels"
order: 15
---

# Downloads

**Path:** `/dashboard/downloads` · **Who:** Any signed-in tenant user

Binaries + packages we publish for offline use. All links resolve to versioned, signed artefacts on R2 — no third-party CDN.

## What you see

- **Desktop app** cards: macOS (universal), Windows (x64 installer), Linux (AppImage + .deb). Shows current version + release date.
- **CLI binaries** (`lintpdf` command-line): pre-built statically for macOS / Linux / Windows.
- **SDKs** — links to the Python, Node, Ruby, and Go packages on their respective registries (plus the canonical GitHub repo for each, **public** mirrors of our source packages).
- **Hot-folder daemon** — standalone binary for polling a local directory and submitting each new PDF to the engine.

## Actions

- **Download** — every button links to a signed URL good for 24 hours. No account magic needed beyond being logged in.
- **Copy install command** — for SDKs + CLI, the install one-liner is pre-formatted (`pip install lintpdf`, `npm install @lintpdf/sdk`, `brew install lintpdf/tap/cli`).

## Gotchas

- **Signed URLs expire in 24 hours.** Don't bake them into scripts — script against the SDK registry or the `lintpdf` homebrew tap instead.
- **Desktop auto-update** ships with the apps; the download card is for first-install. Existing installs pick up new versions on launch.
- **Code-signing**: macOS builds are notarised; Windows builds are EV-signed. Linux AppImages aren't signed — verify the SHA-256 sum shown next to the download.

## Related

- [Desktop app](../desktop-app) — feature overview + architecture
- [SDKs](../sdks) — per-language quickstarts
