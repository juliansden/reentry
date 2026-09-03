"""Harness run configuration, loaded from TOML."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel


class TransportConfig(BaseModel):
    kind: str = "udp"
    host: str
    port: int
    listen_port: int | None = None
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
    include_categories: list[str] | None = None
    exclude_categories: list[str] = []
    timeout: float = 2.0

    @classmethod
    def from_toml(cls, path: str | Path) -> "RunConfig":
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)
