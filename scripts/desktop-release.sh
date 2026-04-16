#!/usr/bin/env bash
# Compile the LintPDF desktop app (Tauri) for macOS + Linux + Windows from a
# macOS host, then upload the resulting installers to Cloudflare R2 under
# `desktop-releases/<version>/` so licensed tenants can download them from
# the dashboard.
#
# Linux builds use Docker (Dockerfile.linux). Windows builds use Docker +
# cargo-xwin (Dockerfile.windows) — experimental; if it fails, skip it
# with `--skip-windows` and let CI handle Windows.
#
# Required env (source .env.desktop-release):
#   R2_ENDPOINT_URL               https://<accountid>.r2.cloudflarestorage.com
#   R2_BUCKET_NAME                lintpdf-uploads
#   AWS_ACCESS_KEY_ID             R2 access key
#   AWS_SECRET_ACCESS_KEY         R2 secret key
#   AWS_DEFAULT_REGION            auto
#   TAURI_SIGNING_PRIVATE_KEY     Contents of ~/.tauri/lintpdf-updater.key
#   TAURI_SIGNING_PRIVATE_KEY_PASSWORD
#
# Optional env (macOS notarisation — skipped if unset):
#   APPLE_SIGNING_IDENTITY
#   APPLE_ID
#   APPLE_TEAM_ID
#   APPLE_PASSWORD                app-specific password
#
# Usage:
#   ./scripts/desktop-release.sh [VERSION] [--flags]
#
# Flags:
#   --platforms=macos,linux,windows   Comma-separated subset (default all).
#   --skip-windows                    Convenience — drop `windows`.
#   --skip-build                      Skip compile, upload existing artifacts.
#   --skip-upload                     Compile only, don't touch R2.
#   --dry-run                         Print what would run, don't execute.

set -euo pipefail

# ── Locations ────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DESKTOP_DIR="${REPO_ROOT}/packages/desktop"
BUNDLE_DIR="${DESKTOP_DIR}/src-tauri/target/release/bundle"
UNIVERSAL_BUNDLE_DIR="${DESKTOP_DIR}/src-tauri/target/universal-apple-darwin/release/bundle"
WINDOWS_BUNDLE_DIR="${DESKTOP_DIR}/src-tauri/target/x86_64-pc-windows-msvc/release/bundle"

# ── Logging helpers ──────────────────────────────────────────
log()  { printf '\033[1;34m[desktop-release]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[desktop-release][warn]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[desktop-release][err]\033[0m %s\n' "$*" >&2; }

# ── Args ─────────────────────────────────────────────────────
VERSION=""
PLATFORMS="macos,linux,windows"
SKIP_BUILD=0
SKIP_UPLOAD=0
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --platforms=*)   PLATFORMS="${arg#--platforms=}" ;;
    --skip-windows)  PLATFORMS="$(echo "$PLATFORMS" | sed 's/,windows//;s/^windows,//;s/^windows$//')" ;;
    --skip-build)    SKIP_BUILD=1 ;;
    --skip-upload)   SKIP_UPLOAD=1 ;;
    --dry-run)       DRY_RUN=1 ;;
    --help|-h)
      sed -n '2,/^$/p' "$0" | sed 's/^# //;s/^#//'
      exit 0
      ;;
    -*)
      err "Unknown flag: $arg"
      exit 2
      ;;
    *)
      if [[ -z "$VERSION" ]]; then
        VERSION="$arg"
      else
        err "Unexpected positional argument: $arg"
        exit 2
      fi
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  VERSION="$(node -p "require('${DESKTOP_DIR}/package.json').version" 2>/dev/null || true)"
fi
if [[ -z "$VERSION" ]]; then
  err "Could not determine version — pass it as the first arg or keep packages/desktop/package.json in place."
  exit 2
fi

want_platform() {
  local needle="$1"
  [[ ",${PLATFORMS}," == *",${needle},"* ]]
}

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '\033[1;36m[dry-run]\033[0m %s\n' "$*"
    return 0
  fi
  "$@"
}

# ── Preflight ────────────────────────────────────────────────
log "Release version: ${VERSION}"
log "Platforms: ${PLATFORMS:-<none>}"

missing_bins=()
for bin in aws jq shasum; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    missing_bins+=("$bin")
  fi
done
if [[ $SKIP_BUILD -eq 0 ]]; then
  for bin in pnpm; do
    if ! command -v "$bin" >/dev/null 2>&1; then
      missing_bins+=("$bin")
    fi
  done
  if want_platform macos && ! command -v rustup >/dev/null 2>&1; then
    missing_bins+=("rustup")
  fi
  if (want_platform linux || want_platform windows) && ! command -v docker >/dev/null 2>&1; then
    missing_bins+=("docker")
  fi
