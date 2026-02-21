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
import test, mock


class SaveTest(test.TestCase):
    def setUp(self):
        self.filename = "SaveTest.tsk"
        self.filename2 = "SaveTest2.tsk"
        self.mockApp = mock.App()
        self.mockApp.addTasks()

    def tearDown(self):
        self.mockApp.iocontroller.save()
        self.mockApp.quitApplication()
        for filename in [self.filename, self.filename2]:
            if os.path.isfile(filename):
                os.remove(filename)
        mock.App.deleteInstance()
        super().tearDown()

    def assertTasksLoaded(self, nrTasks):
        self.assertEqual(nrTasks, len(self.mockApp.taskFile.tasks()))

    def testSave(self):
        self.mockApp.iocontroller.save_as(self.filename)
        self.mockApp.iocontroller.open(self.filename)
        self.assertTasksLoaded(2)

    def testSaveSelection_Child(self):
        self.mockApp.iocontroller.save_as(self.filename)
        self.mockApp.iocontroller.save_selection(
            [self.mockApp.child], self.filename2
        )
        self.mockApp.iocontroller.close()
        self.mockApp.iocontroller.open(self.filename2)
        self.assertTasksLoaded(1)

    def testSaveSelection_Parent(self):
        self.mockApp.iocontroller.save_as(self.filename)
        self.mockApp.iocontroller.save_selection(
            [self.mockApp.parent], self.filename2
        )
        self.mockApp.iocontroller.close()
        self.mockApp.iocontroller.open(self.filename2)
        self.assertTasksLoaded(2)

    def testSaveAndMerge(self):
        mockApp2 = mock.App()
        mockApp2.addTasks()
        mockApp2.iocontroller.save_as(self.filename2)
        self.mockApp.iocontroller.merge(self.filename2)
        self.assertTasksLoaded(4)
        self.mockApp.iocontroller.save_as(self.filename)
        mockApp2.quitApplication()
