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
from taskcoachlib.domain import task, date


class ViewFilterTestCase(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.list = task.TaskList()
        self.filter = task.filter.ViewFilter(
            self.list, tree_mode=self.tree_mode
        )  # pylint: disable=E1101
        self.task = task.Task(subject="task")
        self.dueToday = task.Task(
            subject="due today", dueDateTime=date.Now().endOfDay()
        )
        self.dueTomorrow = task.Task(
            subject="due tomorrow", dueDateTime=date.Tomorrow().endOfDay()
        )
        self.dueYesterday = task.Task(
            subject="due yesterday", dueDateTime=date.Yesterday().endOfDay()
        )
        self.child = task.Task(subject="child")

    def assertFilterShows(self, *tasks):
        self.assertEqual(len(tasks), len(self.filter))
        for eachTask in tasks:
            self.assertTrue(eachTask in self.filter)

    def assertFilterIsEmpty(self):
        self.assertFalse(self.filter)


class ViewFilterTestsMixin(object):
    def testCreate(self):
        self.assertFilterIsEmpty()

    def testAddTask(self):
        self.filter.append(self.task)
        self.assertFilterShows(self.task)

    def testFilterCompletedTask(self):
        self.task.setCompletionDateTime()
        self.filter.append(self.task)
        self.assertFilterShows(self.task)
        self.filter.hide_task_status(task.status.completed)
        self.assertFilterIsEmpty()

    def testNrOfTasksPerStatusIsAffectedByFiltering(self):
        self.task.setCompletionDateTime()
        self.filter.append(self.task)
        self.filter.hide_task_status(task.status.completed)
        self.assertEqual(
            0, self.filter.nr_of_tasks_per_status()[task.status.completed]
        )

    def testFilterCompletedTask_RootTasks(self):
        self.task.setCompletionDateTime()
        self.filter.append(self.task)
        self.filter.hide_task_status(task.status.completed)
        self.assertFalse(self.filter.rootItems())

    def testMarkTaskCompleted(self):
        self.filter.hide_task_status(task.status.completed)
        self.list.append(self.task)
        self.task.setCompletionDateTime()
        self.assertFilterIsEmpty()

    def testMarkTaskUncompleted(self):
        self.filter.hide_task_status(task.status.completed)
        self.task.setCompletionDateTime()
        self.list.append(self.task)
        self.task.setCompletionDateTime(date.DateTime())
        self.assertFilterShows(self.task)

    def testChangeCompletionDateOfAlreadyCompletedTask(self):
        self.filter.hide_task_status(task.status.completed)
        self.task.setCompletionDateTime()
        self.list.append(self.task)
        self.task.setCompletionDateTime(date.Tomorrow())
        self.assertFilterIsEmpty()

    def testFilterInactiveTask(self):
        self.task.setPlannedStartDateTime(date.Tomorrow())
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.inactive)
        self.assertFilterIsEmpty()

    def testFilterInactiveTask_ChangePlannedStartDateTime(self):
        self.task.setPlannedStartDateTime(date.Tomorrow())
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.inactive)
        self.task.setPlannedStartDateTime(date.Now() - date.ONE_SECOND)
        self.assertFilterShows(self.task)

    def testFilterInactiveTask_WhenPlannedStartDateTimePasses(self):
        plannedStart = date.Tomorrow()
        self.task.setPlannedStartDateTime(plannedStart)
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.inactive)
        oldNow = date.Now
        now = plannedStart + date.ONE_SECOND
        date.Now = lambda: now
        self.task.onTimeToStart()
        self.assertFilterShows(self.task)
        date.Now = oldNow

    def testMarkPrerequisiteCompletedWhileFilteringInactiveTasks(self):
        self.task.addPrerequisites([self.dueToday])
        self.dueToday.addDependencies([self.task])
        self.task.setPlannedStartDateTime(date.Now() - date.ONE_SECOND)
        self.dueToday.setPlannedStartDateTime(date.Now())
        self.filter.extend([self.dueToday, self.task])
        self.filter.hide_task_status(task.status.inactive)
        self.filter.hide_task_status(task.status.completed)
        self.assertFilterShows(self.dueToday)
        self.dueToday.setCompletionDateTime()
        self.assertFilterShows(self.task)

    def testAddPrerequisiteToActiveTaskWhileFilteringInactiveTasksShouldHideTask(
        self,
    ):
        for eachTask in (self.task, self.dueToday):
            eachTask.setPlannedStartDateTime(date.Now())
        self.filter.extend([self.dueToday, self.task])
        self.filter.hide_task_status(task.status.inactive)
        self.task.addPrerequisites([self.dueToday])
        self.assertFilterShows(self.dueToday)

    def testFilterLateTask(self):
        self.task.setPlannedStartDateTime(date.Yesterday())
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.late)
        self.assertFilterIsEmpty()

    def testFilterDueSoonTask(self):
        self.task.setDueDateTime(date.Now() + date.ONE_HOUR)
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.duesoon)
        self.assertFilterIsEmpty()

    def testFilterOverDueTask(self):
        self.task.setDueDateTime(date.Now() - date.ONE_HOUR)
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.overdue)
        self.assertFilterIsEmpty()

    def testFilterOverDueTaskWithActiveChild(self):
        self.child.setActualStartDateTime(date.Now())
        self.task.setDueDateTime(date.Now() - date.ONE_HOUR)
        self.task.addChild(self.child)
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.overdue)
        if self.tree_mode:
            self.assertFilterShows(self.task, self.child)
        else:
            self.assertFilterShows(self.child)


