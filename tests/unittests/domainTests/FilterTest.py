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

import test, weakref
from taskcoachlib import patterns, config
from taskcoachlib.domain import task, base


class TestFilter(base.Filter):
    def filter_items(self, items):
        return [item for item in items if item > "b"]


class FilterTestsMixin(object):
    def setUp(self):
        self.observable = self.collectionClass(["a", "b", "c", "d"])
        self.filter = TestFilter(self.observable)

    def test_length(self):
        self.assertEqual(2, len(self.filter))

    def test_contents(self):
        self.assertTrue("c" in self.filter and "d" in self.filter)

    def test_remove_item(self):
        self.filter.remove("c")
        self.assertEqual(1, len(self.filter))
        self.assertTrue("d" in self.filter)
        self.assertEqual(["a", "b", "d"], self.observable)

    def test_notification(self):
        self.observable.append("e")
        self.assertEqual(3, len(self.filter))
        self.assertTrue("e" in self.filter)


class FilterListTest(FilterTestsMixin, test.TestCase):
    collectionClass = patterns.ObservableList


class FilterSetTest(FilterTestsMixin, test.TestCase):
    collectionClass = patterns.ObservableSet


class DummyFilter(base.Filter):
    def filter_items(self, items):
        return items

    def test(self):
        self.testcalled = 1  # pylint: disable=W0201


class DummyItem(str):
    def ancestors(self):
        return []


class StackedFilterTest(test.TestCase):
    def setUp(self):
        self.list = patterns.ObservableList(
            [DummyItem("a"), DummyItem("b"), DummyItem("c"), DummyItem("d")]
        )
        self.filter1 = DummyFilter(self.list)
        self.filter2 = TestFilter(self.filter1)

    def test_delegation(self):
        self.filter2.test()
        self.assertEqual(1, self.filter1.testcalled)

    def test_set_tree_mode_true(self):
        self.filter2.set_tree_mode(True)
        self.assertTrue(self.filter1.tree_mode())

    def test_set_tree_mode_false(self):
        self.filter2.set_tree_mode(False)
        self.assertFalse(self.filter1.tree_mode())

    def test_filters_are_collected(self):
        filter_ref = weakref.ref(self.filter1)
        self.filter2.detach()
        del self.filter1
        del self.filter2
        self.assertTrue(filter_ref() is None)


class SearchFilterTest(test.TestCase):
    def setUp(self):
        self.parent = task.Task(
            subject="*ABC$D", description="Parent description"
        )
        self.child = task.Task(subject="DEF", description="Child description")
        self.parent.addChild(self.child)
        self.list = task.TaskList([self.parent, self.child])
        self.filter = base.SearchFilter(self.list)

    def setSearchString(
        self,
        searchString,
        matchCase=False,
        includeSubItems=False,
        searchDescription=False,
        regularExpression=True,
    ):
        self.filter.setSearchFilter(
            searchString,
            matchCase=matchCase,
            includeSubItems=includeSubItems,
            searchDescription=searchDescription,
            regularExpression=regularExpression,
        )

    def test_no_match(self):
        self.setSearchString("XYZ")
        self.assertEqual(0, len(self.filter))

    def test_match(self):
        self.setSearchString("AB")
        self.assertEqual(1, len(self.filter))

    def test_match_is_case_in_sensitive_by_default(self):
        self.setSearchString("abc")
        self.assertEqual(1, len(self.filter))

    def test_match_case_insensitive(self):
        self.setSearchString("abc", True)
        self.assertEqual(0, len(self.filter))

    def test_match_with_re(self):
        self.setSearchString("a.c")
        self.assertEqual(1, len(self.filter))

    def test_match_without_re(self):
        self.setSearchString("$D", regularExpression=False)
        self.assertEqual(1, len(self.filter))

    def test_match_with_empty_string(self):
        self.setSearchString("")
        self.assertEqual(2, len(self.filter))

    def test_match_child_does_not_select_parent_when_not_in_tree_mode(self):
        self.setSearchString("DEF")
        self.assertEqual(1, len(self.filter))

    def test_match_child_also_selects_parent_when_in_tree_mode(self):
        self.filter.set_tree_mode(True)
        self.setSearchString("DEF")
        self.assertEqual(2, len(self.filter))

    def test_match_child_does_not_select_parent_when_child_not_in_list(self):
        self.list.remove(self.child)
        self.parent.addChild(
            self.child
        )  # simulate a child that has been filtered
        self.setSearchString("DEF")
        self.assertEqual(0, len(self.filter))

    def test_add_task(self):
        self.setSearchString("XYZ")
        task_xyz = task.Task(subject="subject with XYZ")
        self.list.append(task_xyz)
        self.assertEqual([task_xyz], list(self.filter))

    def test_remove_task(self):
        self.setSearchString("DEF")
        self.list.remove(self.child)
        self.assertFalse(self.filter)

    def test_include_sub_items(self):
        self.setSearchString("ABC", includeSubItems=True)
        self.assertEqual(2, len(self.filter))

    def test_invalid_regex(self):
        self.setSearchString("*")
        self.assertEqual(1, len(self.filter))

    def test_invalid_regex_while_match_case(self):
        self.setSearchString("*", matchCase=True)
        self.assertEqual(1, len(self.filter))

    def test_search_description(self):
        self.setSearchString("parent description", searchDescription=True)
        self.assertEqual(1, len(self.filter))

    def test_search_description_turned_off(self):
        self.setSearchString("parent description")
        self.assertEqual(0, len(self.filter))

    def test_search_description_with_sub_items_included(self):
        self.setSearchString(
            "parent description", includeSubItems=True, searchDescription=True
        )
        self.assertEqual(2, len(self.filter))

    def test_description_match_in_child_skips_parent_in_list_mode(
        self,
    ):
        self.setSearchString("child description", searchDescription=True)
        self.assertEqual(1, len(self.filter))

    def test_description_match_in_child_selects_parent_in_tree_mode(
        self,
    ):
        self.filter.set_tree_mode(True)
        self.setSearchString("child description", searchDescription=True)
        self.assertEqual(2, len(self.filter))


class SelectedItemsFilterTest(test.TestCase):
    def setUp(self):
        self.task = task.Task()
        self.child = task.Task(parent=self.task)
        self.list = task.TaskList([self.task])
        self.filter = base.SelectedItemsFilter(
            self.list, selectedItems=[self.task]
        )

    def test_initial_content(self):
        self.assertEqual([self.task], list(self.filter))

    def test_add_child(self):
        self.list.append(self.child)
        self.assertTrue(self.child in self.filter)

    def test_add_child_with_grandchild(self):
        grandchild = task.Task(parent=self.child)
        self.child.addChild(grandchild)
        self.list.append(self.child)
        self.assertTrue(grandchild in self.filter)

    def test_remove_selected_item(self):
        self.list.remove(self.task)
        self.assertFalse(self.filter)

    def test_selected_items_filter_shows_all_tasks_when_selected_items_removed(
        self,
    ):
        other_task = task.Task()
        self.list.append(other_task)
        self.list.remove(self.task)
        self.assertEqual([other_task], list(self.filter))
