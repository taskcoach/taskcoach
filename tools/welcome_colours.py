#!/usr/bin/env python3
"""Write the background colours of the two Welcome demo files.

    python3 tools/welcome_colours.py

Welcome.tsk is the demo for the light theme, Welcome-dark.tsk the same
file for the dark one (docs/WELCOME_FILES.md). Each coloured category
keeps its hue (PALETTE): lightened toward white for the light file,
darkened toward black for the dark one, until a text colour keeps at
least KEPT of the contrast it has on that theme's plain rows (the
status backgrounds in config/defaults.py). For text darker than both
backgrounds (lighter, in the dark theme), the share kept does not
depend on the text colour, so it holds for any status colours.

An item with its own text colour keeps its colours in both files:
the pair reads the same in either theme. Run again after a change of
PALETTE, KEPT or the status backgrounds; the test suite checks that
both files are this script's output (WelcomeFilesTest).
"""

import ast
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(os.path.join(_ROOT, "taskcoachlib")):
    sys.path.insert(0, _ROOT)

from taskcoachlib.config import defaults  # noqa: E402

LIGHT_FILE = os.path.join(_ROOT, "Welcome.tsk")
DARK_FILE = os.path.join(_ROOT, "Welcome-dark.tsk")

# The share of a text colour's contrast on a plain row that a demo
# background keeps
KEPT = 0.9

# Each coloured category's hue, by its ID in the Welcome file
PALETTE = {
    "3e1eac3a-5487-11e2-8b71-0016cbad0bd0": (143, 240, 164),  # @Home
    "42afb411-5487-11e2-8fc4-0016cbad0bd0": (249, 240, 107),  # @Work
    "493027fd-5487-11e2-8d2d-0016cbad0bd0": (255, 204, 153),  # @Errands
    "f010930a-f40f-11f0-b2c5-24418c661769": (173, 216, 230),  # @Computer
    "f010930b-f40f-11f0-b2c5-24418c661769": (255, 182, 193),  # @Phone
    "80f0f933-5487-11e2-ba71-0016cbad0bd0": (153, 193, 241),  # Priority
    "107f6994-5488-11e2-a61b-0016cbad0bd0": (255, 102, 102),  # High
    "f010980c-f40f-11f0-b2c5-24418c661769": (255, 204, 0),  # Medium
    "f010980d-f40f-11f0-b2c5-24418c661769": (144, 238, 144),  # Low
    "9f760359-5463-11e2-acc6-0016cbad0bd0": (220, 138, 221),  # Projects
    "ac9c1023-5463-11e2-bb73-0016cbad0bd0": (135, 206, 250),  # Website
    "b21a4eb3-5463-11e2-8de1-0016cbad0bd0": (255, 218, 185),  # Personal
    "f010980e-f40f-11f0-b2c5-24418c661769": (200, 200, 200),  # Status Tags
    "f010980f-f40f-11f0-b2c5-24418c661769": (255, 255, 153),  # Waiting For
    "f0109810-f40f-11f0-b2c5-24418c661769": (221, 160, 221),  # Someday
    "f0109811-f40f-11f0-b2c5-24418c661769": (152, 251, 152),  # Next Action
    "3add77b7-6e63-45d8-8a05-28fd12ddd0e7": (255, 255, 153),  # Markdown
}


def luminance(rgb):
    """WCAG 2.0 relative luminance."""

    def channel(value):
        value /= 255
        if value <= 0.03928:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(value) for value in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first, second):
    """WCAG 2.0 contrast ratio."""
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def row_backgrounds(section):
    """A theme's plain row backgrounds: its status backgrounds."""
    return [
        ast.literal_eval(value)[:3]
        for value in defaults.defaults[section].values()
    ]


def light_background(hue, rows=None):
    """The hue toward white, until dark text keeps KEPT of its contrast
    on the lightest plain row."""
    rows = rows or row_backgrounds("bgcolor")
    needed = KEPT * (max(luminance(row) for row in rows) + 0.05) - 0.05
    for step in range(1001):
        share = step / 1000
        colour = tuple(round(c + (255 - c) * share) for c in hue)
        if luminance(colour) >= needed:
            return colour
    return (255, 255, 255)


def dark_background(hue, rows=None):
    """The hue toward black, until light text keeps KEPT of its contrast
    on the darkest plain row."""
    rows = rows or row_backgrounds("bgcolor_dark")
    allowed = (min(luminance(row) for row in rows) + 0.05) / KEPT - 0.05
    for step in range(1000, -1, -1):
        colour = tuple(round(c * step / 1000) for c in hue)
        if luminance(colour) <= allowed:
            return colour
    return (0, 0, 0)


def welcome_files(text):
    """The light and the dark Welcome file, from either one's text."""
    light_rows, dark_rows = row_backgrounds("bgcolor"), row_backgrounds(
        "bgcolor_dark"
    )

    def recoloured(dark):
        def tag(match):
            ids = re.findall(r' id="([^"]*)"', match.group(0))
            if not ids or ids[0] not in PALETTE:
                return match.group(0)
            hue = PALETTE[ids[0]]
            colour = (
                dark_background(hue, dark_rows)
                if dark
                else light_background(hue, light_rows)
            )
            return re.sub(
                r' bgColor="[^"]*"',
                ' bgColor="(%d, %d, %d, 255)"' % colour,
                match.group(0),
            )

        return re.sub(r"<(?:task|category|note) [^>]*>", tag, text)

    return recoloured(False), recoloured(True)


def main():
    with open(LIGHT_FILE, encoding="utf-8", newline="") as file:
        light, dark = welcome_files(file.read())
    for path, text in ((LIGHT_FILE, light), (DARK_FILE, dark)):
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.write(text)
        print("Wrote %s" % os.path.relpath(path, _ROOT))


if __name__ == "__main__":
    main()
