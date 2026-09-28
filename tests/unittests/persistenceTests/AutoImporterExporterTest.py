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

from taskcoachlib import persistence, config
from taskcoachlib.domain import task, date
import test
import os
from unittests import dummy


class AutoExporterTestCase(test.TestCase):
    def setUp(self):
        task.Task.settings = self.settings = config.Settings(load=False)
        self.exporter = persistence.AutoImporterExporter(self.settings)
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
        self.settings.set("file", "autoexport", '["Todo.txt"]')
        self.settings.set("file", "autosave", "True")
        autosaver = persistence.AutoSaver(self.settings)
        theTask = task.Task(subject="Some task")
        self.taskFile.tasks().append(theTask)
        autosaver.on_idle(dummy.Event())
        self.assertEqual(
            "Some task tcid:%s\n" % theTask.id(),
            open(self.txtFilename, "r").read(),
        )

    def testAddOneTaskAndSaveManually(self):
        self.settings.set("file", "autoexport", '["Todo.txt"]')
        theTask = task.Task(subject="Whatever")
        self.taskFile.tasks().append(theTask)
        self.taskFile.save()
        self.assertEqual(
            "Whatever tcid:%s\n" % theTask.id(),
            open(self.txtFilename, "r").read(),
        )

    def testImportOneTaskWhenSavingManually(self):
        self.settings.set("file", "autoimport", '["Todo.txt"]')
        with open(self.txtFilename, "w") as todoTxtFile:
            todoTxtFile.write("Imported task\n")
        self.taskFile.save()
        self.assertEqual(
            "Imported task", list(self.taskFile.tasks())[0].subject()
        )

    def testImportOneTaskWhenAutoSaving(self):
        self.settings.set("file", "autoimport", '["Todo.txt"]')
        self.settings.set("file", "autosave", "True")
        autosaver = persistence.AutoSaver(self.settings)
        with open(self.txtFilename, "w") as todoTxtFile:
            todoTxtFile.write("Imported task\n")
        self.taskFile.tasks().append(task.Task(subject="Some task"))
        autosaver.on_idle(dummy.Event())
        self.assertEqual(2, len(self.taskFile.tasks()))

    def testImportAfterReadingTaskFile(self):
        self.taskFile.save()
        self.settings.set("file", "autoimport", '["Todo.txt"]')
        with open(self.txtFilename, "w") as todoTxtFile:
            todoTxtFile.write("Imported task\n")
        self.taskFile.load()
        self.assertEqual(
            "Imported task", list(self.taskFile.tasks())[0].subject()
        )

    def testSaveWithAutoImportWhenFileToImportDoesNotExist(self):
        self.settings.set("file", "autoimport", '["Todo.txt"]')
        self.taskFile.tasks().append(task.Task(subject="Whatever"))
        self.taskFile.save()

    def testBothDeletedTask(self):
        self.settings.set("file", "autoimport", '["Todo.txt"]')
        self.settings.set("file", "autoexport", '["Todo.txt"]')
        aTask = task.Task(subject="Whatever")
        self.taskFile.tasks().append(aTask)
        self.taskFile.save()
        self.taskFile.tasks().remove(aTask)
        self.taskFile.save()
        self.assertEqual(self.taskFile.tasks(), [])

    def testBothMarkCompleted(self):
        self.settings.set("file", "autoimport", '["Todo.txt"]')
        self.settings.set("file", "autoexport", '["Todo.txt"]')
        aTask = task.Task(subject="Whatever")
        self.taskFile.tasks().append(aTask)
        self.taskFile.save()
        now = date.Now()
        aTask.setCompletionDateTime(now)
        self.taskFile.save()
        self.assertEqual(aTask.completionDateTime(), now)
