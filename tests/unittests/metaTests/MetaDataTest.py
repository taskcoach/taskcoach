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

import test, datetime
from taskcoachlib import meta


class VersionNumberTest(test.TestCase):
    def test_version_has_major_minor_and_milestone(self):
        self.assertEqual(3, len(meta.data.version.split(".")))

    def test_full_version_adds_the_patch(self):
        self.assertEqual(
            "%s.%s" % (meta.data.version, meta.data.patch),
            meta.data.version_full,
        )
        for component in meta.data.version_full.split("."):
            self.assertEqual(component, str(int(component)))

    def test_version_components_are_integers(self):
        for component in meta.data.version.split("."):
            self.assertEqual(component, str(int(component)))

    def test_tsk_version_is_integer(self):
        self.assertEqual(int, type(meta.data.tskversion))

    def test_release_status(self):
        self.assertTrue(
            meta.data.release_status in ["alpha", "beta", "stable"]
        )

    def test_release_date(self):
        datetime.date(
            int(meta.data.release_year),
            meta.data.months.index(meta.data.release_month) + 1,
            int(meta.data.release_day),
        )
