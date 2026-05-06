from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.cli import _serialize_finding, build_parser


def test_serialize_finding_includes_bbox_list() -> None:
    finding = Finding(
        inspection_id="LPDF_TEST_001",
        severity=Severity.WARNING,
        message="example",
        page_num=2,
        bbox=(1.0, 2.0, 3.0, 4.0),
    )
    payload = _serialize_finding(finding)
    assert payload["inspection_id"] == "LPDF_TEST_001"
    assert payload["severity"] == "warning"
    assert payload["bbox"] == [1.0, 2.0, 3.0, 4.0]


def test_parser_accepts_metadata_cluster() -> None:
    parser = build_parser()
    args = parser.parse_args(["codex-cluster", "example.pdf", "--cluster", "metadata"])
    assert args.cluster == "metadata"
