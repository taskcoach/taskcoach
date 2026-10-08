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
import test
from taskcoachlib import gui, persistence
from taskcoachlib.domain import category, date, effort, note, task
from taskcoachlib.persistence.allitems import all_items

# Effort starts, in the order the efforts are added; the description
# of each is its place newest first, as an effort view lists them
STARTS = (
    ("4", date.DateTime(2026, 1, 15, 8, 0)),
    ("6", date.DateTime(2013, 1, 1, 18, 15)),
    ("1", date.DateTime(2026, 1, 16, 14, 0)),
    ("3", date.DateTime(2026, 1, 15, 9, 0)),
    ("2", date.DateTime(2026, 1, 16, 8, 0)),
    ("5", date.DateTime(2014, 6, 2, 10, 0)),
)


class AllItemsTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.task_file = persistence.TaskFile()
        self.task = task.Task("Task")
        self.task_file.tasks().append(self.task)
        for place, start in STARTS:
            self.task.addEffort(
                effort.Effort(
                    self.task,
                    start=start,
                    stop=start + date.ONE_HOUR,
                    description="place %s" % place,
                )
            )

    def tearDown(self):
        super().tearDown()
        self.task_file.close()
        self.task_file.stop()

    def assert_newest_first(self, text):
        """The efforts' descriptions are in text in the order of their
        periods, newest first."""
        places = [text.index("place %d" % place) for place in range(1, 7)]
        self.assertEqual(sorted(places), places, text)

    def effort_column(self, name):
        viewer = gui.viewer.EffortViewer(self.frame, self.task_file)
        return [each for each in viewer.columns() if each.name() == name]


class AllItemsTest(AllItemsTestCase):
    def test_efforts_newest_first(self):
        items = all_items(self.task_file, "ALL_EFFORTS")
        self.assertEqual(
            ["place %d" % place for place in range(1, 7)],
            [each.description() for each in items],
        )

    def test_tasks_by_due_date(self):
        self.task_file.tasks().remove(self.task)
        later = task.Task("Later", dueDateTime=date.DateTime(2031, 1, 1))
        sooner = task.Task("Sooner", dueDateTime=date.DateTime(2030, 1, 1))
        undated = task.Task("Undated")
        self.task_file.tasks().extend([undated, later, sooner])
        self.assertEqual(
            [sooner, later, undated], all_items(self.task_file, "ALL_TASKS")
        )

    def test_categories_by_subject_ignoring_case(self):
        subjects = ("beta", "Gamma", "Alpha")
        self.task_file.categories().extend(
            [category.Category(subject) for subject in subjects]
        )
        self.assertEqual(
            ["Alpha", "beta", "Gamma"],
            [
                each.subject()
                for each in all_items(self.task_file, "ALL_CATEGORIES")
            ],
        )

    def test_notes_by_subject_ignoring_case(self):
        subjects = ("beta", "Gamma", "Alpha")
        self.task_file.notes().extend(
            [note.Note(subject=subject) for subject in subjects]
        )
        self.assertEqual(
            ["Alpha", "beta", "Gamma"],
            [
                each.subject()
                for each in all_items(self.task_file, "ALL_NOTES")
            ],
        )

    def test_type_without_items(self):
        self.assertEqual([], all_items(self.task_file, "ALL_ATTACHMENTS"))

    def test_file_keeps_listing_efforts(self):
        all_items(self.task_file, "ALL_EFFORTS")
        added = effort.Effort(self.task)
        self.task.addEffort(added)
        self.assertIn(added, self.task_file.efforts())


class AllEffortsExportTest(AllItemsTestCase):
    def test_html(self):
        fd = io.StringIO()
        persistence.HTMLWriter(fd, "filename").write(
            "ALL_EFFORTS",
            columns=self.effort_column("description"),
            taskFile=self.task_file,
        )
        self.assert_newest_first(fd.getvalue())

    def test_csv(self):
        fd = io.StringIO()
        persistence.CSVWriter(fd).write(
            "ALL_EFFORTS",
            columns=self.effort_column("description"),
            taskFile=self.task_file,
        )
        self.assert_newest_first(fd.getvalue())

    def test_icalendar(self):
        fd = io.StringIO()
        persistence.iCalendarWriter(fd).write(
            "ALL_EFFORTS", taskFile=self.task_file
        )
        self.assert_newest_first(fd.getvalue())
