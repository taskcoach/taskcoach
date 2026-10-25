"""
Task Coach - Your friendly task manager
Copyright (C) 2026 Task Coach developers <developers@taskcoach.org>

Task Coach is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Task Coach is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import ast
import os
import re

import test
from taskcoachlib.config import defaults
from tools import welcome_colours

_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def _read(name):
    with open(os.path.join(_ROOT, name), encoding="utf-8", newline="") as file:
        return file.read()


def _items(text):
    """Each task, category and note: its attributes."""
    return [
        dict(re.findall(r'(\w+)="([^"]*)"', tag))
        for tag in re.findall(r"<(?:task|category|note) [^>]*>", text)
    ]


def _colours(section):
    return [
        ast.literal_eval(value)[:3]
        for value in defaults.defaults[section].values()
    ]


class WelcomeFilesTest(test.TestCase):
    """The light and dark Welcome demo files (docs/WELCOME_FILES.md)."""

    def assert_rows_readable(self, name, text_section, row_section):
        # A row's status text keeps nine tenths of the contrast it has
        # on a plain row, whatever its status
        texts, rows = _colours(text_section), _colours(row_section)
        for item in _items(_read(name)):
            if "bgColor" not in item or "fgColor" in item:
                continue
            background = ast.literal_eval(item["bgColor"])[:3]
            for text in texts:
                plain = min(
                    welcome_colours.contrast(text, row) for row in rows
                )
                self.assertGreaterEqual(
                    welcome_colours.contrast(text, background),
                    0.9 * plain - 0.005,
                    "%s: %s on %s" % (name, item["subject"], item["bgColor"]),
                )

    def test_both_files_are_the_script_output(self):
        light, dark = welcome_colours.welcome_files(_read("Welcome.tsk"))
        self.assertEqual(_read("Welcome.tsk"), light)
        self.assertEqual(_read("Welcome-dark.tsk"), dark)

    def test_light_rows_readable_with_the_light_status_colours(self):
        self.assert_rows_readable("Welcome.tsk", "fgcolor", "bgcolor")

    def test_dark_rows_readable_with_the_dark_status_colours(self):
        self.assert_rows_readable(
            "Welcome-dark.tsk", "fgcolor_dark", "bgcolor_dark"
        )

    def test_an_own_colour_pair_is_the_same_in_both_files(self):
        def pairs(name):
            return [
                (item["subject"], item["fgColor"], item.get("bgColor"))
                for item in _items(_read(name))
                if "fgColor" in item
            ]

        self.assertTrue(pairs("Welcome.tsk"))
        self.assertEqual(pairs("Welcome.tsk"), pairs("Welcome-dark.tsk"))

    def test_the_files_differ_in_background_colours_only(self):
        def without_backgrounds(name):
            return re.sub(r' bgColor="[^"]*"', "", _read(name))

        self.assertEqual(
            without_backgrounds("Welcome.tsk"),
            without_backgrounds("Welcome-dark.tsk"),
        )
