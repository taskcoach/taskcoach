#!/usr/bin/env python3
"""Print a release's section of CHANGELOG.md, the text of its GitHub
release page (docs/PACKAGING.md#release-notes).

    python3 tools/release_notes.py v2.0.3.0

Stops with an error when the section is missing or empty."""

import os
import sys

CHANGELOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "CHANGELOG.md",
)


def section(text, version):
    """The text under the version's heading, up to the next one; None
    when there is none."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "## " + version:
            body = []
            for line in lines[index + 1 :]:
                if line.startswith("## "):
                    break
                body.append(line)
            return "\n".join(body).strip() or None
    return None


def main(tag):
    version = tag.removeprefix("v")
    with open(CHANGELOG, encoding="utf-8") as changelog:
        notes = section(changelog.read(), version)
    if notes is None:
        sys.exit("CHANGELOG.md has no section for %s" % version)
    print(notes)


if __name__ == "__main__":
    main(sys.argv[1])
