"""
Task Coach - Your friendly task manager
Copyright (C) 2013 Task Coach developers <developers@taskcoach.org>

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
from integrationtests import mock
from taskcoachlib.domain import date
import gc
import os
import weakref


class LeakTest(test.TestCase):
    def setUp(self):
        self.mockApp = mock.App()
        self.mockApp.addTask()

    def tearDown(self):
        self.mockApp.iocontroller.save_as("Test.tsk")
        os.remove("Test.tsk")
        self.mockApp.quit_application()
        if os.path.isfile("Test.tsk.lock"):
            os.remove("Test.tsk.lock")
        mock.App.deleteInstance()
        super().tearDown()

    def test_clear_frees_the_task(self):
        task_ref = weakref.ref(self.mockApp.task)
        del self.mockApp.task
        self.mockApp.taskFile.clear()
        # The master loop keeps what changed until its next pass
        self.mockApp.mainwindow._masterScheduler._run_pass(date.Now())
        gc.collect()
        self.assertIsNone(task_ref())
