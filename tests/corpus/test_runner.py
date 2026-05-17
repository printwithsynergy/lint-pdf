"""Tests for corpus runner diff logic."""

from __future__ import annotations

from lintpdf.corpus.runner import _diff_findings, _findings_to_identity_set, _identity_key


def _f(inspection_id: str, severity: str = "error", page_num: int | None = 1) -> dict:
    return {"inspection_id": inspection_id, "severity": severity, "page_num": page_num}


def test_identity_key():
    f = _f("LPDF_IMG_RES", "error", 2)
    assert _identity_key(f) == ("LPDF_IMG_RES", "error", 2)


def test_identity_key_null_page():
    f = _f("LPDF_DOC", "warning", None)
    assert _identity_key(f) == ("LPDF_DOC", "warning", None)


def test_diff_no_change():
    findings = [_f("A"), _f("B")]
    diff = _diff_findings(findings, findings)
    assert diff["missing"] == []
    assert diff["new"] == []
    assert diff["actual_count"] == 2


def test_diff_missing_finding():
    expected = [_f("A"), _f("B")]
    actual = [_f("A")]
    diff = _diff_findings(expected, actual)
    assert len(diff["missing"]) == 1
    assert diff["missing"][0]["inspection_id"] == "B"
    assert diff["new"] == []


def test_diff_new_finding():
    expected = [_f("A")]
    actual = [_f("A"), _f("C")]
    diff = _diff_findings(expected, actual)
    assert diff["missing"] == []
    assert len(diff["new"]) == 1
    assert diff["new"][0]["inspection_id"] == "C"


def test_diff_both_sides():
    expected = [_f("A"), _f("B")]
    actual = [_f("A"), _f("C")]
    diff = _diff_findings(expected, actual)
    assert len(diff["missing"]) == 1
    assert diff["missing"][0]["inspection_id"] == "B"
    assert len(diff["new"]) == 1
    assert diff["new"][0]["inspection_id"] == "C"


def test_diff_severity_change_is_a_diff():
    expected = [_f("A", severity="error")]
    actual = [_f("A", severity="warning")]
    diff = _diff_findings(expected, actual)
    assert len(diff["missing"]) == 1
    assert len(diff["new"]) == 1


def test_diff_page_change_is_a_diff():
    expected = [_f("A", page_num=1)]
    actual = [_f("A", page_num=2)]
    diff = _diff_findings(expected, actual)
    assert len(diff["missing"]) == 1
    assert len(diff["new"]) == 1


def test_findings_to_identity_set_deduplicates():
    findings = [_f("A"), _f("A")]
    keys = _findings_to_identity_set(findings)
    assert len(keys) == 1
