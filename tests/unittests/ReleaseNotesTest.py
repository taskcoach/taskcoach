"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>

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

import io
from unittest import mock

import test
from tools import release_notes

CHANGELOG = """# Changelog

Text before the releases.

## 2.0.4.0

- Newer change

## 2.0.3.0

- First change
- Second change

## 2.0.2.27
"""


class ReleaseNotesTest(test.TestCase):
    """A release's section of CHANGELOG.md, its release page's text
    (docs/PACKAGING.md#release-notes)."""

    def notes(self, tag):
        output = io.StringIO()
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=CHANGELOG)
        ), mock.patch("sys.stdout", output):
            release_notes.main(tag)
        return output.getvalue()

    def test_the_versions_section_up_to_the_next(self):
        self.assertEqual(
            "- First change\n- Second change\n", self.notes("v2.0.3.0")
        )

    def test_the_newest_section(self):
        self.assertEqual("- Newer change\n", self.notes("v2.0.4.0"))

    def test_a_missing_section_stops_with_an_error(self):
        with self.assertRaises(SystemExit) as stop:
            self.notes("v2.0.5.0")
        self.assertIn("no section for 2.0.5.0", str(stop.exception))

    def test_an_empty_section_stops_with_an_error(self):
        with self.assertRaises(SystemExit):
            self.notes("v2.0.2.27")
