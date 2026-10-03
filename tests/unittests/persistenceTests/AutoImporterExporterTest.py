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

from taskcoachlib import persistence
from taskcoachlib.domain import task, date
from taskcoachlib.config import settings
import test
import os
from unittests import dummy


class AutoExporterTestCase(test.TestCase):
    def setUp(self):
        self.exporter = persistence.AutoImporterExporter()
        self.taskFile = persistence.TaskFile()
        self.tskFilename = "autoexport.tsk"
        self.txtFilename = "autoexport.txt"
        self.taskFile.setFilename(self.tskFilename)

    def tearDown(self):
        super().tearDown()
        del self.exporter
        for filename in (
            self.tskFilename,
            self.txtFilename,
            self.txtFilename + "-meta",
        ):
            try:
                os.remove(filename)
            except OSError:
                pass

    def testAddOneTaskWhenAutoSaveIsOn(self):
        settings.set("file", "autoexport", ["Todo.txt"])
        settings.set("file", "autosave", True)
        autosaver = persistence.AutoSaver()
        theTask = task.Task(subject="Some task")
        self.taskFile.tasks().append(theTask)
        autosaver.on_idle(dummy.Event())
        self.assertEqual(
            "Some task tcid:%s\n" % theTask.id(),
            open(self.txtFilename, "r").read(),
        )

    def testAddOneTaskAndSaveManually(self):
        settings.set("file", "autoexport", ["Todo.txt"])
        theTask = task.Task(subject="Whatever")
        self.taskFile.tasks().append(theTask)
        self.taskFile.save()
        self.assertEqual(
            "Whatever tcid:%s\n" % theTask.id(),
            open(self.txtFilename, "r").read(),
        )

    def testImportOneTaskWhenSavingManually(self):
        settings.set("file", "autoimport", ["Todo.txt"])
        with open(self.txtFilename, "w") as todoTxtFile:
            todoTxtFile.write("Imported task\n")
        self.taskFile.save()
        self.assertEqual(
            "Imported task", list(self.taskFile.tasks())[0].subject()
        )

    def testImportOneTaskWhenAutoSaving(self):
        settings.set("file", "autoimport", ["Todo.txt"])
        settings.set("file", "autosave", True)
        autosaver = persistence.AutoSaver()
        with open(self.txtFilename, "w") as todoTxtFile:
            todoTxtFile.write("Imported task\n")
        self.taskFile.tasks().append(task.Task(subject="Some task"))
        autosaver.on_idle(dummy.Event())
        self.assertEqual(2, len(self.taskFile.tasks()))

    def testImportAfterReadingTaskFile(self):
        self.taskFile.save()
        settings.set("file", "autoimport", ["Todo.txt"])
        with open(self.txtFilename, "w") as todoTxtFile:
            todoTxtFile.write("Imported task\n")
        self.taskFile.load()
        self.assertEqual(
            "Imported task", list(self.taskFile.tasks())[0].subject()
        )

    def testSaveWithAutoImportWhenFileToImportDoesNotExist(self):
        settings.set("file", "autoimport", ["Todo.txt"])
        self.taskFile.tasks().append(task.Task(subject="Whatever"))
        self.taskFile.save()

    def testBothDeletedTask(self):
        settings.set("file", "autoimport", ["Todo.txt"])
        settings.set("file", "autoexport", ["Todo.txt"])
        aTask = task.Task(subject="Whatever")
        self.taskFile.tasks().append(aTask)
        self.taskFile.save()
        self.taskFile.tasks().remove(aTask)
        self.taskFile.save()
        self.assertEqual(self.taskFile.tasks(), [])

    def testBothMarkCompleted(self):
        settings.set("file", "autoimport", ["Todo.txt"])
        settings.set("file", "autoexport", ["Todo.txt"])
        aTask = task.Task(subject="Whatever")
        self.taskFile.tasks().append(aTask)
        self.taskFile.save()
        now = date.Now()
        aTask.set_completion_date_time(now)
        self.taskFile.save()
        self.assertEqual(aTask.completionDateTime(), now)
