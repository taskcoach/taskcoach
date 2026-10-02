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
import wx
from taskcoachlib import gui, config, persistence
from taskcoachlib.domain import date, task


class TreeViewerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        self.viewer = gui.viewer.TaskViewer(
            self.frame, self.taskFile, self.settings
        )
        self.expansionContext = self.viewer.settingsSection()
        self.parent = task.Task("parent")
        self.child = task.Task("child")
        self.parent.addChild(self.child)
        self.child.set_parent(self.parent)
        self.taskFile.tasks().extend([self.parent, self.child])
        self.viewer.refresh()
        self.widget = self.viewer.widget

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def firstItem(self):
        root = self.widget.GetRootItem()
        return self.widget.GetFirstChild(root)[0]

    def test_children_in_the_views_order_without_hidden_ones(self):
        other = task.Task("another child")
        self.parent.addChild(other)
        other.set_parent(self.parent)
        self.taskFile.tasks().append(other)
        self.viewer.sortBy("subject")
        self.assertEqual(
            [other, self.child], self.viewer.children(self.parent)
        )
        self.viewer.hide_task_status(task.status.completed)
        other.set_completion_date_time(date.Now())
        self.assertEqual([self.child], self.viewer.children(self.parent))

    def row(self, domain_object):
        for item in self.widget.GetItemChildren(recursively=True):
            if self.widget.GetItemPyData(item) is domain_object:
                return item
        return None

    def start_dragging(self, domain_object):
        # pylint: disable=W0212
        self.viewer.expand_all()
        self.viewer.select([domain_object])
        self.widget._dragItems = [self.row(domain_object)]
        self.widget._dragColumn = 0

    def test_a_dropped_task_stays_selected(self):
        # The move takes it out first, and a neighbour gets the
        # selection meanwhile
        other = task.Task("other")
        self.taskFile.tasks().append(other)
        self.start_dragging(self.child)
        self.widget.OnDrop(self.row(other), [self.row(self.child)], 0, 0)
        wx.Yield()  # The drop runs later
        self.assertEqual(other, self.child.parent())
        self.assertEqual([self.child], self.viewer.curselection())

    def test_a_cancelled_drag_keeps_the_dragged_task_selected(self):
        self.start_dragging(self.child)
        self.widget.StopDragging()  # As Escape does
        self.assertEqual([self.child], self.viewer.curselection())

    def test_the_drop_target_is_not_selected_when_a_drag_ends(self):
        # As the current row it would take the button's release for a
        # second click on it and open an editor
        other = task.Task("other")
        self.taskFile.tasks().append(other)
        self.start_dragging(self.child)
        self.viewer.SetSize(400, 300)
        self.viewer.Layout()
        self.widget.GetMainWindow().CalculatePositions()
        label = self.widget.GetBoundingRect(self.row(other), textOnly=True)

        class EndDrag:
            @staticmethod
            def GetPoint():  # noqa: N802 - the wx event's
                return label.GetPosition() + wx.Point(2, label.height // 2)

        self.widget.OnEndDrag(EndDrag())
        self.assertEqual([self.child], self.viewer.curselection())
        wx.Yield()  # The drop runs later
        self.assertEqual(other, self.child.parent())

    def testWidgetDoesNotDisplayChildItemBeforeItsParentIsExpanded(self):
        self.assertEqual(1, self.viewer.widget.GetItemCount())

    def testExpand(self):
        self.widget.Expand(self.firstItem())
        self.assertTrue(self.parent.isExpanded(context=self.expansionContext))

    def testCollapse(self):
        firstVisibleItem = self.firstItem()
        self.widget.Expand(firstVisibleItem)
        self.widget.Collapse(firstVisibleItem)
        self.assertFalse(self.parent.isExpanded(context=self.expansionContext))

    def testExpandall(self):
        self.viewer.expand_all()
        self.assertTrue(self.parent.isExpanded(context=self.expansionContext))
