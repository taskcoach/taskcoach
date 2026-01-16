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
from taskcoachlib.domain import task, category

# pylint: disable=W0201,E1101

""" The tests below test the category filter. Different fixtures are defined
    for different combinations of tasks and categories. Each fixture is than
    subclassed by a <Fixture>InListMode and a <Fixture>InTreeMode class since 
    we want to run the tests in both list and tree mode. """  # pylint: disable=W0105


class CategoryFilterHelpersMixin(object):
    def setFilterOnAnyCategory(self):
        self.settings.setboolean("view", "categoryfiltermatchall", False)

    def setFilterOnAllCategories(self):
        self.settings.setboolean("view", "categoryfiltermatchall", True)

    def link(self, category, categorizable):  # pylint: disable=W0621
        category.addCategorizable(categorizable)
        categorizable.addCategory(category)

    def assertChildTaskIsFiltered(self):
        self.assertEqual(
            set(
                [self.childTask, self.parentTask]
                if self.treeMode
                else [self.childTask]
            ),
            set(self.filter),
        )

    def assertFilterHidesNothing(self):
        self.assertEqual(set(self.tasks), set(self.filter))

    def assertFilterHidesEverything(self):
        self.assertFalse(self.filter)


class Fixture(CategoryFilterHelpersMixin):
    treeMode = False

    def setUp(self):
        self.settings = task.Task.settings = config.Settings(load=False)
        self.categories = category.CategoryList(self.createCategories())
        self.tasks = task.TaskList(self.createTasks())
        self.categorize()
        self.filter = category.filter.CategoryFilter(
            self.tasks, categories=self.categories, treeMode=self.treeMode
        )

    def createTasks(self):
        return []

    def createCategories(self):
        return []  # pragma: no cover

    def categorize(self):
        pass

    # Common tests that should pass for all fixtures

    def testThatFilterContainsAllItemsWhenNotFiltering(self):
        self.assertEqual(self.filter.originalLength(), len(self.filter))

    def testThatFilterOriginalLengthAlwaysEqualsNumberOfTasksWhenNotFiltering(
        self,
    ):
        self.assertEqual(self.filter.originalLength(), len(self.tasks))

    def testThatFilterContainsNoItemsWhenRemovingOriginalItems(self):
        self.tasks.clear()
        self.assertEqual(0, self.filter.originalLength())

    def testThatFilterLengthIsSmallerOrEqualThanOriginalLength(self):
        self.assertTrue(len(self.filter) <= self.filter.originalLength())

    def testThatFilterIsEmptyWhenFilteringOnACategoryWithoutCategorizables(
        self,
    ):
        emptyCategory = category.Category("empty")
        self.categories.append(emptyCategory)
        emptyCategory.setFiltered()
        self.assertFalse(self.filter)

    def testThatFilterContainsAllItemsAfterRemovingFilteredEmptyCategory(self):
        emptyCategory = category.Category("empty")
        self.categories.append(emptyCategory)
        emptyCategory.setFiltered()
        self.categories.remove(emptyCategory)
        self.assertFilterHidesNothing()

    def testThatFilterContainsAllItemsAfterFilteringAndUnfiltering(self):
        aCategory = list(self.categories)[0]
        aCategory.setFiltered()
        aCategory.setFiltered(False)
        self.assertFilterHidesNothing()

    def testThatFilterContainsAllItemsAfterUnfilteringACategoryThatWasNotFiltered(
        self,
    ):
        aCategory = list(self.categories)[0]
        aCategory.setFiltered(False)
        self.assertFilterHidesNothing()

    def testThatFilterContainsAllItemsWhenFilteringOnAnyCategoryWithoutAnyCategoryFiltered(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.assertFilterHidesNothing()

    def testThatFilterContainsAllItemsWhenFilteringOnAllCategoriesWithoutAnyCategoryFiltered(
        self,
    ):
        self.setFilterOnAllCategories()
        self.assertFilterHidesNothing()

    def testThatFilterContainsNewlyAddedTaskThatBelongsToTheFilteredCategory(
        self,
    ):
        aCategory = list(self.categories)[0]
        aCategory.setFiltered()
        newTask = task.Task()
        newTask.addCategory(aCategory)
        self.tasks.append(newTask)
        self.assertTrue(newTask in self.filter)

    def testThatFilterDoesContainNewlyAddedTaskThatBelongsToTheFilteredCategoryAfterRemoval(
        self,
    ):
        aCategory = list(self.categories)[0]
        aCategory.setFiltered()
        newTask = task.Task()
        newTask.addCategory(aCategory)
        self.tasks.append(newTask)
        self.tasks.remove(newTask)
        self.assertFalse(newTask in self.filter)

    def testThatFilterContainsNoTasksWhenFilteringAllCategoriesIncludingAnEmptyCategory(
        self,
    ):
        emptyCategory = category.Category("empty")
        self.categories.append(emptyCategory)
        for eachCategory in self.categories:
            eachCategory.setFiltered()
        self.setFilterOnAllCategories()
        self.assertFilterHidesEverything()


class OneCategoryFixture(Fixture):
    def createCategories(self):
        self.category = category.Category("category")
        return [self.category]

    def testThatFilterIsEmptyWhenNoCategoriesAreFiltered(self):
        self.assertEqual(0, len(self.filter))

    def testThatFilterIsEmptyWhenCategoryIsFiltered(self):
        self.category.setFiltered()
        self.assertEqual(0, len(self.filter))


class OneCategoryFilterInListModeTest(OneCategoryFixture, test.TestCase):
    treeMode = False


class OneCategoryFilterInTreeModeTest(OneCategoryFixture, test.TestCase):
    treeMode = True


class OneCategoryAndOneTaskFixture(Fixture):
    def createCategories(self):
        self.category = category.Category("category")
        return [self.category]

    def createTasks(self):
        self.task = task.Task("task")
        return [self.task]

    def testThatFilterContainsUncategorizedTaskWhenNoCategoriesAreFiltered(
        self,
    ):
        self.assertFilterHidesNothing()

    def testThatFilterDoesNotContainUncategorizedTaskWhenCategoryIsFiltered(
        self,
    ):
        self.category.setFiltered()
        self.assertFilterHidesEverything()

    def testThatFilterContainsCategorizedTaskWhenCategoryIsFiltered(self):
        self.link(self.category, self.task)
        self.category.setFiltered()
        self.assertFilterHidesNothing()


class OneCategoryAndOneTaskInListModeTest(
    OneCategoryAndOneTaskFixture, test.TestCase
):
    treeMode = False


class OneCategoryAndOneTaskInTreeModeTest(
    OneCategoryAndOneTaskFixture, test.TestCase
):
    treeMode = True


class OneCategoryAndTwoTasksFixture(Fixture):
    def createCategories(self):
        self.category = category.Category("category")
        return [self.category]

    def createTasks(self):
        self.task1 = task.Task("task1")
        self.task2 = task.Task("task2")
        return [self.task1, self.task2]

    def testThatFilterContainsAllUncategorizedTaskWhenCategoryIsNotFiltered(
        self,
    ):
        self.assertFilterHidesNothing()

    def testThatFilterContainsNoUncategorizedTasksWhenCategoryIsFiltered(self):
        self.category.setFiltered()
        self.assertFilterHidesEverything()

    def testThatFilterContainsCategorizedTaskWhenCategoryIsFiltered(self):
        self.category.setFiltered()
        self.link(self.category, self.task1)
        self.assertEqual([self.task1], list(self.filter))

    def testThatFilterContainsCategorizedTasksWhenCategoryIsFiltered(self):
        self.category.setFiltered()
        self.link(self.category, self.task1)
        self.link(self.category, self.task2)
        self.assertFilterHidesNothing()


class OneCategoryAndTwoTasksInListModeTest(
    OneCategoryAndTwoTasksFixture, test.TestCase
):
    treeMode = False


class OneCategoryAndTwoTasksInTreeModeTest(
    OneCategoryAndTwoTasksFixture, test.TestCase
):
    treeMode = True


class TwoCategoriesAndOneTaskFixture(Fixture):
    def createCategories(self):
        self.category1 = category.Category("category1")
        self.category2 = category.Category("category2")
        return [self.category1, self.category2]

    def createTasks(self):
        self.task = task.Task("task")
        return [self.task]

    def categorize(self):
        self.link(self.category1, self.task)

    def testThatFilterContainsTaskWhenFilteringOnAnyCategoryAndBothAreFiltered(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesNothing()

    def testThatFilterDoesNotContainTaskWhenFilteringOnAllCategoriesAndBothAreFiltered(
        self,
    ):
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesEverything()


class TwoCategoriesAndOneTaskInListModeTest(
    TwoCategoriesAndOneTaskFixture, test.TestCase
):
    treeMode = False


class TwoCategoriesAndOneTaskInTreeModeTest(
    TwoCategoriesAndOneTaskFixture, test.TestCase
):
    treeMode = True


class TwoCategoriesAndTwoTasksFixture(Fixture):
    def createCategories(self):
        self.category1 = category.Category("category1")
        self.category2 = category.Category("category2")
        return [self.category1, self.category2]

    def createTasks(self):
        self.task1 = task.Task("task1")
        self.task2 = task.Task("task2")
        return [self.task1, self.task2]

    def testThatFilterContainsAllUncategorizedTaskWhenCategoryIsNotFiltered(
        self,
    ):
        self.assertFilterHidesNothing()

    def testThatFilterContainsNoUncategorizedTasksWhenCategoryIsFiltered(self):
        self.category1.setFiltered()
        self.assertFilterHidesEverything()

    def testThatFilterContainsNoUncategorizedTasksWhenAnyCategoryIsFiltered(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesEverything()

    def testThatFilterContainsNoUncategorizedTasksWhenAllCategoriesAreFiltered(
        self,
    ):
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesEverything()

    def testThatFilterContainsCategorizedTaskWhenAnyCategoryIsFiltered(self):
        self.link(self.category1, self.task1)
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertEqual([self.task1], list(self.filter))

    def testThatFilterDoesNotContainCategorizedTaskWhenAllCategoriesAreFiltered(
        self,
    ):
        self.link(self.category1, self.task1)
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesEverything()

    def testThatFilterContainsCategorizedTaskWhenFilteringByThatCategory(self):
        self.link(self.category1, self.task1)
        self.category1.setFiltered()
        self.assertEqual([self.task1], list(self.filter))

    def testThatFilterDoesNotContainCategorizedTaskWhenFilteringByAnotherCategory(
        self,
    ):
        self.link(self.category1, self.task1)
        self.category2.setFiltered()
        self.assertFilterHidesEverything()

    def testThatFilterContainsCategorizedTasksWhenFilteringByThatCategory(
        self,
    ):
        self.category1.setFiltered()
        self.link(self.category1, self.task1)
        self.link(self.category1, self.task2)
        self.assertFilterHidesNothing()

    def testThatFilterContainsCategorizedTasksWhenFilteringByAnyCategory(self):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.link(self.category1, self.task1)
        self.link(self.category1, self.task2)
        self.assertFilterHidesNothing()

    def testThatFilterDoesNotContainCategorizedTasksWhenFilteringByAllCategories(
        self,
    ):
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.link(self.category1, self.task1)
        self.link(self.category1, self.task2)
        self.assertFilterHidesEverything()


class TwoCategoriesAndTwoTasksInListModeTest(
    TwoCategoriesAndTwoTasksFixture, test.TestCase
):
    treeMode = False


class TwoCategoriesAndTwoTasksInTreeModeTest(
    TwoCategoriesAndTwoTasksFixture, test.TestCase
):
    treeMode = True


class OneCategoryAndParentAndChildTaskFixture(Fixture):
    def createCategories(self):
        self.category = category.Category("category")
        return [self.category]

    def createTasks(self):
        self.parentTask = task.Task("parent")
        self.childTask = task.Task("child")
        self.parentTask.addChild(self.childTask)
        self.childTask.setParent(self.parentTask)
        return [self.parentTask, self.childTask]

    def testThatFilterContainsChildWhenParentIsCategorizedAndFiltered(self):
        self.link(self.category, self.parentTask)
        self.category.setFiltered()
        self.assertFilterHidesNothing()

    def testThatFilterContainsParentWhenChildIsCategorizedAndFilteredButOnlyInTreeMode(
        self,
    ):
        self.link(self.category, self.childTask)
        self.category.setFiltered()
        self.assertEqual(2 if self.treeMode else 1, len(self.filter))


class OneCategoryAndParentAndChildTaskInListModeTest(
    OneCategoryAndParentAndChildTaskFixture, test.TestCase
):
    treeMode = False


class OneCategoryAndParentAndChildTaskInTreeModeTest(
    OneCategoryAndParentAndChildTaskFixture, test.TestCase
):
    treeMode = True


class TwoCategoriesAndParentAndChildTaskFixture(Fixture):
    def createCategories(self):
        self.category1 = category.Category("category1")
        self.category2 = category.Category("category2")
        return [self.category1, self.category2]

    def createTasks(self):
        self.parentTask = task.Task("parent")
        self.childTask = task.Task("child")
        self.parentTask.addChild(self.childTask)
        self.childTask.setParent(self.parentTask)
        return [self.parentTask, self.childTask]

    def categorize(self):
        self.link(self.category1, self.parentTask)
        self.link(self.category2, self.childTask)

    def testThatFilterContainsBothParentAndChildTaskWhenFilteringOnAnyCategoryAndBothCategories(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesNothing()

    def testThatFilterContainsBothParentAndChildTaskWhenFilteringOnAllCategoriesAndBothCategories(
        self,
    ):
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertChildTaskIsFiltered()


class TwoCategoriesAndParentAndChildTaskInListModeTest(
    TwoCategoriesAndParentAndChildTaskFixture, test.TestCase
):
    treeMode = False


class TwoCategoriesAndParentAndChildTaskInTreeModeTest(
    TwoCategoriesAndParentAndChildTaskFixture, test.TestCase
):
    treeMode = True


class ParentAndChildCategoryAndParentAndChildTaskFixture(Fixture):
    def createCategories(self):
        self.parentCategory = category.Category("parent")
        self.childCategory = category.Category("child")
        self.parentCategory.addChild(self.childCategory)
        self.childCategory.setParent(self.parentCategory)
        return [self.parentCategory, self.childCategory]

    def createTasks(self):
        self.parentTask = task.Task("parent")
        self.childTask = task.Task("child")
        self.parentTask.addChild(self.childTask)
        self.childTask.setParent(self.parentTask)
        return [self.parentTask, self.childTask]

    def testThatFilterContainsBothTasksWhenParentTaskIsInParentCategoryAndFilteringParentCategory(
        self,
    ):
        self.link(self.parentCategory, self.parentTask)
        self.parentCategory.setFiltered()
        self.assertFilterHidesNothing()

    def testThatFilterContainsNoTasksWhenParentTaskIsInParentCategoryAndFilteringChildCategory(
        self,
    ):
        self.link(self.parentCategory, self.parentTask)
        self.childCategory.setFiltered()
        self.assertFilterHidesEverything()

    def testThatFilterContainsBothTasksWhenParentTaskIsInChildCategoryAndFilteringParentCategory(
        self,
    ):
        self.link(self.childCategory, self.parentTask)
        self.parentCategory.setFiltered()
        self.assertFilterHidesNothing()

    def testThatFilterContainsBothTasksWhenParentTaskIsInChildCategoryAndFilteringChildCategory(
        self,
    ):
        self.link(self.childCategory, self.parentTask)
        self.childCategory.setFiltered()
        self.assertFilterHidesNothing()

    def testThatFilterContainsChildTaskWhenChildTaskIsInParentCategoryAndFilteringParentCategory(
        self,
    ):
        self.link(self.parentCategory, self.childTask)
        self.parentCategory.setFiltered()
        self.assertChildTaskIsFiltered()

    def testThatFilterContainsNoTasksWhenChildTaskIsInParentCategoryAndFilteringChildCategory(
        self,
    ):
        self.link(self.parentCategory, self.childTask)
        self.childCategory.setFiltered()
        self.assertFilterHidesEverything()

    def testThatFilterContainsChildTaskWhenChildTaskIsInChildCategoryAndFilteringParentCategory(
        self,
    ):
        self.link(self.childCategory, self.childTask)
        self.parentCategory.setFiltered()
        self.assertChildTaskIsFiltered()

    def testThatFilterContainsChildTaskWhenChildTaskIsInChildCategoryAndFilteringChildCategory(
        self,
    ):
        self.link(self.childCategory, self.childTask)
        self.childCategory.setFiltered()
        self.assertChildTaskIsFiltered()

    def testThatFilterContainsBothTasksWhenParentTaskIsInChildCategoryAndFilteringBothCategories(
        self,
    ):
        self.setFilterOnAllCategories()
        self.link(self.childCategory, self.parentTask)
        self.parentCategory.setFiltered()
        self.childCategory.setFiltered()
        self.assertFilterHidesNothing()

    def testThatFilterContainsChildTaskWhenChildTaskIsInChildCategoryAndFilteringBothCategories(
        self,
    ):
        self.setFilterOnAllCategories()
        self.link(self.childCategory, self.childTask)
        self.parentCategory.setFiltered()
        self.childCategory.setFiltered()
        self.assertChildTaskIsFiltered()


class ParentAndChildCategoryAndParentAndChildTaskInListModeTest(
    ParentAndChildCategoryAndParentAndChildTaskFixture, test.TestCase
):
    treeMode = False


class ParentAndChildCategoryAndParentAndChildTaskInTreeModeTest(
    ParentAndChildCategoryAndParentAndChildTaskFixture, test.TestCase
):
    treeMode = True


class ParentAndChildCategoryAndParentAndGrandChildTaskFixture(Fixture):
    def createCategories(self):
        self.parentCategory = category.Category("parent")
        self.childCategory = category.Category("child")
        self.parentCategory.addChild(self.childCategory)
        self.childCategory.setParent(self.parentCategory)
        return [self.parentCategory, self.childCategory]

    def createTasks(self):
        self.parentTask = task.Task("parent")
        self.childTask = task.Task("child")
        self.grandChildTask = task.Task("grandchild")
        self.parentTask.addChild(self.childTask)
        self.childTask.setParent(self.parentTask)
        self.childTask.addChild(self.grandChildTask)
        self.grandChildTask.setParent(self.childTask)
        return [self.parentTask, self.childTask, self.grandChildTask]

    def testThatFilterContainsAllTasksWhenParentTaskIsInChildCategoryAndFiltered(
        self,
    ):
        self.link(self.childCategory, self.parentTask)
        self.parentCategory.setFiltered()
        self.assertFilterHidesNothing()

    def testThatFilterContainsAllTasksWhenParentTaskIsInChildCategoryAndAllCategoriesAreFiltered(
        self,
    ):
        self.setFilterOnAllCategories()
        self.link(self.childCategory, self.parentTask)
        self.parentCategory.setFiltered()
        self.childCategory.setFiltered()
        self.assertFilterHidesNothing()

    def testThatFilterContainsGrandChildTaskWhenChildTaskIsInChildCategoryAndParentCategoryIsFiltered(
        self,
    ):
        self.link(self.childCategory, self.childTask)
        self.parentCategory.setFiltered()
        self.assertTrue(self.grandChildTask in self.filter)

    def testThatFilterContainsGrandChildTaskWhenChildTaskIsInChildCategoryAndAllCategoriesAreFiltered(
        self,
    ):
        self.setFilterOnAllCategories()
        self.link(self.childCategory, self.childTask)
        self.parentCategory.setFiltered()
        self.childCategory.setFiltered()
        self.assertTrue(self.grandChildTask in self.filter)

    def testThatFilterContainsGrandParentWhenGrandChildIsInChildCategoryAndParentCategoryIsFiltered(
        self,
    ):
        self.link(self.childCategory, self.grandChildTask)
        self.parentCategory.setFiltered()
        self.assertEqual(
            set(self.tasks) if self.treeMode else set([self.grandChildTask]),
            set(self.filter),
        )


class ParentAndChildCategoryAndParentAndGrandChildTaskInListModeTest(
    ParentAndChildCategoryAndParentAndGrandChildTaskFixture, test.TestCase
):
    treeMode = False


class ParentAndChildCategoryAndParentAndGrandChildTaskInTreeModeTest(
    ParentAndChildCategoryAndParentAndGrandChildTaskFixture, test.TestCase
):
    treeMode = True


class TwoCategoriesAndParentAndGrandChildTaskFixture(Fixture):
    def createCategories(self):
        self.category1 = category.Category("category1")
        self.category2 = category.Category("category2")
        return [self.category1, self.category2]

    def createTasks(self):
        self.parentTask = task.Task("parent")
        self.childTask = task.Task("child")
        self.grandChildTask = task.Task("grandchild")
        self.parentTask.addChild(self.childTask)
        self.childTask.setParent(self.parentTask)
        self.childTask.addChild(self.grandChildTask)
        self.grandChildTask.setParent(self.childTask)
        return [self.parentTask, self.childTask, self.grandChildTask]

    def categorize(self):
        self.link(self.category1, self.parentTask)
        self.link(self.category2, self.grandChildTask)

    def testThatFilterContainsGrandChildWhenFilteringOnAllCategories(self):
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertEqual(
            set(self.tasks) if self.treeMode else set([self.grandChildTask]),
            set(self.filter),
        )

    def testThatFilterContainsGrandChildWhenFilteringOnAnyCategory(self):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesNothing()


class TwoCategoriesAndParentAndGrandChildTaskInListModeTest(
    TwoCategoriesAndParentAndGrandChildTaskFixture, test.TestCase
):
    treeMode = False


class TwoCategoriesAndParentAndGrandChildTaskInTreeModeTest(
    TwoCategoriesAndParentAndGrandChildTaskFixture, test.TestCase
):
    treeMode = True


class TwoCategoriesAndParentWithTwoChildTasksFixture(Fixture):
    def createCategories(self):
        self.category1 = category.Category("category1")
        self.category2 = category.Category("category2")
        return [self.category1, self.category2]

    def createTasks(self):
        self.parentTask = task.Task("parent")
        self.child1Task = task.Task("child1")
        self.child2Task = task.Task("child2")
        self.parentTask.addChild(self.child1Task)
        self.parentTask.addChild(self.child2Task)
        self.child1Task.setParent(self.parentTask)
        self.child2Task.setParent(self.parentTask)
        return [self.parentTask, self.child1Task, self.child2Task]

    def categorize(self):
        self.link(self.category1, self.child1Task)
        self.link(self.category2, self.child2Task)

    def testThatFilterIsEmptyWhenFilteringOnAllCategoriesAndChildTasksHaveTwoDifferentCategories(
        self,
    ):
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesEverything()

    def testThatFilterContainsAllTasksWhenFilteringOnAnyCategoryAndChildTasksHaveTwoDifferentCategories(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertEqual(3 if self.treeMode else 2, len(self.filter))

    def testThatFilterHidesUnfilteredChild(self):
        self.category1.setFiltered()
        self.assertFalse(self.child2Task in self.filter)


class TwoCategoriesAndParentWithTwoChildTasksInListModeTest(
    TwoCategoriesAndParentWithTwoChildTasksFixture, test.TestCase
):
    treeMode = False


class TwoCategoriesAndParentWithTwoChildTasksInTreeModeTest(
    TwoCategoriesAndParentWithTwoChildTasksFixture, test.TestCase
):
    treeMode = True


class ParentAndChildCategoryAndOneTaskFixture(Fixture):
    def createCategories(self):
        self.parentCategory = category.Category("parent")
        self.childCategory = category.Category("child")
        self.parentCategory.addChild(self.childCategory)
        self.childCategory.setParent(self.parentCategory)
        return [self.parentCategory, self.childCategory]

    def createTasks(self):
        self.task = task.Task("task")
        return [self.task]

    def testThatFilterDoesNotContainTaskIfTaskHasChildCategoryAndParentIsFiltered(
        self,
    ):
        self.link(self.parentCategory, self.task)
        self.childCategory.setFiltered()
        self.assertFalse(self.filter)

    def testThatFilterContainsTaskIfTaskIfTaskHasParentCategoryAndChildIsFiltered(
        self,
    ):
        self.link(self.childCategory, self.task)
        self.parentCategory.setFiltered()
        self.assertFilterHidesNothing()

    def testThatFilterContainsTaskIfTaskHasParentAndChildCategoryAndAnyCategoryIsFiltered(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.link(self.parentCategory, self.task)
        self.link(self.childCategory, self.task)
        self.parentCategory.setFiltered()
        self.childCategory.setFiltered()
        self.assertFilterHidesNothing()

    def testThatFilterContainsTaskIfTaskHasParentAndChildCategoryAndAllCategoriesAreFiltered(
        self,
    ):
        self.setFilterOnAllCategories()
        self.link(self.parentCategory, self.task)
        self.link(self.childCategory, self.task)
        self.parentCategory.setFiltered()
        self.childCategory.setFiltered()
        self.assertFilterHidesNothing()


class ParentAndChildCategoryAndTaskInListModeTest(
    ParentAndChildCategoryAndOneTaskFixture, test.TestCase
):
    treeMode = False


class ParentAndChildCategoryAndTaskInTreeModeTest(
    ParentAndChildCategoryAndOneTaskFixture, test.TestCase
):
    treeMode = True


class CategoryFilterAndViewFilterFixtureAndCommonTestsMixin(
    CategoryFilterHelpersMixin
):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.parent = task.Task("parent task")
        self.parent.setShouldMarkCompletedWhenAllChildrenCompleted(False)
        self.child = task.Task("child task")
        self.child.setCompletionDateTime()
        self.childCategory = category.Category("child category")
        self.childCategory.addCategorizable(self.child)
        self.parent.addChild(self.child)
        self.tasks = task.TaskList([self.parent, self.child])
        self.categories = category.CategoryList([self.childCategory])
        self.viewFilter = task.filter.ViewFilter(
            self.tasks, treeMode=self.treeMode
        )
        self.categoryFilter = category.filter.CategoryFilter(
            self.viewFilter, categories=self.categories, treeMode=self.treeMode
        )

    def testThatParentIsHiddenWhenHiddenCompletedChildIsFiltered(self):
        self.viewFilter.hideTaskStatus(task.status.completed)
        self.assertEqual(1, len(self.viewFilter))
        self.childCategory.setFiltered(True)
        self.assertEqual(0, len(self.categoryFilter))

    def testThatParentIsShownWhenHiddenCompletedChildIsUnfiltered(self):
        self.viewFilter.hideTaskStatus(task.status.completed)
        self.childCategory.setFiltered(True)
        self.assertEqual(0, len(self.categoryFilter))
        self.childCategory.setFiltered(False)
        self.assertEqual(1, len(self.categoryFilter))

    def testThatParentIsHiddenWhenFilteredCompletedChildIsHidden(self):
        self.childCategory.setFiltered(True)
        self.assertEqual(2, len(self.viewFilter))
        self.viewFilter.hideTaskStatus(task.status.completed)
        self.assertEqual(0, len(self.categoryFilter))

    def testThatParentIsShownWhenFilteredCompletedChildIsUnhidden(self):
        self.childCategory.setFiltered(True)
        self.viewFilter.hideTaskStatus(task.status.completed)
        self.assertEqual(0, len(self.categoryFilter))
        self.viewFilter.hideTaskStatus(task.status.completed, False)
        self.assertEqual(2 if self.treeMode else 1, len(self.categoryFilter))


class CategoryFilterAndViewFilterInListModeTest(
    CategoryFilterAndViewFilterFixtureAndCommonTestsMixin, test.TestCase
):
    treeMode = False


class CategoryFilterAndViewFilterInTreeModeTest(
    CategoryFilterAndViewFilterFixtureAndCommonTestsMixin, test.TestCase
):
    treeMode = True


class ViewFilterWrappingCategoryFilterFixture(CategoryFilterHelpersMixin):
    """Test the filter order used in the actual application:
    TaskList -> CategoryFilter -> ViewFilter

    This is the opposite order of CategoryFilterAndViewFilterFixture.
    The bug occurs when:
    1. Parent task has no category
    2. Child task has category A and is completed
    3. Category A filter is active
    4. Completed tasks are hidden

    Without the fix, the parent would still show because:
    - CategoryFilter adds parent as ancestor of categorized child
    - ViewFilter removes child (completed) but parent passes (not completed)

    With the fix, ViewFilter's recursive cleanup removes orphan ancestors.
    """
    treeMode = True

    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        # Parent task with no category
        self.parent = task.Task("parent task")
        self.parent.setShouldMarkCompletedWhenAllChildrenCompleted(False)
        # Child task with category, completed
        self.child = task.Task("child task")
        self.child.setCompletionDateTime()
        self.childCategory = category.Category("child category")
        self.childCategory.addCategorizable(self.child)
        self.parent.addChild(self.child)
        self.tasks = task.TaskList([self.parent, self.child])
        self.categories = category.CategoryList([self.childCategory])
        # Filter order: TaskList -> CategoryFilter -> ViewFilter (like the app)
        self.categoryFilter = category.filter.CategoryFilter(
            self.tasks, categories=self.categories, treeMode=self.treeMode
        )
        self.viewFilter = task.filter.ViewFilter(
            self.categoryFilter, treeMode=self.treeMode
        )

    def testParentHiddenWhenCategoryFilteredAndChildCompleted(self):
        """The main bug scenario: parent should be hidden when its only
        categorized child is hidden due to completion status."""
        # First, filter by category
        self.childCategory.setFiltered(True)
        # At this point, categoryFilter should have parent (as ancestor) and child
        self.assertEqual(2, len(self.categoryFilter))
        # viewFilter should also show both
        self.assertEqual(2, len(self.viewFilter))
        # Now hide completed tasks
        self.viewFilter.hideTaskStatus(task.status.completed)
        # viewFilter should now be empty - parent has no visible categorized children
        self.assertEqual(0, len(self.viewFilter))

    def testParentShownWhenChildUnhidden(self):
        """When we unhide completed tasks, parent should reappear."""
        self.childCategory.setFiltered(True)
        self.viewFilter.hideTaskStatus(task.status.completed)
        self.assertEqual(0, len(self.viewFilter))
        # Unhide completed tasks
        self.viewFilter.hideTaskStatus(task.status.completed, False)
        # Both should be visible again
        self.assertEqual(2, len(self.viewFilter))

    def testParentShownWhenCategoryUnfiltered(self):
        """When we remove category filter, parent should reappear."""
        self.childCategory.setFiltered(True)
        self.viewFilter.hideTaskStatus(task.status.completed)
        self.assertEqual(0, len(self.viewFilter))
        # Remove category filter
        self.childCategory.setFiltered(False)
        # Explicitly reset viewFilter (in the app, UI refresh triggers this)
        # This is needed because categoryFilter items don't change when
        # removing the filter, so no events fire to trigger viewFilter reset
        self.viewFilter.reset()
        # Parent should be visible (no category filter active)
        self.assertEqual(1, len(self.viewFilter))


class ViewFilterWrappingCategoryFilterInTreeModeTest(
    ViewFilterWrappingCategoryFilterFixture, test.TestCase
):
    treeMode = True


class ViewFilterWrappingCategoryFilterInListModeTest(
    ViewFilterWrappingCategoryFilterFixture, test.TestCase
):
    treeMode = False

    def testParentHiddenWhenCategoryFilteredAndChildCompleted(self):
        """In list mode, parent is not shown as ancestor, so behavior differs."""
        self.childCategory.setFiltered(True)
        # In list mode, only child is shown (no ancestors)
        self.assertEqual(1, len(self.categoryFilter))
        self.assertEqual(1, len(self.viewFilter))
        # Hide completed tasks
        self.viewFilter.hideTaskStatus(task.status.completed)
        # Should be empty
        self.assertEqual(0, len(self.viewFilter))

    def testParentShownWhenChildUnhidden(self):
        """In list mode, only child is shown when unhidden."""
        self.childCategory.setFiltered(True)
        self.viewFilter.hideTaskStatus(task.status.completed)
        self.assertEqual(0, len(self.viewFilter))
        self.viewFilter.hideTaskStatus(task.status.completed, False)
        # Only child visible in list mode
        self.assertEqual(1, len(self.viewFilter))
