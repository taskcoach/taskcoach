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
from taskcoachlib import patterns
from taskcoachlib.domain import task, date


class ViewFilterTestCase(test.TestCase):
    def setUp(self):
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
        for each_task in tasks:
            self.assertTrue(each_task in self.filter)

    def assertFilterIsEmpty(self):
        self.assertFalse(self.filter)


class ViewFilterTestsMixin(object):
    def test_create(self):
        self.assertFilterIsEmpty()

    def test_add_task(self):
        self.filter.append(self.task)
        self.assertFilterShows(self.task)

    def test_filter_completed_task(self):
        self.task.set_completion_date_time()
        self.filter.append(self.task)
        self.assertFilterShows(self.task)
        self.filter.hide_task_status(task.status.completed)
        self.assertFilterIsEmpty()

    def test_nr_of_tasks_per_status_is_affected_by_filtering(self):
        self.task.set_completion_date_time()
        self.filter.append(self.task)
        self.filter.hide_task_status(task.status.completed)
        self.assertEqual(
            0, self.filter.nr_of_tasks_per_status()[task.status.completed]
        )

    def test_filter_completed_task_root_tasks(self):
        self.task.set_completion_date_time()
        self.filter.append(self.task)
        self.filter.hide_task_status(task.status.completed)
        self.assertFalse(self.filter.rootItems())

    def test_mark_task_completed(self):
        self.filter.hide_task_status(task.status.completed)
        self.list.append(self.task)
        self.task.set_completion_date_time()
        self.assertFilterIsEmpty()

    def test_mark_task_uncompleted(self):
        self.filter.hide_task_status(task.status.completed)
        self.task.set_completion_date_time()
        self.list.append(self.task)
        self.task.set_completion_date_time(date.DateTime())
        self.assertFilterShows(self.task)

    def test_change_completion_date_of_already_completed_task(self):
        self.filter.hide_task_status(task.status.completed)
        self.task.set_completion_date_time()
        self.list.append(self.task)
        self.task.set_completion_date_time(date.Tomorrow())
        self.assertFilterIsEmpty()

    def test_filter_inactive_task(self):
        self.task.set_planned_start_date_time(date.Tomorrow())
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.inactive)
        self.assertFilterIsEmpty()

    def test_filter_inactive_task_change_planned_start_date_time(self):
        self.task.set_planned_start_date_time(date.Tomorrow())
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.inactive)
        self.task.set_planned_start_date_time(date.Now() - date.ONE_SECOND)
        self.assertFilterShows(self.task)

    def test_filter_inactive_task_when_planned_start_date_time_passes(self):
        planned_start = date.Tomorrow()
        self.task.set_planned_start_date_time(planned_start)
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.inactive)
        old_now = date.Now
        now = planned_start + date.ONE_SECOND
        date.Now = lambda: now
        self.task.compute_stored_status()
        date.Now = old_now
        # The clock's status changes refilter once, after the pass
        patterns.Event("scheduler.pass", self).send()
        self.assertFilterShows(self.task)

    def test_the_clocks_status_changes_refilter_once_per_pass(self):
        resets = []
        original = self.filter.reset
        self.filter.reset = lambda *args, **kwargs: (
            resets.append(1),
            original(*args, **kwargs),
        )
        for each in (self.task, self.dueToday):
            patterns.Event(
                task.Task.statusChangedEventType(), each, None
            ).send()
        patterns.Event("scheduler.pass", self).send()
        self.assertEqual(1, len(resets))

    def test_mark_prerequisite_completed_while_filtering_inactive_tasks(self):
        self.task.add_prerequisites([self.dueToday])
        self.dueToday.add_dependencies([self.task])
        self.task.set_planned_start_date_time(date.Now() - date.ONE_SECOND)
        self.dueToday.set_planned_start_date_time(date.Now())
        self.filter.extend([self.dueToday, self.task])
        self.filter.hide_task_status(task.status.inactive)
        self.filter.hide_task_status(task.status.completed)
        self.assertFilterShows(self.dueToday)
        self.dueToday.set_completion_date_time()
        self.assertFilterShows(self.task)

    def test_adding_prerequisite_hides_task_when_hiding_inactive_tasks(
        self,
    ):
        for each_task in (self.task, self.dueToday):
            each_task.set_planned_start_date_time(date.Now())
        self.filter.extend([self.dueToday, self.task])
        self.filter.hide_task_status(task.status.inactive)
        self.task.add_prerequisites([self.dueToday])
        self.assertFilterShows(self.dueToday)

    def test_filter_late_task(self):
        self.task.set_planned_start_date_time(date.Yesterday())
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.late)
        self.assertFilterIsEmpty()

    def test_filter_due_soon_task(self):
        self.task.set_due_date_time(date.Now() + date.ONE_HOUR)
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.duesoon)
        self.assertFilterIsEmpty()

    def test_filter_over_due_task(self):
        self.task.set_due_date_time(date.Now() - date.ONE_HOUR)
        self.list.append(self.task)
        self.filter.hide_task_status(task.status.overdue)
        self.assertFilterIsEmpty()

    def test_filter_over_due_task_with_active_child(self):
        self.child.set_actual_start_date_time(date.Now())
        self.task.set_due_date_time(date.Now() - date.ONE_HOUR)
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

    def test_filter_completed_tasks(self):
        self.filter.hide_task_status(task.status.completed)
        child = task.Task()
        self.task.addChild(child)
        child.set_parent(self.task)
        self.list.append(self.task)
        self.task.set_completion_date_time()
        self.assertFilterIsEmpty()


