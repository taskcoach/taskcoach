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

from unittests import asserts
from .CommandTestCase import CommandTestCase
from taskcoachlib import patterns, command
from taskcoachlib.domain import category, task


class CategoryCommandTestCase(CommandTestCase, asserts.CommandAssertsMixin):
    def setUp(self):
        super().setUp()
        self.categories = self.task_file.categories()


class NewCategoryCommandTest(CategoryCommandTestCase):
    def new(self):
        new_category_command = command.NewCategoryCommand(self.categories)
        new_category = new_category_command.items[0]
        new_category_command.do()
        return new_category

    def test_new_category(self):
        new_category = self.new()
        self.assertDoUndoRedo(
            lambda: self.assertEqual([new_category], self.categories),
            lambda: self.assertEqual([], self.categories),
        )


class NewSubCategoryCommandTest(CategoryCommandTestCase):
    def setUp(self):
        super().setUp()
        self.category = category.Category("category")
        self.categories.append(self.category)

    def newSubCategory(self, categories=None):
        new_sub_category = command.NewSubCategoryCommand(
            self.categories, categories or []
        )
        new_sub_category.do()

    def test_new_sub_category_without_selection(self):
        self.newSubCategory()
        self.assertDoUndoRedo(
            lambda: self.assertEqual([self.category], self.categories)
        )

    def test_new_sub_category(self):
        self.newSubCategory([self.category])
        new_sub_category = self.category.children()[0]
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                [new_sub_category], self.category.children()
            ),
            lambda: self.assertEqual([self.category], self.categories),
        )


class DragAndDropCategoryCommandTest(CategoryCommandTestCase):
    def setUp(self):
        super().setUp()
        self.parent = category.Category("parent")
        self.child = category.Category("child")
        self.grandchild = category.Category("grandchild")
        self.parent.addChild(self.child)
        self.child.addChild(self.grandchild)
        self.categories.extend([self.parent, self.child])

    def dragAndDrop(self, drop_target, categories=None):
        command.DragAndDropCategoryCommand(
            self.categories, categories or [], drop=drop_target
        ).do()

    def test_cannot_drop_on_parent(self):
        self.dragAndDrop([self.parent], [self.child])
        self.assertFalse(patterns.CommandHistory().has_history())

    def test_cannot_drop_on_child(self):
        self.dragAndDrop([self.child], [self.parent])
        self.assertFalse(patterns.CommandHistory().has_history())

    def test_cannot_drop_on_grandchild(self):
        self.dragAndDrop([self.grandchild], [self.parent])
        self.assertFalse(patterns.CommandHistory().has_history())

    def test_drop_as_root_task(self):
        self.dragAndDrop([], [self.grandchild])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(None, self.grandchild.parent()),
            lambda: self.assertEqual(self.child, self.grandchild.parent()),
        )


class CopyAndPasteCommandTest(CategoryCommandTestCase):
    def setUp(self):
        super().setUp()
        self.original = category.Category("original")
        self.categories.append(self.original)
        self.task = task.Task()

    def copy(self, categories_to_copy):
        command.CopyCommand(self.categories, categories_to_copy).do()

    def paste(self):
        command.PasteCommand(self.categories).do()

    def test_paste_one_category(self):
        self.copy([self.original])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(2, len(self.categories)),
            lambda: self.assertEqual([self.original], self.categories),
        )

    def test_copy_one_category_with_tasks(self):
        self.task.addCategory(self.original)
        self.copy([self.original])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.original]), self.task.categories()
            )
        )

    def test_paste_one_category_with_tasks(self):
        self.task.addCategory(self.original)
        self.copy([self.original])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(2, len(self.task.categories())),
            lambda: self.assertEqual(
                set([self.original]), self.task.categories()
            ),
        )

    def test_paste_category_with_sub_category(self):
        child_cat = category.Category("child")
        self.categories.append(child_cat)
        self.original.addChild(child_cat)
        self.task.addCategory(child_cat)
        self.copy([self.original])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(2, len(self.task.categories())),
            lambda: self.assertEqual(set([child_cat]), self.task.categories()),
        )


class EditExclusiveSubcategoriesCommandTest(CategoryCommandTestCase):
    def setUp(self):
        super().setUp()
        self.category = category.Category("category")

    def test_edit(self):
        self.categories.append(self.category)
        edit = command.EditExclusiveSubcategoriesCommand(
            self.categories, [self.category], newValue=True
        )
        edit.do()
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.category.hasExclusiveSubcategories()),
            lambda: self.assertFalse(
                self.category.hasExclusiveSubcategories()
            ),
        )
