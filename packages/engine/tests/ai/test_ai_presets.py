"""Tests for AI preset definitions."""

from __future__ import annotations


class TestAIPresets:
    """Tests for the preset data defined in ai_presets.py."""

    @staticmethod
    def test_all_seven_presets_exist() -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        assert len(_AI_PRESETS) == 7

    @staticmethod
    def test_expected_preset_slugs() -> None:
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

    @staticmethod
    def test_each_preset_has_required_fields() -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        for slug, data in _AI_PRESETS.items():
            assert "name" in data, f"Preset {slug} missing 'name'"
            assert "description" in data, f"Preset {slug} missing 'description'"
            assert "features" in data, f"Preset {slug} missing 'features'"

    @staticmethod
    def test_each_preset_has_features() -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        for slug, data in _AI_PRESETS.items():
            features = data["features"]
            assert isinstance(features, list), f"Preset {slug} features is not a list"
            assert len(features) > 0, f"Preset {slug} has no features"

    @staticmethod
    def test_full_ai_scan_has_all() -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        features = _AI_PRESETS["full-ai-scan"]["features"]
        assert features == ["all"]

    @staticmethod
    def test_fda_food_label_features() -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        features = _AI_PRESETS["fda-food-label"]["features"]
        assert "fda_nutrition_facts" in features
        assert "barcode_decode" in features
        assert "spell_check" in features

    @staticmethod
    def test_packaging_qc_features() -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        features = _AI_PRESETS["packaging-qc"]["features"]
        assert "dieline_by_name" in features
        assert "barcode_decode" in features
        assert "logo_detection" in features
        assert "duplicate_detection" in features

    @staticmethod
    def test_brand_compliance_features() -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        features = _AI_PRESETS["brand-compliance"]["features"]
        assert "brand_palette_check" in features
        assert "logo_detection" in features
        assert "spell_check" in features

    @staticmethod
    def test_preset_names_are_non_empty_strings() -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        for _slug, data in _AI_PRESETS.items():
            name = data["name"]
            assert isinstance(name, str) and len(name) > 0

    @staticmethod
    def test_preset_descriptions_are_non_empty_strings() -> None:
        from grounded.api.routes.ai_presets import _AI_PRESETS

        for _slug, data in _AI_PRESETS.items():
            desc = data["description"]
            assert isinstance(desc, str) and len(desc) > 0


class TestGetFeatureInfo:
    """Tests for the _get_feature_info helper."""

    @staticmethod
    def test_returns_unknown_for_unregistered_feature() -> None:
        from grounded.api.routes.ai_presets import _get_feature_info

        info = _get_feature_info("nonexistent_feature")
        assert info.slug == "nonexistent_feature"
        assert info.category == "unknown"
        assert info.tier == "unknown"
