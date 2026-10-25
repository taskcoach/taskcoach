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

import test
from taskcoachlib.config import defaults
from tools import welcome_colours


def _colour(section, status):
    return ast.literal_eval(defaults.defaults[section]["%stasks" % status])[:3]


class DefaultStatusColoursTest(test.TestCase):
    """The light theme's default status text colours on their default
    background (docs/TASK_STATUS.md, Default Colours)."""

    def contrast(self, status):
        return welcome_colours.contrast(
            _colour("fgcolor", status), _colour("bgcolor", status)
        )

    def test_text_colours_reach_wcag_aa(self):
        for status in "active", "late", "completed", "inactive":
            self.assertGreaterEqual(self.contrast(status), 4.5, status)

    def test_orange_and_red_are_kept(self):
        # Ruled: their AA shades read as brown or dark red
        self.assertEqual((255, 128, 0), _colour("fgcolor", "duesoon"))
        self.assertEqual((255, 0, 0), _colour("fgcolor", "overdue"))
