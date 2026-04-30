"""Tests for page/document primitives (Tier-0 Batch 09)."""

from __future__ import annotations

from siftpdf.primitives import REGISTRY
from siftpdf.primitives import page as page_p


def test_registry_contains_ten_page_primitives_and_two_doc():
    expected_page = {
        "media_box",
        "crop_box",
        "bleed_box",
        "trim_box",
        "art_box",
        "size_pt",
        "orientation",
        "rotation",
        "user_unit",
        "has_oversize_bleed",
    }
    expected_doc = {"page_count", "has_structure_tree"}
    assert REGISTRY.get("page", {}).keys() == expected_page
    assert expected_doc.issubset(REGISTRY.get("doc", {}).keys())


# ---- box accessors + fallback chain ----------------------------------


def test_media_box_required_for_size():
    assert page_p.media_box({"MediaBox": [0, 0, 612, 792]}) == (0, 0, 612, 792)
    assert page_p.media_box({}) is None


def test_crop_box_falls_back_to_media():
    page = {"MediaBox": [0, 0, 100, 200]}
    assert page_p.crop_box(page) == (0, 0, 100, 200)


def test_crop_box_explicit_overrides_media():
    page = {"MediaBox": [0, 0, 100, 200], "CropBox": [10, 10, 90, 190]}
    assert page_p.crop_box(page) == (10, 10, 90, 190)


def test_trim_box_falls_back_to_crop_then_media():
    page = {"MediaBox": [0, 0, 612, 792]}
    assert page_p.trim_box(page) == (0, 0, 612, 792)


def test_bleed_box_falls_back_to_crop():
    page = {"MediaBox": [0, 0, 612, 792], "CropBox": [9, 9, 603, 783]}
    assert page_p.bleed_box(page) == (9, 9, 603, 783)


def test_art_box_explicit():
    page = {"MediaBox": [0, 0, 612, 792], "ArtBox": [50, 50, 562, 742]}
    assert page_p.art_box(page) == (50, 50, 562, 742)


def test_invalid_rect_returns_none():
    assert page_p.media_box({"MediaBox": [1, 2, 3]}) is None
    assert page_p.media_box({"MediaBox": "not-a-rect"}) is None


# ---- size + orientation + rotation + user_unit ----------------------


def test_size_pt_letter():
    assert page_p.size_pt({"MediaBox": [0, 0, 612, 792]}) == (612.0, 792.0)


def test_size_pt_with_user_unit():
    page = {"MediaBox": [0, 0, 100, 100], "UserUnit": 2.0}
    assert page_p.size_pt(page) == (200.0, 200.0)


def test_size_pt_returns_none_without_media_box():
    assert page_p.size_pt({}) is None


def test_orientation_portrait():
    assert page_p.orientation({"MediaBox": [0, 0, 612, 792]}) == "portrait"


def test_orientation_landscape():
    assert page_p.orientation({"MediaBox": [0, 0, 792, 612]}) == "landscape"


def test_orientation_square():
    assert page_p.orientation({"MediaBox": [0, 0, 500, 500]}) == "square"


def test_orientation_honors_rotate_90():
    """A portrait page rotated 90° displays as landscape."""
    page = {"MediaBox": [0, 0, 612, 792], "Rotate": 90}
    assert page_p.orientation(page) == "landscape"


def test_orientation_honors_rotate_270():
    page = {"MediaBox": [0, 0, 792, 612], "Rotate": 270}
    assert page_p.orientation(page) == "portrait"


def test_rotation_normalized():
    assert page_p.rotation({"Rotate": 0}) == 0
    assert page_p.rotation({"Rotate": 90}) == 90
    assert page_p.rotation({"Rotate": 360}) == 0
    assert page_p.rotation({"Rotate": 450}) == 90
    assert page_p.rotation({}) == 0


def test_user_unit_default_one():
    assert page_p.user_unit({}) == 1.0
    assert page_p.user_unit({"UserUnit": 0.5}) == 0.5


# ---- has_oversize_bleed ---------------------------------------------


def test_oversize_bleed_false_when_within_threshold():
    page = {
        "MediaBox": [0, 0, 612, 792],
        "TrimBox": [9, 9, 603, 783],
        "BleedBox": [0, 0, 612, 792],
    }
    # Bleed extends 9pt past trim on every side; default threshold 36pt
    assert page_p.has_oversize_bleed(page) is False


def test_oversize_bleed_true_when_exceeds_threshold():
    page = {
        "MediaBox": [0, 0, 612, 792],
        "TrimBox": [50, 50, 562, 742],
        "BleedBox": [0, 0, 612, 792],
    }
    # Bleed extends 50pt past trim — > 36pt default
    assert page_p.has_oversize_bleed(page) is True


def test_oversize_bleed_custom_threshold():
    page = {
        "MediaBox": [0, 0, 612, 792],
        "TrimBox": [10, 10, 602, 782],
        "BleedBox": [0, 0, 612, 792],
    }
    # 10pt of bleed; threshold 5pt → True
    assert page_p.has_oversize_bleed(page, max_pt=5.0) is True


def test_oversize_bleed_false_when_boxes_missing():
    assert page_p.has_oversize_bleed({}) is False


# ---- doc.* -----------------------------------------------------------


def test_page_count_explicit():
    assert page_p.page_count({"page_count": 5}) == 5
    assert page_p.page_count({"PageCount": 12}) == 12


def test_page_count_from_pages_list():
    assert page_p.page_count({"pages": [1, 2, 3]}) == 3


def test_page_count_from_pages_count_attr():
    pages_dict = {"Count": 7}
    assert page_p.page_count({"Pages": pages_dict}) == 7


def test_page_count_zero_when_unknown():
    assert page_p.page_count({}) == 0
    assert page_p.page_count(None) == 0


def test_has_structure_tree_via_catalog():
    doc = {"Catalog": {"StructTreeRoot": {"K": []}}}
    assert page_p.has_structure_tree(doc) is True


def test_has_structure_tree_direct_on_doc():
    doc = {"StructTreeRoot": {"K": []}}
    assert page_p.has_structure_tree(doc) is True


def test_has_structure_tree_false_when_absent():
    assert page_p.has_structure_tree({}) is False
    assert page_p.has_structure_tree({"Catalog": {}}) is False
