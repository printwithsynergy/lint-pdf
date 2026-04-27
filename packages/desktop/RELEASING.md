# Releasing the Desktop App

The desktop app (`packages/desktop`) ships via GitHub Releases, with
[`tauri-plugin-updater`](https://v2.tauri.app/plugin/updater/) handling
in-place updates for already-installed clients.

Releases are cut by pushing a `desktop-v*` tag. CI
([`.github/workflows/desktop-release.yml`](../../.github/workflows/desktop-release.yml))
builds macOS (universal), Windows, and Linux bundles and attaches them
to the Release along with the `latest.json` manifest the updater reads.

The same workflow also uploads the installers to **Cloudflare R2** so
that licensed tenants can download them from the in-app
`/dashboard/downloads` page. For the R2 setup, required secrets, and
how to run the upload manually from a dev machine, see
[`RELEASING-R2.md`](./RELEASING-R2.md).

---

## One-time signing-key setup

Before the first release, generate an updater keypair. Anyone with
publish access should do this **once** and store the outputs securely.

```sh
cd packages/desktop
pnpm tauri signer generate -- --write-keys ~/.tauri/lintpdf-updater.key
```

This produces two files:

| File                              | Purpose                    | Where it lives                                   |
| --------------------------------- | -------------------------- | ------------------------------------------------ |
| `lintpdf-updater.key`             | **Private** — signs builds | 1Password + GitHub secret `TAURI_SIGNING_PRIVATE_KEY` |
| `lintpdf-updater.key.pub`         | Public — verifies updates  | Checked into `src-tauri/tauri.conf.json`         |

Then:

1. Copy the contents of `lintpdf-updater.key.pub` into
   `src-tauri/tauri.conf.json` under `plugins.updater.pubkey`, replacing
   the `REPLACE_WITH_PUBLIC_KEY_FROM_TAURI_SIGNER` placeholder. Commit.
2. Add two repository secrets under **Settings → Secrets → Actions**:
   - `TAURI_SIGNING_PRIVATE_KEY` — full contents of `lintpdf-updater.key`
   - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` — the password you set when
     generating

Rotating the key orphans existing installs (they won't accept updates
signed by a new key). Treat it like any other production secret.

## Optional: macOS notarisation

Without these secrets, macOS builds still upload but ship ad-hoc
signed — Gatekeeper will show the unidentified-developer prompt on
first launch (right-click → Open to bypass). The CI workflow is fully
wired to notarize as soon as the six secrets below are populated; no
further workflow edits required.

Add these as repository secrets under **Settings → Secrets → Actions**:

- `APPLE_CERTIFICATE` — base64-encoded `.p12` Developer ID Application
  certificate. Generate via Keychain Access → export the cert as
  `.p12` → `base64 -i cert.p12 | pbcopy`.
- `APPLE_CERTIFICATE_PASSWORD` — the password set during `.p12` export
- `APPLE_SIGNING_IDENTITY` — e.g. `Developer ID Application: LintPDF
  (TEAMID)`. Find via `security find-identity -v -p codesigning`.
- `APPLE_ID` — the Apple ID used for notarisation
- `APPLE_TEAM_ID` — 10-character team ID from
  [developer.apple.com/account](https://developer.apple.com/account)
- `APPLE_PASSWORD` — an
  [app-specific password](https://support.apple.com/en-us/HT204397) (not
  your Apple ID password). Generate at
  [account.apple.com](https://account.apple.com/) → Sign-In and
  Security → App-Specific Passwords.

Once all six are set, tag the next `desktop-v*` release and verify on
the downloaded `.dmg`:

```sh
spctl -a -vv /Volumes/LintPDF\ Hot\ Folders/LintPDF\ Hot\ Folders.app
# Expect: "accepted" + "source=Notarized Developer ID"
```

If notarization fails mid-build, tauri-action surfaces the
`notarytool` log inline. Re-run the workflow after fixing creds —
the cert/password env vars are validated at the import step before
the build kicks off.

---

## Cutting a release

1. Make sure `main` (or whichever branch you release from) has every
   change you want to ship.
2. Bump the version in all three places so they stay in sync:
   - `packages/desktop/package.json` → `version`
   - `packages/desktop/src-tauri/Cargo.toml` → `[package] version`
   - `packages/desktop/src-tauri/tauri.conf.json` → `version`
3. Commit and push the bump.
4. Tag and push:
   ```sh
   git tag desktop-v0.2.0
   git push origin desktop-v0.2.0
   ```
5. Watch the **Desktop Release** workflow in GitHub Actions. When it
   finishes, the tagged release will contain:
   - `LintPDF-HotFolders_*_universal.dmg` (macOS)
   - `LintPDF-HotFolders_*_x64_en-US.msi` (Windows)
   - `LintPDF-HotFolders_*_amd64.AppImage` + `.deb` (Linux)
   - `latest.json` (updater manifest — **do not delete**)
6. On the first ever release, update the download table in
   `packages/web/src/content/docs/desktop-app.md` with the real file
   URLs produced by the release.

## Manual fallback — signing outside CI

If the Action fails and you need to sign locally:

```sh
cd packages/desktop
export TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.tauri/lintpdf-updater.key)"
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD="..."
pnpm tauri build
# bundles land in src-tauri/target/release/bundle/
# Signed .sig files sit alongside each artifact.
```

Upload the artifacts + `latest.json` manually to the GitHub Release
page.

## Verifying auto-update works

1. Install `desktop-v<N-1>` on a clean machine / VM.
2. Push `desktop-v<N>`.
3. Wait for CI to finish and the Release to appear.
4. Launch the installed app. Within a minute of startup the native
   "An update is available" dialog should appear. Approving it downloads
   the new bundle, verifies the signature against the baked-in pubkey,
   and relaunches.
