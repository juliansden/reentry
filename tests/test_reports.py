import json
from xml.etree.ElementTree import fromstring

from reentry.generator.cases import PacketCase
from reentry.harness.runner import Finding
from reentry.harness.profiles import TargetProfile
from reentry.oracle.base import Verdict
from reentry.report.json_report import to_json
from reentry.report.junit_report import to_junit_xml


def _finding(name: str, verdict: Verdict, evidence: dict | None = None) -> Finding:
    return Finding(
        case=PacketCase(name, "known_good", b"packet", False, expect_accept=True),
        verdict=verdict,
        detail="CommandCounter increased from 0 to 1",
        evidence={} if evidence is None else evidence,
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
    assert report["profile"] is None


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


def test_junit_report_preserves_every_verdict_and_structured_evidence():
    evidence = {"before": {"command": 2}, "after": {"command": 2}}
    xml = to_junit_xml(
        [
            _finding("rejected", Verdict.CLEAN_REJECT, evidence),
            _finding("dropped", Verdict.SAFE_DROP, evidence),
            _finding("inconclusive", Verdict.INCONCLUSIVE, evidence),
        ]
    )
    cases = {case.attrib["name"]: case for case in fromstring(xml).findall("testcase")}

    for name, verdict in (
        ("rejected", Verdict.CLEAN_REJECT),
        ("dropped", Verdict.SAFE_DROP),
        ("inconclusive", Verdict.INCONCLUSIVE),
    ):
        output = json.loads(cases[name].findtext("system-out", default=""))
        assert output["verdict"] == verdict.value
        assert output["evidence"] == evidence
        assert cases[name].find("failure") is None


def test_reports_preserve_profile_and_all_verdict_semantics():
    findings = [_finding(verdict.value, verdict) for verdict in Verdict]

    report = json.loads(to_json(findings, profile=TargetProfile.HARDENED_CFS))
    xml = to_junit_xml(findings, profile=TargetProfile.HARDENED_CFS)

    assert report["profile"] == "hardened-cfs"
    assert {finding["verdict"] for finding in report["findings"]} == {
        verdict.value for verdict in Verdict
    }
    assert 'name="reentry.profile" value="hardened-cfs"' in xml
    assert 'failures="3"' in xml
    for verdict in (Verdict.CLEAN_ACCEPT, Verdict.CLEAN_REJECT, Verdict.SAFE_DROP, Verdict.INCONCLUSIVE):
        assert f'name="{verdict.value}"' in xml