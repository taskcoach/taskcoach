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
from taskcoachlib import gui, config, persistence
from taskcoachlib.domain import task


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
        self.child.setParent(self.parent)
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
