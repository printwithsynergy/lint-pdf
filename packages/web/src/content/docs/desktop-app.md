---
title: "Desktop App"
description: "LintPDF Hot Folders is a native desktop app for macOS, Windows, and Linux that watches directories and preflights files automatically."
section: "getting-started"
order: 3
---

# Desktop App

LintPDF Hot Folders is a native desktop application that watches directories on your machine and automatically preflights new files through the LintPDF API. Results appear in a live feed, and files are routed to pass, fail, or error directories.

No code, no terminal, no scripting required.

## Download

The Hot Folders desktop app is a paid add-on. Once the LintPDF team
enables the desktop add-on on your account, download links appear in
the dashboard at **[Desktop App](https://app.lintpdf.com/dashboard/downloads)**
with signed, short-lived URLs for each platform:

| Platform          | Format              | Requirements        |
| ----------------- | ------------------- | ------------------- |
| macOS (Universal) | `.dmg`              | macOS 10.15+        |
| Windows (64-bit)  | `.msi`              | Windows 10+         |
| Linux             | `.AppImage` / `.deb`| GTK 4 / WebKitGTK 6 |

If you don't see the download page, email
[sales@lintpdf.com](mailto:sales@lintpdf.com?subject=Desktop%20App%20Access)
and we'll enable it for you.

Once installed, the app checks for updates on launch and prompts you
before downloading — no re-install cycle.

## How It Works

```
[Files dropped into watched folder]
    |
[Desktop app detects new files]
    |
[Submitted to LintPDF API]
    |
[Results arrive]
    |-- Passed  -> moved to pass directory
    |-- Failed  -> moved to fail directory
    |-- Error   -> moved to error directory
    |
[Sidecar .lintpdf.json written alongside each file]
[Live results feed updates in the app]
```

## Getting Started

### 1. Install and Launch

Download the installer for your platform and launch the app. It opens to the **Folders** tab.

### 2. Configure Your API Key

Go to **Settings** and enter your LintPDF API key. Get one from the [LintPDF dashboard](https://app.lintpdf.com) if you don't have one.

### 3. Add a Hot Folder

Click **Add Folder** and configure:

- **Name** — a label you'll recognize (e.g., "Offset Print Jobs")
- **Watch Directory** — click the folder icon to browse to the directory you want to monitor
- **Profile** — the preflight profile to use (e.g., `gwg-sheetfed`, `gwg-digital`, `pdf-x4`)
- **Pass Directory** — where files that pass preflight are moved
- **Fail Directory** — where files that fail are moved
- **Error Directory** — where files that can't be processed go

Leave any output directory empty to keep files in place.

### 4. Start Watching

Click the **play** button on the folder card, or **Start All** to watch every folder at once. The status bar at the bottom shows how many folders are active and how many files are processing.

### 5. Drop Files

Copy or save PDFs (or any supported file type) into the watched directory. The app will:

1. Wait for the file to finish writing (stabilization)
2. Upload it to LintPDF
3. Poll until results are ready
4. Move the file to the appropriate output directory
5. Write a `.lintpdf.json` sidecar report
6. Update the live results feed

## The Interface

### Folders Tab

Your configured hot folders, shown as cards. Each card displays:

- Folder name and watch path
- Current status (watching / idle / disabled)
- Running totals: passed, failed, errors
- Start/stop toggle and edit button

### Results Tab

A live table of every file processed, with columns for status, file name, folder, finding counts, and time. Click any row to see the full detail panel with:

- Job ID and timestamps
- Pass/fail status
- Error, warning, and advisory counts
- Error messages (if any)
- Destination path

Use the filter tabs to narrow by status: All, Passed, Failed, Errors, Issues.

### Settings Tab

- **API Key** — your LintPDF API key (stored securely on your machine)
- **API Base URL** — the API endpoint (default: `https://api.lintpdf.com`)
- **Notifications** — enable desktop notifications when files finish processing
- **Start minimized** — launch the app directly to the system tray
- **Launch at login** — start the app automatically when you log in

## System Tray

The app lives in your system tray (menu bar on macOS, taskbar on Windows, system tray on Linux). Right-click the icon for:

- **Show Window** — bring the app to the front
- **Start All** — start watching all configured folders
- **Stop All** — stop all watchers
- **Quit** — fully exit the application

Closing the main window hides the app to the tray — it keeps running in the background. Use **Quit** from the tray menu to fully exit.

## Branding & anonymous output

The desktop app honours the **tenant-level branding default** configured in the Dashboard ([Branding & Anonymous Output](/docs/branding-and-anonymous)). If your tenant default is `anonymous`, every sidecar report emitted by the desktop app is branding-free out of the box.

For one-off overrides, each folder card exposes a compact **Brand** dropdown, and the full folder editor has the same options under the "Branding" section:

| Option | Effect |
|---|---|
| *Use tenant default* | No `brand` parameter is sent — the engine resolves per your Dashboard setting. |
| *Anonymous* | Sends `brand=anonymous` on every submission from that folder. |
| *LintPDF* | Sends `brand=lintpdf`. |
| *BrandProfile…* | Sends `brand=profile:<uuid>`. The card fetches your tenant's BrandProfiles from the API and shows them by name. |

Folder-level overrides win over the tenant default. Share links minted from the Results tab freeze their branding at mint time — exactly like the API behaviour described in [Share Links](/docs/share-links).

## Offline &amp; connectivity

The app is designed to keep working when the network doesn't.

- **Connectivity pill** in the title bar shows one of three states:
  green `Online`, amber `Online · N queued` (drain in progress), grey
  or amber `Offline`. Click it to force an immediate `/health` probe.
- **Outbox**: every stabilized file is written to a local SQLite
  outbox as soon as it's seen — before any network I/O. Rows appear
  in Results as `Waiting for connection` (cloud-off icon) when
  offline, or `Retrying` (rotate icon) with an exponential-backoff
  countdown when the engine has been returning errors.
- **Automatic drain**: when the probe transitions back to online,
  the app fires a desktop notification ("Back online — N files
  ready to submit") and the drainer flushes the outbox FIFO. No
  manual re-drag needed.
- **Cold-start**: quitting the app with queued rows in the local DB
  is safe — they reload on next launch and drain as soon as the
  probe succeeds.
- **Polling resilience**: jobs that were mid-poll when the network
  dropped are moved to the retry bucket rather than failing
  permanently. 4xx responses from the engine remain terminal
  (invalid profile ID, bad tenant, etc.); only 5xx / 429 / transport
  errors are retried.
- **Online-only actions**: **Mint share link**, **Open viewer**,
  **AI interpretation**, and the endpoint / approval-template /
  brand-profile dropdowns are disabled while offline. They fail
  fast with a clear message rather than waiting 30s for the HTTP
  call to time out.

## Share links

Every row in the **Results** tab has a **Share** section. For any completed job you can mint tokenised report URLs on demand:

- **HTML** — hosted interactive report page (`/r/{token}`)
- **PDF** — printable report (`/r/{token}.pdf`)
- **JSON** — machine-readable findings (`/r/{token}.json`)
- **XML** — the same findings in XML (`/r/{token}.xml`)
- **Annotated PDF** — the source PDF with findings overlaid (Scale / Enterprise plans)

### Open viewer

The **Open viewer** button on a completed job swaps the main panel
over to a native viewer rendered inside the desktop shell. The
toolbar, page navigation, thumbnail strip, and six side panels
(Findings, Channels, TAC, Layers, Notes, Probe) are all driven
directly by the engine's `/api/v1/viewer/…` endpoints, not by a
hosted web page in a child window.

What each panel does:

- **Findings** — lists every inspection-raised error, warning, and
  advisory. Click a row to jump to that page with the relevant bbox
  halo'd on the canvas. Severity colours: red (error), amber
  (warning), sky (advisory).
- **Channels** — isolate a single process (Cyan/Magenta/Yellow/
  Black) or spot separation as a grayscale overlay, composited
  multiply so hotspots are obvious.
- **TAC** — enable a TAC heatmap overlay with a slider-driven ink
  limit (100–500%). The panel lists every TAC run on the current
  page, colour-coded by whether it exceeds the limit.
- **Layers** — interactive OCG isolation. Checking / unchecking a
  layer sends an `ocg_on` / `ocg_off` mask to the engine's tile,
  channel, and TAC endpoints so the page re-renders with that layer
  set visible. The first toggle for a given combination takes the
  usual tile render round-trip (~500ms); subsequent visits to the
  same mask paint instantly from the local tile cache.
- **Notes** — annotations attached to the job. Click to jump, author
  + timestamp shown.
- **Probe** — the densitometer. Click anywhere on the page image and
  a 300 DPI server-side sample returns per-channel ink coverage plus
  the summed TAC, highlighted red when the result exceeds the active
  limit.

Behind the scenes:

- **Tile cache**: every page raster, channel tile, and TAC heatmap
  the viewer fetches is written through a durable LRU cache at
  `{APPDATA}/lintpdf-desktop/tiles/{job_id}/…` (1 GiB default
  budget). Reopening the same job is instant, and — critically —
  pages you've seen before render offline. Uncached tiles on an
  offline machine fail fast with a clear "Offline — tile not in
  cache" message.
- **DPI switching**: ≤150% zoom uses 150 DPI rasters (fast, small);
  anything higher re-fetches at 300 DPI for crisp detail. The
  densitometer always samples at 300 DPI regardless of zoom.
- **Bearer auth**: the viewer reuses the same API key the rest of
  the app already holds in the OS keyring — no `/r/{token}` mint
  round-trip is required. The "Open hosted viewer" button (kept as
  a secondary action) still mints a share link for sending a short-
  lived URL to a teammate.
- **Clearing the cache**: quitting and relaunching keeps the cache;
  deleting a job from Results prunes its tile directory in the
  background.

Links persist across app restarts (they're cached alongside the job
history) and honour the branding mode the folder was set to at the time
of submission. Plan-gated formats surface the engine's 403 message
inline — the other formats still mint fine.

See [Share Links](/docs/share-links) for the full semantics of these
tokens, including expiry, revocation, and tier gating.

## AI interpretation

When your plan includes AI features, the Results detail panel shows an
**Interpret** button on any completed job. Clicking it calls
`GET /api/v1/captains-log/{job_id}/interpret` and renders the
natural-language summary plus per-finding explanations, "why it matters"
context, and suggestions.

Runs cost AI credits per
[AI Credits](/docs/ai-credits) — a 403 response from the engine is
surfaced inline telling you to enable or top up AI access.

## Submit routing: custom endpoints &amp; external imports

Under **Submit routing** in the folder editor:

- **Custom endpoint** — picks a tenant-defined vanity endpoint from
  `GET /api/v1/endpoints`. When set, the folder submits to
  `POST /api/v1/endpoints/{id}/submit` and the endpoint's bound profile
  and brand win over the folder-level settings.
- **External report import** — flips the folder from "preflight this
  file" to "this file **is** a preflight report, just ingest it." When
  set, `.xml` / `.json` files in the watched directory are submitted to
  `POST /api/v1/jobs` with `preflight_source=external` and your chosen
  `external_format` (PitStop XML, Callas JSON/XML, Acrobat XML, LintPDF
  JSON). PDFs in the same folder still go through fresh preflight.

See [External Imports](/docs/external-imports) for supported report
formats and auto-detection rules.

## Approval chains

Under **Approvals** in the folder editor, attach an
[approval-chain template](/docs/share-links#approval-chains) to every
job submitted from this folder. The app calls
`POST /api/v1/jobs/{id}/approval-chain` with `template_id` right after
the job is created. A failure here is non-fatal — the preflight still
runs, and an advisory note is surfaced in the Results panel so you know
to re-attach manually.

## Batch mode

Under **Batch mode** in the folder editor, toggle on "Group submissions
into batches" and set a **Batch window** (default 10 seconds). Files
stabilizing within the same window are grouped and submitted as a
single `POST /api/v1/batch/submit` request. Each file still shows as
its own row in Results, tagged with the batch's engine-assigned
`batch_id`.

Batch mode composes naturally with offline operation: a burst of files
dropped while offline all get the same `batch_group` key and flush as
one batch once the network returns.

Batch mode is **mutually exclusive** with three other features because
the engine's batch endpoint accepts only `profile_id` + files:

- Custom endpoints (it's a different URL, `/api/v1/endpoints/{id}/submit`)
- External report imports (the batch endpoint ignores `preflight_source`)
- Brand overrides (the batch endpoint ignores `brand` / `unbranded`)

The folder editor disables the toggle with an explanatory message when
any of those are set. Saving a conflicting combination via
`config.json` is rejected with a clear error.

## Advanced Settings Per Folder

| Setting               | Default       | Description                                                                                                          |
| --------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------- |
| Stabilization         | 2 seconds     | How long to wait for file size to stop changing before submitting. Increase this for slow network mounts (NFS, SMB). |
| Poll Interval         | 5 seconds     | How often to check the API for job completion. Lower values = faster results but more API calls.                     |
| JDF Companion Timeout | 30 seconds    | How long to wait for a matching `.jdf` / `.xjdf` after a PDF stabilizes. Set to `0` to disable the wait.              |
| File Extensions       | All supported | Choose which file types to watch. Uncheck types you don't need.                                                      |
| Write Sidecar         | On            | Write a `.lintpdf.json` report alongside each processed file.                                                        |

## Supported File Types

- `.pdf` — PDF documents
- `.eps` — Encapsulated PostScript
- `.ps` — PostScript
- `.tiff`, `.tif` — TIFF images
- `.jpg`, `.jpeg` — JPEG images
- `.png` — PNG images
- `.ai` — Adobe Illustrator (PDF-compatible)

## JDF/XJDF Sidecar Support

The desktop app automatically detects JDF and XJDF companion files placed alongside PDFs in watched directories. When a PDF and a JDF/XJDF file share the same filename stem (e.g., `artwork.pdf` and `artwork.jdf`), the app pairs them automatically.

### How It Works

1. Drop a PDF and its companion JDF/XJDF file into a watched folder
2. The app detects the pair and extracts production parameters from the job ticket
3. JDF parameters (DPI, bleed, TAC, output condition, conformance) are sent to the LintPDF API alongside the PDF
4. These parameters **override** the corresponding thresholds in the selected preflight profile for that submission

### Configuration

JDF pairing is enabled by default. Each folder has a **JDF Companion
Timeout** under Advanced settings — if a PDF stabilizes without a
matching `.jdf` / `.xjdf` next to it, the app waits this many seconds
for the companion to arrive before submitting the PDF on its own. The
default is 30 seconds; set it to `0` to submit PDFs immediately with
no wait.

When JDF parameters are applied, the Results tab shows which thresholds were overridden and their values.

## Data Storage

The app stores data locally on your machine:

| Data          | Location                                                                                                                                                                |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Configuration | `~/.config/lintpdf-desktop/config.json` (Linux), `~/Library/Application Support/lintpdf-desktop/config.json` (macOS), `%APPDATA%/lintpdf-desktop/config.json` (Windows) |
| API key       | macOS Keychain / Windows Credential Manager / Linux Secret Service (service `com.lintpdf.desktop`, user `api_key`). Older installs that stored the key in `config.json` are migrated on first launch. |
| Job History   | `~/.local/share/lintpdf-desktop/jobs.db` (Linux), `~/Library/Application Support/lintpdf-desktop/jobs.db` (macOS), `%APPDATA%/lintpdf-desktop/jobs.db` (Windows)        |

Job history is stored in a local SQLite database and auto-prunes to the most recent 1,000 entries.

> On headless Linux hosts without a running Secret Service daemon, the
> app falls back to storing the API key in `config.json` (the same place
> it was stored before the keyring integration). A warning is written to
> the log on startup so you know.

## CLI Alternative

Prefer the command line? The [hot folder CLI tool](/docs/integrations-hot-folder) provides the same core functionality as a Python package:

```bash
pip install lintpdf-hotfolder

lintpdf-watch \
  --watch-dir /incoming \
  --api-key lpdf_your_key \
  --pass-dir /approved \
  --fail-dir /rejected
```

The CLI is better suited for headless servers, Docker containers, and scripted workflows. See the [Hot Folder Integration](/docs/integrations-hot-folder) docs for details.
