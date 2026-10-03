"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2026 Task Coach developers <developers@taskcoach.org>

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
import shutil
import tempfile

import test
from taskcoachlib import config, persistence
from taskcoachlib.domain import category, note, task
from taskcoachlib.tools import anonymize


class AnonymizeTest(test.TestCase):
    """Help > Anonymize: a copy of the task file to attach to a bug
    report, its texts replaced with X's."""

    def setUp(self):
        super().setUp()
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        self.filename = os.path.join(directory, "tasks.tsk")
        secret = task.Task(subject="Secret", description="One\nTwo")
        with open(self.filename, "wb") as file:
            persistence.XMLWriter(file).write(
                task.TaskList([secret]),
                category.CategoryList(),
                note.NoteContainer(),
            )

    def read_anonymized(self):
        with open(anonymize.anonymize(self.filename), encoding="utf-8") as fd:
            return persistence.XMLReader(fd).read()[0]

    def test_task_coach_opens_the_copy(self):
        # Its version line kept: Task Coach refuses a file without one
        self.assertEqual(1, len(self.read_anonymized()))

    def test_the_subject_is_xs(self):
        self.assertEqual("XXXXXX", self.read_anonymized()[0].subject())

    def test_the_description_keeps_its_line_breaks(self):
        self.assertEqual("XXX\nXXX", self.read_anonymized()[0].description())

    def test_the_copy_is_next_to_the_file(self):
        self.assertEqual(
            self.filename.replace(".tsk", ".anonymized.tsk"),
            anonymize.anonymize(self.filename),
        )
