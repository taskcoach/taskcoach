# -*- coding: utf-8 -*-

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

from taskcoachlib import patterns
from taskcoachlib.domain import task, effort, date, attachment, note, category
from taskcoachlib.config import settings
from unittests import asserts
import test
import wx

# pylint: disable=C0103,C0111


class TaskTestCase(test.TestCase):
    eventTypes = []

    @staticmethod
    def run_scheduler_tick(*tasks):
        """Statuses and their icons are recomputed by the scheduler's
        full loop (docs/SCHEDULERS.md)."""
        from taskcoachlib.gui.scheduler import MasterScheduler

        for each in tasks:
            MasterScheduler._process_task(each, date.Now())

    def labelTaskChildrenAndEffort(self, parent_task, task_label):
        for child_index, child in enumerate(parent_task.children()):
            child_label = "%s_%d" % (task_label, child_index + 1)
            setattr(self, child_label, child)
            self.labelTaskChildrenAndEffort(child, child_label)
            self.labelEfforts(child, child_label)

    def labelEfforts(self, parent_task, task_label):
        for effort_index, each_effort in enumerate(parent_task.efforts()):
            effort_label = "%seffort%d" % (task_label, effort_index + 1)
            setattr(self, effort_label, each_effort)

    def setUp(self):
        self.yesterday = date.Yesterday()
        self.tomorrow = date.Tomorrow()
        self.tasks = self.createTasks()
        self.task = self.tasks[0]
        for index, each_task in enumerate(self.tasks):
            task_label = "task%d" % (index + 1)
            setattr(self, task_label, each_task)
            self.labelTaskChildrenAndEffort(each_task, task_label)
            self.labelEfforts(each_task, task_label)
        for event_type in self.eventTypes:
            self.registerObserver(event_type)  # pylint: disable=W0201

    def createTasks(self):
        def createAttachments(kwargs):
            if "attachments" in kwargs:
                kwargs["attachments"] = [
                    attachment.FileAttachment(filename)
                    for filename in kwargs["attachments"]
                ]
            return kwargs

        return [
            task.Task(**createAttachments(kwargs))
            for kwargs in self.taskCreationKeywordArguments()
        ]

    def taskCreationKeywordArguments(self):  # pylint: disable=R0201
        return [dict(subject="Task")]

    def addEffort(self, hours, task_to_add_effort_to=None):
        task_to_add_effort_to = task_to_add_effort_to or self.task
        start = date.DateTime(2005, 1, 1)
        task_to_add_effort_to.addEffort(
            effort.Effort(task_to_add_effort_to, start, start + hours)
        )

    def assertReminder(
        self, expected_reminder, task_with_reminder=None, recursive=False
    ):
        task_with_reminder = task_with_reminder or self.task
        self.assertEqual(
            expected_reminder, task_with_reminder.reminder(recursive=recursive)
        )

    def assertEvent(self, *expected_event_args):
        self.assertEqual([patterns.Event(*expected_event_args)], self.events)

    def record_changes(self, event_type):
        """Record (value, source) for each change of the event type."""
        self.changes = []
        patterns.Publisher().registerObserver(
            self.on_change, eventType=event_type
        )

    def on_change(self, event):
        for source in event.sources():
            self.changes.append((event.value(source), source))

    def sources_of(self, event_type):
        return [
            event.sources(event_type)
            for event in self.events
            if event_type in event.types()
        ]


class CommonTaskTestsMixin(asserts.TaskAssertsMixin):
    """These tests should succeed for all tasks, regardless of state."""

    def test_copy(self):
        copy = self.task.copy()
        self.assertTaskCopy(copy, self.task)

    def test_copy_id_is_different(self):
        copy = self.task.copy()
        self.assertNotEqual(copy.id(), self.task.id())


class NoBudgetTestsMixin(object):
    """These tests should succeed for all tasks without budget."""

    def test_task_has_no_budget(self):
        self.assertEqual(date.TimeDelta(), self.task.budget())

    def test_task_has_no_recursive_budget(self):
        self.assertEqual(date.TimeDelta(), self.task.budget(recursive=True))

    def test_task_has_no_budget_left(self):
        self.assertEqual(date.TimeDelta(), self.task.budgetLeft())

    def test_task_has_no_recursive_budget_left(self):
        self.assertEqual(
            date.TimeDelta(), self.task.budgetLeft(recursive=True)
        )


