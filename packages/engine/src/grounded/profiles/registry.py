"""Profile registry - manages available voyage plans."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grounded.profiles.schema import VoyagePlan

_BUILTIN_DIR = Path(__file__).parent / "builtin"


class ProfileNotFoundError(Exception):
    """Raised when a profile ID is not found."""


class ProfileRegistry:
    """Registry of available voyage plan profiles.

    Loads built-in profiles from JSON files on first access
    and supports registering custom profiles at runtime.
    """

    def __init__(self) -> None:
        self._profiles: dict[str, VoyagePlan] = {}
        self._loaded_builtins = False

    def _ensure_builtins(self) -> None:
        if self._loaded_builtins:
            return
        self._loaded_builtins = True
        if _BUILTIN_DIR.is_dir():
            for path in sorted(_BUILTIN_DIR.glob("*.json")):
                self._load_builtin(path)

    def _load_builtin(self, path: Path) -> None:
        from grounded.profiles.schema import VoyagePlan

        data = json.loads(path.read_text(encoding="utf-8"))
        profile = VoyagePlan.model_validate(data)
        profile_id = path.stem
        self._profiles[profile_id] = profile

    def register(self, profile_id: str, voyage_plan: VoyagePlan) -> None:
        """Register a voyage plan under the given ID."""
        self._profiles[profile_id] = voyage_plan

    def get(self, profile_id: str) -> VoyagePlan:
        """Retrieve a voyage plan by ID."""
        self._ensure_builtins()
        if profile_id not in self._profiles:
            raise ProfileNotFoundError(f"Profile '{profile_id}' not found")
        return self._profiles[profile_id]

    def list_profiles(self) -> list[str]:
        """List all registered profile IDs."""
        self._ensure_builtins()
        return sorted(self._profiles.keys())

    def has(self, profile_id: str) -> bool:
        """Check if a profile ID exists."""
        self._ensure_builtins()
        return profile_id in self._profiles
