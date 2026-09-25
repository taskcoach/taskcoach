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
from integrationtests import mock
from taskcoachlib.domain import task, category


class TaskViewerAndCategoryFilterIntegrationTestFixture(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.app = mock.App()
        parent = task.Task("parent")
        child = task.Task("child")
        parent.addChild(child)
        self.category = category.Category("category")
        self.app.mainwindow.taskFile.categories().append(self.category)
        self.app.mainwindow.taskFile.tasks().extend([parent, child])
        self.category.addCategorizable(child)
        self.category.setFiltered()
        self.taskViewer = self.app.mainwindow.viewer[0]

    def tearDown(self):
        mock.App.deleteInstance()
        super(
            TaskViewerAndCategoryFilterIntegrationTestFixture, self
        ).tearDown()


class TaskListViewerAndCategoryFilterIntegrationTest(
    TaskViewerAndCategoryFilterIntegrationTestFixture
):

    def testFilterOnCategoryChildDoesHideParent(self):
        import wx

        if wx.VERSION < (3, 0):
            self.taskViewer.settings.setboolean(
                self.taskViewer.settingsSection(), "treemode", False
            )
            self.assertEqual(1, self.taskViewer.widget.GetItemCount())


class TaskTreeViewerAndCategoryFilterIntegrationTest(
    TaskViewerAndCategoryFilterIntegrationTestFixture
):

    def testFilterOnCategoryChildDoesNotHideParent(self):
        self.taskViewer.settings.setboolean(
            self.taskViewer.settingsSection(), "treemode", True
        )
        self.taskViewer.expand_all()
        self.assertEqual(2, self.taskViewer.widget.GetItemCount())
