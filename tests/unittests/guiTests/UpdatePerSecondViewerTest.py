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

from taskcoachlib import gui, config, persistence
from taskcoachlib.domain import base, task, effort, category
import test


class MockWidget(object):
    def __init__(self):
        self.refreshedItems = set()

    def RefreshItems(self, *items):
        self.refreshedItems.update(set(items))

    def ToggleAutoResizing(self, *args, **kwargs):
        pass

    def curselection(self):
        return []


class UpdatePerSecondViewerTestsMixin(object):
    def setUp(self):
        super().setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        self.settings.set("taskviewer", "columns", "['timeSpent']")
        self.taskFile = persistence.TaskFile()
        self.taskList = task.sorter.Sorter(
            self.taskFile.tasks(), sortBy="dueDateTime"
        )
        self.updateViewer = self.createUpdateViewer()
        self.trackedTask = task.Task(subject="tracked")
        self.trackedEffort = effort.Effort(self.trackedTask)
        self.trackedTask.addEffort(self.trackedEffort)
        self.taskList.append(self.trackedTask)

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def createUpdateViewer(self):
        return self.ListViewerClass(self.frame, self.taskFile, self.settings)

    def testClockNotificationResultsInRefreshedItem(self):
        self.updateViewer.widget = MockWidget()
        self.updateViewer.secondRefresher.refreshItems(
            self.updateViewer.secondRefresher.currentlyTrackedItems()
        )
        usingTaskViewer = self.ListViewerClass != gui.viewer.EffortViewer
        expected = self.trackedTask if usingTaskViewer else self.trackedEffort
        self.assertEqual(
            set([expected]), self.updateViewer.widget.refreshedItems
        )

    def testClockNotificationResultsInRefreshedItem_OnlyForTrackedItems(self):
        self.taskList.append(task.Task("not tracked"))
        self.updateViewer.widget = MockWidget()
        self.updateViewer.secondRefresher.refreshItems(
            self.updateViewer.secondRefresher.currentlyTrackedItems()
        )
        self.assertEqual(1, len(self.updateViewer.widget.refreshedItems))

    def testStopTrackingRemovesViewerFromClockObservers(self):
        self.trackedTask.stopTracking()
        # With new architecture, check if the secondRefresher's timer stopped
        self.assertFalse(self.updateViewer.secondRefresher.isClockStarted())

    def testStopTrackingRefreshesTrackedItems(self):
        self.updateViewer.widget = MockWidget()
        self.trackedTask.stopTracking()
        self.assertEqual(1, len(self.updateViewer.widget.refreshedItems))

    def testRemoveTrackedChildAndParentRemovesViewerFromClockObservers(self):
        parent = task.Task()
        self.taskList.append(parent)
        parent.addChild(self.trackedTask)
        self.taskList.remove(parent)
        # With new architecture, check if the secondRefresher's timer stopped
        self.assertFalse(self.updateViewer.secondRefresher.isClockStarted())

    def testCreateViewerWithTrackedItemsStartsTheClock(self):
        self.createUpdateViewer()
        self.assertTrue(self.updateViewer.secondRefresher.isClockStarted())

    def testViewerDoesNotReactToAddEventsFromOtherContainers(self):
        categories = base.filter.SearchFilter(category.CategoryList())
        try:
            categories.append(category.Category("Test"))
        except AttributeError:  # pragma: no cover
            self.fail(
                "Adding a category shouldn't affect the UpdatePerSecondViewer."
            )

    def testViewerDoesNotReactToRemoveEventsFromOtherContainers(self):
        categories = base.filter.SearchFilter(category.CategoryList())
        categories.append(category.Category("Test"))
        try:
            categories.clear()
        except AttributeError:  # pragma: no cover
            self.fail(
                "Removing a category shouldn't affect the UpdatePerSecondViewer."
            )


class TaskListViewerUpdatePerSecondViewerTest(
    UpdatePerSecondViewerTestsMixin, test.wxTestCase
):
    ListViewerClass = gui.viewer.TaskViewer


class SquareTaskViewerUpdatePerSecondViewerTest(
    UpdatePerSecondViewerTestsMixin, test.wxTestCase
):
    ListViewerClass = gui.viewer.SquareTaskViewer


class EffortListViewerUpdatePerSecondTest(
    UpdatePerSecondViewerTestsMixin, test.wxTestCase
):
    ListViewerClass = gui.viewer.EffortViewer
