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
from taskcoachlib import gui, persistence
from taskcoachlib.domain import category
from taskcoachlib.config import settings


class CategoryViewerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.taskFile = persistence.TaskFile()
        self.categories = self.taskFile.categories()
        self.viewer = gui.viewer.CategoryViewer(self.frame, self.taskFile)

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def addTwoCategories(self):
        cat1 = category.Category("1")
        cat2 = category.Category("2")
        self.categories.extend([cat2, cat1])
        return cat1, cat2

    def test_check_all_in_the_editor_keeps_the_categories_on_save(self):
        # The file stores the category's side of the link
        from taskcoachlib.domain import task

        cat1, cat2 = self.addTwoCategories()
        paint = task.Task(subject="paint")
        self.taskFile.tasks().append(paint)
        local = gui.dialog.editor.LocalCategoryViewer(
            [paint], self.frame, self.taskFile
        )
        local.check_all_categories()
        self.assertEqual(
            ({cat1, cat2}, [paint], [paint]),
            (
                paint.categories(),
                list(cat1.members()),
                list(cat2.members()),
            ),
        )

    def test_initial_size(self):
        self.assertEqual(0, self.viewer.size())

    def test_copy_category_with_children(self):
        parent, child = self.addTwoCategories()
        parent.addChild(child)
        copy = parent.copy()
        self.categories.append(copy)
        self.viewer.expand_all()
        self.assertEqual(4, self.viewer.size())

    def test_sort_in_widget(self):
        self.addTwoCategories()
        widget = self.viewer.widget
        for item, cat in zip(
            widget.get_item_children(), self.viewer.presentation()
        ):
            self.assertEqual(cat.subject(), widget.GetItemText(item))

    def test_select_all(self):
        self.addTwoCategories()
        self.viewer.widget.select_all()
        self.viewer.updateSelection()
        self.assertEqual(2, len(self.viewer.curselection()))

    def test_filter_on_all_checked_categories_sets_setting(self):
        self.viewer.filterUICommand.doChoice(True)
        self.assertTrue(settings.get("view", "categoryfiltermatchall"))

    def test_filter_on_any_checked_categories_sets_setting(self):
        self.viewer.filterUICommand.doChoice(False)
        self.assertFalse(settings.get("view", "categoryfiltermatchall"))
