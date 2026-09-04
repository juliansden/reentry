"""Named, reproducible target profiles for common harness runs."""

from __future__ import annotations

from enum import Enum


class TargetProfile(str, Enum):
    """Stable names for documented target-profile behavior."""

    STOCK_CFS = "stock-cfs"
    HARDENED_CFS = "hardened-cfs"
    SMOKE = "smoke"
    FULL_ROBUSTNESS = "full-robustness"


_PROFILE_CATEGORIES: dict[TargetProfile, tuple[str, ...] | None] = {
    TargetProfile.STOCK_CFS: None,
    TargetProfile.HARDENED_CFS: None,
    TargetProfile.SMOKE: ("known_good",),
    TargetProfile.FULL_ROBUSTNESS: None,
}


def categories_for_profile(profile: TargetProfile) -> tuple[str, ...] | None:
    """Return the categories selected by a named profile, or all categories."""
    return _PROFILE_CATEGORIES[profile]