"""Stable provenance metadata for machine-readable run reports."""

from __future__ import annotations

import hashlib
import importlib
import json
from importlib.metadata import version

from reentry.harness.config import RunConfig


def build_provenance(config: RunConfig) -> dict[str, object]:
    module_path, _, class_name = config.oracle.plugin.rpartition(".")
    oracle_class = getattr(importlib.import_module(module_path), class_name)
    contract = getattr(oracle_class, "adapter_contract", None)
    config_data = config.model_dump(mode="json")
    config_hash = hashlib.sha256(
        json.dumps(config_data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "harness_version": version("reentry"),
        "target_build": config.target_build,
        "target_version": config.target_version,
        "resolved_identifiers": config.resolved_identifiers,
        "configuration_hash": config_hash,
        "adapter": contract.name if contract is not None else config.oracle.plugin,
        "telemetry_schema": (
            {
                "name": contract.telemetry.name,
                "version": contract.telemetry.version,
                "fields": list(contract.telemetry.fields),
            }
            if contract is not None
            else None
        ),
    }