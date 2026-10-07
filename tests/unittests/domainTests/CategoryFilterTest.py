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
from taskcoachlib.domain import task, category
from taskcoachlib.config import settings

# pylint: disable=W0201,E1101

""" The tests below test the category filter. Different fixtures are defined
    for different combinations of tasks and categories. Each fixture is than
    subclassed by a <Fixture>InListMode and a <Fixture>InTreeMode class since 
    we want to run the tests in both list and tree mode. """  # pylint: disable=W0105


class CategoryFilterHelpersMixin(object):
    def setFilterOnAnyCategory(self):
        settings.set("view", "categoryfiltermatchall", False)

    def setFilterOnAllCategories(self):
        settings.set("view", "categoryfiltermatchall", True)

    def link(self, category, categorizable):  # pylint: disable=W0621
        categorizable.addCategory(category)

    def assertChildTaskIsFiltered(self):
        self.assertEqual(
            set(
                [self.childTask, self.parentTask]
                if self.tree_mode
                else [self.childTask]
            ),
            set(self.filter),
        )

    def assertFilterHidesNothing(self):
        self.assertEqual(set(self.tasks), set(self.filter))

    def assertFilterHidesEverything(self):
        self.assertFalse(self.filter)


class Fixture(CategoryFilterHelpersMixin):
    tree_mode = False

    def setUp(self):
        self.categories = category.CategoryList(self.createCategories())
        self.tasks = task.TaskList(self.createTasks())
        self.categorize()
        self.filter = category.filter.CategoryFilter(
            self.tasks,
            categories=self.categories,
            tree_mode=self.tree_mode,
        )

    def createTasks(self):
        return []

    def createCategories(self):
        return []  # pragma: no cover

    def categorize(self):
        pass

    # Common tests that should pass for all fixtures

    def test_filter_contains_all_items_when_not_filtering(self):
        self.assertEqual(self.filter.original_length(), len(self.filter))

    def test_filter_original_length_equals_task_count_when_not_filtering(
        self,
    ):
        self.assertEqual(self.filter.original_length(), len(self.tasks))

    def test_filter_contains_no_items_when_removing_original_items(self):
        self.tasks.clear()
        self.assertEqual(0, self.filter.original_length())

    def test_filter_length_is_smaller_or_equal_than_original_length(self):
        self.assertTrue(len(self.filter) <= self.filter.original_length())

    def test_filter_is_empty_when_filtering_on_category_without_categorizables(
        self,
    ):
        empty_category = category.Category("empty")
        self.categories.append(empty_category)
        empty_category.setFiltered()
        self.assertFalse(self.filter)

    def test_filter_contains_all_items_after_removing_filtered_empty_category(
        self,
    ):
        empty_category = category.Category("empty")
        self.categories.append(empty_category)
        empty_category.setFiltered()
        self.categories.remove(empty_category)
        self.assertFilterHidesNothing()

    def test_filter_contains_all_items_after_filtering_and_unfiltering(
        self,
    ):
        a_category = list(self.categories)[0]
        a_category.setFiltered()
        a_category.setFiltered(False)
        self.assertFilterHidesNothing()

    def test_filter_contains_all_after_unfiltering_an_unfiltered_category(
        self,
    ):
        a_category = list(self.categories)[0]
        a_category.setFiltered(False)
        self.assertFilterHidesNothing()

    def test_filter_contains_all_matching_any_with_no_category_filtered(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.assertFilterHidesNothing()

    def test_filter_contains_all_matching_all_with_no_category_filtered(
        self,
    ):
        self.setFilterOnAllCategories()
        self.assertFilterHidesNothing()

    def test_filter_contains_new_task_of_filtered_category(
        self,
    ):
        a_category = list(self.categories)[0]
        a_category.setFiltered()
        new_task = task.Task()
        new_task.addCategory(a_category)
        self.tasks.append(new_task)
        self.assertTrue(new_task in self.filter)

    def test_filter_contains_new_task_of_filtered_category_after_removal(
        self,
    ):
        a_category = list(self.categories)[0]
        a_category.setFiltered()
        new_task = task.Task()
        new_task.addCategory(a_category)
        self.tasks.append(new_task)
        self.tasks.remove(new_task)
        self.assertFalse(new_task in self.filter)

    def test_filter_has_no_tasks_with_all_categories_and_an_empty_one(
        self,
    ):
        empty_category = category.Category("empty")
        self.categories.append(empty_category)
        for each_category in self.categories:
            each_category.setFiltered()
        self.setFilterOnAllCategories()
        self.assertFilterHidesEverything()


class OneCategoryFixture(Fixture):
    def createCategories(self):
        self.category = category.Category("category")
        return [self.category]

    def test_filter_is_empty_when_no_categories_are_filtered(self):
        self.assertEqual(0, len(self.filter))

    def test_filter_is_empty_when_category_is_filtered(self):
        self.category.setFiltered()
        self.assertEqual(0, len(self.filter))


class OneCategoryFilterInListModeTest(OneCategoryFixture, test.TestCase):
    tree_mode = False


class OneCategoryFilterInTreeModeTest(OneCategoryFixture, test.TestCase):
    tree_mode = True


class OneCategoryAndOneTaskFixture(Fixture):
    def createCategories(self):
        self.category = category.Category("category")
        return [self.category]

    def createTasks(self):
        self.task = task.Task("task")
        return [self.task]

    def test_filter_contains_uncategorized_task_when_none_filtered(
        self,
    ):
        self.assertFilterHidesNothing()

    def test_filter_hides_uncategorized_task_when_category_filtered(
        self,
    ):
        self.category.setFiltered()
        self.assertFilterHidesEverything()

    def test_filter_contains_categorized_task_when_category_is_filtered(
        self,
    ):
        self.link(self.category, self.task)
        self.category.setFiltered()
        self.assertFilterHidesNothing()


class OneCategoryAndOneTaskInListModeTest(
    OneCategoryAndOneTaskFixture, test.TestCase
):
    tree_mode = False


class OneCategoryAndOneTaskInTreeModeTest(
    OneCategoryAndOneTaskFixture, test.TestCase
):
    tree_mode = True


class OneCategoryAndTwoTasksFixture(Fixture):
    def createCategories(self):
        self.category = category.Category("category")
        return [self.category]

    def createTasks(self):
        self.task1 = task.Task("task1")
        self.task2 = task.Task("task2")
        return [self.task1, self.task2]

    def test_filter_contains_uncategorized_tasks_when_not_filtered(
        self,
    ):
        self.assertFilterHidesNothing()

    def test_filter_contains_no_uncategorized_tasks_when_category_is_filtered(
        self,
    ):
        self.category.setFiltered()
        self.assertFilterHidesEverything()

    def test_filter_contains_categorized_task_when_category_is_filtered(
        self,
    ):
        self.category.setFiltered()
        self.link(self.category, self.task1)
        self.assertEqual([self.task1], list(self.filter))

    def test_filter_contains_categorized_tasks_when_category_is_filtered(
        self,
    ):
        self.category.setFiltered()
        self.link(self.category, self.task1)
        self.link(self.category, self.task2)
        self.assertFilterHidesNothing()

    def count_resets(self):
        resets = []
        reset = self.filter.reset
        self.filter.reset = lambda *args, **kwargs: (
            resets.append(1),
            reset(*args, **kwargs),
        )
        return resets

    def test_assigning_an_unfiltered_category_refilters_nothing(self):
        resets = self.count_resets()
        self.link(self.category, self.task1)
        self.assertEqual([], resets)

    def test_assigning_a_subcategory_of_a_filtered_one_refilters(self):
        subcategory = category.Category("subcategory")
        self.category.addChild(subcategory)
        self.category.setFiltered()
        resets = self.count_resets()
        self.link(subcategory, self.task1)
        self.assertEqual(
            (True, [self.task1]), (bool(resets), list(self.filter))
        )


class OneCategoryAndTwoTasksInListModeTest(
    OneCategoryAndTwoTasksFixture, test.TestCase
):
    tree_mode = False


class OneCategoryAndTwoTasksInTreeModeTest(
    OneCategoryAndTwoTasksFixture, test.TestCase
):
    tree_mode = True


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

    def test_filter_contains_task_matching_any_with_both_filtered(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesNothing()

    def test_filter_hides_task_matching_all_with_both_filtered(
        self,
    ):
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesEverything()


class TwoCategoriesAndOneTaskInListModeTest(
    TwoCategoriesAndOneTaskFixture, test.TestCase
):
    tree_mode = False


class TwoCategoriesAndOneTaskInTreeModeTest(
    TwoCategoriesAndOneTaskFixture, test.TestCase
):
    tree_mode = True


class TwoCategoriesAndTwoTasksFixture(Fixture):
    def createCategories(self):
        self.category1 = category.Category("category1")
        self.category2 = category.Category("category2")
        return [self.category1, self.category2]

    def createTasks(self):
        self.task1 = task.Task("task1")
        self.task2 = task.Task("task2")
        return [self.task1, self.task2]

    def test_filter_contains_uncategorized_tasks_when_not_filtered(
        self,
    ):
        self.assertFilterHidesNothing()

    def test_filter_contains_no_uncategorized_tasks_when_category_is_filtered(
        self,
    ):
        self.category1.setFiltered()
        self.assertFilterHidesEverything()

    def test_filter_contains_no_uncategorized_tasks_when_any_filtered(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesEverything()

    def test_filter_contains_no_uncategorized_tasks_when_all_filtered(
        self,
    ):
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesEverything()

    def test_filter_contains_categorized_task_when_any_category_is_filtered(
        self,
    ):
        self.link(self.category1, self.task1)
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertEqual([self.task1], list(self.filter))

    def test_filter_hides_categorized_task_when_all_categories_filtered(
        self,
    ):
        self.link(self.category1, self.task1)
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesEverything()

    def test_filter_contains_categorized_task_when_filtering_by_that_category(
        self,
    ):
        self.link(self.category1, self.task1)
        self.category1.setFiltered()
        self.assertEqual([self.task1], list(self.filter))

    def test_filter_hides_categorized_task_filtering_by_another_category(
        self,
    ):
        self.link(self.category1, self.task1)
        self.category2.setFiltered()
        self.assertFilterHidesEverything()

    def test_filter_contains_categorized_tasks_when_filtering_by_that_category(
        self,
    ):
        self.category1.setFiltered()
        self.link(self.category1, self.task1)
        self.link(self.category1, self.task2)
        self.assertFilterHidesNothing()

    def test_filter_contains_categorized_tasks_when_filtering_by_any_category(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.link(self.category1, self.task1)
        self.link(self.category1, self.task2)
        self.assertFilterHidesNothing()

    def test_filter_hides_categorized_tasks_filtering_by_all_categories(
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
    tree_mode = False


class TwoCategoriesAndTwoTasksInTreeModeTest(
    TwoCategoriesAndTwoTasksFixture, test.TestCase
):
    tree_mode = True


class OneCategoryAndParentAndChildTaskFixture(Fixture):
    def createCategories(self):
        self.category = category.Category("category")
        return [self.category]

    def createTasks(self):
        self.parentTask = task.Task("parent")
        self.childTask = task.Task("child")
        self.parentTask.addChild(self.childTask)
        self.childTask.set_parent(self.parentTask)
        return [self.parentTask, self.childTask]

    def test_filter_contains_child_when_parent_is_categorized_and_filtered(
        self,
    ):
        self.link(self.category, self.parentTask)
        self.category.setFiltered()
        self.assertFilterHidesNothing()

    def test_filter_contains_parent_of_filtered_child_only_in_tree_mode(
        self,
    ):
        self.link(self.category, self.childTask)
        self.category.setFiltered()
        self.assertEqual(2 if self.tree_mode else 1, len(self.filter))


class OneCategoryAndParentAndChildTaskInListModeTest(
    OneCategoryAndParentAndChildTaskFixture, test.TestCase
):
    tree_mode = False


class OneCategoryAndParentAndChildTaskInTreeModeTest(
    OneCategoryAndParentAndChildTaskFixture, test.TestCase
):
    tree_mode = True


class TwoCategoriesAndParentAndChildTaskFixture(Fixture):
    def createCategories(self):
        self.category1 = category.Category("category1")
        self.category2 = category.Category("category2")
        return [self.category1, self.category2]

    def createTasks(self):
        self.parentTask = task.Task("parent")
        self.childTask = task.Task("child")
        self.parentTask.addChild(self.childTask)
        self.childTask.set_parent(self.parentTask)
        return [self.parentTask, self.childTask]

    def categorize(self):
        self.link(self.category1, self.parentTask)
        self.link(self.category2, self.childTask)

    def test_filter_contains_parent_and_child_matching_any_of_both(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesNothing()

    def test_filter_contains_parent_and_child_matching_all_of_both(
        self,
    ):
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertChildTaskIsFiltered()


class TwoCategoriesAndParentAndChildTaskInListModeTest(
    TwoCategoriesAndParentAndChildTaskFixture, test.TestCase
):
    tree_mode = False


class TwoCategoriesAndParentAndChildTaskInTreeModeTest(
    TwoCategoriesAndParentAndChildTaskFixture, test.TestCase
):
    tree_mode = True


class ParentAndChildCategoryAndParentAndChildTaskFixture(Fixture):
    def createCategories(self):
        self.parentCategory = category.Category("parent")
        self.childCategory = category.Category("child")
        self.parentCategory.addChild(self.childCategory)
        self.childCategory.set_parent(self.parentCategory)
        return [self.parentCategory, self.childCategory]

    def createTasks(self):
        self.parentTask = task.Task("parent")
        self.childTask = task.Task("child")
        self.parentTask.addChild(self.childTask)
        self.childTask.set_parent(self.parentTask)
        return [self.parentTask, self.childTask]

    def test_filter_parent_task_in_parent_category_parent_filtered_shows_both(
        self,
    ):
        self.link(self.parentCategory, self.parentTask)
        self.parentCategory.setFiltered()
        self.assertFilterHidesNothing()

    def test_filter_parent_task_in_parent_category_child_filtered_shows_none(
        self,
    ):
        self.link(self.parentCategory, self.parentTask)
        self.childCategory.setFiltered()
        self.assertFilterHidesEverything()

    def test_filter_parent_task_in_child_category_parent_filtered_shows_both(
        self,
    ):
        self.link(self.childCategory, self.parentTask)
        self.parentCategory.setFiltered()
        self.assertFilterHidesNothing()

    def test_filter_parent_task_in_child_category_child_filtered_shows_both(
        self,
    ):
        self.link(self.childCategory, self.parentTask)
        self.childCategory.setFiltered()
        self.assertFilterHidesNothing()

    def test_filter_child_task_in_parent_category_parent_filtered_shows_child(
        self,
    ):
        self.link(self.parentCategory, self.childTask)
        self.parentCategory.setFiltered()
        self.assertChildTaskIsFiltered()

    def test_filter_child_task_in_parent_category_child_filtered_shows_none(
        self,
    ):
        self.link(self.parentCategory, self.childTask)
        self.childCategory.setFiltered()
        self.assertFilterHidesEverything()

    def test_filter_child_task_in_child_category_parent_filtered_shows_child(
        self,
    ):
        self.link(self.childCategory, self.childTask)
        self.parentCategory.setFiltered()
        self.assertChildTaskIsFiltered()

    def test_filter_child_task_in_child_category_child_filtered_shows_child(
        self,
    ):
        self.link(self.childCategory, self.childTask)
        self.childCategory.setFiltered()
        self.assertChildTaskIsFiltered()

    def test_filter_parent_task_in_child_category_both_filtered_shows_both(
        self,
    ):
        self.setFilterOnAllCategories()
        self.link(self.childCategory, self.parentTask)
        self.parentCategory.setFiltered()
        self.childCategory.setFiltered()
        self.assertFilterHidesNothing()

    def test_filter_child_task_in_child_category_both_filtered_shows_child(
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
    tree_mode = False


class ParentAndChildCategoryAndParentAndChildTaskInTreeModeTest(
    ParentAndChildCategoryAndParentAndChildTaskFixture, test.TestCase
):
    tree_mode = True


class ParentAndChildCategoryAndParentAndGrandChildTaskFixture(Fixture):
    def createCategories(self):
        self.parentCategory = category.Category("parent")
        self.childCategory = category.Category("child")
        self.parentCategory.addChild(self.childCategory)
        self.childCategory.set_parent(self.parentCategory)
        return [self.parentCategory, self.childCategory]

    def createTasks(self):
        self.parentTask = task.Task("parent")
        self.childTask = task.Task("child")
        self.grandChildTask = task.Task("grandchild")
        self.parentTask.addChild(self.childTask)
        self.childTask.set_parent(self.parentTask)
        self.childTask.addChild(self.grandChildTask)
        self.grandChildTask.set_parent(self.childTask)
        return [self.parentTask, self.childTask, self.grandChildTask]

    def test_filter_parent_task_in_filtered_child_category_shows_all(
        self,
    ):
        self.link(self.childCategory, self.parentTask)
        self.parentCategory.setFiltered()
        self.assertFilterHidesNothing()

    def test_filter_parent_task_in_child_category_all_filtered_shows_all(
        self,
    ):
        self.setFilterOnAllCategories()
        self.link(self.childCategory, self.parentTask)
        self.parentCategory.setFiltered()
        self.childCategory.setFiltered()
        self.assertFilterHidesNothing()

    def test_filter_child_in_child_category_parent_filtered_shows_grandchild(
        self,
    ):
        self.link(self.childCategory, self.childTask)
        self.parentCategory.setFiltered()
        self.assertTrue(self.grandChildTask in self.filter)

    def test_filter_child_in_child_category_all_filtered_shows_grandchild(
        self,
    ):
        self.setFilterOnAllCategories()
        self.link(self.childCategory, self.childTask)
        self.parentCategory.setFiltered()
        self.childCategory.setFiltered()
        self.assertTrue(self.grandChildTask in self.filter)

    def test_parent_filter_shows_grandparent_of_grandchild_in_child_category(
        self,
    ):
        self.link(self.childCategory, self.grandChildTask)
        self.parentCategory.setFiltered()
        self.assertEqual(
            set(self.tasks) if self.tree_mode else set([self.grandChildTask]),
            set(self.filter),
        )


class ParentAndChildCategoryAndParentAndGrandChildTaskInListModeTest(
    ParentAndChildCategoryAndParentAndGrandChildTaskFixture, test.TestCase
):
    tree_mode = False


class ParentAndChildCategoryAndParentAndGrandChildTaskInTreeModeTest(
    ParentAndChildCategoryAndParentAndGrandChildTaskFixture, test.TestCase
):
    tree_mode = True


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
        self.childTask.set_parent(self.parentTask)
        self.childTask.addChild(self.grandChildTask)
        self.grandChildTask.set_parent(self.childTask)
        return [self.parentTask, self.childTask, self.grandChildTask]

    def categorize(self):
        self.link(self.category1, self.parentTask)
        self.link(self.category2, self.grandChildTask)

    def test_filter_contains_grand_child_when_filtering_on_all_categories(
        self,
    ):
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertEqual(
            set(self.tasks) if self.tree_mode else set([self.grandChildTask]),
            set(self.filter),
        )

    def test_filter_contains_grand_child_when_filtering_on_any_category(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesNothing()


class TwoCategoriesAndParentAndGrandChildTaskInListModeTest(
    TwoCategoriesAndParentAndGrandChildTaskFixture, test.TestCase
):
    tree_mode = False


class TwoCategoriesAndParentAndGrandChildTaskInTreeModeTest(
    TwoCategoriesAndParentAndGrandChildTaskFixture, test.TestCase
):
    tree_mode = True


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
        self.child1Task.set_parent(self.parentTask)
        self.child2Task.set_parent(self.parentTask)
        return [self.parentTask, self.child1Task, self.child2Task]

    def categorize(self):
        self.link(self.category1, self.child1Task)
        self.link(self.category2, self.child2Task)

    def test_filter_all_shows_none_with_children_in_different_categories(
        self,
    ):
        self.setFilterOnAllCategories()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertFilterHidesEverything()

    def test_filter_any_shows_all_with_children_in_different_categories(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.category1.setFiltered()
        self.category2.setFiltered()
        self.assertEqual(3 if self.tree_mode else 2, len(self.filter))

    def test_filter_hides_unfiltered_child(self):
        self.category1.setFiltered()
        self.assertFalse(self.child2Task in self.filter)


class TwoCategoriesAndParentWithTwoChildTasksInListModeTest(
    TwoCategoriesAndParentWithTwoChildTasksFixture, test.TestCase
):
    tree_mode = False


class TwoCategoriesAndParentWithTwoChildTasksInTreeModeTest(
    TwoCategoriesAndParentWithTwoChildTasksFixture, test.TestCase
):
    tree_mode = True


class ParentAndChildCategoryAndOneTaskFixture(Fixture):
    def createCategories(self):
        self.parentCategory = category.Category("parent")
        self.childCategory = category.Category("child")
        self.parentCategory.addChild(self.childCategory)
        self.childCategory.set_parent(self.parentCategory)
        return [self.parentCategory, self.childCategory]

    def createTasks(self):
        self.task = task.Task("task")
        return [self.task]

    def test_filter_hides_task_with_child_category_when_parent_filtered(
        self,
    ):
        self.link(self.parentCategory, self.task)
        self.childCategory.setFiltered()
        self.assertFalse(self.filter)

    def test_filter_shows_task_with_parent_category_when_child_filtered(
        self,
    ):
        self.link(self.childCategory, self.task)
        self.parentCategory.setFiltered()
        self.assertFilterHidesNothing()

    def test_filter_shows_task_with_both_categories_when_any_filtered(
        self,
    ):
        self.setFilterOnAnyCategory()
        self.link(self.parentCategory, self.task)
        self.link(self.childCategory, self.task)
        self.parentCategory.setFiltered()
        self.childCategory.setFiltered()
        self.assertFilterHidesNothing()

    def test_filter_shows_task_with_both_categories_when_all_filtered(
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
    tree_mode = False


class ParentAndChildCategoryAndTaskInTreeModeTest(
    ParentAndChildCategoryAndOneTaskFixture, test.TestCase
):
    tree_mode = True


class CategoryFilterAndViewFilterFixtureAndCommonTestsMixin(
    CategoryFilterHelpersMixin
):
    def setUp(self):
        self.parent = task.Task("parent task")
        self.parent.set_should_mark_completed_when_all_children_completed(
            False
        )
        self.child = task.Task("child task")
        self.child.set_completion_date_time()
        self.childCategory = category.Category("child category")
        self.child.addCategory(self.childCategory)
        self.parent.addChild(self.child)
        self.tasks = task.TaskList([self.parent, self.child])
        self.categories = category.CategoryList([self.childCategory])
        self.viewFilter = task.filter.ViewFilter(
            self.tasks, tree_mode=self.tree_mode
        )
        self.categoryFilter = category.filter.CategoryFilter(
            self.viewFilter,
            categories=self.categories,
            tree_mode=self.tree_mode,
        )

    def test_that_parent_is_hidden_when_hidden_completed_child_is_filtered(
        self,
    ):
        self.viewFilter.hide_task_status(task.status.completed)
        self.assertEqual(1, len(self.viewFilter))
        self.childCategory.setFiltered(True)
        self.assertEqual(0, len(self.categoryFilter))

    def test_that_parent_is_shown_when_hidden_completed_child_is_unfiltered(
        self,
    ):
        self.viewFilter.hide_task_status(task.status.completed)
        self.childCategory.setFiltered(True)
        self.assertEqual(0, len(self.categoryFilter))
        self.childCategory.setFiltered(False)
        self.assertEqual(1, len(self.categoryFilter))

    def test_that_parent_is_hidden_when_filtered_completed_child_is_hidden(
        self,
    ):
        self.childCategory.setFiltered(True)
        self.assertEqual(2, len(self.viewFilter))
        self.viewFilter.hide_task_status(task.status.completed)
        self.assertEqual(0, len(self.categoryFilter))

    def test_that_parent_is_shown_when_filtered_completed_child_is_unhidden(
        self,
    ):
        self.childCategory.setFiltered(True)
        self.viewFilter.hide_task_status(task.status.completed)
        self.assertEqual(0, len(self.categoryFilter))
        self.viewFilter.hide_task_status(task.status.completed, False)
        self.assertEqual(2 if self.tree_mode else 1, len(self.categoryFilter))


class CategoryFilterAndViewFilterInListModeTest(
    CategoryFilterAndViewFilterFixtureAndCommonTestsMixin, test.TestCase
):
    tree_mode = False


class CategoryFilterAndViewFilterInTreeModeTest(
    CategoryFilterAndViewFilterFixtureAndCommonTestsMixin, test.TestCase
):
    tree_mode = True


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

    tree_mode = True

    def setUp(self):
        # Parent task with no category
        self.parent = task.Task("parent task")
        self.parent.set_should_mark_completed_when_all_children_completed(
            False
        )
        # Child task with category, completed
        self.child = task.Task("child task")
        self.child.set_completion_date_time()
        self.childCategory = category.Category("child category")
        self.child.addCategory(self.childCategory)
        self.parent.addChild(self.child)
        self.tasks = task.TaskList([self.parent, self.child])
        self.categories = category.CategoryList([self.childCategory])
        # Filter order: TaskList -> CategoryFilter -> ViewFilter (like the app)
        self.categoryFilter = category.filter.CategoryFilter(
            self.tasks,
            categories=self.categories,
            tree_mode=self.tree_mode,
        )
        self.viewFilter = task.filter.ViewFilter(
            self.categoryFilter, tree_mode=self.tree_mode
        )

    def test_parent_hidden_when_category_filtered_and_child_completed(self):
        """The main bug scenario: parent should be hidden when its only
        categorized child is hidden due to completion status."""
        # First, filter by category
        self.childCategory.setFiltered(True)
        # At this point, categoryFilter should have parent (as ancestor) and child
        self.assertEqual(2, len(self.categoryFilter))
        # viewFilter should also show both
        self.assertEqual(2, len(self.viewFilter))
        # Now hide completed tasks
        self.viewFilter.hide_task_status(task.status.completed)
        # viewFilter should now be empty - parent has no visible categorized children
        self.assertEqual(0, len(self.viewFilter))

    def test_parent_shown_when_child_unhidden(self):
        """When we unhide completed tasks, parent should reappear."""
        self.childCategory.setFiltered(True)
        self.viewFilter.hide_task_status(task.status.completed)
        self.assertEqual(0, len(self.viewFilter))
        # Unhide completed tasks
        self.viewFilter.hide_task_status(task.status.completed, False)
        # Both should be visible again
        self.assertEqual(2, len(self.viewFilter))

    def test_parent_shown_when_category_unfiltered(self):
        """When we remove category filter, parent should reappear."""
        self.childCategory.setFiltered(True)
        self.viewFilter.hide_task_status(task.status.completed)
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
    tree_mode = True


class ViewFilterWrappingCategoryFilterInListModeTest(
    ViewFilterWrappingCategoryFilterFixture, test.TestCase
):
    tree_mode = False

    def test_parent_hidden_when_category_filtered_and_child_completed(self):
        """In list mode, parent is not shown as ancestor, so behavior differs."""
        self.childCategory.setFiltered(True)
        # In list mode, only child is shown (no ancestors)
        self.assertEqual(1, len(self.categoryFilter))
        self.assertEqual(1, len(self.viewFilter))
        # Hide completed tasks
        self.viewFilter.hide_task_status(task.status.completed)
        # Should be empty
        self.assertEqual(0, len(self.viewFilter))

    def test_parent_shown_when_child_unhidden(self):
        """In list mode, only child is shown when unhidden."""
        self.childCategory.setFiltered(True)
        self.viewFilter.hide_task_status(task.status.completed)
        self.assertEqual(0, len(self.viewFilter))
        self.viewFilter.hide_task_status(task.status.completed, False)
        # Only child visible in list mode
        self.assertEqual(1, len(self.viewFilter))
