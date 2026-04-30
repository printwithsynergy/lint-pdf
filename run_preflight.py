#!/usr/bin/env python3
"""Run full preflight checks (including AI) on a PDF and generate reports."""

import json
import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from siftpdf.profiles.schema import PreflightProfile, AIFeatureConfig
from siftpdf.profiles.orchestrator import PreflightOrchestrator
from siftpdf.reports.engine import ReportEngine

PDF_PATH = "/home/user/lint-pdf/packages/web/public/lintpdf_preflight_test_final.pdf"
OUTPUT_DIR = "/home/user/lint-pdf/packages/web/public/reports"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Loading PDF: {PDF_PATH}")
    with open(PDF_PATH, "rb") as f:
        pdf_bytes = f.read()
    print(f"  File size: {len(pdf_bytes):,} bytes")

    # Build a profile with AI enabled (all categories)
    profile = PreflightProfile(
        name="Full Preflight + AI",
        description="All engine checks plus all AI analyzers",
        conformance=None,
        workflow="CMYK",
        checks={
            "enabled": ["LPDF_*", "PDFX4-*", "PDFX1A-*", "PDFA-*", "AI_*"],
            "disabled": [],
            "severity_overrides": {},
        },
        thresholds={
            "min_dpi": 150.0,
            "max_dpi": 600.0,
            "tac_limit": 300.0,
            "min_bleed_mm": 3.0,
            "hairline_threshold": 0.25,
            "small_text_threshold": 6.0,
            "safety_margin_mm": 3.0,
        },
        ai=AIFeatureConfig(
            enabled=True,
            categories=["all"],
            features=[],
        ),
    )

    print("\nRunning preflight checks (engine + AI)...")
    start = time.time()
    orchestrator = PreflightOrchestrator(profile, profile_id="full-preflight-ai")
    result = orchestrator.run(pdf_bytes)
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.1f}s")

    # Print summary
    s = result.summary
    print(f"\n{'=' * 60}")
    print(f"  PREFLIGHT SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Pages:     {s.page_count}")
    print(f"  File size: {s.file_size_bytes:,} bytes")
    print(f"  Verdict:   {'PASS' if s.passed else 'FAIL'}")
    print(f"  Total findings: {s.total_findings}")
    print(f"    Errors:    {s.error_count}")
    print(f"    Warnings:  {s.warning_count}")
    print(f"    Advisory:  {s.advisory_count}")
    print(f"  Duration:  {result.duration_ms}ms")
    print(f"{'=' * 60}")

    # Print metadata
    print(f"\n  Metadata:")
    for k, v in result.metadata.items():
        print(f"    {k}: {v}")

    # Print findings grouped by severity
    for sev_label in ["error", "warning", "advisory"]:
        findings = [f for f in result.findings if f.severity.value == sev_label]
        if findings:
            print(f"\n  [{sev_label.upper()}] ({len(findings)} findings):")
            for f in findings:
                page_str = f"p.{f.page_num}" if f.page_num else "doc"
                src = f" [{f.source}]" if f.source and f.source != "engine" else ""
                print(f"    {f.inspection_id} ({page_str}){src}: {f.message}")

    # Generate reports
    engine = ReportEngine()

    # JSON report
    print("\n\nGenerating JSON report...")
    json_bytes = engine.generate(result, "json")
    json_path = os.path.join(OUTPUT_DIR, "preflight_report.json")
    with open(json_path, "wb") as f:
        f.write(json_bytes)
    print(f"  Saved: {json_path}")

    # HTML report (comprehensive, with page screenshots)
    print("Generating HTML report (comprehensive)...")
    html_bytes = engine.generate(
        result,
        "html",
        pdf_bytes=pdf_bytes,
        detail_level="comprehensive",
    )
    html_path = os.path.join(OUTPUT_DIR, "preflight_report.html")
    with open(html_path, "wb") as f:
        f.write(html_bytes)
    print(f"  Saved: {html_path}")

    # PDF report (comprehensive, with page screenshots)
    print("Generating PDF report (comprehensive)...")
    pdf_report_bytes = engine.generate(
        result,
        "pdf",
        pdf_bytes=pdf_bytes,
        detail_level="comprehensive",
    )
    pdf_path = os.path.join(OUTPUT_DIR, "preflight_report.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_report_bytes)
    print(f"  Saved: {pdf_path}")

    print(f"\n{'=' * 60}")
    print("DONE. Reports generated:")
    print(f"  HTML: {html_path}")
    print(f"  PDF:  {pdf_path}")
    print(f"  JSON: {json_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
