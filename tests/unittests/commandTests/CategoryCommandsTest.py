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
from taskcoachlib import patterns, command, config
from taskcoachlib.domain import category, task


class CategoryCommandTestCase(CommandTestCase, asserts.CommandAssertsMixin):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.categories = category.CategoryList()


class NewCategoryCommandTest(CategoryCommandTestCase):
    def new(self):
        newCategoryCommand = command.NewCategoryCommand(self.categories)
        newCategory = newCategoryCommand.items[0]
        newCategoryCommand.do()
        return newCategory

    def testNewCategory(self):
        newCategory = self.new()
        self.assertDoUndoRedo(
            lambda: self.assertEqual([newCategory], self.categories),
            lambda: self.assertEqual([], self.categories),
        )


class NewSubCategoryCommandTest(CategoryCommandTestCase):
    def setUp(self):
        super().setUp()
        self.category = category.Category("category")
        self.categories.append(self.category)

    def newSubCategory(self, categories=None):
        newSubCategory = command.NewSubCategoryCommand(
            self.categories, categories or []
        )
        newSubCategory.do()

    def testNewSubCategory_WithoutSelection(self):
        self.newSubCategory()
        self.assertDoUndoRedo(
            lambda: self.assertEqual([self.category], self.categories)
        )

    def testNewSubCategory(self):
        self.newSubCategory([self.category])
        newSubCategory = self.category.children()[0]
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                [newSubCategory], self.category.children()
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

    def dragAndDrop(self, dropTarget, categories=None):
        command.DragAndDropCategoryCommand(
            self.categories, categories or [], drop=dropTarget
        ).do()

    def testCannotDropOnParent(self):
        self.dragAndDrop([self.parent], [self.child])
        self.assertFalse(patterns.CommandHistory().hasHistory())

    def testCannotDropOnChild(self):
        self.dragAndDrop([self.child], [self.parent])
        self.assertFalse(patterns.CommandHistory().hasHistory())

    def testCannotDropOnGrandchild(self):
        self.dragAndDrop([self.grandchild], [self.parent])
        self.assertFalse(patterns.CommandHistory().hasHistory())

    def testDropAsRootTask(self):
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

    def copy(self, categoriesToCopy):
        command.CopyCommand(self.categories, categoriesToCopy).do()

    def paste(self):
        command.PasteCommand(self.categories).do()

    def testPasteOneCategory(self):
        self.copy([self.original])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(2, len(self.categories)),
            lambda: self.assertEqual([self.original], self.categories),
        )

    def testCopyOneCategoryWithTasks(self):
        self.task.addCategory(self.original)
        self.copy([self.original])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.original]), self.task.categories()
            )
        )

    def testPasteOneCategoryWithTasks(self):
        self.task.addCategory(self.original)
        self.copy([self.original])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(2, len(self.task.categories())),
            lambda: self.assertEqual(
                set([self.original]), self.task.categories()
            ),
        )

    def testPasteCategoryWithSubCategory(self):
        childCat = category.Category("child")
        self.categories.append(childCat)
        self.original.addChild(childCat)
        self.task.addCategory(childCat)
        self.copy([self.original])
        self.paste()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(2, len(self.task.categories())),
            lambda: self.assertEqual(set([childCat]), self.task.categories()),
        )


class EditExclusiveSubcategoriesCommandTest(CategoryCommandTestCase):
    def setUp(self):
        super().setUp()
        self.category = category.Category("category")

    def testEdit(self):
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
