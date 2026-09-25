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
from taskcoachlib.domain import category


class CategoryViewerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        self.categories = self.taskFile.categories()
        self.viewer = gui.viewer.CategoryViewer(
            self.frame, self.taskFile, self.settings
        )

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def addTwoCategories(self):
        cat1 = category.Category("1")
        cat2 = category.Category("2")
        self.categories.extend([cat2, cat1])
        return cat1, cat2

    def testInitialSize(self):
        self.assertEqual(0, self.viewer.size())

    def testCopyCategoryWithChildren(self):
        parent, child = self.addTwoCategories()
        parent.addChild(child)
        copy = parent.copy()
        self.categories.append(copy)
        self.viewer.expand_all()
        self.assertEqual(4, self.viewer.size())

    def testSortInWidget(self):
        self.addTwoCategories()
        widget = self.viewer.widget
        for item, cat in zip(
            widget.GetItemChildren(), self.viewer.presentation()
        ):
            self.assertEqual(cat.subject(), widget.GetItemText(item))

    def testSelectAll(self):
        self.addTwoCategories()
        self.viewer.widget.select_all()
        self.viewer.updateSelection()
        self.assertEqual(2, len(self.viewer.curselection()))

    def testFilterOnAllCheckedCategoriesSetsSetting(self):
        self.viewer.filterUICommand.doChoice(True)
        self.assertTrue(
            self.settings.getboolean("view", "categoryfiltermatchall")
        )

    def testFilterOnAnyCheckedCategoriesSetsSetting(self):
        self.viewer.filterUICommand.doChoice(False)
        self.assertFalse(
            self.settings.getboolean("view", "categoryfiltermatchall")
        )
