import pytest
from pydantic import ValidationError

from reentry.ccsds.constants import APID_MAX
from reentry.harness.config import OracleConfig, RunConfig, TransportConfig


def _transport(**overrides) -> TransportConfig:
    values = {"host": "127.0.0.1", "port": 1234}
    values.update(overrides)
    return TransportConfig(**values)


def _config(**overrides) -> RunConfig:
    return RunConfig(transport=_transport(), **overrides)


@pytest.mark.parametrize("field", ["port", "listen_port"])
@pytest.mark.parametrize("value", [0, 65536])
def test_invalid_port_is_rejected(field, value):
    with pytest.raises(ValidationError, match="between 1 and 65535"):
        _transport(**{field: value})


def test_port_boundaries_are_valid():
    assert _transport(port=1, listen_port=65535).port == 1


def test_invalid_probe_payload_hex_is_rejected():
    with pytest.raises(ValidationError, match="valid hexadecimal"):
        _transport(probe_payload_hex="not-hex")


@pytest.mark.parametrize("field", ["allowed_reply_apid", "target_apid"])
@pytest.mark.parametrize("value", [-1, APID_MAX + 1])
def test_invalid_apid_is_rejected(field, value):
    with pytest.raises(ValidationError, match=f"between 0 and {APID_MAX}"):
        _transport(**{field: value})


def test_invalid_timeout_is_rejected():
    with pytest.raises(ValidationError, match="greater than 0"):
        _config(timeout=0)


def test_empty_health_command_is_rejected():
    with pytest.raises(ValidationError, match="health_command must contain"):
        _config(health_command=[])


def test_target_provenance_fields_are_preserved():
    config = _config(
        target_build="cfs-abc123",
        target_version="7.0.1",
        resolved_identifiers={"CI_LAB_CMD_MID": 0x1880},
    )

    assert config.target_build == "cfs-abc123"
    assert config.target_version == "7.0.1"
    assert config.resolved_identifiers["CI_LAB_CMD_MID"] == 0x1880


def test_invalid_transport_kind_is_rejected():
    with pytest.raises(ValidationError, match="only 'udp' is supported"):
        _transport(kind="tcp")


@pytest.mark.parametrize("field", ["include_categories", "exclude_categories"])
def test_unknown_category_is_rejected(field):
    with pytest.raises(ValidationError, match="unknown case categories"):
        _config(**{field: ["not-a-real-category"]})


def test_empty_exclude_categories_skips_category_lookup(monkeypatch):
    monkeypatch.setattr(
        "reentry.harness.config._known_categories",
        lambda: (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    _config(exclude_categories=[])


def test_oracle_plugin_must_be_importable():
    with pytest.raises(ValidationError, match="cannot be imported"):
        OracleConfig(plugin="reentry.oracle.missing.MissingOracle")


def test_oracle_plugin_must_be_dotted_path():
    with pytest.raises(ValidationError, match="importable dotted path"):
        OracleConfig(plugin="missing")