class DefaultTaskStateTest(
    TaskTestCase, CommonTaskTestsMixin, NoBudgetTestsMixin
):

    # Getters

    def test_task_has_no_due_date_time_by_default(self):
        self.assertEqual(date.DateTime(), self.task.dueDateTime())

    def test_task_has_no_recursive_due_date_time_by_default(self):
        self.assertEqual(
            date.DateTime(), self.task.dueDateTime(recursive=True)
        )

    def test_task_has_no_planned_start_date_time_by_default(self):
        self.assertEqual(date.DateTime(), self.task.plannedStartDateTime())

    def test_task_has_no_recursive_planned_start_date_time_by_default(self):
        self.assertEqual(
            date.DateTime(), self.task.plannedStartDateTime(recursive=True)
        )

    def test_task_has_no_actual_start_date_time_by_default(self):
        self.assertEqual(date.DateTime(), self.task.actualStartDateTime())

    def test_task_has_no_recursive_actual_start_date_time_by_default(self):
        self.assertEqual(
            date.DateTime(), self.task.actualStartDateTime(recursive=True)
        )

    def test_task_has_no_completion_date_time_by_default(self):
        self.assertEqual(date.DateTime(), self.task.completionDateTime())

    def test_task_has_no_recursive_completion_date_time_by_default(self):
        self.assertEqual(
            date.DateTime(), self.task.completionDateTime(recursive=True)
        )

    def test_task_is_not_completed_by_default(self):
        self.assertFalse(self.task.completed())

    def test_task_is_not_active_by_default(self):
        self.assertFalse(self.task.active())

    def test_task_is_inactive_by_default(self):
        self.assertTrue(self.task.inactive())

    def test_task_is_not_due_soon_by_default(self):
        self.assertFalse(self.task.dueSoon())

    def test_task_has_no_description_by_default(self):
        self.assertEqual("", self.task.description())

    def test_task_has_no_children_by_default_so_not_all_children_are_completed(
        self,
    ):
        self.assertFalse(self.task.allChildrenCompleted())

    def test_task_has_no_effort_by_default(self):
        zero = date.TimeDelta()
        for recursive in False, True:
            self.assertEqual(zero, self.task.timeSpent(recursive=recursive))

    def test_task_priority_is_zero_by_default(self):
        for recursive in False, True:
            self.assertEqual(0, self.task.priority(recursive=recursive))

    def test_task_has_no_reminder_set_by_default(self):
        self.assertReminder(date.DateTime())

    def test_task_has_no_recursive_reminder_by_default(self):
        self.assertReminder(date.DateTime(), recursive=True)

    def test_should_mark_task_completed_is_undecided_by_default(self):
        self.assertEqual(
            None, self.task.shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def test_task_has_no_attachments_by_default(self):
        self.assertEqual([], self.task.attachments())

    def test_task_has_no_fixed_fee_by_default(self):
        for recursive in False, True:
            self.assertEqual(0, self.task.fixedFee(recursive=recursive))

    def test_task_has_no_revenue_by_default(self):
        for recursive in False, True:
            self.assertEqual(0, self.task.revenue(recursive=recursive))

    def test_task_has_no_hourly_fee_by_default(self):
        for recursive in False, True:
            self.assertEqual(0, self.task.hourlyFee(recursive=recursive))

    def test_task_does_not_recur_by_default(self):
        self.assertFalse(self.task.recurrence())

    def test_task_does_not_have_notes_by_default(self):
        self.assertFalse(self.task.notes())

    def test_percentage_complete_is_zero_by_default(self):
        self.assertEqual(0, self.task.percentageComplete())

    def test_default_color(self):
        self.assertEqual(None, self.task.foregroundColor())

    def test_default_own_icon(self):
        self.assertEqual("", self.task.icon_id())

    def test_default_recursive_icon(self):
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_default_prerequisites(self):
        self.assertFalse(self.task.prerequisites())

    def test_default_recursive_prerequisites(self):
        self.assertFalse(self.task.prerequisites(recursive=True))

    def test_default_dependencies(self):
        self.assertFalse(self.task.dependencies())

    def test_default_recursive_dependencies(self):
        self.assertFalse(self.task.dependencies(recursive=True))

    # Setters

    def test_set_planned_start_date_time(self):
        self.task.set_planned_start_date_time(self.yesterday)
        for recursive in (False, True):
            self.assertEqual(
                self.yesterday,
                self.task.plannedStartDateTime(recursive=recursive),
            )

    def test_set_planned_start_date_time_notification(self):
        self.record_changes(task.Task.plannedStartDateTimeChangedEventType())
        self.task.set_planned_start_date_time(self.yesterday)
        self.assertEqual((self.yesterday, self.task), self.changes[0])

    def test_set_planned_start_date_time_unchanged_causes_no_notification(
        self,
    ):
        self.record_changes(task.Task.plannedStartDateTimeChangedEventType())
        self.task.set_planned_start_date_time(self.task.plannedStartDateTime())
        self.assertFalse(self.changes)

    def test_set_future_planned_start_date_time_changes_icon(self):
        self.task.set_planned_start_date_time(self.tomorrow)
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_changed_after_set_planned_start_date_time_has_passed(self):
        self.task.set_planned_start_date_time(self.tomorrow)
        now = self.tomorrow + date.ONE_SECOND
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        self.assertEqual(
            task.late.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_set_actual_start_date_time(self):
        self.task.set_actual_start_date_time(self.yesterday)
        for recursive in (False, True):
            self.assertEqual(
                self.yesterday,
                self.task.actualStartDateTime(recursive=recursive),
            )

    def test_set_actual_start_date_time_notification(self):
        self.record_changes(task.Task.actualStartDateTimeChangedEventType())
        self.task.set_actual_start_date_time(self.yesterday)
        self.assertEqual((self.yesterday, self.task), self.changes[0])

    def test_set_actual_start_date_time_unchanged_causes_no_notification(self):
        self.record_changes(task.Task.actualStartDateTimeChangedEventType())
        self.task.set_actual_start_date_time(self.task.actualStartDateTime())
        self.assertFalse(self.changes)

    def test_set_due_date_time(self):
        self.task.set_due_date_time(self.tomorrow)
        for recursive in (False, True):
            self.assertEqual(
                self.tomorrow, self.task.dueDateTime(recursive=recursive)
            )

    def test_set_due_date_time_notification(self):
        self.record_changes(task.Task.dueDateTimeChangedEventType())
        self.task.set_due_date_time(self.tomorrow)
        self.assertEqual((self.tomorrow, self.task), self.changes[0])

    def test_set_due_date_time_unchanged_causes_no_notification(self):
        self.record_changes(task.Task.dueDateTimeChangedEventType())
        self.task.set_due_date_time(self.task.dueDateTime())
        self.assertFalse(self.changes)

    def test_icon_changed_after_set_due_date_time_has_passed(self):
        self.task.set_due_date_time(self.tomorrow)
        now = self.tomorrow + date.ONE_SECOND
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        self.assertEqual(
            task.overdue.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_changed_after_task_has_become_due_soon(self):
        settings.set("behavior", "duesoonhours", 1)
        self.task.set_due_date_time(self.tomorrow)
        now = self.tomorrow + date.ONE_SECOND - date.ONE_HOUR
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        self.assertEqual(
            task.duesoon.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_changes_when_new_due_soon_setting_makes_task_due_soon(
        self,
    ):
        self.task.set_due_date_time(self.tomorrow)
        settings.set("behavior", "duesoonhours", 1)
        now = self.tomorrow + date.ONE_SECOND - date.ONE_HOUR
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        self.assertEqual(
            task.duesoon.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_set_completion_date_time(self):
        now = date.Now()
        self.task.set_completion_date_time(now)
        for recursive in (False, True):
            self.assertEqual(
                now, self.task.completionDateTime(recursive=recursive)
            )

    def test_set_completion_date_time_notification(self):
        self.record_changes(task.Task.completionDateTimeChangedEventType())
        now = date.Now()
        self.task.set_completion_date_time(now)
        self.assertEqual([(now, self.task)], self.changes)

    def test_set_completion_date_time_unchanged_causes_no_notification(self):
        self.record_changes(task.Task.completionDateTimeChangedEventType())
        self.task.set_completion_date_time(date.DateTime())
        self.assertFalse(self.changes)

    def test_set_completion_date_time_makes_task_completed(self):
        self.task.set_completion_date_time()
        self.assertTrue(self.task.completed())

    def test_set_completion_date_time_defaults_to_now(self):
        self.task.set_completion_date_time()
        self.assertAlmostEqual(
            date.Now().toordinal(), self.task.completionDateTime().toordinal()
        )

    def test_set_percentage_complete(self):
        self.task.setPercentageComplete(50)
        self.assertEqual(50, self.task.percentageComplete())

    def test_set_percentage_complete_with_mark_parent_completed_on(
        self,
    ):
        self.task.set_should_mark_completed_when_all_children_completed(True)
        self.task.setPercentageComplete(50)
        self.assertEqual(50, self.task.percentageComplete())

    def test_set_100_percent_complete(self):
        self.task.setPercentageComplete(100)
        self.assertTrue(self.task.completed())

    def test_percentage_complete_notification_via_completion_date_time(self):
        self.record_changes(task.Task.percentageCompleteChangedEventType())
        self.task.set_completion_date_time()
        self.assertEqual([(100, self.task)], self.changes)

    def test_set_percentage_complete_sets_actual_start_date_time(self):
        self.task.setPercentageComplete(50)
        self.assertNotEqual(date.DateTime(), self.task.actualStartDateTime())

    def test_set_percentage_complete_to_zero_sets_no_actual_start(
        self,
    ):
        self.task.setPercentageComplete(50)
        self.task.set_actual_start_date_time(date.DateTime())
        self.task.setPercentageComplete(0)
        self.assertEqual(date.DateTime(), self.task.actualStartDateTime())

    def test_set_description(self):
        self.task.setDescription("A new description")
        self.assertEqual("A new description", self.task.description())

    def test_set_description_notification(self):
        self.registerObserver(task.Task.descriptionChangedEventType())
        self.task.setDescription("A new description")
        self.assertTrue("A new description", self.events[0].value())

    def test_set_description_unchanged_causes_no_notification(self):
        self.registerObserver(task.Task.descriptionChangedEventType())
        self.task.setDescription(self.task.description())
        self.assertFalse(self.events)

    def test_set_budget(self):
        budget = date.ONE_HOUR
        self.task.set_budget(budget)
        self.assertEqual(budget, self.task.budget())

    def test_set_budget_notification(self):
        self.record_changes(task.Task.budgetChangedEventType())
        budget = date.ONE_HOUR
        self.task.set_budget(budget)
        self.assertEqual([(budget, self.task)], self.changes)

    def test_set_budget_unchanged_causes_no_notification(self):
        self.record_changes(task.Task.budgetChangedEventType())
        self.task.set_budget(self.task.budget())
        self.assertFalse(self.changes)

    def test_set_priority(self):
        self.task.setPriority(10)
        self.assertEqual(10, self.task.priority())

    def test_set_priority_causes_notification(self):
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task.setPriority(10)
        self.assertIn(self.task, self.events[0].sources())

    def test_set_priority_unchanged_causes_no_notification(self):
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task.setPriority(self.task.priority())
        self.assertFalse(self.events)

    def test_negative_priority(self):
        self.task.setPriority(-1)
        self.assertEqual(-1, self.task.priority())

    def test_set_fixed_fee(self):
        self.task.set_fixed_fee(1000)
        self.assertEqual(1000, self.task.fixedFee())

    def test_set_fixed_fee_unchanged_causes_no_notification(self):
        self.record_changes(task.Task.fixedFeeChangedEventType())
        self.task.set_fixed_fee(self.task.fixedFee())
        self.assertFalse(self.changes)

    def test_set_fixed_fee_causes_notification(self):
        self.record_changes(task.Task.fixedFeeChangedEventType())
        self.task.set_fixed_fee(1000)
        self.assertEqual([(1000, self.task)], self.changes)

    def test_planned_duration_change_is_a_publisher_event(self):
        self.record_changes(task.Task.plannedDurationChangedEventType())
        self.task.setPlannedDuration(date.ONE_HOUR)
        self.assertEqual([(date.ONE_HOUR, self.task)], self.changes)

    def test_mark_completed_setting_change_sets_the_modification_date(self):
        before = date.Now()
        self.task.set_should_mark_completed_when_all_children_completed(True)
        self.assertTrue(before <= self.task.modificationDateTime())

    def test_budget_change_sets_the_modification_date(self):
        before = date.Now()
        self.task.set_budget(date.ONE_HOUR)
        self.assertTrue(before <= self.task.modificationDateTime())

    def test_fee_change_sets_the_modification_date(self):
        before = date.Now()
        self.task.set_fixed_fee(1000)
        self.assertTrue(before <= self.task.modificationDateTime())
        self.task.set_modification_datetime(date.DateTime.min)
        self.task.set_hourly_fee(100)
        self.assertTrue(before <= self.task.modificationDateTime())

    def test_set_fixed_fee_causes_revenue_change_notification(self):
        events = test.ChangeRecorder(task.Task.revenueChangedEventType())
        self.task.set_fixed_fee(1000)
        self.assertEqual([(1000, self.task)], events)

    def test_set_hourly_fee_via_setter(self):
        self.task.set_hourly_fee(100)
        self.assertEqual(100, self.task.hourlyFee())

    def test_set_hourly_fee_causes_notification(self):
        self.record_changes(task.Task.hourlyFeeChangedEventType())
        self.task.set_hourly_fee(100)
        self.assertEqual([(100, self.task)], self.changes)

    def test_set_recurrence(self):
        self.task.set_recurrence(date.Recurrence("weekly"))
        self.assertEqual(date.Recurrence("weekly"), self.task.recurrence())

    def test_set_recurrence_causes_notification(self):
        self.registerObserver(task.Task.recurrenceChangedEventType())
        self.task.set_recurrence(date.Recurrence("weekly"))
        self.assertEqual([{self.task}], [e.sources() for e in self.events])

    def test_recurrence_change_sets_the_modification_date(self):
        before = date.Now()
        self.task.set_recurrence(date.Recurrence("weekly"))
        self.assertTrue(before <= self.task.modificationDateTime())

    # Add child

    def test_add_child_notification(self):
        self.registerObserver(task.Task.addChildEventType())
        child = task.Task()
        self.task.addChild(child)
        self.assertEqual(child, self.events[0].value())

    def test_add_completed_child_as_only_child_makes_parent_completed(self):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        child = task.Task(completionDateTime=self.yesterday)
        self.task.addChild(child)
        self.assertTrue(self.task.completed())

    def test_add_active_child_makes_parent_active(self):
        self.task.set_completion_date_time()
        child = task.Task()
        self.task.addChild(child)
        self.assertFalse(self.task.completed())

    def test_add_child_with_later_due_keeps_parent_due(
        self,
    ):
        self.task.set_due_date_time(self.tomorrow)
        child = task.Task(dueDateTime=date.Now() + date.ONE_HOUR)
        self.task.addChild(child)
        self.assertEqual(self.tomorrow, self.task.dueDateTime())
        self.assertEqual(
            child.dueDateTime(), self.task.dueDateTime(recursive=True)
        )

    def test_add_child_without_due_keeps_parent_due(
        self,
    ):
        due_date_time = date.Now() + date.ONE_HOUR
        self.task.set_due_date_time(due_date_time)
        child = task.Task()
        self.task.addChild(child)
        self.assertEqual(due_date_time, self.task.dueDateTime())

    def test_add_child_with_earlier_planned_start_keeps_parent_planned_start(
        self,
    ):
        original_planned_start_date_time = self.task.plannedStartDateTime()
        child = task.Task(plannedStartDateTime=self.yesterday)
        self.task.addChild(child)
        self.assertEqual(
            original_planned_start_date_time, self.task.plannedStartDateTime()
        )
        self.assertEqual(
            self.yesterday, self.task.plannedStartDateTime(recursive=True)
        )
        self.assertEqual(self.yesterday, child.plannedStartDateTime())

    def test_add_child_with_earlier_actual_start_keeps_parent_actual_start(
        self,
    ):
        original_actual_start_date_time = self.task.actualStartDateTime()
        child = task.Task(actualStartDateTime=self.yesterday)
        self.task.addChild(child)
        self.assertEqual(
            original_actual_start_date_time, self.task.actualStartDateTime()
        )
        self.assertEqual(
            self.yesterday, self.task.actualStartDateTime(recursive=True)
        )
        self.assertEqual(self.yesterday, child.actualStartDateTime())

    def test_active_recurring_child_earlier_planned_start_leaves_parent(
        self,
    ):
        original_planned_start_date_time = self.task.plannedStartDateTime()
        child = task.Task(plannedStartDateTime=self.yesterday)
        child.set_recurrence(date.Recurrence("monthly"))
        self.task.addChild(child)
        self.assertEqual(
            original_planned_start_date_time, self.task.plannedStartDateTime()
        )
        self.assertEqual(
            self.yesterday, self.task.plannedStartDateTime(recursive=True)
        )
        self.assertEqual(self.yesterday, child.plannedStartDateTime())

    def test_active_recurring_child_earlier_actual_start_leaves_parent(
        self,
    ):
        original_actual_start_date_time = self.task.actualStartDateTime()
        child = task.Task(actualStartDateTime=self.yesterday)
        child.set_recurrence(date.Recurrence("monthly"))
        self.task.addChild(child)
        self.assertEqual(
            original_actual_start_date_time, self.task.actualStartDateTime()
        )
        self.assertEqual(
            self.yesterday, self.task.actualStartDateTime(recursive=True)
        )
        self.assertEqual(self.yesterday, child.actualStartDateTime())

    def test_add_child_with_budget_causes_budget_notification(self):
        child = task.Task()
        child.set_budget(date.TimeDelta(100))
        self.record_changes(task.Task.budgetChangedEventType())
        self.task.addChild(child)
        self.assertEqual([(date.TimeDelta(), self.task)], self.changes)

    def test_add_child_without_budget_causes_no_budget_notification(self):
        self.record_changes(task.Task.budgetChangedEventType())
        child = task.Task()
        self.task.addChild(child)
        self.assertFalse(self.changes)

    def test_add_child_with_effort_causes_budget_left_notification(self):
        self.task.set_budget(date.TimeDelta(hours=100))
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        child = task.Task()
        child.addEffort(
            effort.Effort(
                child,
                date.DateTime(2000, 1, 1, 10, 0, 0),
                date.DateTime(2000, 1, 1, 11, 0, 0),
            )
        )
        self.task.addChild(child)
        self.assertTrue((date.TimeDelta(hours=100), self.task) in events)

    def test_add_child_without_effort_causes_no_budget_left_notification(self):
        self.task.set_budget(date.TimeDelta(hours=100))
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.task.addChild(task.Task())
        self.assertFalse(events)

    def test_adding_child_effort_without_any_budget_sends_budget_left(self):
        # Budget left is the budget less the time spent, with or without
        # a budget (docs/TASK_FIELDS.md)
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        child = task.Task()
        child.addEffort(
            effort.Effort(
                child,
                date.DateTime(2000, 1, 1, 10, 0, 0),
                date.DateTime(2000, 1, 1, 11, 0, 0),
            )
        )
        self.task.addChild(child)
        self.assertEqual(
            ([(date.TimeDelta(), self.task)], -date.ONE_HOUR),
            (events, self.task.budgetLeft(recursive=True)),
        )

    def test_add_child_with_budget_causes_budget_left_notification(self):
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.task.addChild(task.Task(budget=date.TimeDelta(hours=100)))
        self.assertEqual([(date.TimeDelta(), self.task)], events)

    def test_add_child_with_effort_causes_time_spent_notification(self):
        child = task.Task()
        child_effort = effort.Effort(
            child,
            date.DateTime(2000, 1, 1, 10, 0, 0),
            date.DateTime(2000, 1, 1, 11, 0, 0),
        )
        child.addEffort(child_effort)
        events = test.ChangeRecorder(task.Task.timeSpentChangedEventType())
        self.task.addChild(child)
        self.assertEqual([(self.task.timeSpent(), self.task)], events)

    def test_add_child_without_effort_causes_no_time_spent_notification(self):
        events = test.ChangeRecorder(task.Task.timeSpentChangedEventType())
        self.task.addChild(task.Task())
        self.assertFalse(events)

    def test_add_child_with_higher_priority_causes_priority_notification(self):
        self.registerObserver(task.Task.priorityChangedEventType())
        child = task.Task(priority=10)
        self.task.addChild(child)
        self.assertIn(self.task, self.events[0].sources())

    def test_add_child_with_lower_priority_causes_no_priority_notification(
        self,
    ):
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task.addChild(task.Task(priority=-10))
        self.assertFalse(self.events)

    def test_add_child_with_revenue_causes_revenue_notification(self):
        events = test.ChangeRecorder(task.Task.revenueChangedEventType())
        self.task.addChild(task.Task(fixedFee=1000))
        self.assertEqual([(0, self.task)], events)

    def test_add_child_without_revenue_causes_no_revenue_notification(self):
        events = test.ChangeRecorder(task.Task.revenueChangedEventType())
        self.task.addChild(task.Task())
        self.assertFalse(events)

    def test_add_tracked_child_causes_start_tracking_notification(self):
        child = task.Task()
        child.addEffort(effort.Effort(child))
        events = test.ChangeRecorder(self.task.trackingChangedEventType())
        self.task.addChild(child)
        self.assertEqual([(True, self.task)], events)

    def test_child_with_two_tracked_efforts_sends_one_start_tracking(
        self,
    ):
        child = task.Task()
        child.addEffort(effort.Effort(child))
        child.addEffort(effort.Effort(child))
        events = test.ChangeRecorder(self.task.trackingChangedEventType())
        self.task.addChild(child)
        self.assertEqual([(True, self.task)], events)

    # Constructor

    def test_new_child_with_subject(self):
        child = self.task.newChild(subject="Test")
        self.assertEqual("Test", child.subject())

    # Add effort

    def test_add_effort_causes_no_budget_left_notification(self):
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.task.addEffort(effort.Effort(self.task))
        self.assertFalse(events)

    def test_add_active_effort_causes_start_tracking_notification(self):
        events = test.ChangeRecorder(self.task.trackingChangedEventType())
        active_effort = effort.Effort(self.task)
        self.task.addEffort(active_effort)
        self.assertEqual([(True, self.task)], events)

    def test_add_effort_set_actual_start_date_time(self):
        now = date.Now()
        self.task.addEffort(effort.Effort(self.task, now))
        self.assertEqual(now, self.task.actualStartDateTime())

    # Notes:

    def test_add_note(self):
        a_note = note.Note()
        self.task.addNote(a_note)
        self.assertEqual([a_note], self.task.notes())

    def test_add_note_causes_notification(self):
        event_type = task.Task.notesChangedEventType()  # pylint: disable=E1101
        self.registerObserver(event_type)
        a_note = note.Note()
        self.task.addNote(a_note)
        self.assertEvent(event_type, self.task, a_note)

    # Prerequisites

    def test_add_one_prerequisite(self):
        prerequisites = set([task.Task()])
        self.task.add_prerequisites(prerequisites)
        self.assertEqual(prerequisites, self.task.prerequisites())

    def test_add_two_prerequisites(self):
        prerequisites = set([task.Task(), task.Task()])
        self.task.add_prerequisites(prerequisites)
        self.assertEqual(prerequisites, self.task.prerequisites())

    def test_add_prerequisite_causes_notification(self):
        event_type = task.Task.prerequisitesChangedEventType()
        self.registerObserver(event_type)
        self.task.add_prerequisites([task.Task()])
        self.assertEqual([{self.task}], self.sources_of(event_type))

    def test_prerequisite_change_sets_the_modification_date(self):
        before = date.Now()
        self.task.add_prerequisites([task.Task()])
        self.assertTrue(before <= self.task.modificationDateTime())

    def test_moving_a_subtask_sets_its_date_not_its_parents(self):
        parent = task.Task(modificationDateTime=date.DateTime(2020, 1, 1))
        child = task.Task(modificationDateTime=date.DateTime(2020, 1, 1))
        parent.addChild(child)
        self.assertEqual(
            date.DateTime(2020, 1, 1), parent.modificationDateTime()
        )
        self.assertTrue(
            date.DateTime(2020, 1, 1) < child.modificationDateTime()
        )

    def test_dependency_change_keeps_the_modification_date(self):
        # The reverse of a prerequisite: not the task's saved data
        before = self.task.modificationDateTime()
        self.task.add_dependencies([task.Task()])
        self.assertEqual(before, self.task.modificationDateTime())

    def test_remove_prerequisite_that_has_not_been_added(self):
        prerequisite = task.Task()
        self.task.remove_prerequisites([prerequisite])
        self.assertFalse(self.task.prerequisites())

    def test_add_prerequisite_keeps_task_inactive(self):
        prerequisites = set([task.Task()])
        self.task.add_prerequisites(prerequisites)
        self.assertTrue(self.task.inactive())

    def test_add_prerequisite_keeps_actual_start_date_time(self):
        # The reset was removed on purpose in #257 (date status fixes)
        now = date.Now()
        self.task.set_actual_start_date_time(now)
        self.task.add_prerequisites([task.Task()])
        self.assertEqual(now, self.task.actualStartDateTime())

    # Dependencies

    def test_add_one_dependency(self):
        dependencies = set([task.Task()])
        self.task.add_dependencies(dependencies)
        self.assertEqual(dependencies, self.task.dependencies())

    def test_add_two_dependencies(self):
        dependencies = set([task.Task(), task.Task()])
        self.task.add_dependencies(dependencies)
        self.assertEqual(dependencies, self.task.dependencies())

    def test_add_dependency_causes_notification(self):
        event_type = task.Task.dependenciesChangedEventType()
        self.registerObserver(event_type)
        self.task.add_dependencies([task.Task()])
        self.assertEqual([{self.task}], self.sources_of(event_type))

    def test_remove_dependency_that_has_not_been_added(self):
        dependency = task.Task()
        self.task.remove_dependencies([dependency])
        self.assertFalse(self.task.dependencies())

    def test_modification_event_types(self):  # pylint: disable=E1003
        self.assertEqual(
            super(task.Task, self.task).modificationEventTypes()
            + [
                task.Task.plannedStartDateTimeChangedEventType(),
                task.Task.dueDateTimeChangedEventType(),
                task.Task.actualStartDateTimeChangedEventType(),
                task.Task.completionDateTimeChangedEventType(),
                task.Task.effortsChangedEventType(),
                task.Task.budgetChangedEventType(),
                task.Task.percentageCompleteChangedEventType(),
                task.Task.priorityChangedEventType(),
                task.Task.hourlyFeeChangedEventType(),
                task.Task.fixedFeeChangedEventType(),
                task.Task.reminderChangedEventType(),
                task.Task.recurrenceChangedEventType(),
                task.Task.prerequisitesChangedEventType(),
                task.Task.dependenciesChangedEventType(),
                task.Task.shouldMarkCompletedWhenAllChildrenCompletedChangedEventType(),
                task.Task.plannedDurationChangedEventType(),
                task.Task.plannedDurationModeChangedEventType(),
            ],
            self.task.modificationEventTypes(),
        )


class TimerSecondsTest(TaskTestCase):
    """Each timer second is the first second at which a rule of
    compute_status() or processReminder() holds
    (docs/MASTER_SCHEDULER_REFACTOR.md)."""

    moment = date.DateTime(2026, 9, 27, 12, 0, 0)

    def setUp(self):
        super().setUp()
        self.hours = settings.get("behavior", "duesoonhours")

    def status_at(self, moment):
        self.task.compute_stored_status(moment)
        return self.task.computedStatus()

    def assert_starts_at(self, expected_status, second):
        before = second - date.ONE_SECOND
        self.assertNotEqual(expected_status, self.status_at(before))
        self.assertEqual(expected_status, self.status_at(second))

    def timer_second(self, rule):
        return self.task.timer_seconds(self.hours)[rule]

    def test_late_from_the_second_after_the_planned_start(self):
        self.task.set_planned_start_date_time(self.moment)
        self.assertEqual(
            self.moment + date.ONE_SECOND, self.timer_second("late")
        )
        self.assert_starts_at(task.status.late, self.timer_second("late"))

    def test_active_from_the_actual_start(self):
        self.task.set_actual_start_date_time(self.moment)
        self.assertEqual(self.moment, self.timer_second("active"))
        self.assert_starts_at(task.status.active, self.timer_second("active"))

    def test_due_soon_from_the_second_after_due_less_the_hours(self):
        self.task.set_due_date_time(self.moment)
        due_soon = self.moment - date.TimeDelta(hours=self.hours)
        self.assertEqual(
            due_soon + date.ONE_SECOND, self.timer_second("duesoon")
        )
        self.assert_starts_at(
            task.status.duesoon, self.timer_second("duesoon")
        )

    def test_overdue_from_the_second_after_the_due(self):
        self.task.set_due_date_time(self.moment)
        self.assertEqual(
            self.moment + date.ONE_SECOND, self.timer_second("overdue")
        )
        self.assert_starts_at(
            task.status.overdue, self.timer_second("overdue")
        )

    def test_reminder_fires_from_its_second(self):
        self.task.set_reminder(self.moment)
        second = self.timer_second("reminder")
        self.registerObserver("task.reminder.trigger")
        self.task.processReminder(second - date.ONE_SECOND)
        self.assertEqual([], self.events)
        self.task.processReminder(second)
        self.assertEqual(1, len(self.events))

    def test_dates_not_set_give_no_seconds(self):
        self.assertEqual({}, self.task.timer_seconds(self.hours))

    def test_a_completed_task_keeps_its_seconds(self):
        self.task.set_due_date_time(self.moment)
        self.task.set_completion_date_time(self.moment)
        self.assertEqual(
            self.moment + date.ONE_SECOND, self.timer_second("overdue")
        )


class NotSetIsTheLatestDateTest(TaskTestCase):
    """A date not set is the latest date, never None
    (docs/ATTRIBUTE_PATTERN.md)."""

    def test_date_setters_take_none_as_not_set(self):
        for setter, getter in (
            ("set_planned_start_date_time", "plannedStartDateTime"),
            ("set_due_date_time", "dueDateTime"),
            ("set_actual_start_date_time", "actualStartDateTime"),
            ("set_reminder", "reminder"),
        ):
            getattr(self.task, setter)(date.Now())
            getattr(self.task, setter)(None)
            self.assertEqual(date.DateTime(), getattr(self.task, getter)())

    def test_reminder_of_a_tree_without_any_is_the_latest_date(self):
        self.task.addChild(task.Task(subject="child"))
        self.assertEqual(date.DateTime(), self.task.reminder(recursive=True))

    def test_clearing_an_unset_reminder_sends_nothing(self):
        self.record_changes(self.task.reminderChangedEventType())
        self.task.set_reminder(None)
        self.assertEqual([], self.changes)


class TaskDueTodayTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        self.dueDateTime = date.Now() + date.ONE_HOUR  # pylint: disable=W0201
        return [{"dueDateTime": self.dueDateTime}]

    def test_is_due_soon(self):
        self.assertTrue(self.task.dueSoon())

    def test_days_left(self):
        self.assertEqual(0, self.task.timeLeft().days)

    def test_due_date_time(self):
        self.assertAlmostEqual(
            self.dueDateTime.toordinal(), self.task.dueDateTime().toordinal()
        )

    def test_default_due_soon_color(self):
        expected_color = wx.Colour(*settings.get("fgcolor", "duesoontasks"))
        self.assertEqual(
            expected_color, test.styled(self.task).shown_fg_color()
        )

    def test_color_when_task_has_own_color(self):
        color = wx.Colour(191, 128, 64, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, test.styled(self.task).shown_fg_color())

    def test_icon(self):
        self.assertEqual(
            task.duesoon.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_after_changing_due_soon_hours(self):
        settings.set("behavior", "duesoonhours", 0)
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_changing_due_soon_hours(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        settings.set("behavior", "duesoonhours", 0)
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)

    def test_icon_after_due_date_time_has_passed(self):
        now = self.task.dueDateTime() + date.ONE_SECOND
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        self.assertEqual(
            task.overdue.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_due_date_time_has_passed(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        now = self.task.dueDateTime() + date.ONE_SECOND
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)


class TaskDueTomorrowTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"dueDateTime": self.tomorrow.endOfDay()}]

    def test_days_left(self):
        self.assertEqual(1, self.task.timeLeft().days)

    def test_due_date_time(self):
        self.assertAlmostEqual(
            self.taskCreationKeywordArguments()[0]["dueDateTime"].toordinal(),
            self.task.dueDateTime().toordinal(),
        )

    def test_due_soon(self):
        self.assertFalse(self.task.dueSoon())

    def test_due_soon_2days(self):
        settings.set("behavior", "duesoonhours", 48)
        self.assertTrue(self.task.dueSoon())

    def test_icon_not_due_soon(self):
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_due_soon(self):
        settings.set("behavior", "duesoonhours", 48)
        self.assertEqual(
            task.duesoon.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_changing_due_soon_hours(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        settings.set("behavior", "duesoonhours", 48)
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)


class OverdueTaskTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"dueDateTime": self.yesterday}]

    def test_is_overdue(self):
        self.assertTrue(self.task.overdue())

    def test_completed_overdue_task_is_no_longer_overdue(self):
        self.task.set_completion_date_time()
        self.assertFalse(self.task.overdue())

    def test_due_date_time(self):
        self.assertAlmostEqual(
            self.taskCreationKeywordArguments()[0]["dueDateTime"].toordinal(),
            self.task.dueDateTime().toordinal(),
        )

    def test_default_overdue_color(self):
        expected_color = wx.Colour(*settings.get("fgcolor", "overduetasks"))
        self.assertEqual(
            expected_color, test.styled(self.task).shown_fg_color()
        )

    def test_color_when_task_has_own_color(self):
        color = wx.Colour(191, 64, 64, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, test.styled(self.task).shown_fg_color())

    def test_icon(self):
        self.assertEqual(
            task.overdue.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_after_changing_due_date_time(self):
        self.task.set_due_date_time(date.Now() + date.TimeDelta(hours=72))
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_changing_due_date_time(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        self.task.set_due_date_time(date.Now() + date.TimeDelta(hours=72))
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)

    def test_icon_after_marking_complete(self):
        self.task.set_completion_date_time()
        self.assertEqual(
            task.completed.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_marking_complete(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        self.task.set_completion_date_time()
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)


class CompletedTaskTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"completionDateTime": date.Now()}]

    def test_a_task_with_a_completion_date_is_completed(self):
        self.assertTrue(self.task.completed())

    def test_setting_completion_date_time_to_infinite_makes_task_uncompleted(
        self,
    ):
        self.task.set_completion_date_time(date.DateTime())
        self.assertFalse(self.task.completed())
        self.assertEqual(0, self.task.percentageComplete())

    def test_changing_completion_date_leaves_task_completed(
        self,
    ):
        self.task.set_completion_date_time(self.yesterday)
        self.assertTrue(self.task.completed())

    def test_completed_task_is_hundred_procent_complete(self):
        self.assertEqual(100, self.task.percentageComplete())

    def test_set_percentage_complete_to_less_than_100_makes_task_uncompleted(
        self,
    ):
        self.task.setPercentageComplete(99)
        self.assertEqual(date.DateTime(), self.task.completionDateTime())
        self.assertEqual(99, self.task.percentageComplete())

    def test_percentage_complete_notification(self):
        self.record_changes(task.Task.percentageCompleteChangedEventType())
        self.task.set_completion_date_time(date.DateTime.max)
        self.assertEqual([(0, self.task)], self.changes)

    def test_default_completed_color(self):
        expected_color = wx.Colour(*settings.get("fgcolor", "completedtasks"))
        self.assertEqual(
            expected_color, test.styled(self.task).shown_fg_color()
        )

    def test_color_when_task_has_own_color(self):
        color = wx.Colour(64, 191, 64, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, test.styled(self.task).shown_fg_color())

    def test_icon(self):
        self.assertEqual(
            task.completed.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_after_marking_uncomplete(self):
        self.task.set_completion_date_time(date.DateTime.max)
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_marking_uncomplete(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        self.task.set_completion_date_time(date.DateTime.max)
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)


class HundredProcentCompletedTaskTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"percentageComplete": 100}]

    def test_a_hundred_procent_complete_task_is_completed(self):
        self.assertTrue(self.task.completed())


class TaskCompletedInTheFutureTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"completionDateTime": self.tomorrow}]

    def test_a_task_with_a_future_completion_date_is_completed(self):
        self.assertTrue(self.task.completed())


class TaskWithPlannedStartDateInTheFutureTest(
    TaskTestCase, CommonTaskTestsMixin
):
    def taskCreationKeywordArguments(self):
        return [
            {"plannedStartDateTime": self.tomorrow},
            {"subject": "prerequisite"},
        ]

    def test_task_with_start_date_in_the_future_is_inactive(self):
        self.assertTrue(self.task.inactive())

    def test_task_with_future_planned_start_inactive_with_prerequisites_done(
        self,
    ):
        # pylint: disable=E1101
        self.task.add_prerequisites([self.task2])
        self.task2.add_dependencies([self.task])
        self.task2.set_completion_date_time()
        self.assertTrue(self.task.inactive())

    def test_completed_task_with_future_planned_start_is_not_inactive(
        self,
    ):
        self.task.set_completion_date_time()
        self.assertFalse(self.task.inactive())

    def test_planned_start_date_time(self):
        self.assertEqual(self.tomorrow, self.task.plannedStartDateTime())

    def test_set_actual_start_date_time_to_today_makes_task_active(self):
        self.task.set_actual_start_date_time(date.Now())
        self.assertTrue(self.task.active())

    def test_default_inactive_color(self):
        expected_color = wx.Colour(*settings.get("fgcolor", "inactivetasks"))
        self.assertEqual(
            expected_color, test.styled(self.task).shown_fg_color()
        )

    def test_color_when_task_has_own_color(self):
        color = wx.Colour(160, 160, 160, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, test.styled(self.task).shown_fg_color())

    def test_icon(self):
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_after_planned_start_date_time_has_passed(self):
        now = self.task.plannedStartDateTime() + date.ONE_SECOND
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.run_scheduler_tick(self.task)
        self.assertEqual(
            task.late.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_planned_start_date_time_has_passed(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        now = self.task.plannedStartDateTime() + date.ONE_SECOND
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)

    def test_icon_after_marking_complete(self):
        self.task.set_completion_date_time()
        self.assertEqual(
            task.completed.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_marking_complete(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        self.task.set_completion_date_time()
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)

    def test_icon_after_changing_planned_start_date_time(self):
        self.task.set_planned_start_date_time(
            date.Now() - date.TimeDelta(hours=72)
        )
        self.assertEqual(
            task.late.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_changing_planned_start_date_time(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        self.task.set_planned_start_date_time(
            date.Now() - date.TimeDelta(hours=72)
        )
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)


class TaskWithPlannedStartDateInThePastTest(
    TaskTestCase, CommonTaskTestsMixin
):
    def taskCreationKeywordArguments(self):
        return [
            {"plannedStartDateTime": date.DateTime(2000, 1, 1)},
            {"subject": "prerequisite"},
        ]

    def test_task_with_planned_start_date_time_in_the_past_is_active(self):
        self.assertFalse(self.task.inactive())

    def test_task_becomes_inactive_when_adding_an_uncompleted_prerequisite(
        self,
    ):
        # pylint: disable=E1101
        self.task.add_prerequisites([self.task2])
        self.task2.add_dependencies([self.task])
        self.assertTrue(self.task.inactive())

    def test_icon_event_when_adding_an_uncompleted_prerequisite(self):
        # pylint: disable=E1101
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        self.task.add_prerequisites([self.task2])
        self.task2.add_dependencies([self.task])
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)

    def test_task_becomes_active_when_uncompleted_prerequisite_is_completed(
        self,
    ):
        # pylint: disable=E1101
        self.task.add_prerequisites([self.task2])
        self.task2.add_dependencies([self.task])
        self.task2.set_completion_date_time()
        self.assertFalse(self.task.inactive())

    def test_icon_event_when_uncompleted_prerequisite_is_completed(self):
        # pylint: disable=E1101
        self.task.add_prerequisites([self.task2])
        self.task2.add_dependencies([self.task])
        test.styled(self.task)
        self.registerObserver(
            self.task.effectiveIconChangedEventType(), eventSource=self.task
        )
        self.task2.set_completion_date_time()
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)


class TaskWithoutPlannedStartDateTimeTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [
            {"plannedStartDateTime": date.DateTime()},
            {"subject": "prerequisite"},
        ]

    def test_task_without_planned_start_date_time_is_inactive(self):
        self.assertTrue(self.task.inactive())

    def test_task_stays_inactive_when_uncompleted_prerequisite_is_completed(
        self,
    ):
        # pylint: disable=E1101
        self.task.add_prerequisites([self.task2])
        self.task2.add_dependencies([self.task])
        self.task2.set_completion_date_time()
        self.assertTrue(self.task.inactive())
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_no_icon_event_when_uncompleted_prerequisite_is_completed(
        self,
    ):
        # pylint: disable=E1101
        self.task.add_prerequisites([self.task2])
        self.task2.add_dependencies([self.task])
        test.styled(self.task)
        self.registerObserver(
            self.task.effectiveIconChangedEventType(), eventSource=self.task
        )
        self.task2.set_completion_date_time()
        test.styled(self.task)
        self.assertFalse(self.events)


class InactiveTaskWithChildTest(TaskTestCase):
    def taskCreationKeywordArguments(self):
        return [
            {
                "plannedStartDateTime": self.tomorrow,
                "children": [task.Task(subject="child")],
            }
        ]

    def test_icon(self):
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_planned_start_date_time(self):
        for recursive in (False, True):
            self.assertEqual(
                self.tomorrow,
                self.task.plannedStartDateTime(recursive=recursive),
            )


class TaskWithSubject(TaskTestCase, CommonTaskTestsMixin):
    eventTypes = [task.Task.subjectChangedEventType()]

    def taskCreationKeywordArguments(self):
        return [{"subject": "Subject"}]

    def test_subject(self):
        self.assertEqual("Subject", self.task.subject())

    def test_set_subject(self):
        self.task.setSubject("Done")
        self.assertEqual("Done", self.task.subject())

    def test_set_subject_notification(self):
        self.task.setSubject("Done")
        self.assertEvent(
            task.Task.subjectChangedEventType(), self.task, "Done"
        )

    def test_set_subject_unchanged_does_not_trigger_notification(self):
        self.task.setSubject(self.task.subject())
        self.assertFalse(self.events)

    def test_representation_equals_subject(self):
        self.assertEqual(self.task.subject(), repr(self.task))


class TaskWithDescriptionTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"description": "Description"}]

    def test_description(self):
        self.assertEqual("Description", self.task.description())

    def test_set_description(self):
        self.task.setDescription("New description")
        self.assertEqual("New description", self.task.description())


