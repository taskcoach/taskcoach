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
from taskcoachlib import config, patterns
from taskcoachlib.domain import task, effort, date, category


class DummyTaskList(task.TaskList):
    def __init__(self, *args, **kwargs):
        self.tree_mode = "not set"
        super().__init__(*args, **kwargs)

    def set_tree_mode(self, tree_mode):
        self.tree_mode = tree_mode


class TaskSorterTest(test.TestCase):
    def setUp(self):
        a = self.a = task.Task("a")
        b = self.b = task.Task("b")
        c = self.c = task.Task("c")
        d = self.d = task.Task("d")
        self.list = task.TaskList([d, b, c, a])
        self.sorter = task.sorter.Sorter(self.list)

    def testInitiallyEmpty(self):
        sorter = task.sorter.Sorter(task.TaskList())
        self.assertEqual(0, len(sorter))

    def testLength(self):
        self.assertEqual(4, len(self.sorter))

    def testGetItem(self):
        self.assertEqual(self.a, self.sorter[0])

    def testOrder(self):
        self.assertEqual([self.a, self.b, self.c, self.d], list(self.sorter))

    def testRemoveItem(self):
        self.sorter.remove(self.c)
        self.assertEqual([self.a, self.b, self.d], list(self.sorter))
        self.assertEqual(3, len(self.list))

    def testAppend(self):
        e = task.Task("e")
        self.list.append(e)
        self.assertEqual(5, len(self.sorter))
        self.assertEqual(e, self.sorter[-1])

    def testChange(self):
        self.a.setSubject("z")
        self.assertEqual([self.b, self.c, self.d, self.a], list(self.sorter))


