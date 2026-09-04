"""Harness run configuration, loaded from TOML."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, model_validator

from reentry.harness.profiles import TargetProfile


class TransportConfig(BaseModel):
    kind: str = "udp"
    host: str
    port: int
    listen_port: int | None = None
    allowed_reply_host: str | None = None
    allowed_reply_apid: int | None = None
    target_apid: int | None = None
    probe_payload_hex: str = ""

    @property
    def probe_payload(self) -> bytes:
        return bytes.fromhex(self.probe_payload_hex)


class OracleConfig(BaseModel):
    # Dotted path to an Oracle subclass, e.g. "reentry.oracle.liveness.LivenessOracle".
    plugin: str = "reentry.oracle.liveness.LivenessOracle"
    args: dict = {}


class RunConfig(BaseModel):
    transport: TransportConfig
    oracle: OracleConfig = OracleConfig()
    profile: TargetProfile | None = None
    include_categories: list[str] | None = None
    exclude_categories: list[str] = []
    timeout: float = 2.0

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
