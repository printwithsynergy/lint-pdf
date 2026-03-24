---
title: Design Decisions (ADRs)
tags: [decisions, adr, architecture]
---

# Design Decisions

## ADR-001: pikepdf + ParserAdapter Abstraction

Swap parsers without touching analyzers. Only `parser/pikepdf_adapter.py` imports pikepdf.

## ADR-002: ContentStreamInterpreter State Machine

Streaming events, not buffered. Operator dispatch table pattern. Form XObject recursion with 32-level depth limit.

## ADR-003: Pure Function Rules + Flight Plan JSON Profiles

Rules are stateless decorated functions. Composable and tenant-customizable via Flight Plan JSON.

## ADR-004: Async API with Celery + Redis

POST /api/v1/check-in returns 202 + job_id. Poll or webhook for results.

## ADR-005: veraPDF Sidecar for PDF/A

Delegate PDF/A validation to specialist. MPL 2.0 compatible. REST API on port 8080.

## ADR-006: GWG Parameterized Profiles

23 GWG 2022 variants as Flight Plan JSON configs with parameterized thresholds.

## Design Tokens

### Finding Severity
Three levels only: no-fly (spec violation), delay (warning), advisory (informational).

### API Status Values
queued -> taxiing -> arrived

### Report Verdict
- clear-to-fly: Zero no-fly findings
- lintpdf: One or more no-fly findings
- delay: Zero no-fly, one or more delay findings
