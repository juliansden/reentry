"""Compare JSON run reports for CI regression checks."""

from __future__ import annotations


def _findings_by_name(report_name: str, report: dict) -> dict[str, dict[str, str]]:
    findings = report.get("findings")
    if not isinstance(findings, list):
        raise ValueError(f"{report_name} report must contain a 'findings' list")

    cases: dict[str, dict[str, str]] = {}
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ValueError(f"{report_name} finding at index {index} must be an object")
        name = finding.get("name")
        verdict = finding.get("verdict")
        if not isinstance(name, str) or not name:
            raise ValueError(
                f"{report_name} finding at index {index} must contain a non-empty string 'name'"
            )
        if not isinstance(verdict, str) or not verdict:
            raise ValueError(
                f"{report_name} finding {name!r} must contain a non-empty string 'verdict'"
            )
        if name in cases:
            raise ValueError(f"{report_name} report contains duplicate finding name {name!r}")
        cases[name] = {"name": name, "verdict": verdict}
    return cases


def compare_reports(baseline: dict, actual: dict) -> list[dict[str, str | None]]:
    """Return deterministic differences in case presence or verdicts."""
    baseline_cases = _findings_by_name("baseline", baseline)
    actual_cases = _findings_by_name("actual", actual)
    differences: list[dict[str, str | None]] = []

    for name in sorted(baseline_cases.keys() - actual_cases.keys()):
        differences.append(
            {
                "kind": "missing_case",
                "name": name,
                "baseline": baseline_cases[name]["verdict"],
                "actual": None,
            }
        )
    for name in sorted(actual_cases.keys() - baseline_cases.keys()):
        differences.append(
            {
                "kind": "new_case",
                "name": name,
                "baseline": None,
                "actual": actual_cases[name]["verdict"],
            }
        )
    for name in sorted(baseline_cases.keys() & actual_cases.keys()):
        baseline_verdict = baseline_cases[name]["verdict"]
        actual_verdict = actual_cases[name]["verdict"]
        if baseline_verdict != actual_verdict:
            differences.append(
                {
                    "kind": "verdict_changed",
                    "name": name,
                    "baseline": baseline_verdict,
                    "actual": actual_verdict,
                }
            )
    return differences