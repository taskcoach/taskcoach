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

import time, os
import test, mock
from taskcoachlib import persistence, config
from taskcoachlib.domain import task, category, note


class PerformanceTest(test.TestCase):
    def createTestFile(self):
        task.Task.settings = config.Settings(load=False)
        taskList = task.TaskList(
            [task.Task("test") for _ in range(self.nrTasks)]
        )
        taskfile = open(self.taskfilename, "w")
        taskWriter = persistence.XMLWriter(taskfile)
        taskWriter.write(
            taskList,
            category.CategoryList(),
            note.NoteContainer(),
            None,  # SyncML removed
            "fake",
        )
        taskfile.close()

    def setUp(self):
        self.nrTasks = 100
        self.taskfilename = "performanceTest.tsk"
        self.createTestFile()

    def tearDown(self):
        os.remove(self.taskfilename)
        super().tearDown()

    def testRead(self):
        mockApp = mock.App()
        start = time.time()
        mockApp.iocontroller.open(self.taskfilename)
        end = time.time()
        self.assertEqual(self.nrTasks, len(mockApp.taskFile.tasks()))
        self.assertTrue(end - start < self.nrTasks / 10)
        mockApp.quitApplication()
