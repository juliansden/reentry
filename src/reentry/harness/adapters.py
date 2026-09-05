"""Contracts describing target adapters and the evidence they provide."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from reentry.oracle.base import Verdict


@dataclass(frozen=True)
class TelemetrySchema:
    """Stable identity and fields for an adapter's telemetry evidence."""

    name: str
    version: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class AdapterCapabilities:
    """Observable behaviors an adapter can support without inference."""

    reports_command_outcome: bool
    reports_target_health: bool
    enforces_hardened_policy: bool


@dataclass(frozen=True)
class AdapterContract:
    """Declarative contract for an oracle-backed target adapter."""

    name: str
    telemetry: TelemetrySchema
    capabilities: AdapterCapabilities
    required_evidence_fields: tuple[str, ...]
    verdict_mapping: tuple[tuple[str, Verdict], ...]
    supported_profiles: tuple[str, ...]
    profile_evidence_fields: tuple[tuple[str, tuple[str, ...]], ...] = ()
    profile_verdicts: tuple[tuple[str, tuple[Verdict, ...]], ...] = ()

    def requirements_for(self, profile: str) -> tuple[str, ...]:
        """Return capability or evidence requirements for a named profile."""
        if profile == "hardened-cfs":
            requirements = ["enforces_hardened_policy"]
            if not self.capabilities.reports_command_outcome:
                requirements.append("reports_command_outcome")
            evidence = self.evidence_fields_for(profile)
            if not evidence:
                requirements.append("profile evidence")
            return tuple(requirements)
        if profile not in self.supported_profiles:
            return (f"supports profile {profile!r}",)
        return ()

    def evidence_fields_for(self, profile: str) -> tuple[str, ...]:
        return dict(self.profile_evidence_fields).get(profile, self.required_evidence_fields)

    def verdicts_for(self, profile: str) -> tuple[Verdict, ...]:
        return dict(self.profile_verdicts).get(profile, tuple(Verdict))

    def validate_profile(self, profile: str) -> None:
        missing = self.requirements_for(profile)
        if missing:
            raise ValueError(
                f"adapter {self.name!r} cannot run profile {profile!r}; "
                f"missing {', '.join(missing)}"
            )

    def verdict_for(self, signal: str) -> Verdict | None:
        return dict(self.verdict_mapping).get(signal)

    def missing_evidence(self, evidence: Mapping[str, object]) -> tuple[str, ...]:
        return tuple(field for field in self.required_evidence_fields if field not in evidence)


LIVENESS_CONTRACT = AdapterContract(
    name="generic-liveness",
    telemetry=TelemetrySchema(name="none", version="1", fields=()),
    capabilities=AdapterCapabilities(
        reports_command_outcome=False,
        reports_target_health=True,
        enforces_hardened_policy=False,
    ),
    required_evidence_fields=(),
    verdict_mapping=(
        ("no_health_response", Verdict.HANG),
        ("health_response", Verdict.INCONCLUSIVE),
    ),
    supported_profiles=("smoke", "stock-cfs", "hardened-cfs", "full-robustness"),
    profile_verdicts=(
        ("smoke", (Verdict.INCONCLUSIVE, Verdict.HANG)),
    ),
)


CI_LAB_CONTRACT = AdapterContract(
    name="cfs-ci-lab",
    telemetry=TelemetrySchema(
        name="ci_lab_housekeeping",
        version="7.0.1",
        fields=(
            "command",
            "command_error",
            "enable_checksums",
            "socket_connected",
            "ingest_packets",
            "ingest_errors",
        ),
    ),
    capabilities=AdapterCapabilities(
        reports_command_outcome=True,
        reports_target_health=True,
        enforces_hardened_policy=False,
    ),
    required_evidence_fields=("before", "after"),
    verdict_mapping=(
        ("command_error_delta", Verdict.CLEAN_REJECT),
        ("ingest_error_delta", Verdict.SAFE_DROP),
        ("command_delta", Verdict.CLEAN_ACCEPT),
        ("missing_after_telemetry", Verdict.HANG),
        ("transport_failure", Verdict.INCONCLUSIVE),
    ),
    supported_profiles=("smoke", "stock-cfs", "hardened-cfs", "full-robustness"),
    profile_evidence_fields=(
        ("hardened-cfs", ("before", "after")),
    ),
    profile_verdicts=(
        (
            "hardened-cfs",
            (Verdict.CLEAN_REJECT, Verdict.SAFE_DROP, Verdict.HANG, Verdict.INCONCLUSIVE),
        ),
    ),
)
