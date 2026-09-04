"""Serialize findings to JSON for machine consumption / archival."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from reentry.harness.profiles import TargetProfile
from reentry.harness.runner import Finding


def to_json(findings: list[Finding], profile: TargetProfile | None = None) -> str:
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "profile": profile.value if profile is not None else None,
        "findings": [
            {
                "name": f.case.name,
                "category": f.case.category,
                "verdict": f.verdict.value,
                "detail": f.detail,
                "expect_safe_reject": f.case.expect_safe_reject,
                "expect_accept": f.case.expect_accept,
                "evidence": f.evidence,
                "transport_error": f.transport_error,
            }
            for f in findings
        ],
    }
    return json.dumps(payload, indent=2)
