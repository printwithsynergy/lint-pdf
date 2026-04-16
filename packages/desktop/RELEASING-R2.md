# Releasing the Desktop App to R2

The GitHub Release flow (see [`RELEASING.md`](./RELEASING.md)) handles the
Tauri auto-updater path. In parallel, installers are uploaded to **Cloudflare R2**
under `desktop-releases/<version>/` so licensed tenants can download them from
the LintPDF dashboard at `/dashboard/downloads`.

Access is gated by the per-tenant entitlement `desktop_app_enabled`; a
super-admin toggles it in **Dashboard → Admin → Tenants** ("Desktop App"
column). Tenants without the flag see a "Contact sales" card instead.

---

## How downloads are served

```
R2 (private bucket: lintpdf-uploads)
  desktop-releases/
    latest.json                   # pointer: { version, manifest_key }
    <version>/
      manifest.json               # { version, released_at, notes_url, platforms }
      macos/<installer>.dmg
      windows/<installer>.msi
      linux/<installer>.AppImage
      linux/<installer>.deb
```

`/dashboard/downloads` calls the engine at
`GET /api/v1/admin/downloads/desktop/tenants/<tenant_id>/manifest`, which checks
the tenant's entitlement, reads `latest.json` + the pointed-at `manifest.json`,
then returns platform metadata with freshly **presigned 15-minute URLs**. The
bucket stays private; nothing is public.

---

## CI path (normal release)

The same `.github/workflows/desktop-release.yml` that cuts the GitHub Release
also uploads each platform's installer to R2, then a final `publish-manifest`
job composes the merged `manifest.json` and overwrites `latest.json`.

Required GitHub secrets:

| Secret                  | Value                                                                   |
| ----------------------- | ----------------------------------------------------------------------- |
| `R2_ENDPOINT_URL`       | `https://<account-id>.r2.cloudflarestorage.com`                         |
| `R2_ACCESS_KEY_ID`      | R2 API token with Object Read & Write on `lintpdf-uploads`              |
| `R2_SECRET_ACCESS_KEY`  | Secret for the token above                                              |
| `R2_BUCKET_NAME`        | _optional_ — defaults to `lintpdf-uploads`                              |

Issue a token under **Cloudflare → R2 → Manage API tokens**; scope it to the
bucket. The token used on Railway for the engine service (`LINTPDF_S3_*`) can
be reused.

---

## Manual path (local, from a Mac)

When the CI path can't be used (hot-fix, release from a non-tagged branch,
backfill an older version, etc.), the full compile-and-upload flow runs from
your laptop.

### Prerequisites

- Xcode Command Line Tools (`xcode-select --install`)
- Docker Desktop (running) — used for the Linux and Windows cross-compile
- `aws` CLI, `jq`, `pnpm`, `rustup`
  ```sh
  brew install awscli jq pnpm rustup
  brew install --cask docker
  ```

### Env setup

```sh
cp .env.desktop-release.example .env.desktop-release
# Fill in the blanks.
source .env.desktop-release
```

The example file documents every variable, including the Tauri signing key
and the (optional) Apple notarisation credentials.

### Run the script

```sh
# Compile all three platforms and upload to R2:
./scripts/desktop-release.sh 0.4.2

# Skip Windows (cargo-xwin is the most fragile step):
./scripts/desktop-release.sh 0.4.2 --skip-windows

# Compile only (don't touch R2):
./scripts/desktop-release.sh 0.4.2 --skip-upload

# Upload pre-built artifacts without rebuilding:
./scripts/desktop-release.sh 0.4.2 --skip-build

# Specific platform subset:
./scripts/desktop-release.sh 0.4.2 --platforms=macos
```

The script prints a summary of what landed in R2 plus short-lived presigned
URLs for smoke-testing each installer.

### Troubleshooting: `cargo-xwin` fails on Windows

Windows cross-compile from macOS via `cargo-xwin` is the most brittle step.
If the Docker build or the MSI packaging fails, the script prints a warning
and continues with the other platforms. To unblock the release, let CI build
Windows instead:

```sh
git tag desktop-v0.4.2
git push origin desktop-v0.4.2
```

CI builds on a real Windows runner, uploads the `.msi` to R2, and
re-publishes the manifest so the dashboard picks up the Windows slot.

---

## Rolling back (promote a prior version)

Artifacts for previous versions stay in R2 after a new release. To point the
dashboard back at an earlier one without re-uploading:

```sh
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: $LINTPDF_ADMIN_API_KEY" \
  -d '{"version":"0.4.1"}' \
  "$LINTPDF_API_URL/api/v1/admin/downloads/desktop/promote"
```

This overwrites `desktop-releases/latest.json` with a pointer to
`desktop-releases/0.4.1/manifest.json`. The dashboard will serve v0.4.1 on
the next load.

---

## Enabling a tenant

Super-admin only. In **Dashboard → Admin → Tenants**, find the tenant row
and tick the **Desktop App** checkbox. This sets
`entitlement_overrides.desktop_app_enabled = true` via the engine's
`PATCH /api/v1/admin/tenants/{id}/entitlements` endpoint.

Programmatic equivalent:

```sh
curl -sS -X PATCH \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: $LINTPDF_ADMIN_API_KEY" \
  -d '{"desktop_app_enabled": true}' \
  "$LINTPDF_API_URL/api/v1/admin/tenants/$TENANT_ID/entitlements"
```
