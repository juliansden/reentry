"""Map findings to JUnit XML so CI systems can surface them as test results."""

from __future__ import annotations

import json
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

from reentry.harness.profiles import TargetProfile
from reentry.harness.runner import Finding


def to_junit_xml(findings: list[Finding], profile: TargetProfile | None = None) -> str:
    failures = sum(1 for f in findings if f.verdict.is_unsafe)
    suite = Element(
        "testsuite",
        name="reentry",
        tests=str(len(findings)),
        failures=str(failures),
    )
    if profile is not None:
        properties = SubElement(suite, "properties")
        SubElement(properties, "property", name="reentry.profile", value=profile.value)
    for f in findings:
        case_el = SubElement(
            suite,
            "testcase",
            name=f.case.name,
            classname=f"reentry.{f.case.category}",
        )
        SubElement(case_el, "system-out").text = json.dumps(
            {
                "verdict": f.verdict.value,
                "detail": f.detail,
                "evidence": f.evidence,
                "transport_error": f.transport_error,
            },
            sort_keys=True,
        )
        if f.verdict.is_unsafe:
            failure_el = SubElement(case_el, "failure", message=f.verdict.value)
            failure_el.text = f.detail

    return parseString(tostring(suite)).toprettyxml(indent="  ")
