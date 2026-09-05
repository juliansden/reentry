"""Compare JSON run reports for CI regression checks."""

from __future__ import annotations


def compare_reports(baseline: dict, actual: dict) -> list[dict[str, str | None]]:
    """Return deterministic differences in case presence or verdicts."""
    baseline_cases = {finding["name"]: finding for finding in baseline.get("findings", [])}
    actual_cases = {finding["name"]: finding for finding in actual.get("findings", [])}
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