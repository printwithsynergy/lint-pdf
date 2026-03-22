# LintPDF Desktop Hot Folder App — Implementation Plan

## Overview

A Tauri-based cross-platform desktop app that lets users configure and manage
multiple hot folders for automated PDF preflight via the LintPDF API. Runs as a
system tray background service with a configuration UI.

**Framework:** Tauri v2 (Rust + React/Tailwind)
**Platforms:** Linux, macOS, Windows
**Package location:** `packages/desktop/`

---

## Architecture

```
┌──────────────────────────────────────────────┐
│              Tauri Desktop App                │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │     React/Tailwind Frontend          │    │
│  │  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │ Folder   │  │ Results Feed     │  │    │
│  │  │ Config   │  │ (live job table) │  │    │
│  │  │ Panel    │  │                  │  │    │
│  │  └──────────┘  └──────────────────┘  │    │
│  └──────────────────────────────────────┘    │
│                    ↕ IPC (invoke/events)      │
│  ┌──────────────────────────────────────┐    │
│  │        Rust Backend                  │    │
│  │  ┌─────────┐  ┌──────────────────┐   │    │
│  │  │ Folder  │  │ API Submitter    │   │    │
│  │  │ Watcher │  │ (reqwest HTTP)   │   │    │
│  │  │ (notify)│  │                  │   │    │
│  │  └─────────┘  └──────────────────┘   │    │
│  │  ┌─────────────┐ ┌───────────────┐   │    │
│  │  │ Config Store │ │ System Tray   │   │    │
│  │  │ (JSON file)  │ │ Integration   │   │    │
│  │  └─────────────┘ └───────────────┘   │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
         │                        │
         ▼                        ▼
   File System               LintPDF API
   (watch + route)           (submit + poll)
```

**Key design decision:** The Rust backend handles file watching and API
submission natively (no Python dependency). This means end users just install
one binary — no Python, no pip, no virtual environments.