class HideCompositeTasksTestCase(ViewFilterTestCase):
    def setUp(self):
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
    def test_turn_on(self):
        self.filter.hide_composite_tasks()
        expected_tasks = (
            (self.task, self.child)
            if self.filter.tree_mode()
            else (self.child,)
        )
        self.assertFilterShows(*expected_tasks)  # pylint: disable=W0142

    def test_turn_off(self):
        self.filter.hide_composite_tasks()
        self.filter.hide_composite_tasks(False)
        self.assertFilterShows(self.task, self.child)

    def test_add_child(self):
        self.filter.hide_composite_tasks()
        grand_child = task.Task(subject="grandchild")
        self.list.append(grand_child)
        self.child.addChild(grand_child)
        expected_tasks = (
            (self.task, self.child, grand_child)
            if self.filter.tree_mode()
            else (grand_child,)
        )
        self.assertFilterShows(*expected_tasks)  # pylint: disable=W0142

    def test_remove_child(self):
        self.filter.hide_composite_tasks()
        self.list.remove(self.child)
        self.assertFilterShows(self.task)

    def test_add_two_children(self):
        self.filter.hide_composite_tasks()
        self._addTwoGrandChildren()
        expected_tasks = (
            (self.task, self.child, self.grandChild1, self.grandChild2)
            if self.filter.tree_mode()
            else (self.grandChild1, self.grandChild2)
        )
        self.assertFilterShows(*expected_tasks)  # pylint: disable=W0142

    def test_remove_two_children(self):
        self._addTwoGrandChildren()
        self.filter.hide_composite_tasks()
        self.list.removeItems([self.grandChild1, self.grandChild2])
        expected_tasks = (
            (self.task, self.child)
            if self.filter.tree_mode()
            else (self.child,)
        )
        self.assertFilterShows(*expected_tasks)  # pylint: disable=W0142


class HideCompositeTasksInListModeTest(
    HideCompositeTasksTestsMixin, HideCompositeTasksTestCase
):
    tree_mode = False


class HideCompositeTasksInTreeModeTest(
    HideCompositeTasksTestsMixin, HideCompositeTasksTestCase
):
    tree_mode = True
