"""Map findings to JUnit XML so CI systems can surface them as test results."""

from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

from reentry.harness.runner import Finding
from reentry.oracle.base import Verdict


def to_junit_xml(findings: list[Finding]) -> str:
    failures = sum(1 for f in findings if f.verdict.is_unsafe)
    suite = Element(
        "testsuite",
        name="reentry",
        tests=str(len(findings)),
        failures=str(failures),
    )
    for f in findings:
        case_el = SubElement(
            suite,
            "testcase",
            name=f.case.name,
            classname=f"reentry.{f.case.category}",
        )
        if f.verdict.is_unsafe:
            failure_el = SubElement(case_el, "failure", message=f.verdict.value)
            failure_el.text = f.detail
        elif f.verdict in (Verdict.CLEAN_ACCEPT, Verdict.INCONCLUSIVE):
            SubElement(case_el, "system-out").text = f.detail

    return parseString(tostring(suite)).toprettyxml(indent="  ")