# pylint: disable=E1101


class TwoTasksTest(TaskTestCase):
    def taskCreationKeywordArguments(self):
        return [{}, {}]

    def test_two_default_tasks_are_not_equal(self):
        self.assertNotEqual(self.task1, self.task2)


class NewChildTest(TaskTestCase):
    def setUp(self):
        super().setUp()
        self.child = self.task.newChild()

    def test_new_child_has_no_due_date_time_by_default(self):
        self.assertEqual(date.DateTime(), self.child.dueDateTime())

    def test_new_child_has_no_planned_start_date_time_by_default(self):
        self.assertEqual(date.DateTime(), self.child.plannedStartDateTime())

    def test_new_child_has_no_actual_start_date_time_by_default(self):
        self.assertEqual(date.DateTime(), self.child.actualStartDateTime())

    def test_new_child_has_no_completion_date_time_by_default(self):
        self.assertEqual(date.DateTime(), self.child.completionDateTime())

    def test_new_child_has_no_reminder_by_default(self):
        self.assertEqual(date.DateTime(), self.child.reminder())


class TaskWithChildTest(
    TaskTestCase, CommonTaskTestsMixin, NoBudgetTestsMixin
):
    def taskCreationKeywordArguments(self):
        now = date.Now() - date.ONE_SECOND
        return [
            {
                "plannedStartDateTime": now,
                "actualStartDateTime": now,
                "children": [
                    task.Task(
                        subject="child",
                        actualStartDateTime=now,
                        plannedStartDateTime=now,
                    )
                ],
            }
        ]

    def test_remove_child_notification(self):
        self.registerObserver(task.Task.removeChildEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEvent(
            task.Task.removeChildEventType(), self.task1, self.task1_1
        )

    def test_remove_non_existing_child_causes_no_notification(self):
        self.registerObserver(task.Task.removeChildEventType())
        self.task1.removeChild("Not a child")
        self.assertFalse(self.events)

    def test_remove_child_with_budget_causes_budget_notification(self):
        self.task1_1.set_budget(date.TimeDelta(hours=100))
        self.record_changes(task.Task.budgetChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual([(date.TimeDelta(), self.task1)], self.changes)

    def test_remove_child_with_budget_and_effort_causes_budget_notification(
        self,
    ):
        self.task1_1.set_budget(date.TimeDelta(hours=10))
        self.task1_1.addEffort(
            effort.Effort(
                self.task1_1,
                date.DateTime(2009, 1, 1, 1, 0, 0),
                date.DateTime(2009, 1, 1, 11, 0, 0),
            )
        )
        self.record_changes(task.Task.budgetChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual([(date.TimeDelta(), self.task1)], self.changes)

    def test_remove_child_without_budget_causes_no_budget_notification(self):
        self.record_changes(task.Task.budgetChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertFalse(self.changes)

    def test_removing_child_effort_from_task_with_budget_sends_budget_left(
        self,
    ):
        self.task1.set_budget(date.TimeDelta(hours=100))
        self.task1_1.addEffort(
            effort.Effort(
                self.task1_1,
                date.DateTime(2005, 1, 1, 11, 0, 0),
                date.DateTime(2005, 1, 1, 12, 0, 0),
            )
        )
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertTrue((date.TimeDelta(hours=100), self.task1) in events)

    def test_removing_child_effort_without_any_budget_sends_budget_left(self):
        # Budget left is the budget less the time spent, with or without
        # a budget (docs/TASK_FIELDS.md)
        self.task1_1.addEffort(
            effort.Effort(
                self.task1_1,
                date.DateTime(2005, 1, 1, 11, 0, 0),
                date.DateTime(2005, 1, 1, 12, 0, 0),
            )
        )
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual(
            ([(date.TimeDelta(), self.task1)], date.TimeDelta()),
            (events, self.task1.budgetLeft(recursive=True)),
        )

    def test_remove_child_with_effort_causes_time_spent_notification(self):
        child_effort = effort.Effort(
            self.task1_1,
            date.DateTime(2005, 1, 1, 11, 0, 0),
            date.DateTime(2005, 1, 1, 12, 0, 0),
        )
        self.task1_1.addEffort(child_effort)
        events = test.ChangeRecorder(task.Task.timeSpentChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual(
            [(self.task1.timeSpent(recursive=True), self.task1)], events
        )

    def test_remove_child_without_effort_causes_no_time_spent_notification(
        self,
    ):
        events = test.ChangeRecorder(task.Task.timeSpentChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertFalse(events)

    def test_remove_child_with_high_priority_causes_priority_notification(
        self,
    ):
        self.task1_1.setPriority(10)
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertIn(self.task1, self.events[0].sources())

    def test_remove_low_priority_child_sends_no_total_priority_notification(
        self,
    ):
        self.task1_1.setPriority(-10)
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertFalse(self.events)

    def test_remove_child_with_revenue_causes_total_revenue_notification(self):
        self.task1_1.set_fixed_fee(1000)
        events = test.ChangeRecorder(task.Task.revenueChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual([(0, self.task1)], events)

    def test_remove_child_without_revenue_causes_no_revenue_notification(self):
        events = test.ChangeRecorder(task.Task.revenueChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertFalse(events)

    def test_remove_tracked_child_causes_stop_tracking_notification(self):
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        events = test.ChangeRecorder(task.Task.trackingChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual([(False, self.task1)], events)

    def test_removing_tracked_child_of_tracked_parent_sends_no_stop_tracking(
        self,
    ):
        self.task1.addEffort(effort.Effort(self.task1))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        events = test.ChangeRecorder(task.Task.trackingChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertFalse(events)

    def test_parent_due_earlier_than_child_due_keeps_child_due(
        self,
    ):
        child_due_date_time = date.Now() + date.TWO_HOURS
        self.task1_1.set_due_date_time(child_due_date_time)
        parent_due_date_time = date.Now() + date.ONE_HOUR
        self.task1.set_due_date_time(parent_due_date_time)
        self.assertEqual(child_due_date_time, self.task1_1.dueDateTime())

    def test_child_due_later_than_parent_due_keeps_parent_due(
        self,
    ):
        parent_due_date_time = date.Now() + date.ONE_HOUR
        self.task1.set_due_date_time(parent_due_date_time)
        child_due_date_time = date.Now() + date.TWO_HOURS
        self.task1_1.set_due_date_time(child_due_date_time)
        self.assertEqual(parent_due_date_time, self.task1.dueDateTime())

    def test_recursive_due_date_time(self):
        self.assertEqual(
            date.DateTime(), self.task1.dueDateTime(recursive=True)
        )

    def test_recursive_due_date_time_when_child_due_today(self):
        now = date.Now()
        self.task1_1.set_due_date_time(now)
        self.assertEqual(now, self.task1.dueDateTime(recursive=True))

    def test_notification_when_recursive_due_date_time_changes(self):
        self.record_changes(task.Task.dueDateTimeChangedEventType())
        now = date.Now()
        self.task1_1.set_due_date_time(now)
        self.assertEqual(
            set([(now, self.task1), (now, self.task1_1)]), set(self.changes)
        )

    def test_recursive_due_date_time_when_child_due_today_and_completed(self):
        self.task1_1.set_due_date_time(date.Now())
        self.task1_1.set_completion_date_time(date.Now())
        self.assertEqual(
            date.DateTime(), self.task1.dueDateTime(recursive=True)
        )

    def test_setting_planned_start_later_than_childs(
        self,
    ):
        child_planned_start_date_time = self.task1_1.plannedStartDateTime()
        self.task1.set_planned_start_date_time(self.tomorrow)
        self.assertEqual(self.tomorrow, self.task1.plannedStartDateTime())
        self.assertEqual(
            child_planned_start_date_time,
            self.task1.plannedStartDateTime(recursive=True),
        )
        self.assertEqual(
            child_planned_start_date_time, self.task1_1.plannedStartDateTime()
        )

    def test_setting_planned_start_earlier_than_parents(
        self,
    ):
        parent_planned_start_date_time = self.task1.plannedStartDateTime()
        self.task1_1.set_planned_start_date_time(self.yesterday)
        self.assertEqual(self.yesterday, self.task1_1.plannedStartDateTime())
        self.assertEqual(
            self.yesterday, self.task1.plannedStartDateTime(recursive=True)
        )
        self.assertEqual(
            parent_planned_start_date_time, self.task1.plannedStartDateTime()
        )

    def test_recursive_planned_start_date_time(self):
        self.assertAlmostEqual(
            date.Now().toordinal(),
            self.task1.plannedStartDateTime(recursive=True).toordinal(),
            places=2,
        )

    def test_notification_when_recursive_planned_start_date_time_changes(self):
        self.record_changes(task.Task.plannedStartDateTimeChangedEventType())
        now = date.Now()
        self.task1_1.set_planned_start_date_time(now)
        self.assertEqual(
            set([(now, self.task1), (now, self.task1_1)]), set(self.changes)
        )

    def test_recursive_planned_start_date_time_when_child_starts_yesterday(
        self,
    ):
        self.task1_1.set_planned_start_date_time(self.yesterday)
        self.assertEqual(
            self.yesterday, self.task1.plannedStartDateTime(recursive=True)
        )

    def test_recursive_actual_start_date_time(self):
        self.assertAlmostEqual(
            date.Now().toordinal(),
            self.task1.actualStartDateTime(recursive=True).toordinal(),
            places=2,
        )

    def test_notification_when_recursive_actual_start_date_time_changes(self):
        self.record_changes(task.Task.actualStartDateTimeChangedEventType())
        now = date.Now()
        self.task1_1.set_actual_start_date_time(now)
        self.assertEqual(
            set([(now, self.task1), (now, self.task1_1)]), set(self.changes)
        )

    def test_recursive_actual_start_date_time_when_child_starts_yesterday(
        self,
    ):
        self.task1_1.set_actual_start_date_time(self.yesterday)
        self.assertEqual(
            self.yesterday, self.task1.actualStartDateTime(recursive=True)
        )

    def test_recursive_completion_date_time(self):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.task1_1.set_completion_date_time(self.tomorrow)
        self.assertEqual(
            self.tomorrow, self.task1.completionDateTime(recursive=True)
        )

    def test_notification_when_recursive_completion_date_time_changes(self):
        self.task1_1.set_completion_date_time(self.yesterday)
        self.record_changes(task.Task.completionDateTimeChangedEventType())
        now = date.Now()
        self.task1_1.set_completion_date_time(now)
        self.assertEqual(
            set([(now, self.task1), (now, self.task1_1)]), set(self.changes)
        )

    def test_recursive_completion_date_time_when_child_is_completed_yesterday(
        self,
    ):
        self.task1_1.set_completion_date_time(self.yesterday)
        now = date.Now()
        self.task1.set_completion_date_time(now)
        self.assertEqual(now, self.task1.completionDateTime(recursive=True))

    def test_notification_when_recursive_reminder_date_time_changes(self):
        self.record_changes(task.Task.reminderChangedEventType())
        now = date.Now()
        self.task1_1.set_reminder(now)
        self.assertEqual(
            set([(now, self.task1), (now, self.task1_1)]), set(self.changes)
        )

    def test_snoozing_a_child_reminder_notifies_its_parent_too(self):
        self.record_changes(task.Task.reminderChangedEventType())
        now = date.Now()
        self.task1_1.snooze_reminder(date.ONE_HOUR, now=lambda: now)
        snoozed = now + date.ONE_HOUR
        self.assertEqual(
            set([(snoozed, self.task1), (snoozed, self.task1_1)]),
            set(self.changes),
        )

    def test_not_all_children_are_completed(self):
        self.assertFalse(self.task1.allChildrenCompleted())

    def test_all_children_are_completed_after_marking_only_child_as_completed(
        self,
    ):
        self.task1_1.set_completion_date_time()
        self.assertTrue(self.task1.allChildrenCompleted())

    def test_time_left_recursively_is_infinite(self):
        self.assertEqual(
            date.TimeDelta.max, self.task1.timeLeft(recursive=True)
        )

    def test_time_spent_recursively_is_zero(self):
        self.assertEqual(date.TimeDelta(), self.task.timeSpent(recursive=True))

    def test_recursive_budget_when_parent_has_no_budget_while_child_does(self):
        self.task1_1.set_budget(date.ONE_HOUR)
        self.assertEqual(date.ONE_HOUR, self.task.budget(recursive=True))

    def test_recursive_budget_left_when_parent_has_no_budget_while_child_does(
        self,
    ):
        self.task1_1.set_budget(date.ONE_HOUR)
        self.assertEqual(date.ONE_HOUR, self.task.budgetLeft(recursive=True))

    def test_recursive_budget_when_both_have_budget(self):
        self.task1_1.set_budget(date.ONE_HOUR)
        self.task.set_budget(date.ONE_HOUR)
        self.assertEqual(date.TWO_HOURS, self.task.budget(recursive=True))

    def test_recursive_budget_left_when_both_have_budget(self):
        self.task1_1.set_budget(date.ONE_HOUR)
        self.task.set_budget(date.ONE_HOUR)
        self.assertEqual(date.TWO_HOURS, self.task.budgetLeft(recursive=True))

    def test_recursive_budget_left_when_child_budget_is_all_spent(self):
        self.task1_1.set_budget(date.ONE_HOUR)
        self.addEffort(date.ONE_HOUR, self.task1_1)
        self.assertEqual(
            date.TimeDelta(), self.task.budgetLeft(recursive=True)
        )

    def test_budget_notification_when_child_budget_changes(self):
        self.record_changes(task.Task.budgetChangedEventType())
        self.task1_1.set_budget(date.ONE_HOUR)
        self.assertTrue((date.ONE_HOUR, self.task1) in self.changes)

    def test_budget_notification_when_removing_child_with_budget(self):
        self.task1_1.set_budget(date.ONE_HOUR)
        self.record_changes(task.Task.budgetChangedEventType())
        self.task.removeChild(self.task1_1)
        self.assertTrue((date.TimeDelta(0), self.task1) in self.changes)

    def test_budget_left_notification_when_child_budget_changes(self):
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.task1_1.set_budget(date.ONE_HOUR)
        self.assertTrue((date.ONE_HOUR, self.task1) in events)

    def test_budget_left_notification_when_child_time_spent_changes(self):
        self.task1_1.set_budget(date.TWO_HOURS)
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.task1_1.addEffort(
            effort.Effort(
                self.task1_1,
                date.DateTime(2005, 1, 1, 10, 0, 0),
                date.DateTime(2005, 1, 1, 11, 0, 0),
            )
        )
        self.assertTrue((date.ONE_HOUR, self.task1) in events)

    def test_budget_left_notification_when_parent_has_no_budget(self):
        self.task1_1.set_budget(date.TWO_HOURS)
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.task1.addEffort(
            effort.Effort(
                self.task1,
                date.DateTime(2005, 1, 1, 10, 0, 0),
                date.DateTime(2005, 1, 1, 11, 0, 0),
            )
        )
        # Its own budget left: no budget less its hour
        self.assertIn((-date.ONE_HOUR, self.task1), events)

    def test_child_time_spent_without_any_budget_sends_no_budget_left(
        self,
    ):
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.task1_1.addEffort(
            effort.Effort(
                self.task1_1,
                date.DateTime(2005, 1, 1, 10, 0, 0),
                date.DateTime(2005, 1, 1, 11, 0, 0),
            )
        )
        self.assertFalse(events)

    def test_time_spent_notification_when_child_time_spent_changes(self):
        child_effort = effort.Effort(
            self.task1_1,
            date.DateTime(2005, 1, 1, 10, 0, 0),
            date.DateTime(2005, 1, 1, 11, 0, 0),
        )
        self.task1_1.addEffort(child_effort)
        events = test.ChangeRecorder(task.Task.timeSpentChangedEventType())
        child_effort.setStop(date.DateTime(2005, 1, 1, 12, 0, 0))
        self.assertTrue((self.task1.timeSpent(), self.task1) in events)

    def test_subtask_recurrence_change_names_the_chain(self):
        # A collapsed ancestor shows its subtasks' shortest recurrence
        self.registerObserver(task.Task.recurrenceChangedEventType())
        self.task1_1.set_recurrence(date.Recurrence("weekly"))
        self.assertEqual({self.task1_1, self.task1}, self.events[0].sources())

    def test_recursive_priority_notification(self):
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task1_1.setPriority(10)
        sources = self.events[0].sources()
        self.assertIn(self.task1_1, sources)
        self.assertIn(self.task1, sources)

    def test_priority_notification_with_lower_child_priority(self):
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task1_1.setPriority(-1)
        sources = self.events[0].sources()
        self.assertIn(self.task1_1, sources)
        self.assertIn(self.task1, sources)

    def test_revenue_notification_when_child_has_effort_added(self):
        events = test.ChangeRecorder(task.Task.revenueChangedEventType())
        self.task1_1.set_hourly_fee(100)
        self.task1_1.addEffort(
            effort.Effort(
                self.task1_1,
                date.DateTime(2005, 1, 1, 10, 0, 0),
                date.DateTime(2005, 1, 1, 12, 0, 0),
            )
        )
        self.assertTrue((200, self.task1) in events)

    def test_is_being_tracked_recursive_when_child_is_not_tracked(self):
        self.assertFalse(self.task1.isBeingTracked(recursive=True))

    def test_is_being_tracked_recursive_when_child_is_tracked(self):
        self.assertFalse(self.task1.isBeingTracked(recursive=True))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        self.assertTrue(self.task1.isBeingTracked(recursive=True))

    def test_notification_when_child_is_being_tracked(self):
        events = test.ChangeRecorder(self.task1.trackingChangedEventType())
        active_effort = effort.Effort(self.task1_1)
        self.task1_1.addEffort(active_effort)
        self.assertEqual(
            set([(True, self.task1), (True, self.task1_1)]), set(events)
        )

    def test_notification_when_child_tracking_stops(self):
        active_effort = effort.Effort(self.task1_1)
        self.task1_1.addEffort(active_effort)
        events = test.ChangeRecorder(task.Task.trackingChangedEventType())
        active_effort.setStop()
        self.assertEqual(
            set([(False, self.task), (False, self.task1_1)]), set(events)
        )

    def test_set_fixed_fee_of_child(self):
        self.record_changes(task.Task.fixedFeeChangedEventType())
        self.task1_1.set_fixed_fee(1000)
        self.assertTrue((1000, self.task1) in self.changes)

    def test_get_fixed_fee_recursive(self):
        self.task.set_fixed_fee(2000)
        self.task1_1.set_fixed_fee(1000)
        self.assertEqual(3000, self.task.fixedFee(recursive=True))

    def test_recursive_revenue_from_fixed_fee(self):
        self.task.set_fixed_fee(2000)
        self.task1_1.set_fixed_fee(1000)
        self.assertEqual(3000, self.task.revenue(recursive=True))

    def test_efforts_take_their_task_foreground_color(self):
        self.task.addEffort(effort.Effort(self.task))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        self.task.setForegroundColor(wx.RED)
        test.styled(self.task1_1)
        self.assertEqual(
            [wx.RED, wx.RED],
            [
                each.shown_fg_color()
                for each in self.task.efforts(recursive=True)
            ],
        )

    def test_efforts_take_their_task_background_color(self):
        self.task.addEffort(effort.Effort(self.task))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        self.task.setBackgroundColor(wx.RED)
        test.styled(self.task1_1)
        self.assertEqual(
            [wx.RED, wx.RED],
            [
                each.shown_bg_color()
                for each in self.task.efforts(recursive=True)
            ],
        )

    def test_efforts_take_their_task_category_foreground_color(self):
        self.task.addEffort(effort.Effort(self.task))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        cat = category.Category("Cat")
        self.task.addCategory(cat)
        cat.setForegroundColor(wx.RED)
        test.styled(self.task1_1)
        self.assertEqual(
            [wx.RED, wx.RED],
            [
                each.shown_fg_color()
                for each in self.task.efforts(recursive=True)
            ],
        )

    def test_efforts_take_their_task_category_background_color(self):
        self.task.addEffort(effort.Effort(self.task))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        cat = category.Category("Cat")
        self.task.addCategory(cat)
        cat.setBackgroundColor(wx.RED)
        test.styled(self.task1_1)
        self.assertEqual(
            [wx.RED, wx.RED],
            [
                each.shown_bg_color()
                for each in self.task.efforts(recursive=True)
            ],
        )

    def test_child_uses_foreground_color_of_parents_category(self):
        cat = category.Category("Cat", fgColor=wx.RED)
        self.task.addCategory(cat)
        self.assertEqual(wx.RED, test.styled(self.task1_1).shown_fg_color())

    def test_child_takes_the_parent_own_color(self):
        self.task.setForegroundColor(wx.RED)
        self.assertEqual(wx.RED, test.styled(self.task1_1).shown_fg_color())

    def test_child_shows_its_own_status_not_the_parent_status(self):
        self.task.set_should_mark_completed_when_all_children_completed(False)
        self.task1_1.set_completion_date_time()
        test.styled(self.task1_1)
        self.assertEqual(
            task.completed.icon_id(),
            self.task1_1.shown_icon_id(),
        )
        self.assertEqual(
            self.task1_1.statusFgColor(), self.task1_1.shown_fg_color()
        )

    def test_child_of_a_tracked_task_shows_its_own_icon(self):
        self.task.addEffort(effort.Effort(self.task))
        self.assertEqual(
            task.active.icon_id(),
            test.styled(self.task1_1).shown_icon_id(),
        )

    def test_percentage_completed(self):
        self.assertEqual(0, self.task.percentageComplete(recursive=True))

    def test_percentage_completed_when_child_is_50_procent_complete(self):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.task1_1.setPercentageComplete(50)
        self.assertEqual(50, self.task.percentageComplete(recursive=True))

    def test_percentage_with_half_complete_child_and_marking_parent_off(
        self,
    ):
        self.task.set_should_mark_completed_when_all_children_completed(False)
        self.task1_1.setPercentageComplete(50)
        self.assertEqual(25, self.task.percentageComplete(recursive=True))

    def test_percentage_with_half_complete_child_and_global_marking_off(
        self,
    ):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", False
        )
        self.task1_1.setPercentageComplete(50)
        self.assertEqual(25, self.task.percentageComplete(recursive=True))

    def test_percentage_completed_notification_when_child_percentage_changes(
        self,
    ):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.record_changes(task.Task.percentageCompleteChangedEventType())
        self.task1_1.setPercentageComplete(50)
        self.assertEqual(
            {(50, self.task1_1), (50, self.task)}, set(self.changes)
        )

    def test_percentage_notification_on_mark_completed_setting_change(
        self,
    ):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.task1_1.setPercentageComplete(50)
        self.record_changes(task.Task.percentageCompleteChangedEventType())
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", False
        )
        self.assertEqual([(0, self.task)], self.changes)

    def test_icon(self):
        self.assertEqual(
            task.active.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_child_icon(self):
        self.assertEqual(
            task.active.icon_id(),
            test.styled(self.task1_1).shown_icon_id(),
        )

    def test_chosen_icon_of_a_task_with_subtasks_is_shown_as_is(self):
        self.task.set_icon_id("nuvola_actions_ledgreen")
        self.assertEqual(
            "nuvola_actions_ledgreen", test.styled(self.task).shown_icon_id()
        )

    def test_child_is_inactive_when_parent_has_prerequisite(self):
        prerequisite = task.Task()
        self.task.add_prerequisites([prerequisite])
        self.assertTrue(self.task1_1.inactive())

    def test_child_is_not_active_when_parent_has_prerequisite(self):
        prerequisite = task.Task()
        self.task.add_prerequisites([prerequisite])
        self.assertFalse(self.task1_1.active())

    def test_adding_prerequisite_to_parent_recomputes_child_appearance(self):
        # First make sure the icon is cached:
        self.assertEqual(
            task.active.icon_id(),
            test.styled(self.task1_1).shown_icon_id(),
        )
        prerequisite = task.Task()
        self.task.add_prerequisites([prerequisite])
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task1_1).shown_icon_id(),
        )

    def test_setting_prerequisites_of_parent_recomputes_child_appearance(self):
        # First make sure the icon is cached:
        self.assertEqual(
            task.active.icon_id(),
            test.styled(self.task1_1).shown_icon_id(),
        )
        prerequisite = task.Task()
        self.task.set_prerequisites([prerequisite])
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task1_1).shown_icon_id(),
        )

    def test_removing_prerequisite_from_parent_recomputes_child_appearance(
        self,
    ):
        prerequisite = task.Task()
        self.task.add_prerequisites([prerequisite])
        # First make sure the icon is cached:
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task1_1).shown_icon_id(),
        )
        self.task.remove_prerequisites([prerequisite])
        # The child has an actual start date: active, not late
        self.assertEqual(
            task.active.icon_id(),
            test.styled(self.task1_1).shown_icon_id(),
        )

    def test_completing_prerequisite_of_parent_recomputes_child_appearance(
        self,
    ):
        prerequisite = task.Task()
        self.task.add_prerequisites([prerequisite])
        prerequisite.add_dependencies([self.task])
        # First make sure the icon is cached:
        self.assertEqual(
            task.inactive.icon_id(),
            test.styled(self.task1_1).shown_icon_id(),
        )
        prerequisite.set_completion_date_time(date.Now())
        # The child has an actual start date: active, not late
        self.assertEqual(
            task.active.icon_id(),
            test.styled(self.task1_1).shown_icon_id(),
        )


class TaskWithTwoChildrenTest(
    TaskTestCase, CommonTaskTestsMixin, NoBudgetTestsMixin
):
    def taskCreationKeywordArguments(self):
        return [
            {
                "children": [
                    task.Task(subject="child1"),
                    task.Task(subject="child2"),
                ]
            }
        ]

    def test_remove_last_active_child_completes_parent(self):
        self.task.set_should_mark_completed_when_all_children_completed(True)
        self.task1_1.set_completion_date_time()
        self.task.removeChild(self.task1_2)
        self.assertTrue(self.task.completed())

    def test_percentage_completed_when_one_child_is_50_procent_complete(self):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.task1_1.setPercentageComplete(50)
        self.assertEqual(25, self.task.percentageComplete(recursive=True))

    def test_percentage_with_one_half_complete_child_and_marking_parent_off(
        self,
    ):
        self.task.set_should_mark_completed_when_all_children_completed(False)
        self.task1_1.setPercentageComplete(50)
        self.assertEqual(
            int(100 / 6.0), self.task.percentageComplete(recursive=True)
        )

    def test_percentage_completed_when_one_child_is_complete(self):
        settings.set(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.task1_1.setPercentageComplete(100)
        self.assertEqual(50, self.task.percentageComplete(recursive=True))

    def test_percentage_with_one_child_complete_and_marking_parent_off(
        self,
    ):
        self.task.set_should_mark_completed_when_all_children_completed(False)
        self.task1_1.setPercentageComplete(100)
        self.assertEqual(33, self.task.percentageComplete(recursive=True))


class CompletedTaskWithChildTest(TaskTestCase):
    def taskCreationKeywordArguments(self):
        return [
            {
                "completionDateTime": date.Now(),
                "children": [task.Task(subject="child")],
            }
        ]

    def test_icon(self):
        self.assertEqual(
            task.completed.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )


class OverdueTaskWithChildTest(TaskTestCase):
    def taskCreationKeywordArguments(self):
        return [
            {
                "dueDateTime": self.yesterday,
                "children": [task.Task(subject="child")],
            }
        ]

    def test_icon(self):
        self.assertEqual(
            task.overdue.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )

    def test_due_date_time(self):
        for recursive in (False, True):
            self.assertEqual(
                self.yesterday, self.task.dueDateTime(recursive=recursive)
            )


class DuesoonTaskWithChildTest(TaskTestCase):
    def taskCreationKeywordArguments(self):
        return [
            {
                "dueDateTime": date.Now() + date.ONE_HOUR,
                "children": [task.Task(subject="child")],
            }
        ]

    def test_icon(self):
        self.assertEqual(
            task.duesoon.icon_id(),
            test.styled(self.task).shown_icon_id(),
        )


class TaskWithGrandChildTest(
    TaskTestCase, CommonTaskTestsMixin, NoBudgetTestsMixin
):
    def taskCreationKeywordArguments(self):
        return [{}, {}, {}]

    def setUp(self):
        super().setUp()
        self.task1.addChild(self.task2)
        self.task2.addChild(self.task3)

    def test_time_spent_recursively_is_zero(self):
        self.assertEqual(date.TimeDelta(), self.task.timeSpent(recursive=True))


class TaskWithOneEffortTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [
            {
                "efforts": [
                    effort.Effort(
                        None,
                        date.DateTime(2005, 1, 1),
                        date.DateTime(2005, 1, 2),
                    )
                ]
            }
        ]

    def test_time_spent_on_task_equals_effort_duration(self):
        self.assertEqual(self.task1effort1.timeSpent(), self.task.timeSpent())

    def test_time_spent_recursively_on_task_equals_effort_duration(self):
        self.assertEqual(
            self.task1effort1.timeSpent(), self.task.timeSpent(recursive=True)
        )

    def test_time_spent_on_task_is_zero_after_removal_of_effort(self):
        self.task.removeEffort(self.task1effort1)
        self.assertEqual(date.TimeDelta(), self.task.timeSpent())

    def test_task_effort_list_contains_the_one_effort_added(self):
        self.assertEqual([self.task1effort1], self.task.efforts())

    def test_start_tracking_effort(self):
        events = test.ChangeRecorder(self.task.trackingChangedEventType())
        self.task1effort1.setStop(date.DateTime.max)
        self.assertEqual([(True, self.task)], events)

    def test_stop_tracking_effort(self):
        self.task1effort1.setStop(date.DateTime.max)
        events = test.ChangeRecorder(self.task.trackingChangedEventType())
        self.task1effort1.setStop()
        self.assertEqual([(False, self.task)], events)

    def test_revenue_with_effort_but_with_zero_fee(self):
        self.assertEqual(0, self.task.revenue())

    def test_effort_takes_its_task_background_color(self):
        self.task.setBackgroundColor(wx.RED)
        test.styled(self.task)
        self.assertEqual(wx.RED, self.task1effort1.shown_bg_color())


class TaskWithTwoEffortsTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [
            {
                "efforts": [
                    effort.Effort(
                        None,
                        date.DateTime(2005, 1, 1),
                        date.DateTime(2005, 1, 2),
                    ),
                    effort.Effort(
                        None,
                        date.DateTime(2005, 2, 1),
                        date.DateTime(2005, 2, 2),
                    ),
                ]
            }
        ]

    def setUp(self):
        super().setUp()
        self.totalDuration = (
            self.task1effort1.timeSpent() + self.task1effort2.timeSpent()
        )

    def test_time_spent_on_task_equals_effort_duration(self):
        self.assertEqual(self.totalDuration, self.task.timeSpent())

    def test_time_spent_recursively_on_task_equals_effort_duration(self):
        self.assertEqual(
            self.totalDuration, self.task.timeSpent(recursive=True)
        )


class TaskWithActiveEffort(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [
            {
                "efforts": [effort.Effort(None, date.DateTime.now())],
                "icon": "nuvola_apps_clanbomber",
            }
        ]

    def test_task_is_being_tracked(self):
        self.assertTrue(self.task.isBeingTracked())

    def test_stop_tracking(self):
        self.task.stopTracking()
        self.assertFalse(self.task.isBeingTracked())

    def test_active_effort_given_to_constructor_sends_no_start_tracking(
        self,
    ):
        events = test.ChangeRecorder(task.Task.trackingChangedEventType())
        task.Task(efforts=[effort.Effort(None)])
        self.assertFalse(events)

    def test_no_start_tracking_event_after_adding_a_second_active_effort(self):
        events = test.ChangeRecorder(task.Task.trackingChangedEventType())
        self.task.addEffort(effort.Effort(self.task))
        self.assertFalse(events)

    def test_no_stop_tracking_event_after_removing_first_of_two_active_efforts(
        self,
    ):
        events = test.ChangeRecorder(task.Task.trackingChangedEventType())
        second_effort = effort.Effort(self.task)
        self.task.addEffort(second_effort)
        self.task.removeEffort(second_effort)
        self.assertFalse(events)

    def test_remove_active_effort_should_cause_stop_tracking_event(self):
        events = test.ChangeRecorder(self.task.trackingChangedEventType())
        self.task.removeEffort(self.task1effort1)
        self.assertEqual([(False, self.task)], events)

    def test_stop_tracking_event(self):
        events = test.ChangeRecorder(self.task.trackingChangedEventType())
        self.task.stopTracking()
        self.assertEqual([(False, self.task)], events)

    def test_icon(self):
        self.assertEqual(
            "nuvola_apps_clock", test.styled(self.task).shown_icon_id()
        )

    def test_icon_after_stop_tracking(self):
        self.task.stopTracking()
        self.assertNotEqual(
            "nuvola_apps_clock", test.styled(self.task).shown_icon_id()
        )


class TaskWithChildAndEffortTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [
            {
                "children": [
                    task.Task(
                        efforts=[
                            effort.Effort(
                                None,
                                date.DateTime(2005, 2, 1),
                                date.DateTime(2005, 2, 2),
                            )
                        ]
                    )
                ],
                "efforts": [
                    effort.Effort(
                        None,
                        date.DateTime(2005, 1, 1),
                        date.DateTime(2005, 1, 2),
                    )
                ],
            }
        ]

    def test_time_spent_on_task_equals_effort_duration(self):
        self.assertEqual(self.task1effort1.timeSpent(), self.task1.timeSpent())

    def test_time_spent_recursively_on_task_equals_total_effort_duration(self):
        self.assertEqual(
            self.task1effort1.timeSpent() + self.task1_1effort1.timeSpent(),
            self.task1.timeSpent(recursive=True),
        )

    def test_efforts_recursive(self):
        self.assertEqual(
            [self.task1effort1, self.task1_1effort1],
            self.task1.efforts(recursive=True),
        )

    def test_recursive_revenue(self):
        self.task.set_hourly_fee(100)
        self.task1_1.set_hourly_fee(100)
        self.assertEqual(4800, self.task.revenue(recursive=True))

    def test_child_effort_takes_the_parent_background_color(self):
        self.task.setBackgroundColor(wx.RED)
        test.styled(self.task1_1)
        self.assertEqual(wx.RED, self.task1_1effort1.shown_bg_color())


class TaskWithGrandChildAndEffortTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [
            {
                "children": [
                    task.Task(
                        children=[
                            task.Task(
                                efforts=[
                                    effort.Effort(
                                        None,
                                        date.DateTime(2005, 3, 1),
                                        date.DateTime(2005, 3, 2),
                                    )
                                ]
                            )
                        ],
                        efforts=[
                            effort.Effort(
                                None,
                                date.DateTime(2005, 2, 1),
                                date.DateTime(2005, 2, 2),
                            )
                        ],
                    )
                ],
                "efforts": [
                    effort.Effort(
                        None,
                        date.DateTime(2005, 1, 1),
                        date.DateTime(2005, 1, 2),
                    )
                ],
            }
        ]

    def test_time_spent_recursively_on_task_equals_total_effort_duration(self):
        self.assertEqual(
            self.task1effort1.timeSpent()
            + self.task1_1effort1.timeSpent()
            + self.task1_1_1effort1.timeSpent(),
            self.task1.timeSpent(recursive=True),
        )

    def test_efforts_recursive(self):
        self.assertEqual(
            [self.task1effort1, self.task1_1effort1, self.task1_1_1effort1],
            self.task1.efforts(recursive=True),
        )


class TaskWithBudgetTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"budget": date.TWO_HOURS}]

    def setUp(self):
        super().setUp()
        self.oneHourEffort = effort.Effort(
            self.task,
            date.DateTime(2005, 1, 1, 13, 0),
            date.DateTime(2005, 1, 1, 14, 0),
        )

    def expectedBudget(self):
        return self.taskCreationKeywordArguments()[0]["budget"]

    def test_budget(self):
        self.assertEqual(self.expectedBudget(), self.task.budget())

    def test_budget_left(self):
        self.assertEqual(self.expectedBudget(), self.task.budgetLeft())

    def test_budget_left_after_half_spent(self):
        self.addEffort(date.ONE_HOUR)
        self.assertEqual(date.ONE_HOUR, self.task.budgetLeft())

    def test_budget_left_notification(self):
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.addEffort(date.ONE_HOUR)
        self.assertEqual([(date.ONE_HOUR, self.task)], events)

    def test_budget_left_after_all_spent(self):
        self.addEffort(date.TWO_HOURS)
        self.assertEqual(date.TimeDelta(), self.task.budgetLeft())

    def test_budget_left_when_over_budget(self):
        self.addEffort(date.TimeDelta(hours=3))
        self.assertEqual(-date.ONE_HOUR, self.task.budgetLeft())

    def test_recursive_budget(self):
        self.assertEqual(
            self.expectedBudget(), self.task.budget(recursive=True)
        )

    def test_recursive_budget_with_child_without_budget(self):
        self.task.addChild(task.Task())
        self.assertEqual(
            self.expectedBudget(), self.task.budget(recursive=True)
        )

    def test_budget_is_copied_when_task_is_copied(self):
        copy = self.task.copy()
        self.assertEqual(copy.budget(), self.task.budget())
        self.task.set_budget(date.ONE_HOUR)
        self.assertEqual(date.TWO_HOURS, copy.budget())


class TaskReminderTestCase(TaskTestCase, CommonTaskTestsMixin):
    eventTypes = [task.Task.reminderChangedEventType()]

    def taskCreationKeywordArguments(self):
        return [{"reminder": date.DateTime(2005, 1, 1)}]

    def initialReminder(self):
        return self.taskCreationKeywordArguments()[0]["reminder"]

    def test_reminder(self):
        self.assertReminder(self.initialReminder())

    def test_set_reminder(self):
        some_other_time = date.DateTime(2005, 1, 2)
        self.task.set_reminder(some_other_time)
        for recursive in (False, True):
            self.assertReminder(some_other_time, recursive=recursive)

    def test_cancel_reminder(self):
        self.task.set_reminder()
        self.assertReminder(date.DateTime())

    def test_snooze_reminder(self):
        snooze_period = date.ONE_HOUR
        now = date.Now()
        self.task.snooze_reminder(snooze_period, now=lambda: now)
        self.assertReminder(now + snooze_period)

    def test_snooze_reminder_twice(self):
        snooze_period = date.ONE_HOUR
        now = date.Now()
        self.task.snooze_reminder(snooze_period, now=lambda: now)
        self.task.snooze_reminder(
            snooze_period, now=lambda: now + snooze_period
        )
        self.assertReminder(now + 2 * snooze_period)

    def test_snooze_when_reminder_not_set(self):
        self.task.set_reminder()
        snooze_period = date.ONE_HOUR
        now = date.Now()
        self.task.snooze_reminder(snooze_period, now=lambda: now)
        self.assertReminder(now + snooze_period)

    def test_snooze_with_zero_time_delta(self):
        self.task.snooze_reminder(date.TimeDelta())
        # Not set is the latest date (docs/ATTRIBUTE_PATTERN.md)
        self.assertReminder(date.DateTime())
        self.assertEqual(
            date.DateTime(), self.task.reminder(include_snooze=False)
        )

    def test_original_reminder(self):
        self.assertEqual(
            self.initialReminder(), self.task.reminder(include_snooze=False)
        )

    def test_original_reminder_after_snooze(self):
        self.task.snooze_reminder(date.ONE_HOUR)
        self.assertEqual(
            self.initialReminder(), self.task.reminder(include_snooze=False)
        )

    def test_original_reminder_after_two_snoozes(self):
        self.task.snooze_reminder(date.ONE_HOUR)
        self.task.snooze_reminder(date.ONE_HOUR)
        self.assertEqual(
            self.initialReminder(), self.task.reminder(include_snooze=False)
        )

    def test_original_reminder_after_cancel(self):
        self.task.set_reminder(None)
        self.assertEqual(
            date.DateTime(), self.task.reminder(include_snooze=False)
        )

    def test_cancel_reminder_with_max_date_time(self):
        self.task.set_reminder(date.DateTime.max)
        self.assertReminder(date.DateTime())

    def test_task_notifies_observer_of_new_reminder(self):
        self.record_changes(task.Task.reminderChangedEventType())
        new_reminder = self.initialReminder() + date.ONE_SECOND
        self.task.set_reminder(new_reminder)
        self.assertEqual([(new_reminder, self.task)], self.changes)

    def test_new_reminder_cancels_previous_reminder(self):
        self.record_changes(task.Task.reminderChangedEventType())
        self.task.set_reminder()
        self.assertEqual([(date.DateTime(), self.task)], self.changes)

    def test_mark_completed_cancels_reminder(self):
        self.task.set_completion_date_time()
        self.assertReminder(date.DateTime())

    def test_recursive_reminder(self):
        self.assertEqual(
            self.initialReminder(), self.task.reminder(recursive=True)
        )

    def test_recursive_reminder_with_child_without_reminder(self):
        self.task.addChild(task.Task())
        self.assertEqual(
            self.initialReminder(), self.task.reminder(recursive=True)
        )

    def test_recursive_reminder_with_child_with_later_reminder(self):
        self.task.addChild(task.Task(reminder=date.DateTime(3000, 1, 1)))
        self.assertEqual(
            self.initialReminder(), self.task.reminder(recursive=True)
        )

    def test_recursive_reminder_with_child_with_earlier_reminder(self):
        self.task.addChild(task.Task(reminder=date.DateTime(2000, 1, 1)))
        self.assertEqual(
            date.DateTime(2000, 1, 1), self.task.reminder(recursive=True)
        )


class TaskSettingTestCase(TaskTestCase, CommonTaskTestsMixin):
    eventTypes = [
        task.Task.shouldMarkCompletedWhenAllChildrenCompletedChangedEventType(),
        task.Task.percentageCompleteChangedEventType(),
    ]


class MarkTaskCompletedWhenAllChildrenCompletedSettingIsTrueFixture(
    TaskSettingTestCase
):
    def taskCreationKeywordArguments(self):
        return [{"shouldMarkCompletedWhenAllChildrenCompleted": True}]

    def test_setting(self):
        self.assertEqual(
            True, self.task.shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def test_set_setting(self):
        self.task.set_should_mark_completed_when_all_children_completed(False)
        self.assertEqual(
            False, self.task.shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def test_set_setting_causes_notification(self):
        cls = task.Task
        self.record_changes(
            cls.shouldMarkCompletedWhenAllChildrenCompletedChangedEventType()
        )
        self.task.set_should_mark_completed_when_all_children_completed(False)
        self.assertEqual([(False, self.task)], self.changes)

    def test_set_setting_causes_percentage_complete_notification(self):
        self.record_changes(task.Task.percentageCompleteChangedEventType())
        # The calculation of the total percentage complete depends on whether
        # a task is marked completed when all its children are completed
        self.task.set_should_mark_completed_when_all_children_completed(False)
        self.assertEqual([(0, self.task)], self.changes)


class MarkTaskCompletedWhenAllChildrenCompletedSettingIsFalseFixture(
    TaskTestCase
):
    def taskCreationKeywordArguments(self):
        return [{"shouldMarkCompletedWhenAllChildrenCompleted": False}]

    def test_setting(self):
        self.assertEqual(
            False, self.task.shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def test_set_setting(self):
        self.task.set_should_mark_completed_when_all_children_completed(True)
        self.assertEqual(
            True, self.task.shouldMarkCompletedWhenAllChildrenCompleted()
        )


class AttachmentTestCase(TaskTestCase, CommonTaskTestsMixin):
    eventTypes = [task.Task.attachmentsChangedEventType()]


class TaskWithoutAttachmentFixture(AttachmentTestCase):
    def test_remove_non_existing_attachment_raises_no_exception(self):
        self.task.removeAttachments("Non-existing attachment")

    def test_add_empty_list_of_attachments(self):
        self.task.addAttachments()
        self.assertFalse(self.events, self.events)


class TaskWithAttachmentFixture(AttachmentTestCase):
    def taskCreationKeywordArguments(self):
        return [{"attachments": ["/home/frank/attachment.txt"]}]

    def test_attachments(self):
        for index, name in enumerate(
            self.taskCreationKeywordArguments()[0]["attachments"]
        ):
            self.assertEqual(name, self.task.attachments()[index].location())

    def test_remove_non_existing_attachment(self):
        self.task.removeAttachments("Non-existing attachment")

        for index, name in enumerate(
            self.taskCreationKeywordArguments()[0]["attachments"]
        ):
            self.assertEqual(name, self.task.attachments()[index].location())

    def test_copy_creates_new_list_of_attachments(self):
        copy = self.task.copy()

        def locations(item):
            return [each.location() for each in item.attachments()]

        self.assertEqual(locations(copy), locations(self.task))
        self.task.removeAttachments(self.task.attachments()[0])
        self.assertNotEqual(locations(copy), locations(self.task))

    def test_copy_copies_individual_attachments(self):
        copy = self.task.copy()
        self.assertEqual(
            copy.attachments()[0].location(),
            self.task.attachments()[0].location(),
        )
        self.task.attachments()[0].setDescription("new")
        # The location of a copy is actually the same; it's a filename
        # or URI.
        self.assertEqual(
            copy.attachments()[0].location(),
            self.task.attachments()[0].location(),
        )


class TaskWithAttachmentAddedTestCase(AttachmentTestCase):
    def setUp(self):
        super().setUp()
        self.attachment = attachment.FileAttachment("./test.txt")
        self.task.addAttachments(self.attachment)


class TaskWithAttachmentAddedFixture(TaskWithAttachmentAddedTestCase):
    def test_add_attachment(self):
        self.assertTrue(self.attachment in self.task.attachments())

    def test_notification(self):
        self.assertTrue(self.events)


class TaskWithAttachmentRemovedFixture(TaskWithAttachmentAddedTestCase):
    def setUp(self):
        super().setUp()
        self.task.removeAttachments(self.attachment)

    def test_remove_attachment(self):
        self.assertFalse(self.attachment in self.task.attachments())

    def test_notification(self):
        self.assertEqual(2, len(self.events))


class RecursivePriorityFixture(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"priority": 1, "children": [task.Task(priority=2)]}]

    def test_priority_recursive_when_child_has_lowest_priority(self):
        self.task1_1.setPriority(0)
        self.assertEqual(1, self.task1.priority(recursive=True))

    def test_priority_recursive_when_parent_has_lowest_priority(self):
        self.assertEqual(2, self.task1.priority(recursive=True))

    def test_recursive_priority_when_highest_priority_child_is_completed(
        self,
    ):
        self.task1_1.set_completion_date_time()
        self.assertEqual(1, self.task1.priority(recursive=True))

    def test_priority_notification_when_marking_child_completed(self):
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task1_1.set_completion_date_time()
        self.assertIn(self.task1, self.events[0].sources())

    def test_priority_notification_when_marking_child_uncompleted(self):
        self.task1_1.set_completion_date_time()
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task1_1.set_completion_date_time(date.DateTime())
        self.assertIn(self.task1, self.events[0].sources())


class TaskWithFixedFeeFixture(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"fixedFee": 1000}]

    def test_set_fixed_fee_via_contructor(self):
        self.assertEqual(1000, self.task.fixedFee())

    def test_revenue_from_fixed_fee(self):
        self.assertEqual(1000, self.task.revenue())


class TaskWithHourlyFeeFixture(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"subject": "Task", "hourlyFee": 100}]

    def setUp(self):
        super().setUp()
        self.effort = effort.Effort(
            self.task,
            date.DateTime(2005, 1, 1, 10, 0, 0),
            date.DateTime(2005, 1, 1, 11, 0, 0),
        )

    def test_set_hourly_fee_via_constructor(self):
        self.assertEqual(100, self.task.hourlyFee())

    def test_revenue_without_effort(self):
        self.assertEqual(0, self.task.revenue())

    def test_revenue_with_one_hour_effort(self):
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2005, 1, 1, 10, 0, 0),
                date.DateTime(2005, 1, 1, 11, 0, 0),
            )
        )
        self.assertEqual(100, self.task.revenue())

    def test_revenue_notification(self):
        events = test.ChangeRecorder(task.Task.revenueChangedEventType())
        self.task.addEffort(self.effort)
        self.assertEqual([(100, self.task)], events)

    def test_recursive_revenue_notification(self):
        child = task.Task("child", hourlyFee=100)
        self.task.addChild(child)
        events = test.ChangeRecorder(task.Task.revenueChangedEventType())
        child.addEffort(
            effort.Effort(
                child,
                date.DateTime(2005, 1, 1, 10, 0, 0),
                date.DateTime(2005, 1, 1, 11, 0, 0),
            )
        )
        self.assertTrue((100, self.task) in events)

    def test_adding_effort_does_not_trigger_revenue_notification_for_effort(
        self,
    ):
        events = test.ChangeRecorder(effort.Effort.revenueChangedEventType())
        self.task.addEffort(self.effort)
        self.assertFalse(events)

    def test_task_notifies_effort_observers_of_revenue_change(self):
        events = test.ChangeRecorder(effort.Effort.revenueChangedEventType())
        self.task.addEffort(self.effort)
        self.task.set_hourly_fee(200)
        self.assertEqual([(200, self.effort)], events)