- **File watching:** `notify` crate (cross-platform, same approach as Python's watchdog)
- **HTTP client:** `reqwest` crate (async HTTP, multipart uploads)
- **Config persistence:** JSON file in platform-appropriate app data directory
- **System tray:** Tauri v2 tray plugin

---

## Result Delivery

Results are delivered **two ways simultaneously:**

### 1. Folder routing (for workflow integration)
Each hot folder config specifies optional output directories:
- `pass_dir` — files that passed preflight are moved here
- `fail_dir` — files that failed are moved here
- `error_dir` — files that errored during submission are moved here
- JSON sidecar report (`.lintpdf.json`) written alongside each file

If no output dirs are configured, files stay in place and only get a sidecar.

### 2. App UI (for human visibility)
- Live results feed in the main window (table with file name, status, finding counts, timestamp)
- System tray badge/tooltip updates (e.g., "3 files processed, 1 failed")
- Desktop notifications on completion (optional, configurable)
- Click a result row to view full findings detail

---

## Data Model

### Hot Folder Configuration (persisted JSON)

```json
{
  "version": 1,
  "api_key": "encrypted-or-keychain-stored",
  "base_url": "https://api.lintpdf.com",
  "folders": [
    {
      "id": "uuid",
      "name": "Offset Print Jobs",
      "enabled": true,
      "watch_dir": "/Users/me/Dropbox/hotfolder-offset",
      "profile_id": "gwg-sheetfed-2024",
      "pass_dir": "/Users/me/Dropbox/hotfolder-offset/_passed",
      "fail_dir": "/Users/me/Dropbox/hotfolder-offset/_failed",
      "error_dir": "/Users/me/Dropbox/hotfolder-offset/_errors",
      "write_sidecar": true,
      "stabilization_secs": 2.0,
      "poll_interval_secs": 5.0,
      "file_extensions": [".pdf", ".eps", ".tiff", ".ai"]
    }
  ],
  "notifications_enabled": true,
  "start_minimized": false,
  "launch_at_login": false
}
```

### Job Result (in-memory + SQLite for history)

```json
{
  "id": "uuid",
  "folder_id": "uuid",
  "file_name": "brochure.pdf",
  "file_path": "/original/path",
  "status": "passed|failed|error|processing|queued",
  "job_id": "api-job-id",
  "summary": { "passed": false, "aground_count": 2, "squall_count": 1, "advisory_count": 0 },
  "findings": [...],
  "routed_to": "/path/to/output/dir/brochure.pdf",
  "submitted_at": "2026-03-22T10:30:00Z",
  "completed_at": "2026-03-22T10:30:45Z"
}
```

---

## Implementation Steps

### Step 1: Scaffold Tauri v2 project

Create `packages/desktop/` with:
- `src-tauri/` — Rust backend (Cargo.toml, main.rs, lib.rs)
- `src/` — React frontend (Vite + React + Tailwind)
- `package.json` — frontend dependencies
- Tauri config (`tauri.conf.json`)

Key Rust dependencies:
- `tauri` v2 — app framework
- `tauri-plugin-shell` — if needed
- `notify` v7 — file system watching
- `reqwest` — HTTP client with multipart
- `serde` / `serde_json` — serialization
- `tokio` — async runtime
- `uuid` — folder IDs
- `rusqlite` — local job history DB (lightweight)

Key frontend dependencies:
- `react` + `react-dom`
- `@tauri-apps/api` v2 — IPC bridge
- `tailwindcss` — styling (match existing LintPDF design)
- `lucide-react` — icons (already used in `packages/app`)

### Step 2: Config management (Rust)

- `config.rs` — Load/save JSON config from app data dir
  - Linux: `~/.config/lintpdf-desktop/config.json`
  - macOS: `~/Library/Application Support/com.lintpdf.desktop/config.json`
  - Windows: `%APPDATA%/lintpdf-desktop/config.json`
- Tauri commands: `get_config`, `save_config`, `add_folder`, `remove_folder`, `update_folder`
- API key stored via platform keychain (tauri-plugin-store or OS keyring)

### Step 3: File watcher (Rust)

- `watcher.rs` — Multi-folder watcher manager
  - Spawns one `notify::RecommendedWatcher` per enabled folder
  - Stabilization logic: track file size, wait N seconds of no change
  - Queue stabilized files for submission
  - Handle watcher start/stop/restart when config changes
- Tauri commands: `start_watching`, `stop_watching`, `get_watcher_status`
- Tauri events: `file-detected`, `file-stabilized` (emitted to frontend)

### Step 4: API submitter (Rust)

- `submitter.rs` — Async job submission and polling
  - POST `/api/v1/jobs` with multipart file upload
  - Poll `/api/v1/jobs/{id}` until complete/failed
  - Handle rate limiting (429 + Retry-After)
  - Route files to pass/fail/error directories
  - Write JSON sidecar reports
  - Emit events to frontend: `job-submitted`, `job-completed`, `job-failed`
- Concurrent submission with configurable parallelism (default: 2 per folder)

### Step 5: Job history (Rust)

- `db.rs` — SQLite database for job history
  - Table: `jobs` (id, folder_id, file_name, status, summary, findings, timestamps)
  - Tauri commands: `get_recent_jobs`, `get_job_detail`, `clear_history`
  - Auto-prune old entries (keep last 1000 or 30 days)

### Step 6: System tray (Rust)

- `tray.rs` — System tray integration
  - Tray icon with status indicator (idle/processing/error)
  - Context menu: Show Window, Start All, Stop All, Quit
  - Tooltip: "LintPDF — 3 folders active, 12 files processed"
  - Close-to-tray behavior (window hides, app keeps running)
  - Optional: launch at login (platform-specific)

### Step 7: Frontend — Folder configuration UI

- `src/pages/FolderList.tsx` — List of configured hot folders
  - Add/edit/remove folders
  - Enable/disable toggle per folder
  - Status indicator (watching/stopped/error)
  - Quick stats (files processed today)

- `src/pages/FolderEdit.tsx` — Edit a single folder config
  - Directory picker for watch_dir, pass_dir, fail_dir, error_dir
  - Profile selector (dropdown of available profiles from API)
  - File extension checkboxes
  - Advanced: stabilization time, poll interval

- `src/pages/Settings.tsx` — Global settings
  - API key input (masked)
  - Base URL
  - Notifications toggle
  - Start minimized toggle
  - Launch at login toggle

### Step 8: Frontend — Results feed UI

- `src/pages/Results.tsx` — Live results table
  - Columns: File, Folder, Status, Findings (aground/squall/advisory), Time
  - Color-coded rows (green=pass, red=fail, yellow=error)
  - Click row to expand findings detail
  - Filter by folder, status, date range
  - Real-time updates via Tauri events

- `src/components/StatusBar.tsx` — Bottom bar
  - "Watching 3 folders | 5 queued | 12 processed | 1 failed"

### Step 9: Desktop notifications

- Use Tauri notification plugin
- Notify on: job completed (pass/fail), watcher error, API connection issues
- Configurable: all results, failures only, errors only, or disabled

### Step 10: Build and packaging

- Tauri build config for all three platforms:
  - macOS: `.dmg` (universal binary for Intel + Apple Silicon)
  - Windows: `.msi` installer + portable `.exe`
  - Linux: `.AppImage` + `.deb`
- App icon and branding
- Code signing setup (macOS notarization, Windows Authenticode)
- Auto-updater config (Tauri's built-in updater)

---

## File Structure

```
packages/desktop/
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── lib/
│   │   ├── tauri.ts          # IPC helpers
│   │   └── types.ts          # TypeScript types matching Rust structs
│   ├── pages/
│   │   ├── FolderList.tsx
│   │   ├── FolderEdit.tsx
│   │   ├── Results.tsx
│   │   └── Settings.tsx
│   ├── components/
│   │   ├── Layout.tsx
│   │   ├── StatusBar.tsx
│   │   ├── FolderCard.tsx
│   │   ├── ResultsTable.tsx
│   │   ├── ResultDetail.tsx
│   │   └── DirectoryPicker.tsx
│   └── styles/
│       └── globals.css
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── capabilities/
│   │   └── default.json
│   ├── icons/
│   │   └── (app icons)
│   └── src/
│       ├── main.rs            # Entry point
│       ├── lib.rs             # Tauri setup, plugin registration
│       ├── config.rs          # Config load/save
│       ├── watcher.rs         # Multi-folder file watcher
│       ├── submitter.rs       # API submission + polling
│       ├── router.rs          # File routing (pass/fail/error dirs)
│       ├── db.rs              # SQLite job history
│       ├── tray.rs            # System tray setup
│       └── commands.rs        # All Tauri IPC commands
└── README.md
```

---

## Open Questions / Future Enhancements

1. **Profile fetching:** Should the app fetch available profiles from the API for a dropdown, or let users type profile IDs manually? (Start with manual, add API fetch later)
2. **Batch operations:** Should there be a "drag and drop" mode in addition to hot folder watching? (Nice-to-have, v2)
3. **Team sharing:** Export/import folder configs for team distribution? (v2)
4. **Auto-updater:** Tauri has built-in auto-update support. Enable from v1? (Yes, configure update server URL)
