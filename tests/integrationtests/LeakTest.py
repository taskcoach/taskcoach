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

import weakref
import test, mock, os


class LeakTest(test.TestCase):
    def setUp(self):
        self.mockApp = mock.App()
        self.mockApp.addTask()

    def tearDown(self):
        self.mockApp.iocontroller.save_as("Test.tsk")
        os.remove("Test.tsk")
        self.mockApp.quitApplication()
        mock.App.deleteInstance()
        super().tearDown()

    def testClear(self):
        """taskRef = weakref.ref(self.mockApp.task)
        del self.mockApp.task
        self.mockApp.taskFile.clear()
        self.failUnless(taskRef() is None)"""
