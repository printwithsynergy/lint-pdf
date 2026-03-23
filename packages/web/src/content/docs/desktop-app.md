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

| Platform          | Download                         | Requirements        |
| ----------------- | -------------------------------- | ------------------- |
| macOS (Universal) | [LintPDF-HotFolders.dmg](#)      | macOS 10.15+        |
| Windows (64-bit)  | [LintPDF-HotFolders.msi](#)      | Windows 10+         |
| Linux (AppImage)  | [LintPDF-HotFolders.AppImage](#) | GTK 4 / WebKitGTK 6 |

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

## Advanced Settings Per Folder

| Setting         | Default       | Description                                                                                                          |
| --------------- | ------------- | -------------------------------------------------------------------------------------------------------------------- |
| Stabilization   | 2 seconds     | How long to wait for file size to stop changing before submitting. Increase this for slow network mounts (NFS, SMB). |
| Poll Interval   | 5 seconds     | How often to check the API for job completion. Lower values = faster results but more API calls.                     |
| File Extensions | All supported | Choose which file types to watch. Uncheck types you don't need.                                                      |
| Write Sidecar   | On            | Write a `.lintpdf.json` report alongside each processed file.                                                        |

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

JDF pairing is enabled by default. You can configure the companion file timeout per folder in the folder settings — this controls how long the app waits for a JDF/XJDF file after detecting a new PDF. The default is 30 seconds.

When JDF parameters are applied, the Results tab shows which thresholds were overridden and their values.

## Data Storage

The app stores data locally on your machine:

| Data          | Location                                                                                                                                                                |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Configuration | `~/.config/lintpdf-desktop/config.json` (Linux), `~/Library/Application Support/lintpdf-desktop/config.json` (macOS), `%APPDATA%/lintpdf-desktop/config.json` (Windows) |
| Job History   | `~/.local/share/lintpdf-desktop/jobs.db` (Linux), `~/Library/Application Support/lintpdf-desktop/jobs.db` (macOS), `%APPDATA%/lintpdf-desktop/jobs.db` (Windows)        |

Job history is stored in a local SQLite database and auto-prunes to the most recent 1,000 entries.

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
