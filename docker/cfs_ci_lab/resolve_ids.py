"""Extract ci_lab's real, build-resolved MID/APID/port values — never guessed.

CI_LAB_CMD_MID / CI_LAB_SEND_HK_MID are computed at build time from the mission's
msgid mapping table. The Docker image exports those values as JSON after compiling
against the generated headers, so this script does not recreate cFS macro expansion
rules on the host.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Macro names we need resolved numeric values for.
WANTED_DEFINES = (
    "CI_LAB_CMD_MID",
    "CI_LAB_SEND_HK_MID",
    "CI_LAB_HK_TLM_MID",
    "CI_LAB_CMD_UDP_PORT",
    "TO_LAB_CMD_MID",
    "TO_LAB_TLM_PORT",
)

def find_resolved_defines(build_tree: Path) -> dict[str, int]:
    artifacts = sorted(build_tree.rglob("ci_lab_ids.json"))
    if not artifacts:
        return {}
    try:
        values = json.loads(artifacts[0].read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read {artifacts[0]}: {exc}") from exc
    if not isinstance(values, dict):
        raise ValueError(f"expected an object in {artifacts[0]}")
    return {
        name: value
        for name in WANTED_DEFINES
        if isinstance((value := values.get(name)), int) and not isinstance(value, bool)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_tree", type=Path, help="Path to the cFS build/install tree")
    parser.add_argument("output", type=Path, help="Path to write resolved_ids.json")
    args = parser.parse_args()

    try:
        found = find_resolved_defines(args.build_tree)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    missing = [name for name in WANTED_DEFINES if name not in found]
    if missing:
        print(f"error: could not resolve {missing} under {args.build_tree}", file=sys.stderr)

    args.output.write_text(json.dumps(found, indent=2) + "\n")
    if missing:
        print(f"wrote partial {args.output} with {found}", file=sys.stderr)
    else:
        print(f"wrote {args.output} with {found}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
