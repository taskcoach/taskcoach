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
from taskcoachlib import config
from taskcoachlib.domain import category, task


class CategoryContainerTest(test.TestCase):
    def setUp(self):
        self.categories = category.CategoryList()
        self.category = category.Category("Unfiltered category")
        self.filteredCategory = category.Category(
            "Filtered category", filtered=True
        )

    def testAddExistingCategory_WithoutTasks(self):
        self.categories.append(self.category)
        self.categories.append(category.Category(self.category.subject()))
        self.assertEqual(2, len(self.categories))

    def testAddCategoryWithCategorizable(self):
        aTask = task.Task()
        aTask.addCategory(self.category)
        self.categories.append(self.category)
        self.assertEqual(set([self.category]), aTask.categories())

    def testRemoveCategoryWithTask(self):
        aTask = task.Task()
        self.categories.append(self.category)
        aTask.addCategory(self.category)
        self.categories.removeItems([self.category])
        self.assertFalse(aTask.categories())

    def testFilteredCategoriesWhenCategoriesIsEmpty(self):
        self.assertFalse(self.categories.filteredCategories())

    def testFilteredCategoriesAfterAddingOneUnfilteredCategory(self):
        self.categories.append(self.category)
        self.assertFalse(self.categories.filteredCategories())

    def testFilteredCategoriesAfterAddingOneFilteredCategory(self):
        self.categories.append(self.filteredCategory)
        self.assertEqual(
            [self.filteredCategory], self.categories.filteredCategories()
        )

    def testFilteredCategoriesAfterAddingOneUnfilteredCategoryAndMakingItFilter(
        self,
    ):
        self.categories.append(self.category)
        self.category.setFiltered(True)
        self.assertEqual([self.category], self.categories.filteredCategories())

    def testFilteredCategoriesAfterRemovingOneUnfilteredCategory(self):
        self.categories.append(self.category)
        self.categories.remove(self.category)
        self.assertFalse(self.categories.filteredCategories())

    def testFilteredCategoriesAfterRemovingOneFilteredCategory(self):
        self.categories.append(self.filteredCategory)
        self.categories.remove(self.filteredCategory)
        self.assertFalse(self.categories.filteredCategories())

    def testFilteredCategoriesAfterAddingOneFilteredAndOneUnfilteredCategory(
        self,
    ):
        self.categories.extend([self.category, self.filteredCategory])
        self.assertEqual(
            [self.filteredCategory], self.categories.filteredCategories()
        )

    def testFilteredCategoriesAfterAddingOneFilteredAndOneUnfilteredCategoryAndMakingBothFiltered(
        self,
    ):
        self.categories.extend([self.category, self.filteredCategory])
        self.category.setFiltered(True)
        self.assertEqual(2, len(self.categories.filteredCategories()))

    def testFilteredCategoriesAfterAddingOneFilteredAndOneUnfilteredCategoryAndMakingNoneFiltered(
        self,
    ):
        self.categories.extend([self.category, self.filteredCategory])
        self.filteredCategory.setFiltered(False)
        self.assertFalse(self.categories.filteredCategories())

    def testResetAllFilteredCategories(self):
        self.categories.extend([self.category, self.filteredCategory])
        self.categories.resetAllFilteredCategories()
        self.assertFalse(self.filteredCategory.isFiltered())
