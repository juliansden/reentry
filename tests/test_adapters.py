from reentry.harness.adapters import CI_LAB_CONTRACT, LIVENESS_CONTRACT
from reentry.oracle.base import Verdict
from reentry.oracle.ci_lab import CiLabOracle
from reentry.oracle.liveness import LivenessOracle


def test_liveness_adapter_contract_declares_health_only():
    contract = LivenessOracle.adapter_contract

    assert contract is LIVENESS_CONTRACT
    assert contract.capabilities.reports_target_health is True
    assert contract.capabilities.reports_command_outcome is False
    assert contract.capabilities.enforces_hardened_policy is False
    assert contract.telemetry.fields == ()
    assert contract.verdict_for("no_health_response") == Verdict.HANG


def test_ci_lab_adapter_contract_declares_schema_and_verdict_mapping():
    contract = CiLabOracle.adapter_contract

    assert contract is CI_LAB_CONTRACT
    assert contract.name == "cfs-ci-lab"
    assert contract.telemetry.name == "ci_lab_housekeeping"
    assert contract.telemetry.version == "7.0.1"
    assert "command" in contract.telemetry.fields
    assert contract.required_evidence_fields == ("before", "after")
    assert contract.capabilities.reports_command_outcome is True
    assert contract.capabilities.enforces_hardened_policy is False
    assert contract.verdict_for("command_error_delta") == Verdict.CLEAN_REJECT
    assert contract.verdict_for("command_delta") == Verdict.CLEAN_ACCEPT


def test_contract_reports_missing_evidence_without_requiring_partial_hang_evidence():
    assert CI_LAB_CONTRACT.missing_evidence({"before": {}}) == ("after",)
    assert CI_LAB_CONTRACT.missing_evidence({"before": {}, "after": {}}) == ()
    assert LIVENESS_CONTRACT.missing_evidence({}) == ()


def test_hardened_profile_declares_required_evidence_and_verdicts():
    assert CI_LAB_CONTRACT.evidence_fields_for("hardened-cfs") == ("before", "after")
    assert CI_LAB_CONTRACT.verdicts_for("hardened-cfs") == (
        Verdict.CLEAN_REJECT,
        Verdict.SAFE_DROP,
        Verdict.HANG,
        Verdict.INCONCLUSIVE,
    )
    assert CI_LAB_CONTRACT.requirements_for("hardened-cfs") == (
        "enforces_hardened_policy",
    )


def test_hardened_profile_rejects_adapters_without_required_capabilities():
    assert LIVENESS_CONTRACT.requirements_for("hardened-cfs") == (
        "enforces_hardened_policy",
        "reports_command_outcome",
        "profile evidence",
    )
