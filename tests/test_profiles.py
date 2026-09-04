import pytest
from pydantic import ValidationError

from reentry.harness.config import RunConfig, TransportConfig
from reentry.harness.profiles import TargetProfile, categories_for_profile
from reentry.harness.runner import _select_cases


def _config(**overrides) -> RunConfig:
    return RunConfig(transport=TransportConfig(host="127.0.0.1", port=1234), **overrides)


def test_smoke_profile_selects_only_known_good_control():
    cases = _select_cases(_config(profile=TargetProfile.SMOKE))

    assert [case.name for case in cases] == ["ci_lab_noop"]


@pytest.mark.parametrize(
    "profile",
    [
        TargetProfile.STOCK_CFS,
        TargetProfile.HARDENED_CFS,
        TargetProfile.FULL_ROBUSTNESS,
    ],
)
def test_complete_profiles_select_every_generated_category(profile):
    cases = _select_cases(_config(profile=profile))

    assert categories_for_profile(profile) is None
    assert {case.category for case in cases} == {
        "known_good",
        "command_malformed",
        "version",
        "apid",
        "seq_flags",
        "packet_length",
        "secondary_header",
        "truncation",
        "oversized",
        "degenerate_payload",
    }


def test_profile_cannot_be_combined_with_category_filters():
    with pytest.raises(ValidationError, match="profile cannot be combined"):
        _config(profile=TargetProfile.SMOKE, include_categories=["known_good"])


def test_unknown_profile_is_rejected():
    with pytest.raises(ValidationError):
        _config(profile="not-a-profile")