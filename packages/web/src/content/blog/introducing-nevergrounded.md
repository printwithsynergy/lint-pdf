---
title: "Introducing LintPDF — PDF Preflight for the API Era"
date: "2026-03-15"
author: "Think Neverland"
category: "Product Updates"
excerpt: "Today we are launching LintPDF, a detection-only PDF preflight engine built API-first for web-to-print platforms, prepress houses, and any developer who needs PDF quality gates at scale."
tags: ["launch", "product", "api"]
---

Today we are launching LintPDF, a detection-only PDF preflight engine built API-first for web-to-print platforms, prepress houses, and any developer who needs PDF quality gates at scale.

## The problem we set out to solve

The print industry has a tooling gap. On one side, enterprise preflight software does everything — inspection, correction, normalization — but requires a sales call, opaque pricing, and months of onboarding. On the other side, developer-friendly file APIs are easy to integrate but lack the depth that real print production demands. No font embedding checks, no ink coverage analysis, no custom profiles.

LintPDF sits in the middle. Comprehensive print preflight delivered through a REST API with self-service signup and transparent per-file pricing.

## What LintPDF does

You send a PDF (or EPS, TIFF, JPEG, PNG, AI file) to the Submit endpoint with a Ruleset — a preflight profile defining which checks to run. LintPDF processes your file through 250+ checks: fonts, color spaces, images, transparency, overprint, page geometry, ink coverage, barcode grading, PDF/X-4, PDF/A compliance, and more.

You get back a Report — a detailed report in JSON, XML, or a white-labeled PDF with your logo and colors. Every finding includes a severity level (Error, Warning, or Info), page location, and Check ID.

## What LintPDF does not do

LintPDF is detection-only. We find problems, we report them, and we never touch your files. Your originals stay exactly as they were — byte for byte, every time.

This is not a limitation. It is a deliberate design decision. Automated PDF correction introduces risk: re-rendered transparency, dropped ICC profiles, re-encoded images. The cost of a single damaged file in a production print run far exceeds the cost of detection and human review.

## Getting started

Sign up at [app.lintpdf.com](https://app.lintpdf.com), generate an API Key, and submit your first file. The Free plan includes 50 files per month with full check coverage.

One POST. Full report. JSON, XML, or a white-labeled PDF with your logo. That's it.
