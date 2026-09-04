import json

from reentry.generator.cases import PacketCase
from reentry.harness.runner import Finding
from reentry.oracle.base import Verdict
from reentry.report.json_report import to_json
from reentry.report.junit_report import to_junit_xml


def _finding(name: str, verdict: Verdict) -> Finding:
    return Finding(
        case=PacketCase(name, "known_good", b"packet", False, expect_accept=True),
        verdict=verdict,
        detail="CommandCounter increased from 0 to 1",
    )


def test_json_report_identifies_known_good_acceptance():
    report = json.loads(to_json([_finding("ci_lab_noop", Verdict.CLEAN_ACCEPT)]))

    assert report["findings"] == [
        {
            "name": "ci_lab_noop",
            "category": "known_good",
            "verdict": "clean_accept",
            "detail": "CommandCounter increased from 0 to 1",
            "expect_safe_reject": False,
            "expect_accept": True,
            "evidence": {},
        }
    ]


def test_junit_report_only_marks_unsafe_findings_as_failures():
    xml = to_junit_xml(
        [
            _finding("ci_lab_noop", Verdict.CLEAN_ACCEPT),
            _finding("bad_packet", Verdict.INCONCLUSIVE),
            _finding("crash", Verdict.CRASH),
        ]
    )

    assert 'tests="3"' in xml
    assert 'failures="1"' in xml
    assert 'name="crash"' in xml
    assert 'name="ci_lab_noop"' in xml
    assert "CommandCounter increased from 0 to 1" in xml