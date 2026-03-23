---
title: "80+ New Inspections: Color Management, AI, and Extended Gamut for LintPDF"
date: "2026-03-21"
author: "Think Neverland"
excerpt: "LintPDF now includes comprehensive color management, extended gamut readiness, HP Indigo EPM checks, and a novel Color Quality Score."
---

# 80+ New Inspections: Color Management, AI, and Extended Gamut for LintPDF

Today we're shipping the biggest update in LintPDF history: 80+ new inspections spanning color management, AI-powered analysis, extended gamut readiness, and digital press optimization.

## Color Management — Competing with the Desktop Tools

LintPDF now includes 25+ color management inspections that match what you'd expect from PitStop or pdfToolbox — but via API, at scale, without per-seat licenses.

**ICC Profile Validation.** We parse and validate every embedded ICC profile: structural integrity, version compatibility, corruption detection via LittleCMS.

**Output Intent Validation.** Deep cross-referencing against FOGRA, GRACoL, SWOP, and Japan Color conditions. Not just "is it present?" but "is it correct?"

**Spot Color Analysis.** Complete inventory with fallback validation, naming consistency checks, and DeviceN structural verification.

**Ink Coverage.** TAC calculation with per-separation breakdown, channel count validation, and heatmap data for visualization.

## Color Quality Score — Nobody Has This

Every preflight report now includes a **0-100 Color Quality Score**. This weighted composite considers color spaces, ink coverage, profiles, spot colors, and overprint patterns to give you a single number that answers: "How ready is this file for press?"

## Extended Gamut & Digital Press

**ECG Readiness.** For print shops moving to CMYKOGV, we assess spot color achievability against FOGRA55 and validate DeviceN structure.

**HP Indigo EPM.** Eight dedicated checks for CMY-only workflows: K-channel detection, composite black quality, gray balance risk, and more.

## Standards Compliance

G7, GRACoL, and ISO 12647 readiness checking — because your clients ask for compliance and you need to verify it at intake.

## What's Next

We're continuing to build the most comprehensive PDF preflight API on the market. All these features are available today on all paid plans. AI features remain in invite-only beta.

Preflight, Evolved.
