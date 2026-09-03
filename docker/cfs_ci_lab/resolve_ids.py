"""Extracts ci_lab's real, build-resolved MID/APID/port values — never guessed.

CI_LAB_CMD_MID / CI_LAB_SEND_HK_MID are NOT fixed constants in ci_lab's source; their
numeric values are computed at build time from the mission's msgid mapping table. The
only trustworthy source for the actual numbers is the generated headers produced by a
real `make native_std.install` build, so this script searches the install tree for them
instead of assuming one fixed path (the exact generated header layout should be
confirmed/adjusted against a real build the first time this runs in anger).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Macro names we need resolved numeric values for.
WANTED_DEFINES = (
    "CI_LAB_CMD_MID",
    "CI_LAB_SEND_HK_MID",
    "CI_LAB_CMD_UDP_PORT",
)

DEFINE_RE = re.compile(r"^\s*#define\s+(\w+)\s+(?:\(?\s*(0x[0-9A-Fa-f]+|\d+)\s*\)?)\s*(?:/\*.*\*/)?\s*$")


def find_resolved_defines(build_tree: Path) -> dict[str, int]:
    found: dict[str, int] = {}
    for header in build_tree.rglob("*.h"):
        try:
            lines = header.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for line in lines:
            match = DEFINE_RE.match(line)
            if not match:
                continue
            name, value = match.groups()
            if name in WANTED_DEFINES and name not in found:
                found[name] = int(value, 0)
        if len(found) == len(WANTED_DEFINES):
            break
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_tree", type=Path, help="Path to the cFS build/install tree")
    parser.add_argument("output", type=Path, help="Path to write resolved_ids.json")
    args = parser.parse_args()

    found = find_resolved_defines(args.build_tree)
    missing = [name for name in WANTED_DEFINES if name not in found]
    if missing:
        print(f"warning: could not resolve {missing} under {args.build_tree}", file=sys.stderr)

    args.output.write_text(json.dumps(found, indent=2))
    print(f"wrote {args.output} with {found}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
