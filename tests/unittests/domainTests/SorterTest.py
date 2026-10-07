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
from taskcoachlib.patterns.snapshot import register_collection
from taskcoachlib.domain import attachment, base, task, effort, date
from taskcoachlib.domain import category
from taskcoachlib.config import settings


class RecordingFilter(base.Filter):
    """Passes every item, and records the tree mode its sorter passes
    on: in the app a sorter always sits on a filter."""

    def __init__(self, *args, **kwargs):
        self.tree_mode_passed = "not set"
        super().__init__(*args, **kwargs)

    def filter_items(self, items):
        return items

    def set_tree_mode(self, tree_mode):
        self.tree_mode_passed = tree_mode
        super().set_tree_mode(tree_mode)


class TaskSorterTest(test.TestCase):
    def setUp(self):
        a = self.a = task.Task("a")
        b = self.b = task.Task("b")
        c = self.c = task.Task("c")
        d = self.d = task.Task("d")
        self.list = task.TaskList([d, b, c, a])
        self.sorter = task.sorter.Sorter(self.list)

    def test_initially_empty(self):
        sorter = task.sorter.Sorter(task.TaskList())
        self.assertEqual(0, len(sorter))

    def test_length(self):
        self.assertEqual(4, len(self.sorter))

    def test_get_item(self):
        self.assertEqual(self.a, self.sorter[0])

    def test_order(self):
        self.assertEqual([self.a, self.b, self.c, self.d], list(self.sorter))

    def test_remove_item(self):
        self.sorter.remove(self.c)
        self.assertEqual([self.a, self.b, self.d], list(self.sorter))
        self.assertEqual(3, len(self.list))

    def test_append(self):
        e = task.Task("e")
        self.list.append(e)
        self.assertEqual(5, len(self.sorter))
        self.assertEqual(e, self.sorter[-1])

    def test_change(self):
        self.a.setSubject("z")
        self.assertEqual([self.b, self.c, self.d, self.a], list(self.sorter))


