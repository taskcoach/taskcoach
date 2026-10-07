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
import test
from integrationtests import mock


class SaveTest(test.TestCase):
    def setUp(self):
        self.filename = "SaveTest.tsk"
        self.filename2 = "SaveTest2.tsk"
        self.mockApp = mock.App()
        self.mockApp.addTasks()

    def tearDown(self):
        self.mockApp.iocontroller.save()
        self.mockApp.quit_application()
        for filename in [self.filename, self.filename2]:
            for each in [filename, filename + ".lock"]:
                if os.path.isfile(each):
                    os.remove(each)
        mock.App.deleteInstance()
        super().tearDown()

    def assertTasksLoaded(self, nr_tasks):
        self.assertEqual(nr_tasks, len(self.mockApp.taskFile.tasks()))

    def test_save(self):
        self.mockApp.iocontroller.save_as(self.filename)
        self.mockApp.iocontroller.open(self.filename)
        self.assertTasksLoaded(2)

    def test_save_selection_child(self):
        self.mockApp.iocontroller.save_as(self.filename)
        self.mockApp.iocontroller.save_selection(
            [self.mockApp.child], self.filename2
        )
        self.mockApp.iocontroller.close()
        self.mockApp.iocontroller.open(self.filename2)
        self.assertTasksLoaded(1)

    def test_save_selection_parent(self):
        self.mockApp.iocontroller.save_as(self.filename)
        self.mockApp.iocontroller.save_selection(
            [self.mockApp.parent], self.filename2
        )
        self.mockApp.iocontroller.close()
        self.mockApp.iocontroller.open(self.filename2)
        self.assertTasksLoaded(2)

    def test_save_and_merge(self):
        mock_app_2 = mock.App()
        mock_app_2.addTasks()
        mock_app_2.iocontroller.save_as(self.filename2)
        self.mockApp.iocontroller.merge(self.filename2)
        self.assertTasksLoaded(4)
        self.mockApp.iocontroller.save_as(self.filename)
        mock_app_2.quit_application()