class TaskWithCategoryTestCase(TaskTestCase):
    def taskCreationKeywordArguments(self):
        self.category = category.Category("category")  # pylint: disable=W0201
        return [dict(categories=set([self.category]))]

    def setUp(self):
        super().setUp()
        self.task.addCategory(self.category)

    def test_category(self):
        self.assertEqual(set([self.category]), self.task.categories())

    def test_category_icon(self):
        self.category.set_icon_id("icon")
        self.assertEqual("icon", test.styled(self.task).shown_icon_id())


class TaskColorTest(test.TestCase):
    def setUp(self):
        super().setUp()
        self.yesterday = date.Yesterday()
        self.tomorrow = date.Tomorrow()

    def test_default_task(self):
        self.assertEqual(wx.Colour(192, 192, 192), task.Task().statusFgColor())

    def test_completed_task(self):
        completed = task.Task()
        completed.set_completion_date_time()
        self.assertEqual(wx.GREEN, completed.statusFgColor())

    def test_over_due_task(self):
        overdue = task.Task(dueDateTime=self.yesterday)
        self.assertEqual(wx.RED, overdue.statusFgColor())

    def test_due_today_task(self):
        duetoday = task.Task(dueDateTime=date.Now() + date.ONE_HOUR)
        self.assertEqual(wx.Colour(255, 128, 0), duetoday.statusFgColor())

    def test_due_tomorrow(self):
        duetomorrow = task.Task(dueDateTime=self.tomorrow + date.ONE_HOUR)
        self.assertEqual(wx.Colour(192, 192, 192), duetomorrow.statusFgColor())

    def test_active(self):
        active = task.Task(actualStartDateTime=date.Now())
        self.assertEqual(
            wx.Colour(*settings.get("fgcolor", "activetasks")),
            active.statusFgColor(),
        )

    def test_active_task_with_category(self):
        active_task = task.Task(actualStartDateTime=date.Now())
        red_category = category.Category(
            subject="Red category", fgColor=wx.RED
        )
        active_task.addCategory(red_category)
        self.assertEqual(wx.RED, test.styled(active_task).shown_fg_color())