class TaskSorterSettingsTest(test.TestCase):
    def setUp(self):
        self.taskList = task.TaskList()
        self.sorter = task.sorter.Sorter(self.taskList)
        self.task1 = task.Task(subject="A")
        self.task2 = task.Task(subject="B")
        self.taskList.extend([self.task1, self.task2])

    def test_sort_by_subject(self):
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def test_sort_by_subject_descending(self):
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending(False)
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_due_date_time(self):
        self.task2.set_due_date_time(date.Now() + date.ONE_WEEK)
        self.sorter.sort_by("dueDateTime")
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_subject_turn_off(self):
        self.task2.set_due_date_time(date.Now() + date.ONE_WEEK)
        self.sorter.sort_by("subject")
        self.sorter.sort_by("dueDateTime")
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_completion_status(self):
        self.task1.set_completion_date_time(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_inactive_status(self):
        self.task2.set_actual_start_date_time(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_planned_start_date_time(self):
        self.sorter.sort_by("plannedStartDateTime")
        self.task2.set_planned_start_date_time(date.Tomorrow())
        self.task1.set_planned_start_date_time(date.Now() + date.ONE_WEEK)
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_actual_start_date_time(self):
        self.sorter.sort_by("actualStartDateTime")
        self.task1.set_actual_start_date_time(date.Yesterday())
        self.task2.set_actual_start_date_time(date.Now() - date.ONE_WEEK)
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_actual_start_resorts_when_actual_start_changes(
        self,
    ):
        self.sorter.sort_by("actualStartDateTime")
        self.task1.set_actual_start_date_time(date.Yesterday())
        self.task2.set_actual_start_date_time(date.Now() - date.ONE_WEEK)
        self.task1.set_actual_start_date_time(date.Now() - date.ONE_YEAR)
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def test_sort_by_due_date_time_descending(self):
        self.task1.set_due_date_time(date.Now() + date.ONE_YEAR)
        self.task2.set_due_date_time(date.Now() + date.ONE_WEEK)
        self.sorter.sort_by("dueDateTime")
        self.sorter.sort_ascending(False)
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def test_by_due_date_without_first_sorting_by_status(self):
        self.task1.set_due_date_time(date.Now() + date.ONE_YEAR)
        self.task2.set_due_date_time(date.Now() + date.ONE_WEEK)
        self.sorter.sort_by("dueDateTime")
        self.sorter.sort_by_task_status_first(False)
        self.task2.set_completion_date_time(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_reminder_ascending(self):
        self.sorter.sort_by("reminder")
        self.sorter.sort_ascending(True)
        self.task2.set_reminder(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_reminder_descending(self):
        self.sorter.sort_by("reminder")
        self.sorter.sort_ascending(False)
        self.task2.set_reminder(date.Now())
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def test_sort_by_subject_with_first_sorting_by_status(self):
        self.sorter.sort_by_task_status_first(True)
        self.sorter.sort_by("subject")
        self.task1.set_completion_date_time(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_subject_without_first_sorting_by_status(self):
        self.sorter.sort_by_task_status_first(False)
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        self.task1.set_completion_date_time(date.Now())
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def test_sort_case_sensitive(self):
        self.sorter.sort_by_task_status_first(False)
        self.sorter.sort_case_sensitive(True)
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        task3 = task.Task("a")
        self.taskList.append(task3)
        self.assertEqual([self.task1, self.task2, task3], list(self.sorter))

    def test_sort_case_insensitive(self):
        self.sorter.sort_by_task_status_first(False)
        self.sorter.sort_case_sensitive(False)
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        task3 = task.Task("a")
        self.taskList.append(task3)
        self.assertEqual([self.task1, task3, self.task2], list(self.sorter))

    def test_sort_by_time_left_ascending(self):
        self.task1.set_due_date_time(date.Now() + date.ONE_YEAR)
        self.task2.set_due_date_time(date.Now() + date.ONE_WEEK)
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("timeLeft")
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_time_left_descending(self):
        self.task1.set_due_date_time(date.Now() + date.ONE_YEAR)
        self.task2.set_due_date_time(date.Now() + date.ONE_WEEK)
        self.sorter.sort_by("timeLeft")
        self.sorter.sort_ascending(False)
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def test_sort_by_budget_ascending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("budget")
        self.task1.set_budget(date.TimeDelta(100))
        self.task2.set_budget(date.TimeDelta(10))
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_budget_descending(self):
        self.sorter.sort_by("budget")
        self.sorter.sort_ascending(False)
        self.task1.set_budget(date.TimeDelta(100))
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def test_sort_by_time_spent_ascending(self):
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

    def test_sort_by_time_spent_descending(self):
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

    def test_sort_by_hourly_fee_ascending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("hourlyFee")
        self.task1.set_hourly_fee(100)
        self.task2.set_hourly_fee(200)
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def test_sort_by_hourly_fee_descending(self):
        self.sorter.sort_by("hourlyFee")
        self.sorter.sort_ascending(False)
        self.task1.set_hourly_fee(100)
        self.task2.set_hourly_fee(200)
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_prerequisite_ascending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("prerequisites")
        self.task1.add_prerequisites([self.task2])
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_prerequisite_descending(self):
        self.sorter.sort_by("prerequisites")
        self.sorter.sort_ascending(False)
        self.task2.add_prerequisites([self.task1])
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_recursive_prerequisite_ascending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("prerequisites")
        child1 = task.Task(subject="Child 1")
        self.task1.addChild(child1)
        self.taskList.append(child1)
        child1.add_prerequisites([self.task2])
        self.task2.add_prerequisites([self.task1])
        self.assertEqual([self.task1, self.task2, child1], list(self.sorter))

    def test_sort_by_dependency_ascending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("dependencies")
        self.task1.add_dependencies([self.task2])
        self.task2.add_dependencies([self.task1])
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_dependency_descending(self):
        self.sorter.sort_by("dependencies")
        self.sorter.sort_ascending(False)
        self.task1.add_dependencies([self.task2])
        self.task2.add_dependencies([self.task1])
        self.assertEqual([self.task1, self.task2], list(self.sorter))

    def test_sort_by_recursive_dependency_ascending(self):
        self.sorter.sort_ascending(True)
        self.sorter.sort_by("dependencies")
        child1 = task.Task(subject="Child 1")
        self.task1.addChild(child1)
        self.taskList.append(child1)
        child1.add_dependencies([self.task2])
        self.task2.add_dependencies([self.task1])
        self.assertEqual([self.task1, self.task2, child1], list(self.sorter))

    def test_always_keep_subscription_to_completion_date_time(self):
        """TaskSorter should keep a subscription to task.completionDateTime
        even when the completion date is not the sort key, because sorting
        on task status (active, completed, etc.) depends on the completion
        date."""

        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        self.assertEqual([self.task1, self.task2], list(self.sorter))
        self.task1.set_completion_date_time(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_always_keep_subscription_to_planned_start_date_time(self):
        """TaskSorter should keep a subscription to task.plannedStartDateTime
        even when the planned start date is not the sort key, because sorting
        on task status (active, completed, etc.) depends on the planned start
        date."""
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        self.assertEqual([self.task1, self.task2], list(self.sorter))
        self.task2.set_planned_start_date_time(date.Now() - date.ONE_SECOND)
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_always_keep_subscription_to_actual_start_date_time(self):
        """TaskSorter should keep a subscription to task.actualStartDateTime
        even when the actual start date is not the sort key, because sorting
        on task status (active, completed, etc.) depends on the actual start
        date."""
        self.sorter.sort_by("subject")
        self.sorter.sort_ascending()
        self.assertEqual([self.task1, self.task2], list(self.sorter))
        self.task2.set_actual_start_date_time(date.Now())
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_categories(self):
        self.sorter.sort_by("categories")
        self.task1.addCategory(category.Category("Category 2"))
        self.task2.addCategory(category.Category("Category 1"))
        self.assertEqual([self.task2, self.task1], list(self.sorter))

    def test_sort_by_invalid_sort_key(self):
        self.sorter.sort_by("invalidKey")
        self.assertEqual([self.task1, self.task2], list(self.sorter))


class TaskSorterStatusPriorityTest(test.TestCase):
    def setUp(self):
        self.taskList = task.TaskList()
        self.sorter = task.sorter.Sorter(self.taskList)
        self.sorter.sort_by("subject")
        self.sorter.sort_by_task_status_first(True)
        yesterday = date.Now() - date.ONE_DAY
        overdue = task.Task(subject="A", dueDateTime=yesterday)
        active = task.Task(subject="B", actualStartDateTime=yesterday)
        self.taskList.extend([overdue, active])

    def swap_priorities(self):
        overdue = settings.get("statussortpriority", "overduetasks")
        active = settings.get("statussortpriority", "activetasks")
        settings.set("statussortpriority", "overduetasks", active)
        settings.set("statussortpriority", "activetasks", overdue)

    def test_new_priorities_resort_once_preferences_send_them(self):
        before = list(self.sorter)
        self.swap_priorities()
        self.assertEqual(before, list(self.sorter))
        patterns.Event("settings.statussortpriority.changed", self).send()
        self.assertEqual(list(reversed(before)), list(self.sorter))


class TaskSorterStatusChangeTest(test.TestCase):
    """A status the clock changes re-sorts after the loop's pass."""

    def setUp(self):
        self.task_list = task.TaskList()
        self.sorter = task.sorter.Sorter(self.task_list)
        self.sorter.sort_by("subject")
        self.sorter.sort_by_task_status_first(True)
        self.start = date.Now() + date.ONE_HOUR
        self.inactive = task.Task(subject="A", plannedStartDateTime=self.start)
        self.active = task.Task(
            subject="B", actualStartDateTime=date.Now() - date.ONE_DAY
        )
        self.task_list.extend([self.inactive, self.active])
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: self.start + date.ONE_SECOND
        self.inactive.compute_stored_status()  # Late now

    def test_order_waits_for_the_pass(self):
        self.assertEqual([self.active, self.inactive], list(self.sorter))

    def test_pass_resorts_by_the_new_status(self):
        patterns.Event("scheduler.pass", self).send()
        self.assertEqual([self.inactive, self.active], list(self.sorter))


class TaskSorterStatusColumnTest(test.TestCase):
    """The Status column sorts by the status sort priorities, the most
    urgent first, without "Sort by status first"."""

    def setUp(self):
        self.task_list = task.TaskList()
        self.sorter = task.sorter.Sorter(self.task_list)
        self.sorter.sort_by_task_status_first(False)
        self.start = date.Now() + date.ONE_HOUR
        self.inactive = task.Task(subject="A", plannedStartDateTime=self.start)
        self.active = task.Task(
            subject="B", actualStartDateTime=date.Now() - date.ONE_DAY
        )
        self.task_list.extend([self.inactive, self.active])
        self.sorter.sort_by("status")

    def test_most_urgent_first(self):
        self.assertEqual([self.active, self.inactive], list(self.sorter))

    def test_pass_resorts_a_status_the_clock_changed(self):
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: self.start + date.ONE_SECOND
        self.inactive.compute_stored_status()  # Late now
        self.assertEqual([self.active, self.inactive], list(self.sorter))
        patterns.Event("scheduler.pass", self).send()
        self.assertEqual([self.inactive, self.active], list(self.sorter))


class TaskSorterTreeModeTest(test.TestCase):
    def setUp(self):
        self.taskList = task.TaskList()
        self.filter = RecordingFilter(self.taskList, tree_mode=True)
        self.sorter = task.sorter.Sorter(self.filter, tree_mode=True)
        self.parent1 = task.Task(subject="parent 1")
        self.child1 = task.Task(subject="child 1")
        self.parent1.addChild(self.child1)
        self.parent2 = task.Task(subject="parent 2")
        self.child2 = task.Task(subject="child 2")
        self.parent2.addChild(self.child2)
        self.taskList.extend([self.parent1, self.parent2])

    def test_default_sort_order(self):
        self.assertEqual(
            [self.parent1, self.child1, self.parent2, self.child2],
            list(self.sorter),
        )

    def test_sort_by_due_date_time(self):
        self.sorter.sort_by("dueDateTime")
        self.child2.set_due_date_time(date.Now().endOfDay())
        self.assertTrue(
            list(self.sorter).index(self.parent2)
            < list(self.sorter).index(self.parent1)
        )

    def test_sort_by_priority(self):
        self.sorter.sort_by("priority")
        self.sorter.sort_ascending(False)
        self.parent1.setPriority(5)
        self.child2.setPriority(10)
        self.assertTrue(
            list(self.sorter).index(self.parent2)
            < list(self.sorter).index(self.parent1)
        )

    def test_sort_by_categories_when_parents_have_no_categories(self):
        self.child1.addCategory(category.Category("Category 2"))
        self.child2.addCategory(category.Category("Category 1"))
        self.sorter.sort_by("categories")
        self.assertTrue(
            list(self.sorter).index(self.parent2)
            < list(self.sorter).index(self.parent1)
        )

    def test_sort_by_categories_with_parent_category_as_other_child_category(
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

    def test_children_of_follows_the_lists_order(self):
        # Looked up by their places in the sorted list
        other = task.Task(subject="another child")
        self.parent1.addChild(other)
        self.taskList.append(other)
        self.assertEqual(
            [other, self.child1], self.sorter.children_of(self.parent1)
        )
        self.sorter.sort_ascending(False)
        self.assertEqual(
            [self.child1, other], self.sorter.children_of(self.parent1)
        )
        self.taskList.remove(other)
        self.assertEqual([self.child1], self.sorter.children_of(self.parent1))

    def test_undoing_a_move_sorts_again_once(self):
        # Undo puts the links back alone, with no list change: the
        # sorter forgets its root items and tells the views, once
        history = patterns.CommandHistory()
        with history.action("Move"):
            self.taskList.removeItems([self.child2])
            self.child2.set_parent(None)
            self.taskList.extend([self.child2])
        self.assertIn(self.child2, self.sorter.rootItems())
        self.registerObserver(self.sorter.sort_event_type())
        history.undo()
        self.assertNotIn(self.child2, self.sorter.rootItems())
        self.assertEqual(1, len(self.events))

    def test_undoing_a_removal_is_told_by_the_list_alone(self):
        # Its subitem comes back too, but the list change tells it
        register_collection(self.taskList)
        history = patterns.CommandHistory()
        with history.action("Delete"):
            self.taskList.removeItems([self.child2])
        self.registerObserver(self.sorter.sort_event_type())
        history.undo()
        self.assertIn(self.child2, self.sorter)
        self.assertNotIn(self.child2, self.sorter.rootItems())
        self.assertEqual([], self.events)  # Not sorted again

    def test_set_sorter_to_list_mode(self):
        self.sorter.set_tree_mode(False)
        self.assertEqual(
            [self.child1, self.child2, self.parent1, self.parent2],
            list(self.sorter),
        )

    def test_tree_mode_true_is_passed_to_the_filter(self):
        self.sorter.set_tree_mode(True)
        self.assertEqual(True, self.filter.tree_mode_passed)

    def test_tree_mode_false_is_passed_to_the_filter(self):
        self.sorter.set_tree_mode(False)
        self.assertEqual(False, self.filter.tree_mode_passed)

    def test_sort_by_invalid_sort_key(self):
        self.sorter.sort_by("invalidKey")
        self.assertEqual(
            [self.parent1, self.child1, self.parent2, self.child2],
            list(self.sorter),
        )


class EffortSorterTest(test.TestCase):
    def setUp(self):
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

    def test_descending(self):
        self.assertEqual([self.newestEffort, self.oldestEffort], self.sorter)

    def test_resort(self):
        self.oldestEffort.setStart(date.DateTime(2004, 3, 1))
        self.assertEqual([self.oldestEffort, self.newestEffort], self.sorter)

    def test_create_when_effort_list_is_filled(self):
        sorter = effort.EffortSorter(self.effortList)
        self.assertEqual([self.newestEffort, self.oldestEffort], sorter)

    def test_add_effort(self):
        even_newer_effort = effort.Effort(
            self.task, date.DateTime(2005, 1, 1), date.DateTime(2005, 1, 2)
        )
        self.task.addEffort(even_newer_effort)
        self.assertEqual(
            [even_newer_effort, self.newestEffort, self.oldestEffort],
            self.sorter,
        )

    def test_task_effort_comes_before_child_effort(self):
        child = task.Task("Child")
        child.set_parent(self.task)
        self.task.addChild(child)
        self.taskList.append(child)
        child_effort = effort.Effort(
            child, date.DateTime(2004, 1, 1), date.DateTime(2008, 1, 2)
        )
        child.addEffort(child_effort)
        self.assertEqual(
            [self.newestEffort, child_effort, self.oldestEffort], self.sorter
        )


class AttachmentSorterTest(test.TestCase):
    """File, link and mail attachments send their changes under their
    own classes' event types."""

    def setUp(self):
        self.file = attachment.FileAttachment("b.txt", subject="b")
        self.link = attachment.URIAttachment("https://a", subject="c")
        self.sorter = attachment.AttachmentSorter(
            attachment.AttachmentList([self.file, self.link])
        )

    def test_a_file_attachment_change_resorts(self):
        self.file.setSubject("d")
        self.assertEqual([self.link, self.file], list(self.sorter))

    def test_a_link_change_resorts(self):
        self.link.setSubject("a")
        self.assertEqual([self.link, self.file], list(self.sorter))
