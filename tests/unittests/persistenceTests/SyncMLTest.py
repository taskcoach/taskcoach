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

import test
from taskcoachlib import config, persistence
from taskcoachlib.domain import task, note, category, effort, date


class TaskFileTestCase(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        self.task = task.Task(subject="Subject")

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def testTaskIsDirtyAfterEditingSubject(self):
        self.taskFile.tasks().append(self.task)
        self.assertTrue(task.Task.STATUS_NEW, self.task.getStatus())
        self.task.setSubject("New subject")
        self.assertTrue(task.Task.STATUS_CHANGED, self.task.getStatus())

    def testNoteIsDirtyAfterEditingSubject(self):
        aNote = note.Note(subject="Subject")
        self.taskFile.notes().append(aNote)
        self.assertTrue(note.Note.STATUS_NEW, aNote.getStatus())
        aNote.setSubject("New subject")
        self.assertTrue(note.Note.STATUS_CHANGED, aNote.getStatus())

    def testCategoryIsDirtyAfterEditingSubject(self):
        aCategory = category.Category(subject="Subject")
        self.taskFile.categories().append(aCategory)
        self.assertTrue(category.Category.STATUS_NEW, aCategory.getStatus())
        aCategory.setSubject("New subject")
        self.assertTrue(
            category.Category.STATUS_CHANGED, aCategory.getStatus()
        )

    def testEffortIsDirtyAfterEditingStart(self):
        self.taskFile.tasks().append(self.task)
        anEffort = effort.Effort(self.task)
        self.task.addEffort(anEffort)
        self.assertTrue(effort.Effort.STATUS_NEW, anEffort.getStatus())
        anEffort.setStart(date.DateTime(2000, 1, 1, 10, 0, 0))
        self.assertTrue(effort.Effort.STATUS_CHANGED, anEffort.getStatus())