class TaskWithPrerequisite(TaskTestCase):
    def taskCreationKeywordArguments(self):
        self.prerequisite = task.Task(
            subject="prerequisite"
        )  # pylint: disable=W0201
        return [dict(subject="task", prerequisites=[self.prerequisite])]

    def test_task_has_prerequisite(self):
        self.assertTrue(self.prerequisite in self.task.prerequisites())

    def test_dependency_has_not_been_set_automatically(self):
        self.assertFalse(self.task in self.prerequisite.dependencies())

    def test_remove_prerequisite(self):
        self.task.remove_prerequisites([self.prerequisite])
        self.assertFalse(self.task.prerequisites())

    def test_remove_prerequisite_not_in_prerequisites(self):
        self.task.remove_prerequisites([task.Task()])
        self.assertTrue(self.prerequisite in self.task.prerequisites())

    def test_remove_prerequisite_notification(self):
        event_type = task.Task.prerequisitesChangedEventType()
        self.registerObserver(event_type)
        self.task.remove_prerequisites([self.prerequisite])
        self.assertEqual([{self.task}], self.sources_of(event_type))

    def test_set_prerequisites_removes_old_prerequisites(self):
        new_prerequisites = set([task.Task()])
        self.task.set_prerequisites(new_prerequisites)
        self.assertEqual(new_prerequisites, self.task.prerequisites())

    def test_dont_copy_prerequisites(self):
        self.assertFalse(self.prerequisite in self.task.copy().prerequisites())

    def test_prerequisite_subject_changed_notification(self):
        self.prerequisite.add_dependencies([self.task])
        event_type = task.Task.prerequisitesChangedEventType()
        self.registerObserver(event_type)
        self.prerequisite.setSubject("New subject")
        self.assertEqual([{self.task}], self.sources_of(event_type))

    def test_icon_event_after_marking_prerequisite_completed(self):
        # Inactive until the prerequisite is completed, then late
        self.task.set_planned_start_date_time(date.Now() - date.ONE_HOUR)
        self.prerequisite.add_dependencies([self.task])
        event_type = self.task.effectiveIconChangedEventType()
        test.styled(self.task)
        self.registerObserver(event_type, eventSource=self.task)
        self.prerequisite.set_completion_date_time(date.Now())
        test.styled(self.task)
        self.assertEvent(event_type, self.task)


