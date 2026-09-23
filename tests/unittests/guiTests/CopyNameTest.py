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

import os

import test
from taskcoachlib.gui.iocontroller import copy_name


class CopyNameTest(test.TestCase):
    """Save As suggests "name copy", "name copy 2", and so on."""

    def suggest(self, path, existing=()):
        existing = {os.path.join("folder", name) for name in existing}
        return copy_name(os.path.join("folder", path), existing.__contains__)

    def test_first_copy(self):
        self.assertEqual("Tasks copy.tsk", self.suggest("Tasks.tsk"))

    def test_next_free_number(self):
        self.assertEqual(
            "Tasks copy 3.tsk",
            self.suggest("Tasks.tsk", ["Tasks copy.tsk", "Tasks copy 2.tsk"]),
        )

    def test_copy_of_a_copy_is_numbered_on(self):
        self.assertEqual("Tasks copy 2.tsk", self.suggest("Tasks copy.tsk"))
        self.assertEqual(
            "Tasks copy 3.tsk",
            self.suggest("Tasks copy 2.tsk", ["Tasks copy.tsk"]),
        )
