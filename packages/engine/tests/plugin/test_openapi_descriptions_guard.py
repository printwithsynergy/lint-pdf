"""Unit tests for scripts/check_openapi_descriptions.py — the regex.

We don't run the full script (which reads api/schemas.py + a baseline
file from disk); we exercise the pure ``count_undescribed_fields``
function on synthetic input so the contract is locked in.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ENGINE_ROOT / "scripts" / "check_openapi_descriptions.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_openapi_descriptions", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_openapi_descriptions"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_counts_zero_on_well_described_fields():
    mod = _load_module()
    src = """
from pydantic import BaseModel, Field

class Foo(BaseModel):
    a: int = Field(..., description="A.")
    b: str = Field("x", description="B with default.")
"""
    assert mod.count_undescribed_fields(src) == 0


def test_counts_undescribed_fields():
    mod = _load_module()
    src = """
from pydantic import BaseModel, Field

class Foo(BaseModel):
    a: int = Field(...)
    b: str = Field("x")
    c: int = Field(..., description="C.")
"""
    assert mod.count_undescribed_fields(src) == 2


def test_handles_multiline_field_calls():
    mod = _load_module()
    src = """
from pydantic import BaseModel, Field

class Foo(BaseModel):
    a: int = Field(
        ...,
        ge=0,
        le=100,
    )
    b: str = Field(
        "default",
        description=(
            "Multi-line description "
            "with concatenated string."
        ),
    )
"""
    assert mod.count_undescribed_fields(src) == 1


def test_handles_no_field_calls():
    mod = _load_module()
    src = """
from pydantic import BaseModel

class Foo(BaseModel):
    a: int = 1
"""
    assert mod.count_undescribed_fields(src) == 0