class TaskWithDependency(TaskTestCase):
    def taskCreationKeywordArguments(self):
        self.dependency = task.Task(
            subject="dependency"
        )  # pylint: disable=W0201
        return [dict(subject="task", dependencies=[self.dependency])]

    def test_task_has_dependency(self):
        self.assertTrue(self.dependency in self.task.dependencies())

    def test_prerequisite_has_not_been_set_automatically(self):
        self.assertFalse(self.task in self.dependency.prerequisites())

    def test_remove_dependency(self):
        self.task.remove_dependencies([self.dependency])
        self.assertFalse(self.task.dependencies())

    def test_remove_dependency_not_in_dependencies(self):
        self.task.remove_dependencies([task.Task()])
        self.assertTrue(self.dependency in self.task.dependencies())

    def test_remove_dependency_notification(self):
        event_type = task.Task.dependenciesChangedEventType()
        self.registerObserver(event_type)
        self.task.remove_dependencies([self.dependency])
        self.assertEqual([{self.task}], self.sources_of(event_type))

    def test_set_dependencies_removes_old_dependencies(self):
        new_dependencies = set([task.Task()])
        self.task.set_dependencies(new_dependencies)
        self.assertEqual(new_dependencies, self.task.dependencies())

    def test_dont_copy_dependencies(self):
        self.assertFalse(self.dependency in self.task.copy().dependencies())

    def test_dependency_subject_changed_notification(self):
        self.dependency.add_prerequisites([self.task])
        event_type = task.Task.dependenciesChangedEventType()
        self.registerObserver(event_type)
        self.dependency.setSubject("New subject")
        self.assertEqual([{self.task}], self.sources_of(event_type))


