"""EPM v2 corpus regression — Gate G5 PR 19.

Runs the v2 EPM-A/B/C analyzers (PRs 5-7) against every PDF under
``tests/fixtures/accuracy/`` and asserts the fired LPDF_EPM_*_REJECT
codes + the ``score_epm_candidacy`` verdict match a per-fixture
golden snapshot stored at
``tests/fixtures/accuracy/epm-golden/<basename>.json``.

First run: pass ``--update-snapshots`` to seed the goldens.
Subsequent runs: a tightening / loosening of an analyzer threshold
that changes a verdict requires a deliberate snapshot refresh and
review.

The whole regression is marked ``corpus`` so default ``pytest`` runs
skip it (matches the existing per-pyproject convention; CI runs
``pytest -m corpus`` separately).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from siftpdf.analyzers.epm_v2_a import EpmTierAAnalyzer
from siftpdf.analyzers.epm_v2_b import EpmTierBAnalyzer
from siftpdf.analyzers.epm_v2_c import EpmTierCAnalyzer
from siftpdf.epm.scoring import score_epm_candidacy

_CORPUS_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "accuracy"
_GOLDEN_DIR = _CORPUS_DIR / "epm-golden"


pytestmark = pytest.mark.corpus


def _list_corpus() -> list[Path]:
    return sorted(_CORPUS_DIR.glob("*.pdf"))


def _golden_path(pdf: Path) -> Path:
    return _GOLDEN_DIR / f"{pdf.stem}.json"


def _run_v2_analyzers(pdf_path: Path) -> dict[str, Any]:
    """Run only the v2 EPM analyzers (skip the rest of the orchestrator
    pipeline so the snapshot stays narrow + fast)."""
    from siftpdf.parser.pikepdf_adapter import PikePDFAdapter
    from siftpdf.semantic.builder import SemanticModelBuilder
    from siftpdf.semantic.interpreter import ContentStreamInterpreter

    pdf_bytes = pdf_path.read_bytes()
    adapter = PikePDFAdapter()
    pdf_doc = adapter.open(pdf_bytes)
    document = SemanticModelBuilder(adapter).build(pdf_doc)

    events: list[Any] = []
    for pdf_page in pdf_doc.pages:
        instructions = adapter.parse_content_stream(pdf_page)
        if not instructions:
            continue
        sem_page = document.pages[pdf_page.page_num - 1]
        interpreter = ContentStreamInterpreter(
            page_num=pdf_page.page_num,
            resources=sem_page.resources or {},
        )
        events.extend(interpreter.interpret(instructions))

    findings = []
    for analyzer in (
        EpmTierAAnalyzer(),
        EpmTierBAnalyzer(),
        EpmTierCAnalyzer(),
    ):
        findings.extend(analyzer.analyze(document, events))

    fired = sorted({f.inspection_id for f in findings})
    verdict = score_epm_candidacy(fired)
    return {
        "fired_codes": fired,
        "verdict": {
            "tier": verdict.tier.value if hasattr(verdict.tier, "value") else str(verdict.tier),
            "rejection_drivers": list(verdict.rejection_drivers),
            "advisories": list(verdict.advisories),
            "recommends_indichrome": verdict.recommends_indichrome,
            "epm_findings_count": len(fired),
        },
    }


def _maybe_update(snapshot_path: Path, payload: dict[str, Any]) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


@pytest.fixture(scope="session")
def update_snapshots(request) -> bool:
    return bool(request.config.getoption("--update-snapshots", default=False))


@pytest.mark.parametrize("pdf", _list_corpus(), ids=lambda p: p.stem)
def test_epm_v2_corpus_matches_golden(pdf: Path, update_snapshots: bool) -> None:
    """Every corpus PDF's fired EPM codes + verdict match the golden."""
    if not pdf.exists():
        pytest.skip(f"corpus fixture missing: {pdf}")

    payload = _run_v2_analyzers(pdf)
    snapshot = _golden_path(pdf)

    if update_snapshots or not snapshot.exists():
        _maybe_update(snapshot, payload)
        if update_snapshots:
            pytest.skip(f"snapshot updated for {pdf.name}")
        else:
            pytest.skip(f"seeded snapshot for {pdf.name} — re-run to verify")

    expected = json.loads(snapshot.read_text())
    assert payload == expected, (
        f"EPM verdict drift for {pdf.name}.\n"
        f"  expected: {json.dumps(expected, indent=2, sort_keys=True)}\n"
        f"  actual:   {json.dumps(payload, indent=2, sort_keys=True)}"
    )
