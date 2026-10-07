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
    def test_toggle_category_affects_categorizable(self):
        self.toggleItem([self.categorizable])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.category]), self.categorizable.categories()
            ),
            lambda: self.assertEqual(set(), self.categorizable.categories()),
        )

    def test_toggle_category_affects_category(self):
        self.toggleItem([self.categorizable])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.categorizable]), self.category.members()
            ),
            lambda: self.assertEqual(set(), self.category.members()),
        )

    def test_toggle_category_affects_categorizable_that_is_in_category(self):
        self.categorizable.addCategory(self.category)
        self.toggleItem([self.categorizable])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set(), self.categorizable.categories()),
            lambda: self.assertEqual(
                set([self.category]), self.categorizable.categories()
            ),
        )

    def test_toggle_category_affects_category_already_containing_item(
        self,
    ):
        self.categorizable.addCategory(self.category)
        self.toggleItem([self.categorizable])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set(), self.category.members()),
            lambda: self.assertEqual(
                set([self.categorizable]), self.category.members()
            ),
        )

    def test_toggle_category_when_some_categorizables_are_in_category(self):
        """If some of the selected categorizables are in the category and some
        are not, toggle category puts all categorizables in the category,
        rather than toggling all categorizables."""
        categorizable2 = categorizable.CategorizableCompositeObject(
            subject="Categorizable2"
        )
        categorizable2.addCategory(self.category)
        self.toggleItem([self.categorizable, categorizable2])
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.categorizable, categorizable2]),
                self.category.members(),
            ),
            lambda: self.assertEqual(
                set([categorizable2]), self.category.members()
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
                if self.categorizable in each.members()
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

    def addMutualExclusiveSubcategories(self, parent_category):
        sub_category_1 = category.Category("subCategory1")
        sub_category_2 = category.Category("subCategory2")
        parent_category.addChild(sub_category_1)
        parent_category.addChild(sub_category_2)
        parent_category.makeSubcategoriesExclusive()
        return sub_category_1, sub_category_2

    def test_toggle_mutual_exclusive_subcategory(self):
        self.categorizable.addCategory(self.subCategory1)
        self.toggleItem([self.categorizable], self.subCategory2)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.subCategory2]), self.categorizable.categories()
            ),
            lambda: self.assertEqual(
                set([self.subCategory1]), self.categorizable.categories()
            ),
        )

    def test_toggle_mutual_exclusive_subcategory_that_is_already_checked(self):
        self.categorizable.addCategory(self.subCategory1)
        self.toggleItem([self.categorizable], self.subCategory1)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set(), self.categorizable.categories()),
            lambda: self.assertEqual(
                set([self.subCategory1]), self.categorizable.categories()
            ),
        )

    def test_toggle_mutual_exclusive_subcategory_unchecks_parent(self):
        self.categorizable.addCategory(self.category)
        self.toggleItem([self.categorizable], self.subCategory1)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set(), self.category.members()),
            lambda: self.assertEqual(
                set([self.categorizable]), self.category.members()
            ),
        )

    def test_toggle_mutual_exclusive_category_unchecks_checked_child(self):
        self.categorizable.addCategory(self.subCategory1)
        self.toggleItem([self.categorizable], self.category)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set(), self.subCategory1.members()),
            lambda: self.assertEqual(
                set([self.categorizable]), self.subCategory1.members()
            ),
        )

    def test_toggle_exclusive_subcategory_keeps_exclusive_parent_checked(
        self,
    ):
        sub_category_1_1, sub_category_1_2 = (
            self.addMutualExclusiveSubcategories(self.subCategory1)
        )
        self.categorizable.addCategory(self.subCategory1)
        self.categorizable.addCategory(sub_category_1_1)
        self.toggleItem([self.categorizable], sub_category_1_2)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                set([self.categorizable]), self.subCategory1.members()
            )
        )

    def test_toggle_exclusive_subcategory_unchecks_children_recursively(
        self,
    ):
        sub_category_1_1 = self.addMutualExclusiveSubcategories(
            self.subCategory1
        )[0]
        self.categorizable.addCategory(self.subCategory1)
        self.categorizable.addCategory(sub_category_1_1)
        self.toggleItem([self.categorizable], self.subCategory2)
        self.assertDoUndoRedo(
            lambda: self.assertEqual(set(), sub_category_1_1.members()),
            lambda: self.assertEqual(
                set([self.categorizable]), sub_category_1_1.members()
            ),
        )
