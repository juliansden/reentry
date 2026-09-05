"""Harness run configuration, loaded from TOML."""

from __future__ import annotations

import tomllib
import importlib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from reentry.ccsds.constants import APID_MAX
from reentry.generator.boundary import generate_all
from reentry.harness.profiles import TargetProfile


@lru_cache
def _known_categories() -> frozenset[str]:
    return frozenset(case.category for case in generate_all())


def _validate_categories(value: list[str] | None) -> list[str] | None:
    if value is None or not value:
        return value
    unknown = sorted(set(value) - _known_categories())
    if unknown:
        raise ValueError(
            f"unknown case categories: {', '.join(unknown)}; "
            f"valid categories are: {', '.join(sorted(_known_categories()))}"
        )
    return value


class TransportConfig(BaseModel):
    kind: str = "udp"
    host: str
    port: int
    listen_port: int | None = None
    allowed_reply_host: str | None = None
    allowed_reply_apid: int | None = None
    target_apid: int | None = None
    probe_payload_hex: str = ""

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        if value != "udp":
            raise ValueError(f"unsupported transport kind: {value!r}; only 'udp' is supported")
        return value

    @field_validator("port", "listen_port")
    @classmethod
    def validate_port(cls, value: int | None) -> int | None:
        if value is not None and not 1 <= value <= 65535:
            raise ValueError(f"port must be between 1 and 65535, got {value}")
        return value

    @field_validator("allowed_reply_apid", "target_apid")
    @classmethod
    def validate_apid(cls, value: int | None) -> int | None:
        if value is not None and not 0 <= value <= APID_MAX:
            raise ValueError(f"APID must be between 0 and {APID_MAX}, got {value}")
        return value

    @field_validator("probe_payload_hex")
    @classmethod
    def validate_probe_payload_hex(cls, value: str) -> str:
        try:
            bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError(f"probe_payload_hex must be valid hexadecimal: {exc}") from exc
        return value

    @property
    def probe_payload(self) -> bytes:
        return bytes.fromhex(self.probe_payload_hex)


class OracleConfig(BaseModel):
    # Dotted path to an Oracle subclass, e.g. "reentry.oracle.liveness.LivenessOracle".
    plugin: str = "reentry.oracle.liveness.LivenessOracle"
    args: dict = Field(default_factory=dict)

    @field_validator("plugin")
    @classmethod
    def validate_plugin(cls, value: str) -> str:
        module_path, separator, class_name = value.rpartition(".")
        if not separator or not module_path or not class_name:
            raise ValueError(f"oracle plugin must be an importable dotted path, got {value!r}")
        try:
            module = importlib.import_module(module_path)
            getattr(module, class_name)
        except (ImportError, AttributeError) as exc:
            raise ValueError(f"oracle plugin cannot be imported: {value!r}") from exc
        return value


class RunConfig(BaseModel):
    transport: TransportConfig
    oracle: OracleConfig = OracleConfig()
    profile: TargetProfile | None = None
    health_command: list[str] | None = None
    target_build: str | None = None
    target_version: str | None = None
    resolved_identifiers: dict[str, int | str] = Field(default_factory=dict)
    include_categories: list[str] | None = None
    exclude_categories: list[str] = Field(default_factory=list)
    timeout: float = 2.0

    _validate_include_categories = field_validator("include_categories")(_validate_categories)
    _validate_exclude_categories = field_validator("exclude_categories")(_validate_categories)

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError(f"timeout must be greater than 0, got {value}")
        return value

    @field_validator("health_command")
    @classmethod
    def validate_health_command(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and not value:
            raise ValueError("health_command must contain an executable command")
        return value

    @model_validator(mode="after")
    def validate_profile_filters(self) -> "RunConfig":
        if self.profile is not None and (
            self.include_categories is not None or self.exclude_categories
        ):
            raise ValueError(
                "profile cannot be combined with include_categories or exclude_categories"
            )
        return self

    def with_profile(self, profile: TargetProfile) -> "RunConfig":
        """Return this configuration with a CLI-selected profile applied."""
        data = self.model_dump()
        data["profile"] = profile
        return type(self).model_validate(data)

    @classmethod
    def from_toml(cls, path: str | Path) -> "RunConfig":
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)