class ViewFilterInListModeTest(ViewFilterTestsMixin, ViewFilterTestCase):
    tree_mode = False


class ViewFilterInTreeModeTest(ViewFilterTestsMixin, ViewFilterTestCase):
    tree_mode = True

    def testFilterCompletedTasks(self):
        self.filter.hide_task_status(task.status.completed)
        child = task.Task()
        self.task.addChild(child)
        child.setParent(self.task)
        self.list.append(self.task)
        self.task.setCompletionDateTime()
        self.assertFilterIsEmpty()


class HideCompositeTasksTestCase(ViewFilterTestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.list = task.TaskList()
        self.filter = task.filter.ViewFilter(
            self.list, tree_mode=self.tree_mode
        )  # pylint: disable=E1101
        self.task = task.Task(subject="task")
        self.child = task.Task(subject="child")
        self.task.addChild(self.child)
        self.filter.append(self.task)

    def _addTwoGrandChildren(self):
        # pylint: disable=W0201
        self.grandChild1 = task.Task(subject="grandchild 1")
        self.grandChild2 = task.Task(subject="grandchild 2")
        self.child.addChild(self.grandChild1)
        self.child.addChild(self.grandChild2)
        self.list.extend([self.grandChild1, self.grandChild2])


class HideCompositeTasksTestsMixin(object):
    def testTurnOn(self):
        self.filter.hide_composite_tasks()
        expectedTasks = (
            (self.task, self.child)
            if self.filter.tree_mode()
            else (self.child,)
        )
        self.assertFilterShows(*expectedTasks)  # pylint: disable=W0142

    def testTurnOff(self):
        self.filter.hide_composite_tasks()
        self.filter.hide_composite_tasks(False)
        self.assertFilterShows(self.task, self.child)

    def testAddChild(self):
        self.filter.hide_composite_tasks()
        grandChild = task.Task(subject="grandchild")
        self.list.append(grandChild)
        self.child.addChild(grandChild)
        expectedTasks = (
            (self.task, self.child, grandChild)
            if self.filter.tree_mode()
            else (grandChild,)
        )
        self.assertFilterShows(*expectedTasks)  # pylint: disable=W0142

    def testRemoveChild(self):
        self.filter.hide_composite_tasks()
        self.list.remove(self.child)
        self.assertFilterShows(self.task)

    def testAddTwoChildren(self):
        self.filter.hide_composite_tasks()
        self._addTwoGrandChildren()
        expectedTasks = (
            (self.task, self.child, self.grandChild1, self.grandChild2)
            if self.filter.tree_mode()
            else (self.grandChild1, self.grandChild2)
        )
        self.assertFilterShows(*expectedTasks)  # pylint: disable=W0142

    def testRemoveTwoChildren(self):
        self._addTwoGrandChildren()
        self.filter.hide_composite_tasks()
        self.list.removeItems([self.grandChild1, self.grandChild2])
        expectedTasks = (
            (self.task, self.child)
            if self.filter.tree_mode()
            else (self.child,)
        )
        self.assertFilterShows(*expectedTasks)  # pylint: disable=W0142


class HideCompositeTasksInListModeTest(
    HideCompositeTasksTestsMixin, HideCompositeTasksTestCase
):
    tree_mode = False


class HideCompositeTasksInTreeModeTest(
    HideCompositeTasksTestsMixin, HideCompositeTasksTestCase
):
    tree_mode = True