fi
if [[ ${#missing_bins[@]} -gt 0 ]]; then
  err "Missing required binaries: ${missing_bins[*]}"
  err "Install via: brew install awscli jq pnpm rustup && brew install --cask docker"
  exit 3
fi

if [[ $SKIP_UPLOAD -eq 0 ]]; then
  missing_env=()
  for var in R2_ENDPOINT_URL R2_BUCKET_NAME AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION; do
    if [[ -z "${!var:-}" ]]; then
      missing_env+=("$var")
    fi
  done
  if [[ ${#missing_env[@]} -gt 0 ]]; then
    err "Missing required env vars: ${missing_env[*]}"
    err "Copy .env.desktop-release.example to .env.desktop-release, fill it in, and \`source\` it."
    exit 4
  fi
fi

# ── Build phase ──────────────────────────────────────────────
declare -a BUILT_ARTIFACTS
declare -A PLATFORM_PATHS    # platform -> absolute file path

record_artifact() {
  local platform="$1"
  local path="$2"
  if [[ -f "$path" ]]; then
    PLATFORM_PATHS["$platform"]="$path"
    BUILT_ARTIFACTS+=("$platform:$path")
    log "Found ${platform} artifact: $(basename "$path")"
  else
    warn "${platform}: expected artifact not found at ${path}"
  fi
}

build_macos() {
  log "Building macOS universal bundle..."
  run rustup target add x86_64-apple-darwin aarch64-apple-darwin
  pushd "$DESKTOP_DIR" >/dev/null
  run pnpm install --ignore-workspace
  run pnpm tauri build --target universal-apple-darwin
  popd >/dev/null

  local dmg
  dmg="$(ls "${UNIVERSAL_BUNDLE_DIR}/dmg/"*.dmg 2>/dev/null | head -n1 || true)"
  record_artifact macos "$dmg"
}

build_linux() {
  log "Building Linux x86_64 bundle via Docker..."
  run docker build \
    -t lintpdf-desktop-linux-builder \
    -f "${DESKTOP_DIR}/docker/Dockerfile.linux" \
    "$REPO_ROOT"
  run docker run --rm \
    -v "${REPO_ROOT}:/workspace" \
    -v lintpdf-desktop-cargo-cache:/root/.cargo \
    -v lintpdf-desktop-linux-target:/workspace/packages/desktop/src-tauri/target \
    -e TAURI_SIGNING_PRIVATE_KEY \
    -e TAURI_SIGNING_PRIVATE_KEY_PASSWORD \
    -w /workspace/packages/desktop \
    lintpdf-desktop-linux-builder \
    bash -lc 'pnpm install --ignore-workspace && pnpm tauri build'

  local appimage deb
  appimage="$(ls "${BUNDLE_DIR}/appimage/"*.AppImage 2>/dev/null | head -n1 || true)"
  deb="$(ls "${BUNDLE_DIR}/deb/"*.deb 2>/dev/null | head -n1 || true)"
  record_artifact linux_appimage "$appimage"
  record_artifact linux_deb "$deb"
}

build_windows() {
  log "Building Windows x86_64 bundle via Docker + cargo-xwin (experimental)..."
  if ! run docker build \
      -t lintpdf-desktop-windows-builder \
      -f "${DESKTOP_DIR}/docker/Dockerfile.windows" \
      "$REPO_ROOT"; then
    warn "Windows builder image failed to build — skipping Windows."
    warn "Fall back to CI: \`git tag desktop-v${VERSION} && git push --tags\`."
    return 0
  fi
  if ! run docker run --rm \
      -v "${REPO_ROOT}:/workspace" \
      -v lintpdf-desktop-cargo-cache:/root/.cargo \
      -v lintpdf-desktop-windows-target:/workspace/packages/desktop/src-tauri/target \
      -v lintpdf-desktop-xwin-cache:/root/.xwin \
      -e TAURI_SIGNING_PRIVATE_KEY \
      -e TAURI_SIGNING_PRIVATE_KEY_PASSWORD \
      -e XWIN_CACHE_DIR=/root/.xwin \
      -w /workspace/packages/desktop \
      lintpdf-desktop-windows-builder \
      bash -lc 'pnpm install --ignore-workspace && pnpm tauri build --runner cargo-xwin --target x86_64-pc-windows-msvc'; then
    warn "Windows cross-compile failed — skipping."
    warn "Fall back to CI: \`git tag desktop-v${VERSION} && git push --tags\`."
    return 0
  fi

  local msi
  msi="$(ls "${WINDOWS_BUNDLE_DIR}/msi/"*.msi 2>/dev/null | head -n1 || true)"
  record_artifact windows "$msi"
}

if [[ $SKIP_BUILD -eq 0 ]]; then
  want_platform macos  && build_macos
  want_platform linux  && build_linux
  want_platform windows && build_windows
else
  log "Skipping build phase (--skip-build). Picking up existing artifacts..."
  want_platform macos && record_artifact macos "$(ls "${UNIVERSAL_BUNDLE_DIR}/dmg/"*.dmg 2>/dev/null | head -n1 || true)"
  if want_platform linux; then
    record_artifact linux_appimage "$(ls "${BUNDLE_DIR}/appimage/"*.AppImage 2>/dev/null | head -n1 || true)"
    record_artifact linux_deb      "$(ls "${BUNDLE_DIR}/deb/"*.deb         2>/dev/null | head -n1 || true)"
  fi
  want_platform windows && record_artifact windows "$(ls "${WINDOWS_BUNDLE_DIR}/msi/"*.msi 2>/dev/null | head -n1 || true)"
fi

if [[ ${#BUILT_ARTIFACTS[@]} -eq 0 ]]; then
  err "No artifacts to upload."
  exit 5
fi

# ── Upload phase ─────────────────────────────────────────────
if [[ $SKIP_UPLOAD -eq 1 ]]; then
  log "Skipping upload phase (--skip-upload). Built artifacts:"
  for entry in "${BUILT_ARTIFACTS[@]}"; do
    log "  - $entry"
  done
  exit 0
fi

# platform name → R2 sub-prefix
declare -A PLATFORM_PREFIX=(
  [macos]=macos
  [windows]=windows
  [linux_appimage]=linux
  [linux_deb]=linux
)

released_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
notes_url="https://github.com/thinkneverland/lint-pdf/releases/tag/desktop-v${VERSION}"

manifest_platforms='{}'

upload_one() {
  local platform="$1"
  local file="$2"
  local filename
  filename="$(basename "$file")"
  local subdir="${PLATFORM_PREFIX[$platform]}"
  local key="desktop-releases/${VERSION}/${subdir}/${filename}"

  local size sha
  size="$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file")"
  sha="$(shasum -a 256 "$file" | awk '{print $1}')"

  log "Uploading ${platform}: ${filename} (${size} bytes)"
  run aws s3 cp \
    --endpoint-url "$R2_ENDPOINT_URL" \
    "$file" \
    "s3://${R2_BUCKET_NAME}/${key}" \
    --only-show-errors

  # Append to manifest_platforms via jq
  manifest_platforms="$(jq \
    --arg p "$platform" \
    --arg fn "$filename" \
    --argjson size "$size" \
    --arg sha "$sha" \
    --arg key "$key" \
    '. + {($p): {filename: $fn, size: $size, sha256: $sha, key: $key}}' \
    <<<"$manifest_platforms")"
}

for entry in "${BUILT_ARTIFACTS[@]}"; do
  platform="${entry%%:*}"
  file="${entry#*:}"
  upload_one "$platform" "$file"
done

# Build the manifest JSON
manifest_json="$(jq -n \
  --arg version "$VERSION" \
  --arg released_at "$released_at" \
  --arg notes_url "$notes_url" \
  --argjson platforms "$manifest_platforms" \
  '{version: $version, released_at: $released_at, notes_url: $notes_url, platforms: $platforms}')"

manifest_key="desktop-releases/${VERSION}/manifest.json"
latest_key="desktop-releases/latest.json"
manifest_tmp="$(mktemp -t lintpdf-manifest.XXXXXX.json)"
trap 'rm -f "$manifest_tmp"' EXIT

printf '%s\n' "$manifest_json" > "$manifest_tmp"

log "Uploading manifest: ${manifest_key}"
run aws s3 cp \
  --endpoint-url "$R2_ENDPOINT_URL" \
  --content-type application/json \
  "$manifest_tmp" \
  "s3://${R2_BUCKET_NAME}/${manifest_key}" \
  --only-show-errors

latest_tmp="$(mktemp -t lintpdf-latest.XXXXXX.json)"
trap 'rm -f "$manifest_tmp" "$latest_tmp"' EXIT
jq -n \
  --arg version "$VERSION" \
  --arg manifest_key "$manifest_key" \
  '{version: $version, manifest_key: $manifest_key}' > "$latest_tmp"

log "Promoting latest.json → ${VERSION}"
run aws s3 cp \
  --endpoint-url "$R2_ENDPOINT_URL" \
  --content-type application/json \
  "$latest_tmp" \
  "s3://${R2_BUCKET_NAME}/${latest_key}" \
  --only-show-errors

# ── Summary ──────────────────────────────────────────────────
log "Done. Released v${VERSION}:"
jq -r '.platforms | to_entries[] | "  - \(.key): \(.value.filename) (\(.value.size) bytes, sha256 \(.value.sha256[0:12])…)"' <<<"$manifest_json"

log "Smoke-test presigned URLs (15 min expiry):"
jq -r '.platforms | to_entries[] | .value.key' <<<"$manifest_json" | while read -r key; do
  url="$(aws s3 presign --endpoint-url "$R2_ENDPOINT_URL" --expires-in 900 "s3://${R2_BUCKET_NAME}/${key}" 2>/dev/null || true)"
  if [[ -n "$url" ]]; then
    log "  ${key}"
    log "    ${url}"
  fi
done
