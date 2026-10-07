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

import time
import os
import test
from integrationtests import mock
from taskcoachlib import persistence, config
from taskcoachlib.domain import task, category, note


class PerformanceTest(test.TestCase):
    def createTestFile(self):
        task_list = task.TaskList(
            [task.Task("test") for _ in range(self.nrTasks)]
        )
        taskfile = open(self.taskfilename, "w")
        task_writer = persistence.XMLWriter(taskfile)
        task_writer.write(
            task_list,
            category.CategoryList(),
            note.NoteContainer(),
        )
        taskfile.close()

    def setUp(self):
        self.nrTasks = 100
        self.taskfilename = "performanceTest.tsk"
        self.createTestFile()

    def tearDown(self):
        os.remove(self.taskfilename)
        if os.path.isfile(self.taskfilename + ".lock"):
            os.remove(self.taskfilename + ".lock")
        super().tearDown()

    def test_read(self):
        mock_app = mock.App()
        start = time.time()
        mock_app.iocontroller.open(self.taskfilename)
        end = time.time()
        self.assertEqual(self.nrTasks, len(mock_app.taskFile.tasks()))
        self.assertTrue(end - start < self.nrTasks / 10)
        mock_app.quit_application()
