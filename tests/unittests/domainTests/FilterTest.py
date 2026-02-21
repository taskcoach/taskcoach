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

    def testLength(self):
        self.assertEqual(2, len(self.filter))

    def testContents(self):
        self.assertTrue("c" in self.filter and "d" in self.filter)

    def testRemoveItem(self):
        self.filter.remove("c")
        self.assertEqual(1, len(self.filter))
        self.assertTrue("d" in self.filter)
        self.assertEqual(["a", "b", "d"], self.observable)

    def testNotification(self):
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

    def testDelegation(self):
        self.filter2.test()
        self.assertEqual(1, self.filter1.testcalled)

    def testSetTreeMode_True(self):
        self.filter2.set_tree_mode(True)
        self.assertTrue(self.filter1.tree_mode())

    def testSetTreeMode_False(self):
        self.filter2.set_tree_mode(False)
        self.assertFalse(self.filter1.tree_mode())

    def testFiltersAreCollected(self):
        filterRef = weakref.ref(self.filter1)
        self.filter2.detach()
        del self.filter1
        del self.filter2
        self.assertTrue(filterRef() is None)


class SearchFilterTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
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

    def testNoMatch(self):
        self.setSearchString("XYZ")
        self.assertEqual(0, len(self.filter))

    def testMatch(self):
        self.setSearchString("AB")
        self.assertEqual(1, len(self.filter))

    def testMatchIsCaseInSensitiveByDefault(self):
        self.setSearchString("abc")
        self.assertEqual(1, len(self.filter))

    def testMatchCaseInsensitive(self):
        self.setSearchString("abc", True)
        self.assertEqual(0, len(self.filter))

    def testMatchWithRE(self):
        self.setSearchString("a.c")
        self.assertEqual(1, len(self.filter))

    def testMatchWithoutRE(self):
        self.setSearchString("$D", regularExpression=False)
        self.assertEqual(1, len(self.filter))

    def testMatchWithEmptyString(self):
        self.setSearchString("")
        self.assertEqual(2, len(self.filter))

    def testMatchChildDoesNotSelectParentWhenNotInTreeMode(self):
        self.setSearchString("DEF")
        self.assertEqual(1, len(self.filter))

    def testMatchChildAlsoSelectsParentWhenInTreeMode(self):
        self.filter.set_tree_mode(True)
        self.setSearchString("DEF")
        self.assertEqual(2, len(self.filter))

    def testMatchChildDoesNotSelectParentWhenChildNotInList(self):
        self.list.remove(self.child)
        self.parent.addChild(
            self.child
        )  # simulate a child that has been filtered
        self.setSearchString("DEF")
        self.assertEqual(0, len(self.filter))

    def testAddTask(self):
        self.setSearchString("XYZ")
        taskXYZ = task.Task(subject="subject with XYZ")
        self.list.append(taskXYZ)
        self.assertEqual([taskXYZ], list(self.filter))

    def testRemoveTask(self):
        self.setSearchString("DEF")
        self.list.remove(self.child)
        self.assertFalse(self.filter)

    def testIncludeSubItems(self):
        self.setSearchString("ABC", includeSubItems=True)
        self.assertEqual(2, len(self.filter))

    def testInvalidRegex(self):
        self.setSearchString("*")
        self.assertEqual(1, len(self.filter))

    def testInvalidRegex_WhileMatchCase(self):
        self.setSearchString("*", matchCase=True)
        self.assertEqual(1, len(self.filter))

    def testSearchDescription(self):
        self.setSearchString("parent description", searchDescription=True)
        self.assertEqual(1, len(self.filter))

    def testSearchDescription_TurnedOff(self):
        self.setSearchString("parent description")
        self.assertEqual(0, len(self.filter))

    def testSearchDescriptionWithSubItemsIncluded(self):
        self.setSearchString(
            "parent description", includeSubItems=True, searchDescription=True
        )
        self.assertEqual(2, len(self.filter))

    def testSearchDescription_MatchChildDoesNotSelectParentWhenNotInTreeMode(
        self,
    ):
        self.setSearchString("child description", searchDescription=True)
        self.assertEqual(1, len(self.filter))

    def testSearchDescription_MatchChildAlsoSelectsParentWhenInTreeMode(self):
        self.filter.set_tree_mode(True)
        self.setSearchString("child description", searchDescription=True)
        self.assertEqual(2, len(self.filter))


class DeletedFilterTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.list = task.TaskList()
        self.filter = base.DeletedFilter(self.list)
        self.task = task.Task()

    def testAddItem(self):
        self.list.append(self.task)
        self.assertEqual(1, len(self.filter))

    def testDeleteItem(self):
        self.list.append(self.task)
        self.list.remove(self.task)
        self.assertEqual(0, len(self.filter))

    def testMarkDeleted(self):
        self.list.append(self.task)
        self.task.markDeleted()
        self.assertEqual(0, len(self.filter))

    def testMarkNotDeleted(self):
        self.list.append(self.task)
        self.task.markDeleted()
        self.task.cleanDirty()
        self.assertEqual(1, len(self.filter))


class SelectedItemsFilterTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.task = task.Task()
        self.child = task.Task(parent=self.task)
        self.list = task.TaskList([self.task])
        self.filter = base.SelectedItemsFilter(
            self.list, selectedItems=[self.task]
        )

    def testInitialContent(self):
        self.assertEqual([self.task], list(self.filter))

    def testAddChild(self):
        self.list.append(self.child)
        self.assertTrue(self.child in self.filter)

    def testAddChildWithGrandchild(self):
        grandchild = task.Task(parent=self.child)
        self.child.addChild(grandchild)
        self.list.append(self.child)
        self.assertTrue(grandchild in self.filter)

    def testRemoveSelectedItem(self):
        self.list.remove(self.task)
        self.assertFalse(self.filter)

    def testSelectedItemsFilterShowsAllTasksWhenSelectedItemsRemoved(self):
        otherTask = task.Task()
        self.list.append(otherTask)
        self.list.remove(self.task)
        self.assertEqual([otherTask], list(self.filter))