class TaskSorterSettingsTest(test.TestCase):
    def setUp(self):
        self.taskList = task.TaskList()
        self.sorter = task.sorter.Sorter(self.taskList)
        self.task1 = task.Task(subject="A")
        self.task2 = task.Task(subject="B")
        self.taskList.extend([self.task1, self.task2])

    def testSortBySubject(self):
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def testSortBySubjectDescending(self):
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending(False)
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortDueDateTime(self):
        self.task2.setDueDateTime(date.Now() + date.ONE_WEEK)
        self.sorter.sort_by("dueDateTime")
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortBySubject_TurnOff(self):
        self.task2.setDueDateTime(date.Now() + date.ONE_WEEK)
        self.sorter.sort_by("subject")
        self.sorter.sort_by("dueDateTime")
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByCompletionStatus(self):
        self.task1.setCompletionDateTime(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByInactiveStatus(self):
        self.task2.setActualStartDateTime(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByPlannedStartDateTime(self):
        self.sorter.sort_by("plannedStartDateTime")
        self.task2.setPlannedStartDateTime(date.Tomorrow())
        self.task1.setPlannedStartDateTime(date.Now() + date.ONE_WEEK)
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByActualStartDateTime(self):
        self.sorter.sort_by("actualStartDateTime")
        self.task1.setActualStartDateTime(date.Yesterday())
        self.task2.setActualStartDateTime(date.Now() - date.ONE_WEEK)
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByActualStartDateTimeKeepsSortingWhenChangingActualStartDateTime(
        self,
    ):
        self.sorter.sort_by("actualStartDateTime")
        self.task1.setActualStartDateTime(date.Yesterday())
        self.task2.setActualStartDateTime(date.Now() - date.ONE_WEEK)
        self.task1.setActualStartDateTime(date.Now() - date.ONE_YEAR)
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def testSortByDueDateTimeDescending(self):
        self.task1.setDueDateTime(date.Now() + date.ONE_YEAR)
        self.task2.setDueDateTime(date.Now() + date.ONE_WEEK)
        self.sorter.sort_by("dueDateTime")
        self.sorter.sort_ascending(False)
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def testByDueDateWithoutFirstSortingByStatus(self):
        self.task1.setDueDateTime(date.Now() + date.ONE_YEAR)
        self.task2.setDueDateTime(date.Now() + date.ONE_WEEK)
        self.sorter.sort_by("dueDateTime")
        self.sorter.sort_by_task_status_first(False)
        self.task2.setCompletionDateTime(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByReminderAscending(self):
        self.sorter.sort_by("reminder")
        self.sorter.sort_ascending(True)
        self.task2.setReminder(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByReminderDescending(self):
        self.sorter.sort_by("reminder")
        self.sorter.sort_ascending(False)
        self.task2.setReminder(date.Now())
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def testSortBySubjectWithFirstSortingByStatus(self):
        self.sorter.sort_by_task_status_first(True)
        self.sorter.sort_by("subject")
        self.task1.setCompletionDateTime(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortBySubjectWithoutFirstSortingByStatus(self):
        self.sorter.sort_by_task_status_first(False)
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        self.task1.setCompletionDateTime(date.Now())
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def testSortCaseSensitive(self):
        self.sorter.sort_by_task_status_first(False)
        self.sorter.sort_case_sensitive(True)
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        task3 = task.Task("a")
        self.taskList.append(task3)
        self.assertEqual([self.task1, self.task2, task3], list(self.sorter))

    def testSortCaseInsensitive(self):
        self.sorter.sort_by_task_status_first(False)
        self.sorter.sort_case_sensitive(False)
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        task3 = task.Task("a")
        self.taskList.append(task3)
        self.assertEqual([self.task1, task3, self.task2], list(self.sorter))

    def testSortByTimeLeftAscending(self):
        self.task1.setDueDateTime(date.Now() + date.ONE_YEAR)
        self.task2.setDueDateTime(date.Now() + date.ONE_WEEK)
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("timeLeft")
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByTimeLeftDescending(self):
        self.task1.setDueDateTime(date.Now() + date.ONE_YEAR)
        self.task2.setDueDateTime(date.Now() + date.ONE_WEEK)
        self.sorter.sort_by("timeLeft")
        self.sorter.sort_ascending(False)
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def testSortByBudgetAscending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("budget")
        self.task1.setBudget(date.TimeDelta(100))
        self.task2.setBudget(date.TimeDelta(10))
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByBudgetDescending(self):
        self.sorter.sort_by("budget")
        self.sorter.sort_ascending(False)
        self.task1.setBudget(date.TimeDelta(100))
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def testSortByTimeSpentAscending(self):
        self.sorter.sort_by("timeSpent")
        self.task2.addEffort(
            effort.Effort(
                self.task2,
                date.DateTime(2005, 1, 1),
                date.DateTime(2006, 1, 1),
            )
        )
        self.task1.addEffort(
            effort.Effort(
                self.task1,
                date.DateTime(2005, 1, 1),
                date.DateTime(2007, 1, 1),
            )
        )
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByTimeSpentDescending(self):
        self.sorter.sort_ascending(False)
        self.sorter.sort_by("timeSpent")
        self.task1.addEffort(
            effort.Effort(
                self.task1,
                date.DateTime(2005, 1, 1, 10, 0, 0),
                date.DateTime(2005, 1, 1, 11, 0, 0),
            )
        )
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def testSortByHourlyFeeAscending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("hourlyFee")
        self.task1.setHourlyFee(100)
        self.task2.setHourlyFee(200)
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def testSortByHourlyFeeDescending(self):
        self.sorter.sort_by("hourlyFee")
        self.sorter.sort_ascending(False)
        self.task1.setHourlyFee(100)
        self.task2.setHourlyFee(200)
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByPrerequisiteAscending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("prerequisites")
        self.task1.addPrerequisites([self.task2])
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByPrerequisiteDescending(self):
        self.sorter.sort_by("prerequisites")
        self.sorter.sort_ascending(False)
        self.task2.addPrerequisites([self.task1])
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByRecursivePrerequisiteAscending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("prerequisites")
        child1 = task.Task(subject="Child 1")
        self.task1.addChild(child1)
        self.taskList.append(child1)
        child1.addPrerequisites([self.task2])
        self.task2.addPrerequisites([self.task1])
        self.assertEqual([self.task1, self.task2, child1], list(self.sorter))

    def testSortByDependencyAscending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("dependencies")
        self.task1.addDependencies([self.task2])
        self.task2.addDependencies([self.task1])
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByDependencyDescending(self):
        self.sorter.sort_by("dependencies")
        self.sorter.sort_ascending(False)
        self.task1.addDependencies([self.task2])
        self.task2.addDependencies([self.task1])
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def testSortByRecursiveDependencyAscending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("dependencies")
        child1 = task.Task(subject="Child 1")
        self.task1.addChild(child1)
        self.taskList.append(child1)
        child1.addDependencies([self.task2])
        self.task2.addDependencies([self.task1])
        self.assertEqual([self.task1, self.task2, child1], list(self.sorter))

    def testAlwaysKeepSubscriptionToCompletionDateTime(self):
        """TaskSorter should keep a subscription to task.completionDateTime
        even when the completion date is not the sort key, because sorting
        on task status (active, completed, etc.) depends on the completion
        date."""

        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        self.assertEqual([self.task1, self.task2], list(self.sorter))
        self.task1.setCompletionDateTime(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testAlwaysKeepSubscriptionToPlannedStartDateTime(self):
        """TaskSorter should keep a subscription to task.plannedStartDateTime
        even when the planned start date is not the sort key, because sorting
        on task status (active, completed, etc.) depends on the planned start
        date."""
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        self.assertEqual([self.task1, self.task2], list(self.sorter))
        self.task2.setPlannedStartDateTime(date.Now() - date.ONE_SECOND)
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testAlwaysKeepSubscriptionToActualStartDateTime(self):
        """TaskSorter should keep a subscription to task.actualStartDateTime
        even when the actual start date is not the sort key, because sorting
        on task status (active, completed, etc.) depends on the actual start
        date."""
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        self.assertEqual([self.task1, self.task2], list(self.sorter))
        self.task2.setActualStartDateTime(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByCategories(self):
        self.sorter.sort_by("categories")
        self.task1.addCategory(category.Category("Category 2"))
        self.task2.addCategory(category.Category("Category 1"))
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def testSortByInvalidSortKey(self):
        self.sorter.sort_by("invalidKey")
        self.assertEqual([self.task1, self.task2], list(self.sorter))


class TaskSorterStatusPriorityTest(test.TestCase):
    def setUp(self):
        task.Task.settings = self.settings = config.Settings(load=False)
        self.taskList = task.TaskList()
        self.sorter = task.sorter.Sorter(self.taskList)
        self.sorter.sort_by("subject")
        self.sorter.sort_by_task_status_first(True)
        yesterday = date.Now() - date.ONE_DAY
        overdue = task.Task(subject="A", dueDateTime=yesterday)
        active = task.Task(subject="B", actualStartDateTime=yesterday)
        self.taskList.extend([overdue, active])

    def swap_priorities(self):
        get = self.settings.get
        overdue = get("statussortpriority", "overduetasks")
        active = get("statussortpriority", "activetasks")
        self.settings.set("statussortpriority", "overduetasks", active)
        self.settings.set("statussortpriority", "activetasks", overdue)

    def test_new_priorities_resort_once_preferences_send_them(self):
        before = list(self.sorter)
        self.swap_priorities()
        self.assertEqual(before, list(self.sorter))
        patterns.Event(
            "settings.statussortpriority.changed", self.settings
        ).send()
        self.assertEqual(list(reversed(before)), list(self.sorter))


class TaskSorterTreeModeTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.taskList = DummyTaskList()
        self.sorter = task.sorter.Sorter(self.taskList, tree_mode=True)
        self.parent1 = task.Task(subject="parent 1")
        self.child1 = task.Task(subject="child 1")
        self.parent1.addChild(self.child1)
        self.parent2 = task.Task(subject="parent 2")
        self.child2 = task.Task(subject="child 2")
        self.parent2.addChild(self.child2)
        self.taskList.extend([self.parent1, self.parent2])

    def testDefaultSortOrder(self):
        self.assertEqual(
            [self.parent1, self.child1, self.parent2, self.child2],
            list(self.sorter),
        )

    def testSortByDueDateTime(self):
        self.sorter.sort_by("dueDateTime")
        self.child2.setDueDateTime(date.Now().endOfDay())
        self.assertTrue(
            list(self.sorter).index(self.parent2)
            < list(self.sorter).index(self.parent1)
        )

    def testSortByPriority(self):
        self.sorter.sort_by("priority")
        self.sorter.sort_ascending(False)
        self.parent1.setPriority(5)
        self.child2.setPriority(10)
        self.assertTrue(
            list(self.sorter).index(self.parent2)
            < list(self.sorter).index(self.parent1)
        )

    def testSortByCategories_WhenParentsHaveNoCategories(self):
        self.child1.addCategory(category.Category("Category 2"))
        self.child2.addCategory(category.Category("Category 1"))
        self.sorter.sort_by("categories")
        self.assertTrue(
            list(self.sorter).index(self.parent2)
            < list(self.sorter).index(self.parent1)
        )

    def testSortByCategories_WhenParentCategoryEqualsChildCategoryOfAnotherParent(
        self,
    ):
        category1 = category.Category("Category 1")
        category2 = category.Category("Category 2")
        category3 = category.Category("Category 3")
        self.child1.addCategory(category1)
        self.parent1.addCategory(category3)
        self.parent2.addCategory(category2)
        self.sorter.sort_by("categories")
        self.assertTrue(
            list(self.sorter).index(self.parent2)
            < list(self.sorter).index(self.parent1)
        )

    def testSetSorterToListMode(self):
        self.sorter.set_tree_mode(False)
        self.assertEqual(
            [self.child1, self.child2, self.parent1, self.parent2],
            list(self.sorter),
        )

    def testTreeModeDelegation_True(self):
        self.sorter.set_tree_mode(True)
        self.assertEqual(True, self.taskList.tree_mode)

    def testTreeModeDelegation_False(self):
        self.sorter.set_tree_mode(False)
        self.assertEqual(False, self.taskList.tree_mode)

    def testSortByInvalidSortKey(self):
        self.sorter.sort_by("invalidKey")
        self.assertEqual(
            [self.parent1, self.child1, self.parent2, self.child2],
            list(self.sorter),
        )


class EffortSorterTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.taskList = task.TaskList()
        self.effortList = effort.EffortList(self.taskList)
        self.sorter = effort.EffortSorter(self.effortList)
        self.task = task.Task("Task")
        self.oldestEffort = effort.Effort(
            self.task, date.DateTime(2004, 1, 1), date.DateTime(2004, 1, 2)
        )
        self.newestEffort = effort.Effort(
            self.task, date.DateTime(2004, 2, 1), date.DateTime(2004, 2, 2)
        )
        self.task.addEffort(self.oldestEffort)
        self.task.addEffort(self.newestEffort)
        self.taskList.append(self.task)

    def testDescending(self):
        self.assertEqual([self.newestEffort, self.oldestEffort], self.sorter)

    def testResort(self):
        self.oldestEffort.setStart(date.DateTime(2004, 3, 1))
        self.assertEqual([self.oldestEffort, self.newestEffort], self.sorter)

    def testCreateWhenEffortListIsFilled(self):
        sorter = effort.EffortSorter(self.effortList)
        self.assertEqual([self.newestEffort, self.oldestEffort], sorter)

    def testAddEffort(self):
        evenNewerEffort = effort.Effort(
            self.task, date.DateTime(2005, 1, 1), date.DateTime(2005, 1, 2)
        )
        self.task.addEffort(evenNewerEffort)
        self.assertEqual(
            [evenNewerEffort, self.newestEffort, self.oldestEffort],
            self.sorter,
        )

    def testTaskEffortComesBeforeChildEffort(self):
        child = task.Task("Child")
        child.setParent(self.task)
        self.task.addChild(child)
        self.taskList.append(child)
        childEffort = effort.Effort(
            child, date.DateTime(2004, 1, 1), date.DateTime(2008, 1, 2)
        )
        child.addEffort(childEffort)
        self.assertEqual(
            [self.newestEffort, childEffort, self.oldestEffort], self.sorter
        )