class TaskSuggestedDateTimeBaseSetupAndTests(object):
    def setUp(self):
        # pylint: disable=W0142
        self.changeSettings()
        self.now = now = date.Now()
        tomorrow = now + date.ONE_DAY
        day_after_tomorrow = tomorrow + date.ONE_DAY
        current_time_kw_args = dict(
            hour=now.hour,
            minute=now.minute,
            second=now.second,
        )
        next_friday = tomorrow.endOfWorkWeek().replace(**current_time_kw_args)
        next_monday = (
            (now + date.ONE_WEEK)
            .startOfWorkWeek()
            .replace(**current_time_kw_args)
        )
        start_of_working_day_hour = settings.get("view", "efforthourstart")
        start_of_working_day_kw_args = dict(
            hour=start_of_working_day_hour, minute=0, second=0
        )
        end_of_working_day_hour = settings.get("view", "efforthourend")
        if end_of_working_day_hour == 24:
            end_of_working_day_hour = 23
            minute = 59
            second = 59
        else:
            minute = 0
            second = 0
        end_of_working_day_kw_args = dict(
            hour=end_of_working_day_hour,
            minute=minute,
            second=second,
        )
        start_of_working_day = now.replace(**start_of_working_day_kw_args)
        end_of_working_day = now.replace(**end_of_working_day_kw_args)
        start_of_working_tomorrow = tomorrow.replace(
            **start_of_working_day_kw_args
        )
        end_of_working_tomorrow = tomorrow.replace(
            **end_of_working_day_kw_args
        )
        start_of_working_after_tomorrow = day_after_tomorrow.replace(
            **start_of_working_day_kw_args
        )
        end_of_working_day_after_tomorrow = day_after_tomorrow.replace(
            **end_of_working_day_kw_args
        )
        start_of_working_next_friday = next_friday.replace(
            **start_of_working_day_kw_args
        )
        end_of_working_next_friday = next_friday.replace(
            **end_of_working_day_kw_args
        )
        start_of_working_next_monday = next_monday.replace(
            **start_of_working_day_kw_args
        )
        end_of_working_next_monday = next_monday.replace(
            **end_of_working_day_kw_args
        )

        self.times = dict(
            today_startofday=now.startOfDay(),
            today_startofworkingday=start_of_working_day,
            today_currenttime=now,
            today_endofworkingday=end_of_working_day,
            today_endofday=now.endOfDay(),
            tomorrow_startofday=tomorrow.startOfDay(),
            tomorrow_startofworkingday=start_of_working_tomorrow,
            tomorrow_currenttime=tomorrow,
            tomorrow_endofworkingday=end_of_working_tomorrow,
            tomorrow_endofday=tomorrow.endOfDay(),
            dayaftertomorrow_startofday=day_after_tomorrow.startOfDay(),
            dayaftertomorrow_startofworkingday=start_of_working_after_tomorrow,
            dayaftertomorrow_currenttime=day_after_tomorrow,
            dayaftertomorrow_endofworkingday=end_of_working_day_after_tomorrow,
            dayaftertomorrow_endofday=day_after_tomorrow.endOfDay(),
            nextfriday_startofday=next_friday.startOfDay(),
            nextfriday_startofworkingday=start_of_working_next_friday,
            nextfriday_currenttime=next_friday,
            nextfriday_endofworkingday=end_of_working_next_friday,
            nextfriday_endofday=next_friday.endOfDay(),
            nextmonday_startofday=next_monday.startOfDay(),
            nextmonday_startofworkingday=start_of_working_next_monday,
            nextmonday_currenttime=next_monday,
            nextmonday_endofworkingday=end_of_working_next_monday,
            nextmonday_endofday=next_monday.endOfDay(),
        )

    def changeSettings(self):
        pass

    def test_suggested_planned_start_date_time(self):
        for time_value, expected_date_time in list(self.times.items()):
            settings.set(
                "view", "defaultplannedstartdatetime", "preset_" + time_value
            )
            self.assertEqual(
                expected_date_time,
                task.Task.suggestedPlannedStartDateTime(lambda: self.now),
            )

    def test_suggested_actual_start_date_time(self):
        for time_value, expected_date_time in list(self.times.items()):
            settings.set(
                "view", "defaultactualstartdatetime", "preset_" + time_value
            )
            self.assertEqual(
                expected_date_time,
                task.Task.suggestedActualStartDateTime(lambda: self.now),
            )

    def test_suggested_due_date_time(self):
        for time_value, expected_date_time in list(self.times.items()):
            settings.set("view", "defaultduedatetime", "propose_" + time_value)
            self.assertEqual(
                expected_date_time,
                task.Task.suggestedDueDateTime(lambda: self.now),
            )

    def test_suggested_completion_date_time(self):
        for time_value, expected_date_time in list(self.times.items()):
            settings.set(
                "view", "defaultcompletiondatetime", "propose_" + time_value
            )
            self.assertEqual(
                expected_date_time,
                task.Task.suggestedCompletionDateTime(lambda: self.now),
                "Expected %s, but got %s, with default completion date time "
                "set to %s"
                % (
                    expected_date_time,
                    task.Task.suggestedCompletionDateTime(lambda: self.now),
                    "preset_" + time_value,
                ),
            )

    def test_suggested_reminder_date_time(self):
        for time_value, expected_date_time in list(self.times.items()):
            settings.set(
                "view", "defaultreminderdatetime", "propose_" + time_value
            )
            self.assertEqual(
                expected_date_time,
                task.Task.suggestedReminderDateTime(lambda: self.now),
            )


