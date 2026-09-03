"""Serialize findings to JSON for machine consumption / archival."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from reentry.harness.runner import Finding


def to_json(findings: list[Finding]) -> str:
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "findings": [
            {
                "name": f.case.name,
                "category": f.case.category,
                "verdict": f.verdict.value,
                "detail": f.detail,
                "expect_safe_reject": f.case.expect_safe_reject,
            }
            for f in findings
        ],
    }
    return json.dumps(payload, indent=2)
