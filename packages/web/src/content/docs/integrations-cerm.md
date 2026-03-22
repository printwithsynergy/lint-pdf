---
title: "CERM Integration"
description: "Integrate LintPDF with CERM MIS through JDF-based workflows via Esko AE or Hybrid CLOUDFLOW."
section: "integrations"
order: 6
---

# CERM Integration

CERM (by Heidelberg) is a label and packaging MIS. CERM integrates with LintPDF through an **indirect path** — JDF job tickets flow through a prepress workflow engine (Esko Automation Engine or Hybrid CLOUDFLOW), which calls LintPDF as a preflight step.

> **No public REST API.** CERM does not expose a public REST API for direct integration. The integration path is JDF-based through workflow engines. This is the standard approach for CERM installations.

## Integration Architecture

```
┌────────┐  JDF + files  ┌──────────────┐  HTTP POST  ┌──────────┐
│  CERM  │──────────────→│  Esko AE /   │────────────→│ LintPDF  │
│  MIS   │               │  CLOUDFLOW   │             │ API      │
│        │◄──────────────│              │◄────────────│          │
│        │  JDF status   │              │  Results    │          │
└────────┘               └──────────────┘             └──────────┘
```

## How It Works

### Step 1: CERM Sends JDF to Workflow Engine

CERM writes JDF job tickets with custom extensions. These are placed in hotfolders monitored by the prepress workflow engine.

**CERM supports Premium Integration Partnerships with:**

- **Esko Automation Engine** — Bidirectional JDF/JMF communication
- **Hybrid CLOUDFLOW** — Bidirectional sync of artwork status and color details

The JDF ticket contains job specifications, artwork references, and production parameters.

### Step 2: Workflow Engine Runs LintPDF Preflight

The workflow engine picks up the JDF ticket, extracts the artwork file(s), and submits them to LintPDF for preflight.

**For Esko AE:** See [Esko Automation Engine integration](/docs/integrations-esko-ae) for step-by-step setup.

**For CLOUDFLOW:** See [Hybrid CLOUDFLOW integration](/docs/integrations-hybrid-cloudflow) for setup details.

The workflow engine:

1. Parses the JDF ticket to identify artwork files
2. Submits each file to LintPDF via `POST /api/v1/jobs`
3. Polls for results via `GET /api/v1/jobs/{job_id}`
4. Routes files based on pass/fail

### Step 3: Results Flow Back to CERM

The workflow engine reports preflight results back to CERM through the JDF/JMF channel:

- **Pass:** Job status updated to "preflight passed" in CERM
- **Fail:** Job status updated to "preflight failed" with finding details

For the CERM-CLOUDFLOW integration specifically, the bidirectional sync includes artwork status and color details, which can carry preflight results.

## Example Flow

```
CERM creates job → JDF ticket written to hotfolder
    ↓
Esko AE / CLOUDFLOW picks up JDF
    ↓
Workflow extracts artwork PDF
    ↓
POST /api/v1/jobs → LintPDF preflight
    ↓
GET /api/v1/jobs/{id} → Poll for results
    ↓
Results: passed=true/false, aground/squall/advisory counts
    ↓
Workflow routes file (pass/fail)
    ↓
JDF/JMF status update → CERM
    ↓
CERM displays preflight status on job record
```

## LintPDF API Call (from Workflow Engine)

The LintPDF portion is identical regardless of which MIS originated the job:

```bash
# Submit the artwork PDF
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -F file=@artwork.pdf \
  -F profile_id=gwg-sheetfed

# Poll for results
curl https://api.lintpdf.com/api/v1/jobs/{job_id} \
  -H "Authorization: Bearer lpdf_your_api_key"
```

## Tips

- **Profile selection:** Map CERM job parameters (substrate, print method) to LintPDF profiles in the workflow engine. Use `gwg-sheetfed` for offset, `gwg-digital` for digital, or a custom profile.
- **JDF extensions:** CERM uses custom JDF extensions. Work with your prepress workflow integrator to ensure these extensions are correctly parsed.
- **Bidirectional sync:** The CERM-CLOUDFLOW integration provides bidirectional sync. Leverage this to push preflight results back to CERM job records automatically.
- **Hotfolder monitoring:** Ensure the JDF hotfolder is correctly configured and monitored by the workflow engine. Test with a sample JDF ticket before going live.
