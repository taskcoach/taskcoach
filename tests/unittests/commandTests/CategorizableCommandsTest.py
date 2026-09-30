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

from taskcoachlib import command
from taskcoachlib.domain import category, categorizable
from .CommandTestCase import CommandTestCase


class ToggleCategoryCommandTestCase(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.category = category.Category("Cat")
        self.categorizable = categorizable.CategorizableCompositeObject(
            subject="Categorizable"
        )

    def toggleItem(self, items=None, category=None):
        check = command.ToggleCategoryCommand(
            category=category or self.category, items=items or []
        )
        check.do()


class ToggleCategory(ToggleCategoryCommandTestCase):
    def testToggleCategory_AffectsCategorizable(self):
        self.toggleItem([self.categorizable])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.category]), self.categorizable.categories()
            ),
            lambda: self.assertEqual(set(), self.categorizable.categories()),
        )

    def testToggleCategory_AffectsCategory(self):
        self.toggleItem([self.categorizable])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.categorizable]), self.category.categorizables()
            ),
            lambda: self.assertEqual(set(), self.category.categorizables()),
        )

    def testToggleCategory_AffectsCategorizableThatIsInCategory(self):
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.toggleItem([self.categorizable])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set(), self.categorizable.categories()),
            lambda: self.assertEqual(
                set([self.category]), self.categorizable.categories()
            ),
        )

    def testToggleCategory_AffectsCategoryThatAlreadyContainsCategorizable(
        self,
    ):
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.toggleItem([self.categorizable])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set(), self.category.categorizables()),
            lambda: self.assertEqual(
                set([self.categorizable]), self.category.categorizables()
            ),
        )

    def testToggleCategory_WhenSomeCategorizablesAreInCategory(self):
        """If some of the selected categorizables are in the category and some
        are not, toggle category puts all categorizables in the category,
        rather than toggling all categorizables."""
        categorizable2 = categorizable.CategorizableCompositeObject(
            subject="Categorizable2"
        )
        categorizable2.addCategory(self.category)
        self.category.addCategorizable(categorizable2)
        self.toggleItem([self.categorizable, categorizable2])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.categorizable, categorizable2]),
                self.category.categorizables(),
            ),
            lambda: self.assertEqual(
                set([categorizable2]), self.category.categorizables()
            ),
        )


class LinkCategories(ToggleCategoryCommandTestCase):
    # The editor's Check all and Uncheck all
    def link(self, link=True):
        self.other = category.Category("Other")
        command.LinkCategoriesCommand(
            None,
            [self.categorizable],
            categories=[self.category, self.other],
            link=link,
        ).do()

    def both_sides(self):
        return (
            self.categorizable.categories(),
            {
                each
                for each in (self.category, self.other)
                if self.categorizable in each.categorizables()
            },
        )

    def test_check_all_links_both_sides(self):
        self.link()
        both = {self.category, self.other}
        self.assertDoUndoRedo(
            lambda: self.assertEqual((both, both), self.both_sides()),
            lambda: self.assertEqual((set(), set()), self.both_sides()),
        )

    def test_uncheck_all_unlinks_both_sides(self):
        self.toggleItem([self.categorizable])
        self.link(link=False)
        linked = {self.category}
        self.assertDoUndoRedo(
            lambda: self.assertEqual((set(), set()), self.both_sides()),
            lambda: self.assertEqual((linked, linked), self.both_sides()),
        )


class ToggleMutualExclusiveCategories(ToggleCategoryCommandTestCase):
    def setUp(self):
        super().setUp()
        self.subCategory1, self.subCategory2 = (
            self.addMutualExclusiveSubcategories(self.category)
        )

    def addMutualExclusiveSubcategories(self, parentCategory):
        subCategory1 = category.Category("subCategory1")
        subCategory2 = category.Category("subCategory2")
        parentCategory.addChild(subCategory1)
        parentCategory.addChild(subCategory2)
        parentCategory.makeSubcategoriesExclusive()
        return subCategory1, subCategory2

    def testToggleMutualExclusiveSubcategory(self):
        self.categorizable.addCategory(self.subCategory1)
        self.subCategory1.addCategorizable(self.categorizable)
        self.toggleItem([self.categorizable], self.subCategory2)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.subCategory2]), self.categorizable.categories()
            ),
            lambda: self.assertEqual(
                set([self.subCategory1]), self.categorizable.categories()
            ),
        )

    def testToggleMutualExclusiveSubcategoryThatIsAlreadyChecked(self):
        self.categorizable.addCategory(self.subCategory1)
        self.subCategory1.addCategorizable(self.categorizable)
        self.toggleItem([self.categorizable], self.subCategory1)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set(), self.categorizable.categories()),
            lambda: self.assertEqual(
                set([self.subCategory1]), self.categorizable.categories()
            ),
        )

    def testToggleMutualExclusiveSubcategoryUnchecksParent(self):
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.toggleItem([self.categorizable], self.subCategory1)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set(), self.category.categorizables()),
            lambda: self.assertEqual(
                set([self.categorizable]), self.category.categorizables()
            ),
        )

    def testToggleMutualExclusiveCategoryUnchecksCheckedChild(self):
        self.categorizable.addCategory(self.subCategory1)
        self.subCategory1.addCategorizable(self.categorizable)
        self.toggleItem([self.categorizable], self.category)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set(), self.subCategory1.categorizables()
            ),
            lambda: self.assertEqual(
                set([self.categorizable]), self.subCategory1.categorizables()
            ),
        )

    def testToggleMutualExclusiveSubcategoryDoesNotUncheckMutualExclusiveParent(
        self,
    ):
        subCategory1_1, subCategory1_2 = self.addMutualExclusiveSubcategories(
            self.subCategory1
        )
        self.categorizable.addCategory(self.subCategory1)
        self.subCategory1.addCategorizable(self.categorizable)
        self.categorizable.addCategory(subCategory1_1)
        subCategory1_1.addCategorizable(self.categorizable)
        self.toggleItem([self.categorizable], subCategory1_2)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.categorizable]), self.subCategory1.categorizables()
            )
        )

    def testToggleMutualExclusiveSubcategoryRecursivelyUnchecksCheckedChildren(
        self,
    ):
        subCategory1_1 = self.addMutualExclusiveSubcategories(
            self.subCategory1
        )[0]
        self.categorizable.addCategory(self.subCategory1)
        self.subCategory1.addCategorizable(self.categorizable)
        self.categorizable.addCategory(subCategory1_1)
        subCategory1_1.addCategorizable(self.categorizable)
        self.toggleItem([self.categorizable], self.subCategory2)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set(), subCategory1_1.categorizables()),
            lambda: self.assertEqual(
                set([self.categorizable]), subCategory1_1.categorizables()
            ),
        )