class TaskSuggestedDateTimeTestWithDefaultStartAndEndOfWorkingDay(
    TaskSuggestedDateTimeBaseSetupAndTests, test.TestCase
):
    pass


class TaskSuggestedDateTimeTestWithStartAndEndOfWorkingDayEqualToDay(
    TaskSuggestedDateTimeBaseSetupAndTests, test.TestCase
):
    def changeSettings(self):
        settings.set("view", "efforthourstart", 0)
        settings.set("view", "efforthourend", 24)


class TaskConstructionTest(test.TestCase):
    def test_actual_start_date_time_is_not_determined_by_efforts_when_missing(
        self,
    ):
        new_task = task.Task(
            efforts=[effort.Effort(None, date.DateTime(2000, 1, 1))]
        )
        self.assertEqual(date.DateTime(), new_task.actualStartDateTime())

    def test_actual_start_given_is_not_determined_by_efforts(
        self,
    ):
        new_task = task.Task(
            actualStartDateTime=date.DateTime(2010, 1, 1),
            efforts=[effort.Effort(None, date.DateTime(2000, 1, 1))],
        )
        self.assertEqual(
            date.DateTime(2010, 1, 1), new_task.actualStartDateTime()
        )


class PlannedDurationTest(test.TestCase):
    """In Implicit mode the planned duration is due minus planned
    start, whichever way a date changes (docs/DURATION_CALCULATIONS.md,
    Stored Duration)."""

    def setUp(self):
        self.start = date.DateTime(2026, 10, 1, 9, 0, 0)
        self.task = task.Task(
            plannedStartDateTime=self.start,
            dueDateTime=self.start + date.ONE_HOUR,
        )

    def test_a_date_change_sets_it(self):
        self.task.set_due_date_time(self.start + date.ONE_DAY)
        self.assertEqual(date.ONE_DAY, self.task.plannedDuration())
        self.task.set_planned_start_date_time(self.start + date.ONE_HOUR)
        self.assertEqual(date.TimeDelta(hours=23), self.task.plannedDuration())

    def test_in_whole_minutes_as_the_editor_shows_the_dates(self):
        self.task.set_planned_start_date_time(
            date.DateTime(2026, 10, 1, 9, 0, 40)
        )
        self.task.set_due_date_time(date.DateTime(2026, 10, 1, 10, 30, 20))
        self.assertEqual(
            date.TimeDelta(hours=1, minutes=30), self.task.plannedDuration()
        )

    def test_a_negative_one_is_kept(self):
        self.task.set_due_date_time(self.start - date.ONE_HOUR)
        self.assertEqual(-date.ONE_HOUR, self.task.plannedDuration())

    def test_without_both_dates_it_stays(self):
        self.task.set_due_date_time(self.start + date.ONE_DAY)
        self.task.set_due_date_time(None)
        self.assertEqual(date.ONE_DAY, self.task.plannedDuration())

    def test_the_adjust_modes_keep_it(self):
        # There the editor moves the other date by it
        for mode in ("adjdue", "adjstart"):
            self.task.setPlannedDurationMode(mode)
            self.task.setPlannedDuration(date.ONE_HOUR)
            self.task.set_due_date_time(self.start + date.ONE_DAY)
            self.assertEqual(date.ONE_HOUR, self.task.plannedDuration())
            self.task.set_due_date_time(self.start + date.ONE_HOUR)

    def test_undo_puts_both_back_in_one_step(self):
        history = patterns.CommandHistory()
        self.addCleanup(history.clear)
        with history.action("Change due date"):
            self.task.set_due_date_time(self.start + date.ONE_DAY)
        history.undo()
        self.assertEqual(
            (self.start + date.ONE_HOUR, date.TimeDelta()),
            (self.task.dueDateTime(), self.task.plannedDuration()),
        )


# NOTE (Scheduler Refactoring - 2024):
# TaskScheduledTest and TaskNotScheduledTest were removed because they tested
# the old scheduler-based status transitions. With the new GlobalTimer architecture,
# status changes are handled by polling rather than individual scheduled jobs.
# See docs/SCHEDULERS.md for details.
