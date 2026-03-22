"""PDF artwork comparison engine.

Compares two PDF documents (reference vs candidate) and produces
a structured diff report covering text, structure, metadata, and
visual differences.

Comparison modes:
- structural: Compare page count, boxes, fonts, color spaces
- text: Compare extracted text content per page
- metadata: Compare document info, XMP, output intents
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ComparisonDiff:
    """A single difference between two documents."""

    diff_type: str  # "text", "structure", "metadata", "visual"
    category: str  # "added", "removed", "changed"
    page_num: int = 0
    description: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    severity: str = "advisory"  # how significant is this diff


@dataclass
class ComparisonResult:
    """Result of comparing two PDF documents."""

    reference_pages: int = 0
    candidate_pages: int = 0
    diffs: list[ComparisonDiff] = field(default_factory=list)
    identical: bool = True
    similarity_score: float = 1.0  # 0.0-1.0


class ComparisonEngine:
    """Compares two PDF documents and produces a diff report."""

    def compare(
        self,
        reference_doc: Any,  # SemanticDocument
        candidate_doc: Any,  # SemanticDocument
        *,
        modes: list[str] | None = None,
    ) -> ComparisonResult:
        """Compare two documents and return differences.

        Args:
            reference_doc: The reference (expected) SemanticDocument.
            candidate_doc: The candidate (actual) SemanticDocument.
            modes: List of comparison modes to run. Defaults to
                ["structural", "text", "metadata"].

        Returns:
            ComparisonResult with all detected diffs.
        """
        if modes is None:
            modes = ["structural", "text", "metadata"]

        result = ComparisonResult(
            reference_pages=reference_doc.page_count,
            candidate_pages=candidate_doc.page_count,
        )

        if "structural" in modes:
            result.diffs.extend(self._compare_structure(reference_doc, candidate_doc))
        if "text" in modes:
            result.diffs.extend(self._compare_text(reference_doc, candidate_doc))
        if "metadata" in modes:
            result.diffs.extend(self._compare_metadata(reference_doc, candidate_doc))

        result.identical = len(result.diffs) == 0
        if result.diffs:
            # Simple similarity: 1 - (diff_count / max_reasonable_diffs)
            result.similarity_score = max(0.0, 1.0 - len(result.diffs) / 100.0)

        return result

    def _compare_structure(
        self,
        reference: Any,
        candidate: Any,
    ) -> list[ComparisonDiff]:
        """Compare structural aspects: page count, page sizes, fonts, color spaces, boxes."""
        diffs: list[ComparisonDiff] = []

        # Page count
        if reference.page_count != candidate.page_count:
            diffs.append(
                ComparisonDiff(
                    diff_type="structure",
                    category="changed",
                    description=(
                        f"Page count changed from {reference.page_count} "
                        f"to {candidate.page_count}"
                    ),
                    details={
                        "reference": reference.page_count,
                        "candidate": candidate.page_count,
                    },
                    severity="squall",
                )
            )

        # Compare pages that exist in both documents
        min_pages = min(reference.page_count, candidate.page_count)
        for i in range(min_pages):
            ref_page = reference.pages[i]
            cand_page = candidate.pages[i]
            page_num = i + 1

            # Page size (trim box or media box)
            ref_box = ref_page.trim_box or ref_page.media_box
            cand_box = cand_page.trim_box or cand_page.media_box
            ref_size = (round(ref_box.width, 1), round(ref_box.height, 1))
            cand_size = (round(cand_box.width, 1), round(cand_box.height, 1))
            if ref_size != cand_size:
                diffs.append(
                    ComparisonDiff(
                        diff_type="structure",
                        category="changed",
                        page_num=page_num,
                        description=(
                            f"Page {page_num} size changed from "
                            f"{ref_size[0]}x{ref_size[1]}pt to "
                            f"{cand_size[0]}x{cand_size[1]}pt"
                        ),
                        details={
                            "reference_size": ref_size,
                            "candidate_size": cand_size,
                        },
                    )
                )

            # Box hierarchy comparison (bleed, trim, crop)
            for box_name in ("bleed_box", "trim_box", "crop_box", "art_box"):
                ref_b = getattr(ref_page, box_name, None)
                cand_b = getattr(cand_page, box_name, None)
                if ref_b is not None and cand_b is None:
                    diffs.append(
                        ComparisonDiff(
                            diff_type="structure",
                            category="removed",
                            page_num=page_num,
                            description=(
                                f"Page {page_num}: {box_name} removed "
                                f"(was {ref_b.as_tuple()})"
                            ),
                            details={"box": box_name, "reference": ref_b.as_tuple()},
                        )
                    )
                elif ref_b is None and cand_b is not None:
                    diffs.append(
                        ComparisonDiff(
                            diff_type="structure",
                            category="added",
                            page_num=page_num,
                            description=(
                                f"Page {page_num}: {box_name} added "
                                f"({cand_b.as_tuple()})"
                            ),
                            details={"box": box_name, "candidate": cand_b.as_tuple()},
                        )
                    )
                elif ref_b is not None and cand_b is not None:
                    if ref_b.as_tuple() != cand_b.as_tuple():
                        diffs.append(
                            ComparisonDiff(
                                diff_type="structure",
                                category="changed",
                                page_num=page_num,
                                description=(
                                    f"Page {page_num}: {box_name} changed from "
                                    f"{ref_b.as_tuple()} to {cand_b.as_tuple()}"
                                ),
                                details={
                                    "box": box_name,
                                    "reference": ref_b.as_tuple(),
                                    "candidate": cand_b.as_tuple(),
                                },
                            )
                        )

            # Font sets
            ref_fonts = set(ref_page.fonts.keys())
            cand_fonts = set(cand_page.fonts.keys())
            added_fonts = cand_fonts - ref_fonts
            removed_fonts = ref_fonts - cand_fonts
            if added_fonts:
                diffs.append(
                    ComparisonDiff(
                        diff_type="structure",
                        category="added",
                        page_num=page_num,
                        description=(
                            f"Page {page_num}: fonts added: "
                            f"{', '.join(sorted(added_fonts))}"
                        ),
                        details={"added_fonts": sorted(added_fonts)},
                    )
                )
            if removed_fonts:
                diffs.append(
                    ComparisonDiff(
                        diff_type="structure",
                        category="removed",
                        page_num=page_num,
                        description=(
                            f"Page {page_num}: fonts removed: "
                            f"{', '.join(sorted(removed_fonts))}"
                        ),
                        details={"removed_fonts": sorted(removed_fonts)},
                    )
                )

            # Color space sets
            ref_cs = set(ref_page.color_spaces.keys())
            cand_cs = set(cand_page.color_spaces.keys())
            added_cs = cand_cs - ref_cs
            removed_cs = ref_cs - cand_cs
            if added_cs:
                diffs.append(
                    ComparisonDiff(
                        diff_type="structure",
                        category="added",
                        page_num=page_num,
                        description=(
                            f"Page {page_num}: color spaces added: "
                            f"{', '.join(sorted(added_cs))}"
                        ),
                        details={"added_color_spaces": sorted(added_cs)},
                    )
                )
            if removed_cs:
                diffs.append(
                    ComparisonDiff(
                        diff_type="structure",
                        category="removed",
                        page_num=page_num,
                        description=(
                            f"Page {page_num}: color spaces removed: "
                            f"{', '.join(sorted(removed_cs))}"
                        ),
                        details={"removed_color_spaces": sorted(removed_cs)},
                    )
                )

        # Pages only in reference (removed)
        for i in range(min_pages, reference.page_count):
            diffs.append(
                ComparisonDiff(
                    diff_type="structure",
                    category="removed",
                    page_num=i + 1,
                    description=f"Page {i + 1} removed in candidate",
                    severity="squall",
                )
            )

        # Pages only in candidate (added)
        for i in range(min_pages, candidate.page_count):
            diffs.append(
                ComparisonDiff(
                    diff_type="structure",
                    category="added",
                    page_num=i + 1,
                    description=f"Page {i + 1} added in candidate",
                    severity="squall",
                )
            )

        return diffs

    def _compare_text(
        self,
        reference: Any,
        candidate: Any,
    ) -> list[ComparisonDiff]:
        """Compare text content per page using content stream bytes."""
        diffs: list[ComparisonDiff] = []

        min_pages = min(reference.page_count, candidate.page_count)
        for i in range(min_pages):
            ref_page = reference.pages[i]
            cand_page = candidate.pages[i]
            page_num = i + 1

            ref_stream = ref_page.content_stream
            cand_stream = cand_page.content_stream

            if ref_stream != cand_stream:
                # Determine the nature of the change
                if not ref_stream and cand_stream:
                    diffs.append(
                        ComparisonDiff(
                            diff_type="text",
                            category="added",
                            page_num=page_num,
                            description=(
                                f"Page {page_num}: content added "
                                f"({len(cand_stream)} bytes)"
                            ),
                            details={
                                "candidate_size": len(cand_stream),
                            },
                        )
                    )
                elif ref_stream and not cand_stream:
                    diffs.append(
                        ComparisonDiff(
                            diff_type="text",
                            category="removed",
                            page_num=page_num,
                            description=(
                                f"Page {page_num}: content removed "
                                f"({len(ref_stream)} bytes)"
                            ),
                            details={
                                "reference_size": len(ref_stream),
                            },
                        )
                    )
                else:
                    size_diff = len(cand_stream) - len(ref_stream)
                    diffs.append(
                        ComparisonDiff(
                            diff_type="text",
                            category="changed",
                            page_num=page_num,
                            description=(
                                f"Page {page_num}: content stream changed "
                                f"(ref {len(ref_stream)} bytes, "
                                f"cand {len(cand_stream)} bytes, "
                                f"delta {size_diff:+d} bytes)"
                            ),
                            details={
                                "reference_size": len(ref_stream),
                                "candidate_size": len(cand_stream),
                                "size_delta": size_diff,
                            },
                        )
                    )

        return diffs

    def _compare_metadata(
        self,
        reference: Any,
        candidate: Any,
    ) -> list[ComparisonDiff]:
        """Compare document metadata: info_dict, output_intents, version, encryption."""
        diffs: list[ComparisonDiff] = []

        # PDF version
        if reference.version != candidate.version:
            diffs.append(
                ComparisonDiff(
                    diff_type="metadata",
                    category="changed",
                    description=(
                        f"PDF version changed from {reference.version} "
                        f"to {candidate.version}"
                    ),
                    details={
                        "reference": reference.version,
                        "candidate": candidate.version,
                    },
                )
            )

        # Encryption status
        if reference.is_encrypted != candidate.is_encrypted:
            if candidate.is_encrypted:
                diffs.append(
                    ComparisonDiff(
                        diff_type="metadata",
                        category="added",
                        description="Encryption added to candidate document",
                        severity="squall",
                    )
                )
            else:
                diffs.append(
                    ComparisonDiff(
                        diff_type="metadata",
                        category="removed",
                        description="Encryption removed in candidate document",
                        severity="squall",
                    )
                )

        # Info dict comparison
        ref_info = reference.info_dict or {}
        cand_info = candidate.info_dict or {}
        all_keys = set(ref_info.keys()) | set(cand_info.keys())
        for key in sorted(all_keys):
            ref_val = ref_info.get(key)
            cand_val = cand_info.get(key)
            if ref_val is None and cand_val is not None:
                diffs.append(
                    ComparisonDiff(
                        diff_type="metadata",
                        category="added",
                        description=f"Info dict key '{key}' added",
                        details={"key": key, "candidate_value": str(cand_val)},
                    )
                )
            elif ref_val is not None and cand_val is None:
                diffs.append(
                    ComparisonDiff(
                        diff_type="metadata",
                        category="removed",
                        description=f"Info dict key '{key}' removed",
                        details={"key": key, "reference_value": str(ref_val)},
                    )
                )
            elif str(ref_val) != str(cand_val):
                diffs.append(
                    ComparisonDiff(
                        diff_type="metadata",
                        category="changed",
                        description=(
                            f"Info dict key '{key}' changed from "
                            f"'{ref_val}' to '{cand_val}'"
                        ),
                        details={
                            "key": key,
                            "reference_value": str(ref_val),
                            "candidate_value": str(cand_val),
                        },
                    )
                )

        # Output intents
        ref_intents = reference.output_intents or []
        cand_intents = candidate.output_intents or []
        if len(ref_intents) != len(cand_intents):
            diffs.append(
                ComparisonDiff(
                    diff_type="metadata",
                    category="changed",
                    description=(
                        f"Output intent count changed from "
                        f"{len(ref_intents)} to {len(cand_intents)}"
                    ),
                    details={
                        "reference_count": len(ref_intents),
                        "candidate_count": len(cand_intents),
                    },
                    severity="squall",
                )
            )
        else:
            for idx, (ref_oi, cand_oi) in enumerate(zip(ref_intents, cand_intents)):
                ref_cond = ref_oi.get("OutputCondition", "")
                cand_cond = cand_oi.get("OutputCondition", "")
                ref_id = ref_oi.get("OutputConditionIdentifier", "")
                cand_id = cand_oi.get("OutputConditionIdentifier", "")
                if ref_cond != cand_cond or ref_id != cand_id:
                    diffs.append(
                        ComparisonDiff(
                            diff_type="metadata",
                            category="changed",
                            description=(
                                f"Output intent {idx} changed: "
                                f"condition '{ref_cond}' -> '{cand_cond}', "
                                f"identifier '{ref_id}' -> '{cand_id}'"
                            ),
                            details={
                                "index": idx,
                                "reference_condition": ref_cond,
                                "candidate_condition": cand_cond,
                                "reference_identifier": ref_id,
                                "candidate_identifier": cand_id,
                            },
                            severity="squall",
                        )
                    )

        return diffs
