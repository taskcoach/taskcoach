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

from taskcoachlib import gui, persistence
from taskcoachlib.domain import base, task, effort, category
from taskcoachlib.config import settings
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
        settings.set("taskviewer", "columns", ["timeSpent"])
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
        return self.ListViewerClass(self.frame, self.taskFile)

    def test_clock_notification_results_in_refreshed_item(self):
        self.updateViewer.widget = MockWidget()
        self.updateViewer.second_refresher.refresh_items(
            self.updateViewer.second_refresher.currently_tracked_items()
        )
        using_task_viewer = self.ListViewerClass != gui.viewer.EffortViewer
        expected = (
            self.trackedTask if using_task_viewer else self.trackedEffort
        )
        self.assertEqual(
            set([expected]), self.updateViewer.widget.refreshedItems
        )

    def test_clock_notification_refreshes_only_tracked_items(
        self,
    ):
        self.taskList.append(task.Task("not tracked"))
        self.updateViewer.widget = MockWidget()
        self.updateViewer.second_refresher.refresh_items(
            self.updateViewer.second_refresher.currently_tracked_items()
        )
        self.assertEqual(1, len(self.updateViewer.widget.refreshedItems))

    def test_stop_tracking_removes_viewer_from_clock_observers(self):
        self.trackedTask.stopTracking()
        self.assertFalse(self.updateViewer.second_refresher.is_clock_started())

    def test_stop_tracking_refreshes_tracked_items(self):
        self.updateViewer.widget = MockWidget()
        self.trackedTask.stopTracking()
        self.assertEqual(1, len(self.updateViewer.widget.refreshedItems))

    def test_removing_tracked_child_and_parent_stops_clock_observing(
        self,
    ):
        parent = task.Task()
        self.taskList.append(parent)
        parent.addChild(self.trackedTask)
        self.taskList.remove(parent)
        self.assertFalse(self.updateViewer.second_refresher.is_clock_started())

    def test_create_viewer_with_tracked_items_starts_the_clock(self):
        self.createUpdateViewer()
        self.assertTrue(self.updateViewer.second_refresher.is_clock_started())

    def test_viewer_does_not_react_to_add_events_from_other_containers(self):
        categories = base.filter.SearchFilter(category.CategoryList())
        try:
            categories.append(category.Category("Test"))
        except AttributeError:  # pragma: no cover
            self.fail(
                "Adding a category shouldn't affect the UpdatePerSecondViewer."
            )

    def test_viewer_does_not_react_to_remove_events_from_other_containers(
        self,
    ):
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
