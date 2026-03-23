---
title: "Hot Folder Integration"
description: "Automatically preflight files by dropping them into a watched directory. Choose the desktop app for a visual experience or the CLI for headless servers."
section: "integrations"
order: 11
---

# Hot Folder Integration

LintPDF hot folders let you preflight files by dropping them into a watched directory. Files are automatically submitted to the LintPDF API and routed to pass, fail, or error directories based on results.

Two options:

|                  | **Desktop App**                                     | **CLI**                                         |
| ---------------- | --------------------------------------------------- | ----------------------------------------------- |
| **Best for**     | Operators, prepress desks, anyone who prefers a GUI | Servers, headless environments, CI/CD           |
| **Platform**     | macOS, Windows, Linux                               | Any platform with Python 3.10+                  |
| **Multi-folder** | Configure unlimited folders in one window           | Run one instance per folder                     |
| **System tray**  | Runs in background with live status                 | Runs as a foreground process or systemd service |
| **Results**      | Live results feed with filtering                    | Sidecar JSON reports + log output               |
| **Install**      | Download native installer                           | `pip install lintpdf-hotfolder`                 |

---

## Desktop App

The LintPDF Hot Folders desktop app is a native application built with Tauri that provides a visual interface for managing watched directories.

### Download

| Platform          | Download                         |
| ----------------- | -------------------------------- |
| macOS (Universal) | [LintPDF-HotFolders.dmg](#)      |
| Windows (64-bit)  | [LintPDF-HotFolders.msi](#)      |
| Linux (AppImage)  | [LintPDF-HotFolders.AppImage](#) |

### Features

- **Multiple folders** — Configure as many watched directories as you need, each with its own preflight profile and output directories
- **Visual results feed** — See pass/fail status, finding counts (aground, squall, advisory), and job details in real time
- **System tray** — Runs quietly in the background. Right-click the tray icon to start/stop all watchers or open the window
- **File type filtering** — Choose which file types to watch per folder (.pdf, .eps, .tiff, .jpg, .png, .ai, etc.)
- **Sidecar reports** — Optionally write `.lintpdf.json` reports alongside processed files
- **Close to tray** — Closing the window keeps the app running. Quit from the tray menu when done

### Quick Start

1. Launch **LintPDF Hot Folders**
2. Go to **Settings** and enter your API key
3. Click **Add Folder** and configure:
   - **Name** — a label for this folder (e.g., "Offset Print Jobs")
   - **Watch Directory** — the directory to monitor
   - **Profile** — the preflight profile to use (e.g., `gwg-sheetfed`)
   - **Pass/Fail/Error Directories** — where to route files after preflight
4. Click **Start** on the folder card (or **Start All** to watch everything)
5. Drop files into the watched directory and watch results appear in the **Results** tab

### Folder Configuration

Each hot folder has these settings:

| Setting         | Default            | Description                                           |
| --------------- | ------------------ | ----------------------------------------------------- |
| Name            | —                  | Display name for the folder                           |
| Watch Directory | —                  | Path to monitor for new files                         |
| Profile         | `grounded-default` | Preflight profile ID                                  |
| Pass Directory  | —                  | Move passed files here (leave empty to keep in place) |
| Fail Directory  | —                  | Move failed files here                                |
| Error Directory | —                  | Move files that couldn't be processed here            |
| Write Sidecar   | On                 | Write a `.lintpdf.json` report alongside each file    |
| Stabilization   | 2s                 | Wait for file size to stabilize before submitting     |
| Poll Interval   | 5s                 | How often to check job status                         |
| File Extensions | All supported      | Which file types to watch                             |

### Running at Startup

Enable **Launch at login** in Settings to start the app automatically when you log in. Combined with **Start minimized**, the app will begin watching immediately in the background.

---

## CLI Tool

The CLI is ideal for headless servers, Docker containers, and scripted workflows.

### Installation

```bash
pip install lintpdf-hotfolder
```

Or install from source:

```bash
cd packages/hotfolder
pip install -e .
```

### Quick Start

```bash
# Watch a directory and route files based on results
lintpdf-watch \
  --watch-dir /path/to/incoming \
  --api-key lpdf_your_api_key \
  --profile gwg-sheetfed \
  --pass-dir /path/to/approved \
  --fail-dir /path/to/rejected \
  --error-dir /path/to/errors
```

Drop a PDF into `/path/to/incoming` and the tool will:

1. Detect the new file
2. Wait for the file to be fully written (stabilization check)
3. Submit it to LintPDF
4. Poll for results
5. Move it to `approved/` or `rejected/` based on pass/fail
6. Write a JSON sidecar report alongside the moved file

### Directory Layout

```
/incoming/          <- Drop files here (watched directory)
    artwork.pdf     <- New file detected

/approved/          <- Files that passed preflight
    artwork.pdf
    artwork.pdf.lintpdf.json    <- Sidecar report

/rejected/          <- Files that failed preflight
    label.pdf
    label.pdf.lintpdf.json

/errors/            <- Files that couldn't be processed
    corrupt.pdf
    corrupt.pdf.lintpdf.json    <- Contains error details
```

### Command-Line Options

```
Usage: lintpdf-watch [OPTIONS]

Options:
  --watch-dir PATH          Directory to watch for new files (required)
  --api-key TEXT            LintPDF API key (or set LINTPDF_API_KEY env var)
  --base-url TEXT           API base URL [default: https://api.lintpdf.com]
  --profile TEXT            Voyage Plan profile ID [default: grounded-default]
  --pass-dir PATH           Move passed files here
  --fail-dir PATH           Move failed files here
  --error-dir PATH          Move errored files here
  --sidecar / --no-sidecar  Write JSON sidecar reports [default: --sidecar]
  --stabilization FLOAT     Seconds to wait for file stability [default: 2.0]
  --poll-interval FLOAT     Seconds between status polls [default: 5.0]
  --log-level TEXT          Log level (DEBUG, INFO, WARNING, ERROR) [default: INFO]
  --help                    Show this message and exit.
```

### Configuration via Environment Variables

```bash
export LINTPDF_API_KEY=lpdf_your_api_key
export LINTPDF_BASE_URL=https://api.lintpdf.com
export LINTPDF_PROFILE=gwg-sheetfed

lintpdf-watch --watch-dir /incoming --pass-dir /approved --fail-dir /rejected
```

### Running as a System Service

Create a systemd unit for always-on watching:

```ini
# /etc/systemd/system/lintpdf-hotfolder.service
[Unit]
Description=LintPDF Hot Folder Watcher
After=network.target

[Service]
Type=simple
User=prepress
Environment=LINTPDF_API_KEY=lpdf_your_api_key
ExecStart=/usr/local/bin/lintpdf-watch \
  --watch-dir /srv/prepress/incoming \
  --pass-dir /srv/prepress/approved \
  --fail-dir /srv/prepress/rejected \
  --error-dir /srv/prepress/errors \
  --profile gwg-sheetfed
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now lintpdf-hotfolder
```

### Multiple Profiles

Run multiple instances for different workflows:

```bash
# Offset jobs
lintpdf-watch --watch-dir /jobs/offset --profile gwg-sheetfed --pass-dir /approved/offset &

# Digital jobs
lintpdf-watch --watch-dir /jobs/digital --profile gwg-digital --pass-dir /approved/digital &
```

Or use the desktop app, which handles multiple folders in a single window.

---

## Sidecar Report Format

Both the desktop app and CLI produce the same JSON sidecar format:

```json
{
  "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "file_name": "artwork.pdf",
  "status": "failed",
  "summary": {
    "passed": false,
    "aground_count": 2,
    "squall_count": 1,
    "advisory_count": 3
  },
  "submitted_at": "2025-03-22T10:15:30Z",
  "completed_at": "2025-03-22T10:15:42Z"
}
```

## Supported File Types

Both tools watch for these extensions:

- `.pdf` — PDF documents
- `.eps` — Encapsulated PostScript
- `.ps` — PostScript
- `.tiff`, `.tif` — TIFF images
- `.jpg`, `.jpeg` — JPEG images
- `.png` — PNG images
- `.ai` — Adobe Illustrator

## Use Cases

### Prepress Hotfolder Integration

Many prepress systems use hotfolder-based workflows. Place the LintPDF hot folder upstream:

```
[Designer drops PDF] -> /hotfolder/incoming
    |
[LintPDF hot folder watches]
    |
[Passed?]
    |-- Yes -> /hotfolder/approved -> [Prepress workflow picks up]
    |-- No  -> /hotfolder/rejected -> [Designer notified]
```

### ERP/MIS Output Processing

If your ERP exports artwork files to a directory:

```bash
lintpdf-watch \
  --watch-dir /erp/artwork-export \
  --pass-dir /prepress/ready \
  --fail-dir /erp/needs-review \
  --error-dir /erp/errors \
  --profile gwg-sheetfed
```

Or configure the same setup in the desktop app with the folder editor.

### Production Floor Stations

Install the desktop app on prepress workstations. Operators can:

1. Drop files into the watched folder from their design application
2. See pass/fail results immediately in the system tray
3. Open the app to review finding details
4. Retrieve approved files from the pass directory

No terminal experience required.

## Tips

- **Rate limits:** Both tools respect LintPDF rate limits with automatic backoff using the `Retry-After` header.
- **Disk space:** Files are moved (not copied). Ensure output directories have enough space.
- **Network mounts:** Increase stabilization time to 5-10 seconds for NFS/SMB mounts where file writes are delayed.
- **File collisions:** If a file with the same name exists in the destination, a numeric suffix is added automatically (e.g., `artwork_1.pdf`).
- **Startup behavior:** On startup, files already in the watch directory are processed immediately. Clear the directory first to avoid re-processing.
