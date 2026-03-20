"""Tests for AI preset definitions."""

from __future__ import annotations


# skipcq: PYL-R0201
class TestAIPresets:
    """Tests for the preset data defined in ai_presets.py."""

    def test_all_seven_presets_exist(self) -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        assert len(_AI_PRESETS) == 7

    def test_expected_preset_slugs(self) -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        expected = {
            "fda-food-label",
            "eu-food-label",
            "pharma-eu",
            "ghs-chemical",
            "packaging-qc",
            "brand-compliance",
            "full-ai-scan",
        }
        assert set(_AI_PRESETS.keys()) == expected

    def test_each_preset_has_required_fields(self) -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        for slug, data in _AI_PRESETS.items():
            assert "name" in data, f"Preset {slug} missing 'name'"
            assert "description" in data, f"Preset {slug} missing 'description'"
            assert "features" in data, f"Preset {slug} missing 'features'"

    def test_each_preset_has_features(self) -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        for slug, data in _AI_PRESETS.items():
            features = data["features"]
            assert isinstance(features, list), f"Preset {slug} features is not a list"
            assert len(features) > 0, f"Preset {slug} has no features"

    def test_full_ai_scan_has_all(self) -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        features = _AI_PRESETS["full-ai-scan"]["features"]
        assert features == ["all"]

    def test_fda_food_label_features(self) -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        features = _AI_PRESETS["fda-food-label"]["features"]
        assert "fda_nutrition_facts" in features
        assert "barcode_decode" in features
        assert "spell_check" in features

    def test_packaging_qc_features(self) -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        features = _AI_PRESETS["packaging-qc"]["features"]
        assert "dieline_by_name" in features
        assert "barcode_decode" in features
        assert "logo_detection" in features
        assert "duplicate_detection" in features

    def test_brand_compliance_features(self) -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        features = _AI_PRESETS["brand-compliance"]["features"]
        assert "brand_palette_check" in features
        assert "logo_detection" in features
        assert "spell_check" in features

    def test_preset_names_are_non_empty_strings(self) -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        for _slug, data in _AI_PRESETS.items():
            name = data["name"]
            assert isinstance(name, str) and len(name) > 0

    def test_preset_descriptions_are_non_empty_strings(self) -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        for _slug, data in _AI_PRESETS.items():
            desc = data["description"]
            assert isinstance(desc, str) and len(desc) > 0


class TestGetFeatureInfo:
    """Tests for the _get_feature_info helper."""

    def test_returns_unknown_for_unregistered_feature(self) -> None:
        from grounded.api.routes.ai_presets import _get_feature_info

        info = _get_feature_info("nonexistent_feature")
        assert info.slug == "nonexistent_feature"
        assert info.category == "unknown"
        assert info.tier == "unknown"
