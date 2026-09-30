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

import ast
from taskcoachlib import patterns, config
from taskcoachlib.domain import task, effort, date, attachment, note, category
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

    def labelTaskChildrenAndEffort(self, parentTask, taskLabel):
        for childIndex, child in enumerate(parentTask.children()):
            childLabel = "%s_%d" % (taskLabel, childIndex + 1)
            setattr(self, childLabel, child)
            self.labelTaskChildrenAndEffort(child, childLabel)
            self.labelEfforts(child, childLabel)

    def labelEfforts(self, parentTask, taskLabel):
        for effortIndex, eachEffort in enumerate(parentTask.efforts()):
            effortLabel = "%seffort%d" % (taskLabel, effortIndex + 1)
            setattr(self, effortLabel, eachEffort)

    def setUp(self, settings=None):
        self.settings = task.Task.settings = config.Settings(load=False)
        if settings is not None:
            for section, name, value in settings:
                # XXXTODO: other types ? Not needed right now
                self.settings.setint(section, name, value)
        self.yesterday = date.Yesterday()
        self.tomorrow = date.Tomorrow()
        self.tasks = self.createTasks()
        self.task = self.tasks[0]
        for index, eachTask in enumerate(self.tasks):
            taskLabel = "task%d" % (index + 1)
            setattr(self, taskLabel, eachTask)
            self.labelTaskChildrenAndEffort(eachTask, taskLabel)
            self.labelEfforts(eachTask, taskLabel)
        for eventType in self.eventTypes:
            self.registerObserver(eventType)  # pylint: disable=W0201

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

    def addEffort(self, hours, taskToAddEffortTo=None):
        taskToAddEffortTo = taskToAddEffortTo or self.task
        start = date.DateTime(2005, 1, 1)
        taskToAddEffortTo.addEffort(
            effort.Effort(taskToAddEffortTo, start, start + hours)
        )

    def assertReminder(
        self, expectedReminder, taskWithReminder=None, recursive=False
    ):
        taskWithReminder = taskWithReminder or self.task
        self.assertEqual(
            expectedReminder, taskWithReminder.reminder(recursive=recursive)
        )

    def assertEvent(self, *expectedEventArgs):
        self.assertEqual([patterns.Event(*expectedEventArgs)], self.events)

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

    def testCopy(self):
        copy = self.task.copy()
        self.assertTaskCopy(copy, self.task)

    def testCopy_IdIsDifferent(self):
        copy = self.task.copy()
        self.assertNotEqual(copy.id(), self.task.id())


class NoBudgetTestsMixin(object):
    """These tests should succeed for all tasks without budget."""

    def testTaskHasNoBudget(self):
        self.assertEqual(date.TimeDelta(), self.task.budget())

    def testTaskHasNoRecursiveBudget(self):
        self.assertEqual(date.TimeDelta(), self.task.budget(recursive=True))

    def testTaskHasNoBudgetLeft(self):
        self.assertEqual(date.TimeDelta(), self.task.budgetLeft())

    def testTaskHasNoRecursiveBudgetLeft(self):
        self.assertEqual(
            date.TimeDelta(), self.task.budgetLeft(recursive=True)
        )


class DefaultTaskStateTest(
    TaskTestCase, CommonTaskTestsMixin, NoBudgetTestsMixin
):

    # Getters

    def testTaskHasNoDueDateTimeByDefault(self):
        self.assertEqual(date.DateTime(), self.task.dueDateTime())

    def testTaskHasNoRecursiveDueDateTimeByDefault(self):
        self.assertEqual(
            date.DateTime(), self.task.dueDateTime(recursive=True)
        )

    def testTaskHasNoPlannedStartDateTimeByDefault(self):
        self.assertEqual(date.DateTime(), self.task.plannedStartDateTime())

    def testTaskHasNoRecursivePlannedStartDateTimeByDefault(self):
        self.assertEqual(
            date.DateTime(), self.task.plannedStartDateTime(recursive=True)
        )

    def testTaskHasNoActualStartDateTimeByDefault(self):
        self.assertEqual(date.DateTime(), self.task.actualStartDateTime())

    def testTaskHasNoRecursiveActualStartDateTimeByDefault(self):
        self.assertEqual(
            date.DateTime(), self.task.actualStartDateTime(recursive=True)
        )

    def testTaskHasNoCompletionDateTimeByDefault(self):
        self.assertEqual(date.DateTime(), self.task.completionDateTime())

    def testTaskHasNoRecursiveCompletionDateTimeByDefault(self):
        self.assertEqual(
            date.DateTime(), self.task.completionDateTime(recursive=True)
        )

    def testTaskIsNotCompletedByDefault(self):
        self.assertFalse(self.task.completed())

    def testTaskIsNotActiveByDefault(self):
        self.assertFalse(self.task.active())

    def testTaskIsInactiveByDefault(self):
        self.assertTrue(self.task.inactive())

    def testTaskIsNotDueSoonByDefault(self):
        self.assertFalse(self.task.dueSoon())

    def testTaskHasNoDescriptionByDefault(self):
        self.assertEqual("", self.task.description())

    def testTaskHasNoChildrenByDefaultSoNotAllChildrenAreCompleted(self):
        self.assertFalse(self.task.allChildrenCompleted())

    def testTaskHasNoEffortByDefault(self):
        zero = date.TimeDelta()
        for recursive in False, True:
            self.assertEqual(zero, self.task.timeSpent(recursive=recursive))

    def testTaskPriorityIsZeroByDefault(self):
        for recursive in False, True:
            self.assertEqual(0, self.task.priority(recursive=recursive))

    def testTaskHasNoReminderSetByDefault(self):
        self.assertReminder(date.DateTime())

    def testTaskHasNoRecursiveReminderByDefault(self):
        self.assertReminder(date.DateTime(), recursive=True)

    def testShouldMarkTaskCompletedIsUndecidedByDefault(self):
        self.assertEqual(
            None, self.task.shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def testTaskHasNoAttachmentsByDefault(self):
        self.assertEqual([], self.task.attachments())

    def testTaskHasNoFixedFeeByDefault(self):
        for recursive in False, True:
            self.assertEqual(0, self.task.fixedFee(recursive=recursive))

    def testTaskHasNoRevenueByDefault(self):
        for recursive in False, True:
            self.assertEqual(0, self.task.revenue(recursive=recursive))

    def testTaskHasNoHourlyFeeByDefault(self):
        for recursive in False, True:
            self.assertEqual(0, self.task.hourlyFee(recursive=recursive))

    def testTaskDoesNotRecurByDefault(self):
        self.assertFalse(self.task.recurrence())

    def testTaskDoesNotHaveNotesByDefault(self):
        self.assertFalse(self.task.notes())

    def testPercentageCompleteIsZeroByDefault(self):
        self.assertEqual(0, self.task.percentageComplete())

    def testDefaultColor(self):
        self.assertEqual(None, self.task.foregroundColor())

    def testDefaultOwnIcon(self):
        self.assertEqual("", self.task.icon_id())

    def testDefaultRecursiveIcon(self):
        self.assertEqual(
            task.inactive.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testDefaultPrerequisites(self):
        self.assertFalse(self.task.prerequisites())

    def testDefaultRecursivePrerequisites(self):
        self.assertFalse(self.task.prerequisites(recursive=True))

    def testDefaultDependencies(self):
        self.assertFalse(self.task.dependencies())

    def testDefaultRecursiveDependencies(self):
        self.assertFalse(self.task.dependencies(recursive=True))

    # Setters

    def testSetPlannedStartDateTime(self):
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

    def testSetFuturePlannedStartDateTimeChangesIcon(self):
        self.task.set_planned_start_date_time(self.tomorrow)
        self.assertEqual(
            task.inactive.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testIconChangedAfterSetPlannedStartDateTimeHasPassed(self):
        self.task.set_planned_start_date_time(self.tomorrow)
        now = self.tomorrow + date.ONE_SECOND
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        self.assertEqual(
            task.late.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testSetActualStartDateTime(self):
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

    def testSetDueDateTime(self):
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

    def testIconChangedAfterSetDueDateTimeHasPassed(self):
        self.task.set_due_date_time(self.tomorrow)
        now = self.tomorrow + date.ONE_SECOND
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        self.assertEqual(
            task.overdue.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testIconChangedAfterTaskHasBecomeDueSoon(self):
        self.settings.setint("behavior", "duesoonhours", 1)
        self.task.set_due_date_time(self.tomorrow)
        now = self.tomorrow + date.ONE_SECOND - date.ONE_HOUR
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        self.assertEqual(
            task.duesoon.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testIconChangedAfterTaskHasBecomeDueSoonAccordingToNewDueSoonSetting(
        self,
    ):
        self.task.set_due_date_time(self.tomorrow)
        self.settings.setint("behavior", "duesoonhours", 1)
        now = self.tomorrow + date.ONE_SECOND - date.ONE_HOUR
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        self.assertEqual(
            task.duesoon.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testSetCompletionDateTime(self):
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

    def testSetCompletionDateTimeMakesTaskCompleted(self):
        self.task.set_completion_date_time()
        self.assertTrue(self.task.completed())

    def testSetCompletionDateTimeDefaultsToNow(self):
        self.task.set_completion_date_time()
        self.assertAlmostEqual(
            date.Now().toordinal(), self.task.completionDateTime().toordinal()
        )

    def testSetPercentageComplete(self):
        self.task.setPercentageComplete(50)
        self.assertEqual(50, self.task.percentageComplete())

    def testSetPercentageCompleteWhenMarkCompletedWhenAllChildrenCompletedIsTrue(
        self,
    ):
        self.task.set_should_mark_completed_when_all_children_completed(True)
        self.task.setPercentageComplete(50)
        self.assertEqual(50, self.task.percentageComplete())

    def testSet100PercentComplete(self):
        self.task.setPercentageComplete(100)
        self.assertTrue(self.task.completed())

    def test_percentage_complete_notification_via_completion_date_time(self):
        self.record_changes(task.Task.percentageCompleteChangedEventType())
        self.task.set_completion_date_time()
        self.assertEqual([(100, self.task)], self.changes)

    def testSetPercentageCompleteSetsActualStartDateTime(self):
        self.task.setPercentageComplete(50)
        self.assertNotEqual(date.DateTime(), self.task.actualStartDateTime())

    def testSetPercentageCompleteToZeroDoesNotSetActualStartDateTime(self):
        self.task.setPercentageComplete(50)
        self.task.set_actual_start_date_time(date.DateTime())
        self.task.setPercentageComplete(0)
        self.assertEqual(date.DateTime(), self.task.actualStartDateTime())

    def testSetDescription(self):
        self.task.setDescription("A new description")
        self.assertEqual("A new description", self.task.description())

    def testSetDescriptionNotification(self):
        self.registerObserver(task.Task.descriptionChangedEventType())
        self.task.setDescription("A new description")
        self.assertTrue("A new description", self.events[0].value())

    def testSetDescriptionUnchangedCausesNoNotification(self):
        self.registerObserver(task.Task.descriptionChangedEventType())
        self.task.setDescription(self.task.description())
        self.assertFalse(self.events)

    def testSetBudget(self):
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

    def testSetPriority(self):
        self.task.setPriority(10)
        self.assertEqual(10, self.task.priority())

    def testSetPriorityCausesNotification(self):
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task.setPriority(10)
        self.assertIn(self.task, self.events[0].sources())

    def testSetPriorityUnchangedCausesNoNotification(self):
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task.setPriority(self.task.priority())
        self.assertFalse(self.events)

    def testNegativePriority(self):
        self.task.setPriority(-1)
        self.assertEqual(-1, self.task.priority())

    def testSetFixedFee(self):
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

    def testSetHourlyFeeViaSetter(self):
        self.task.set_hourly_fee(100)
        self.assertEqual(100, self.task.hourlyFee())

    def test_set_hourly_fee_causes_notification(self):
        self.record_changes(task.Task.hourlyFeeChangedEventType())
        self.task.set_hourly_fee(100)
        self.assertEqual([(100, self.task)], self.changes)

    def testSetRecurrence(self):
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

    def testAddChildNotification(self):
        self.registerObserver(task.Task.addChildEventType())
        child = task.Task()
        self.task.addChild(child)
        self.assertEqual(child, self.events[0].value())

    def testAddCompletedChildAsOnlyChildMakesParentCompleted(self):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        child = task.Task(completionDateTime=self.yesterday)
        self.task.addChild(child)
        self.assertTrue(self.task.completed())

    def testAddActiveChildMakesParentActive(self):
        self.task.set_completion_date_time()
        child = task.Task()
        self.task.addChild(child)
        self.assertFalse(self.task.completed())

    def testAddChildWithLaterDueDateTimeDoesNotChangeParentDueDateTime(self):
        self.task.set_due_date_time(self.tomorrow)
        child = task.Task(dueDateTime=date.Now() + date.ONE_HOUR)
        self.task.addChild(child)
        self.assertEqual(self.tomorrow, self.task.dueDateTime())
        self.assertEqual(
            child.dueDateTime(), self.task.dueDateTime(recursive=True)
        )

    def testAddChildWithoutDueDateTimeDoesNotResetParentDueDateTime(self):
        dueDateTime = date.Now() + date.ONE_HOUR
        self.task.set_due_date_time(dueDateTime)
        child = task.Task()
        self.task.addChild(child)
        self.assertEqual(dueDateTime, self.task.dueDateTime())

    def testAddChildWithEarlierPlannedStartDateTimeDoesNotChangeParentsPlannedStartDateTime(
        self,
    ):
        originalPlannedStartDateTime = self.task.plannedStartDateTime()
        child = task.Task(plannedStartDateTime=self.yesterday)
        self.task.addChild(child)
        self.assertEqual(
            originalPlannedStartDateTime, self.task.plannedStartDateTime()
        )
        self.assertEqual(
            self.yesterday, self.task.plannedStartDateTime(recursive=True)
        )
        self.assertEqual(self.yesterday, child.plannedStartDateTime())

    def testAddChildWithEarlierActualStartDateTimeDoesNotChangeParentActualStartDateTime(
        self,
    ):
        originalActualStartDateTime = self.task.actualStartDateTime()
        child = task.Task(actualStartDateTime=self.yesterday)
        self.task.addChild(child)
        self.assertEqual(
            originalActualStartDateTime, self.task.actualStartDateTime()
        )
        self.assertEqual(
            self.yesterday, self.task.actualStartDateTime(recursive=True)
        )
        self.assertEqual(self.yesterday, child.actualStartDateTime())

    def testAddActiveRecurringChildWithEarlierPlannedStartDateTimeDoesNotChangeParentsPlannedStartDateTime(
        self,
    ):
        originalPlannedStartDateTime = self.task.plannedStartDateTime()
        child = task.Task(plannedStartDateTime=self.yesterday)
        child.set_recurrence(date.Recurrence("monthly"))
        self.task.addChild(child)
        self.assertEqual(
            originalPlannedStartDateTime, self.task.plannedStartDateTime()
        )
        self.assertEqual(
            self.yesterday, self.task.plannedStartDateTime(recursive=True)
        )
        self.assertEqual(self.yesterday, child.plannedStartDateTime())

    def testAddActiveRecurringChildWithEarlierActualStartDateTimeDoesNotChangeParentActualStartDateTime(
        self,
    ):
        originalActualStartDateTime = self.task.actualStartDateTime()
        child = task.Task(actualStartDateTime=self.yesterday)
        child.set_recurrence(date.Recurrence("monthly"))
        self.task.addChild(child)
        self.assertEqual(
            originalActualStartDateTime, self.task.actualStartDateTime()
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
        childEffort = effort.Effort(
            child,
            date.DateTime(2000, 1, 1, 10, 0, 0),
            date.DateTime(2000, 1, 1, 11, 0, 0),
        )
        child.addEffort(childEffort)
        events = test.ChangeRecorder(task.Task.timeSpentChangedEventType())
        self.task.addChild(child)
        self.assertEqual([(self.task.timeSpent(), self.task)], events)

    def test_add_child_without_effort_causes_no_time_spent_notification(self):
        events = test.ChangeRecorder(task.Task.timeSpentChangedEventType())
        self.task.addChild(task.Task())
        self.assertFalse(events)

    def testAddChildWithHigherPriorityCausesPriorityNotification(self):
        self.registerObserver(task.Task.priorityChangedEventType())
        child = task.Task(priority=10)
        self.task.addChild(child)
        self.assertIn(self.task, self.events[0].sources())

    def testAddChildWithLowerPriorityCausesNoPriorityNotification(self):
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

    def testNewChild_WithSubject(self):
        child = self.task.newChild(subject="Test")
        self.assertEqual("Test", child.subject())

    # Add effort

    def test_add_effort_causes_no_budget_left_notification(self):
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.task.addEffort(effort.Effort(self.task))
        self.assertFalse(events)

    def test_add_active_effort_causes_start_tracking_notification(self):
        events = test.ChangeRecorder(self.task.trackingChangedEventType())
        activeEffort = effort.Effort(self.task)
        self.task.addEffort(activeEffort)
        self.assertEqual([(True, self.task)], events)

    def testAddEffortSetActualStartDateTime(self):
        now = date.Now()
        self.task.addEffort(effort.Effort(self.task, now))
        self.assertEqual(now, self.task.actualStartDateTime())

    # Notes:

    def testAddNote(self):
        aNote = note.Note()
        self.task.addNote(aNote)
        self.assertEqual([aNote], self.task.notes())

    def testAddNoteCausesNotification(self):
        eventType = task.Task.notesChangedEventType()  # pylint: disable=E1101
        self.registerObserver(eventType)
        aNote = note.Note()
        self.task.addNote(aNote)
        self.assertEvent(eventType, self.task, aNote)

    # Prerequisites

    def testAddOnePrerequisite(self):
        prerequisites = set([task.Task()])
        self.task.add_prerequisites(prerequisites)
        self.assertEqual(prerequisites, self.task.prerequisites())

    def testAddTwoPrerequisites(self):
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

    def testRemovePrerequisiteThatHasNotBeenAdded(self):
        prerequisite = task.Task()
        self.task.remove_prerequisites([prerequisite])
        self.assertFalse(self.task.prerequisites())

    def testAddPrerequisiteKeepsTaskInactive(self):
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

    def testAddOneDependency(self):
        dependencies = set([task.Task()])
        self.task.add_dependencies(dependencies)
        self.assertEqual(dependencies, self.task.dependencies())

    def testAddTwoDependencies(self):
        dependencies = set([task.Task(), task.Task()])
        self.task.add_dependencies(dependencies)
        self.assertEqual(dependencies, self.task.dependencies())

    def test_add_dependency_causes_notification(self):
        event_type = task.Task.dependenciesChangedEventType()
        self.registerObserver(event_type)
        self.task.add_dependencies([task.Task()])
        self.assertEqual([{self.task}], self.sources_of(event_type))

    def testRemoveDependencyThatHasNotBeenAdded(self):
        dependency = task.Task()
        self.task.remove_dependencies([dependency])
        self.assertFalse(self.task.dependencies())

    # State (FIXME: need to test other attributes too)

    def testTaskStateIncludesPriority(self):
        state = self.task.__getstate__()
        self.task.setPriority(10)
        self.task.__setstate__(state)
        self.assertEqual(0, self.task.priority())

    def testTaskStateIncludesRecurrence(self):
        state = self.task.__getstate__()
        self.task.set_recurrence(date.Recurrence("weekly"))
        self.task.__setstate__(state)
        self.assertFalse(self.task.recurrence())

    def testTaskStateIncludesNotes(self):
        state = self.task.__getstate__()
        self.task.addNote(note.Note())
        self.task.__setstate__(state)
        self.assertFalse(self.task.notes())

    def testTaskStateIncludesReminder(self):
        state = self.task.__getstate__()
        self.task.set_reminder(
            date.DateTime.now() + date.TimeDelta(seconds=10)
        )
        self.task.__setstate__(state)
        self.assertEqual(date.DateTime(), self.task.reminder())

    def testTaskStateIncludesPlannedStartDateTime(self):
        previousPlannedStartDateTime = self.task.plannedStartDateTime()
        state = self.task.__getstate__()
        self.task.set_planned_start_date_time(self.yesterday)
        self.task.__setstate__(state)
        self.assertEqual(
            previousPlannedStartDateTime, self.task.plannedStartDateTime()
        )

    def testTaskStateIncludesActualStartDateTime(self):
        previousActualStartDateTime = self.task.actualStartDateTime()
        state = self.task.__getstate__()
        self.task.set_actual_start_date_time(self.yesterday)
        self.task.__setstate__(state)
        self.assertEqual(
            previousActualStartDateTime, self.task.actualStartDateTime()
        )

    def testTaskStateIncludesDueDateTime(self):
        previousDueDateTime = self.task.dueDateTime()
        state = self.task.__getstate__()
        self.task.set_due_date_time(self.yesterday)
        self.task.__setstate__(state)
        self.assertEqual(previousDueDateTime, self.task.dueDateTime())

    def testTaskStateIncludesCompletionDateTime(self):
        previousCompletionDateTime = self.task.completionDateTime()
        state = self.task.__getstate__()
        self.task.set_completion_date_time(self.yesterday)
        self.task.__setstate__(state)
        self.assertEqual(
            previousCompletionDateTime, self.task.completionDateTime()
        )

    def testTaskStateIncludesPrerequisites(self):
        self.task.add_prerequisites([task.Task(subject="prerequisite1")])
        previousPrerequisites = self.task.prerequisites()
        state = self.task.__getstate__()
        self.task.add_prerequisites([task.Task(subject="prerequisite2")])
        self.task.__setstate__(state)
        self.assertEqual(previousPrerequisites, self.task.prerequisites())

    def testTaskStateIncludesDependencies(self):
        self.task.add_dependencies([task.Task(subject="dependency1")])
        previousDependencies = self.task.dependencies()
        state = self.task.__getstate__()
        self.task.add_dependencies([task.Task(subject="dependency2")])
        self.task.__setstate__(state)
        self.assertEqual(previousDependencies, self.task.dependencies())

    def testModificationEventTypes(self):  # pylint: disable=E1003
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
        self.hours = self.settings.getint("behavior", "duesoonhours")

    def status_at(self, moment):
        self.task.compute_stored_status(moment)
        return self.task.computedStatus()

    def assert_starts_at(self, expected_status, second):
        before = second - date.ONE_SECOND
        self.assertNotEqual(expected_status, self.status_at(before))
        self.assertEqual(expected_status, self.status_at(second))

    def timer_second(self, index):
        return self.task.timer_seconds(self.hours)[index]

    def test_late_from_the_second_after_the_planned_start(self):
        self.task.set_planned_start_date_time(self.moment)
        self.assertEqual(self.moment + date.ONE_SECOND, self.timer_second(0))
        self.assert_starts_at(task.status.late, self.timer_second(0))

    def test_active_from_the_actual_start(self):
        self.task.set_actual_start_date_time(self.moment)
        self.assertEqual(self.moment, self.timer_second(1))
        self.assert_starts_at(task.status.active, self.timer_second(1))

    def test_due_soon_from_the_second_after_due_less_the_hours(self):
        self.task.set_due_date_time(self.moment)
        due_soon = self.moment - date.TimeDelta(hours=self.hours)
        self.assertEqual(due_soon + date.ONE_SECOND, self.timer_second(2))
        self.assert_starts_at(task.status.duesoon, self.timer_second(2))

    def test_overdue_from_the_second_after_the_due(self):
        self.task.set_due_date_time(self.moment)
        self.assertEqual(self.moment + date.ONE_SECOND, self.timer_second(3))
        self.assert_starts_at(task.status.overdue, self.timer_second(3))

    def test_reminder_fires_from_its_second(self):
        self.task.set_reminder(self.moment)
        second = self.timer_second(4)
        self.registerObserver("task.reminder.trigger")
        self.task.processReminder(second - date.ONE_SECOND)
        self.assertEqual([], self.events)
        self.task.processReminder(second)
        self.assertEqual(1, len(self.events))

    def test_dates_not_set_give_seconds_never_reached(self):
        seconds = self.task.timer_seconds(self.hours)
        self.assertEqual(date.DateTime(), max(seconds))
        self.assertLess(date.DateTime(9999, 12, 1), min(seconds))

    def test_a_completed_task_keeps_its_seconds(self):
        self.task.set_due_date_time(self.moment)
        self.task.set_completion_date_time(self.moment)
        self.assertEqual(self.moment + date.ONE_SECOND, self.timer_second(3))


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

    def testIsDueSoon(self):
        self.assertTrue(self.task.dueSoon())

    def testDaysLeft(self):
        self.assertEqual(0, self.task.timeLeft().days)

    def testDueDateTime(self):
        self.assertAlmostEqual(
            self.dueDateTime.toordinal(), self.task.dueDateTime().toordinal()
        )

    def testDefaultDueSoonColor(self):
        expectedColor = wx.Colour(
            *ast.literal_eval(self.settings.get("fgcolor", "duesoontasks"))
        )
        self.assertEqual(
            expectedColor, test.styled(self.task).shown_fg_color()
        )

    def testColorWhenTaskHasOwnColor(self):
        color = wx.Colour(191, 128, 64, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, test.styled(self.task).shown_fg_color())

    def testIcon(self):
        self.assertEqual(
            task.duesoon.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testIconAfterChangingDueSoonHours(self):
        self.settings.setint("behavior", "duesoonhours", 0)
        self.assertEqual(
            task.inactive.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_changing_due_soon_hours(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        self.settings.setint("behavior", "duesoonhours", 0)
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)

    def testIconAfterDueDateTimeHasPassed(self):
        now = self.task.dueDateTime() + date.ONE_SECOND
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.task.compute_stored_status()
        self.assertEqual(
            task.overdue.icon_id(self.settings),
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

    def testDaysLeft(self):
        self.assertEqual(1, self.task.timeLeft().days)

    def testDueDateTime(self):
        self.assertAlmostEqual(
            self.taskCreationKeywordArguments()[0]["dueDateTime"].toordinal(),
            self.task.dueDateTime().toordinal(),
        )

    def testDueSoon(self):
        self.assertFalse(self.task.dueSoon())

    def testDueSoon_2days(self):
        self.settings.setint("behavior", "duesoonhours", 48)
        self.assertTrue(self.task.dueSoon())

    def testIconNotDueSoon(self):
        self.assertEqual(
            task.inactive.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testIconDueSoon(self):
        self.settings.setint("behavior", "duesoonhours", 48)
        self.assertEqual(
            task.duesoon.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_changing_due_soon_hours(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        self.settings.setint("behavior", "duesoonhours", 48)
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)


class OverdueTaskTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"dueDateTime": self.yesterday}]

    def testIsOverdue(self):
        self.assertTrue(self.task.overdue())

    def testCompletedOverdueTaskIsNoLongerOverdue(self):
        self.task.set_completion_date_time()
        self.assertFalse(self.task.overdue())

    def testDueDateTime(self):
        self.assertAlmostEqual(
            self.taskCreationKeywordArguments()[0]["dueDateTime"].toordinal(),
            self.task.dueDateTime().toordinal(),
        )

    def testDefaultOverdueColor(self):
        expectedColor = wx.Colour(
            *ast.literal_eval(self.settings.get("fgcolor", "overduetasks"))
        )
        self.assertEqual(
            expectedColor, test.styled(self.task).shown_fg_color()
        )

    def testColorWhenTaskHasOwnColor(self):
        color = wx.Colour(191, 64, 64, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, test.styled(self.task).shown_fg_color())

    def testIcon(self):
        self.assertEqual(
            task.overdue.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testIconAfterChangingDueDateTime(self):
        self.task.set_due_date_time(date.Now() + date.TimeDelta(hours=72))
        self.assertEqual(
            task.inactive.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_changing_due_date_time(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        self.task.set_due_date_time(date.Now() + date.TimeDelta(hours=72))
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)

    def testIconAfterMarkingComplete(self):
        self.task.set_completion_date_time()
        self.assertEqual(
            task.completed.icon_id(self.settings),
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

    def testATaskWithACompletionDateIsCompleted(self):
        self.assertTrue(self.task.completed())

    def testSettingTheCompletionDateTimeToInfiniteMakesTheTaskUncompleted(
        self,
    ):
        self.task.set_completion_date_time(date.DateTime())
        self.assertFalse(self.task.completed())
        self.assertEqual(0, self.task.percentageComplete())

    def testSettingTheCompletionDateTimeToAnotherDateTimeLeavesTheTaskCompleted(
        self,
    ):
        self.task.set_completion_date_time(self.yesterday)
        self.assertTrue(self.task.completed())

    def testCompletedTaskIsHundredProcentComplete(self):
        self.assertEqual(100, self.task.percentageComplete())

    def testSetPercentageCompleteToLessThan100MakesTaskUncompleted(self):
        self.task.setPercentageComplete(99)
        self.assertEqual(date.DateTime(), self.task.completionDateTime())
        self.assertEqual(99, self.task.percentageComplete())

    def test_percentage_complete_notification(self):
        self.record_changes(task.Task.percentageCompleteChangedEventType())
        self.task.set_completion_date_time(date.DateTime.max)
        self.assertEqual([(0, self.task)], self.changes)

    def testDefaultCompletedColor(self):
        expectedColor = wx.Colour(
            *ast.literal_eval(self.settings.get("fgcolor", "completedtasks"))
        )
        self.assertEqual(
            expectedColor, test.styled(self.task).shown_fg_color()
        )

    def testColorWhenTaskHasOwnColor(self):
        color = wx.Colour(64, 191, 64, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, test.styled(self.task).shown_fg_color())

    def testIcon(self):
        self.assertEqual(
            task.completed.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testIconAfterMarkingUncomplete(self):
        self.task.set_completion_date_time(date.DateTime.max)
        self.assertEqual(
            task.inactive.icon_id(self.settings),
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

    def testAHundredProcentCompleteTaskIsCompleted(self):
        self.assertTrue(self.task.completed())


class TaskCompletedInTheFutureTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"completionDateTime": self.tomorrow}]

    def testATaskWithAFutureCompletionDateIsCompleted(self):
        self.assertTrue(self.task.completed())


class TaskWithPlannedStartDateInTheFutureTest(
    TaskTestCase, CommonTaskTestsMixin
):
    def taskCreationKeywordArguments(self):
        return [
            {"plannedStartDateTime": self.tomorrow},
            {"subject": "prerequisite"},
        ]

    def testTaskWithStartDateInTheFutureIsInactive(self):
        self.assertTrue(self.task.inactive())

    def testTaskWithPlannedStartDateInTheFutureIsInactiveEvenWhenAllPrerequisitesAreCompleted(
        self,
    ):
        # pylint: disable=E1101
        self.task.add_prerequisites([self.task2])
        self.task2.add_dependencies([self.task])
        self.task2.set_completion_date_time()
        self.assertTrue(self.task.inactive())

    def testACompletedTaskWithPlannedStartDateTimeInTheFutureIsNotInactive(
        self,
    ):
        self.task.set_completion_date_time()
        self.assertFalse(self.task.inactive())

    def testPlannedStartDateTime(self):
        self.assertEqual(self.tomorrow, self.task.plannedStartDateTime())

    def testSetActualStartDateTimeToTodayMakesTaskActive(self):
        self.task.set_actual_start_date_time(date.Now())
        self.assertTrue(self.task.active())

    def testDefaultInactiveColor(self):
        expectedColor = wx.Colour(
            *ast.literal_eval(self.settings.get("fgcolor", "inactivetasks"))
        )
        self.assertEqual(
            expectedColor, test.styled(self.task).shown_fg_color()
        )

    def testColorWhenTaskHasOwnColor(self):
        color = wx.Colour(160, 160, 160, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, test.styled(self.task).shown_fg_color())

    def testIcon(self):
        self.assertEqual(
            task.inactive.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testIconAfterPlannedStartDateTimeHasPassed(self):
        now = self.task.plannedStartDateTime() + date.ONE_SECOND
        self.addCleanup(setattr, date, "Now", date.Now)
        date.Now = lambda: now
        self.run_scheduler_tick(self.task)
        self.assertEqual(
            task.late.icon_id(self.settings),
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

    def testIconAfterMarkingComplete(self):
        self.task.set_completion_date_time()
        self.assertEqual(
            task.completed.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def test_icon_event_after_marking_complete(self):
        test.styled(self.task)
        self.registerObserver(self.task.effectiveIconChangedEventType())
        self.task.set_completion_date_time()
        test.styled(self.task)
        self.assertEvent(self.task.effectiveIconChangedEventType(), self.task)

    def testIconAfterChangingPlannedStartDateTime(self):
        self.task.set_planned_start_date_time(
            date.Now() - date.TimeDelta(hours=72)
        )
        self.assertEqual(
            task.late.icon_id(self.settings),
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

    def testTaskWithPlannedStartDateTimeInThePastIsActive(self):
        self.assertFalse(self.task.inactive())

    def testTaskBecomesInactiveWhenAddingAnUncompletedPrerequisite(self):
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

    def testTaskBecomesActiveWhenUncompletedPrerequisiteIsCompleted(self):
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

    def testTaskWithoutPlannedStartDateTimeIsInactive(self):
        self.assertTrue(self.task.inactive())

    def testTaskStaysInactiveWhenUncompletedPrerequisiteIsCompleted(self):
        # pylint: disable=E1101
        self.task.add_prerequisites([self.task2])
        self.task2.add_dependencies([self.task])
        self.task2.set_completion_date_time()
        self.assertTrue(self.task.inactive())
        self.assertEqual(
            task.inactive.icon_id(self.settings),
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

    def testIcon(self):
        self.assertEqual(
            task.inactive.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testPlannedStartDateTime(self):
        for recursive in (False, True):
            self.assertEqual(
                self.tomorrow,
                self.task.plannedStartDateTime(recursive=recursive),
            )


class TaskWithSubject(TaskTestCase, CommonTaskTestsMixin):
    eventTypes = [task.Task.subjectChangedEventType()]

    def taskCreationKeywordArguments(self):
        return [{"subject": "Subject"}]

    def testSubject(self):
        self.assertEqual("Subject", self.task.subject())

    def testSetSubject(self):
        self.task.setSubject("Done")
        self.assertEqual("Done", self.task.subject())

    def testSetSubjectNotification(self):
        self.task.setSubject("Done")
        self.assertEvent(
            task.Task.subjectChangedEventType(), self.task, "Done"
        )

    def testSetSubjectUnchangedDoesNotTriggerNotification(self):
        self.task.setSubject(self.task.subject())
        self.assertFalse(self.events)

    def testRepresentationEqualsSubject(self):
        self.assertEqual(self.task.subject(), repr(self.task))


class TaskWithDescriptionTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"description": "Description"}]

    def testDescription(self):
        self.assertEqual("Description", self.task.description())

    def testSetDescription(self):
        self.task.setDescription("New description")
        self.assertEqual("New description", self.task.description())


# pylint: disable=E1101


class TwoTasksTest(TaskTestCase):
    def taskCreationKeywordArguments(self):
        return [{}, {}]

    def testTwoDefaultTasksAreNotEqual(self):
        self.assertNotEqual(self.task1, self.task2)


class NewChildTest(TaskTestCase):
    def setUp(self):
        super().setUp()
        self.child = self.task.newChild()

    def testNewChildHasNoDueDateTimeByDefault(self):
        self.assertEqual(date.DateTime(), self.child.dueDateTime())

    def testNewChildHasNoPlannedStartDateTimeByDefault(self):
        self.assertEqual(date.DateTime(), self.child.plannedStartDateTime())

    def testNewChildHasNoActualStartDateTimeByDefault(self):
        self.assertEqual(date.DateTime(), self.child.actualStartDateTime())

    def testNewChildHasNoCompletionDateTimeByDefault(self):
        self.assertEqual(date.DateTime(), self.child.completionDateTime())

    def testNewChildHasNoReminderByDefault(self):
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

    def testRemoveChildNotification(self):
        self.registerObserver(task.Task.removeChildEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEvent(
            task.Task.removeChildEventType(), self.task1, self.task1_1
        )

    def testRemoveNonExistingChildCausesNoNotification(self):
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
        childEffort = effort.Effort(
            self.task1_1,
            date.DateTime(2005, 1, 1, 11, 0, 0),
            date.DateTime(2005, 1, 1, 12, 0, 0),
        )
        self.task1_1.addEffort(childEffort)
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

    def testRemoveChildWithHighPriorityCausesPriorityNotification(self):
        self.task1_1.setPriority(10)
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertIn(self.task1, self.events[0].sources())

    def testRemoveChildWithLowPriorityCausesNoTotalPriorityNotification(self):
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

    def testSettingParentDueDateTimeEarlierThanChildDueDateTimeDoesNotChangeChildDueDateTime(
        self,
    ):
        childDueDateTime = date.Now() + date.TWO_HOURS
        self.task1_1.set_due_date_time(childDueDateTime)
        parentDueDateTime = date.Now() + date.ONE_HOUR
        self.task1.set_due_date_time(parentDueDateTime)
        self.assertEqual(childDueDateTime, self.task1_1.dueDateTime())

    def testSettingChildDueDateTimeLaterThanParentDueDateTimeDoesNotChangeParentDueDateTime(
        self,
    ):
        parentDueDateTime = date.Now() + date.ONE_HOUR
        self.task1.set_due_date_time(parentDueDateTime)
        childDueDateTime = date.Now() + date.TWO_HOURS
        self.task1_1.set_due_date_time(childDueDateTime)
        self.assertEqual(parentDueDateTime, self.task1.dueDateTime())

    def testRecursiveDueDateTime(self):
        self.assertEqual(
            date.DateTime(), self.task1.dueDateTime(recursive=True)
        )

    def testRecursiveDueDateTimeWhenChildDueToday(self):
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

    def testRecursiveDueDateTimeWhenChildDueTodayAndCompleted(self):
        self.task1_1.set_due_date_time(date.Now())
        self.task1_1.set_completion_date_time(date.Now())
        self.assertEqual(
            date.DateTime(), self.task1.dueDateTime(recursive=True)
        )

    def testSettingPlannedStartDateTimeLaterThanChildPlannedStartDateTime(
        self,
    ):
        childPlannedStartDateTime = self.task1_1.plannedStartDateTime()
        self.task1.set_planned_start_date_time(self.tomorrow)
        self.assertEqual(self.tomorrow, self.task1.plannedStartDateTime())
        self.assertEqual(
            childPlannedStartDateTime,
            self.task1.plannedStartDateTime(recursive=True),
        )
        self.assertEqual(
            childPlannedStartDateTime, self.task1_1.plannedStartDateTime()
        )

    def testSettingPlannedStartDateTimeEarlierThanParentPlannedStartDateTime(
        self,
    ):
        parentPlannedStartDateTime = self.task1.plannedStartDateTime()
        self.task1_1.set_planned_start_date_time(self.yesterday)
        self.assertEqual(self.yesterday, self.task1_1.plannedStartDateTime())
        self.assertEqual(
            self.yesterday, self.task1.plannedStartDateTime(recursive=True)
        )
        self.assertEqual(
            parentPlannedStartDateTime, self.task1.plannedStartDateTime()
        )

    def testRecursivePlannedStartDateTime(self):
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

    def testRecursivePlannedStartDateTimeWhenChildStartsYesterday(self):
        self.task1_1.set_planned_start_date_time(self.yesterday)
        self.assertEqual(
            self.yesterday, self.task1.plannedStartDateTime(recursive=True)
        )

    def testRecursiveActualStartDateTime(self):
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

    def testRecursiveActualStartDateTimeWhenChildStartsYesterday(self):
        self.task1_1.set_actual_start_date_time(self.yesterday)
        self.assertEqual(
            self.yesterday, self.task1.actualStartDateTime(recursive=True)
        )

    def testRecursiveCompletionDateTime(self):
        self.settings.setboolean(
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

    def testRecursiveCompletionDateTimeWhenChildIsCompletedYesterday(self):
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

    def testNotAllChildrenAreCompleted(self):
        self.assertFalse(self.task1.allChildrenCompleted())

    def testAllChildrenAreCompletedAfterMarkingTheOnlyChildAsCompleted(self):
        self.task1_1.set_completion_date_time()
        self.assertTrue(self.task1.allChildrenCompleted())

    def testTimeLeftRecursivelyIsInfinite(self):
        self.assertEqual(
            date.TimeDelta.max, self.task1.timeLeft(recursive=True)
        )

    def testTimeSpentRecursivelyIsZero(self):
        self.assertEqual(date.TimeDelta(), self.task.timeSpent(recursive=True))

    def testRecursiveBudgetWhenParentHasNoBudgetWhileChildDoes(self):
        self.task1_1.set_budget(date.ONE_HOUR)
        self.assertEqual(date.ONE_HOUR, self.task.budget(recursive=True))

    def testRecursiveBudgetLeftWhenParentHasNoBudgetWhileChildDoes(self):
        self.task1_1.set_budget(date.ONE_HOUR)
        self.assertEqual(date.ONE_HOUR, self.task.budgetLeft(recursive=True))

    def testRecursiveBudgetWhenBothHaveBudget(self):
        self.task1_1.set_budget(date.ONE_HOUR)
        self.task.set_budget(date.ONE_HOUR)
        self.assertEqual(date.TWO_HOURS, self.task.budget(recursive=True))

    def testRecursiveBudgetLeftWhenBothHaveBudget(self):
        self.task1_1.set_budget(date.ONE_HOUR)
        self.task.set_budget(date.ONE_HOUR)
        self.assertEqual(date.TWO_HOURS, self.task.budgetLeft(recursive=True))

    def testRecursiveBudgetLeftWhenChildBudgetIsAllSpent(self):
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
        childEffort = effort.Effort(
            self.task1_1,
            date.DateTime(2005, 1, 1, 10, 0, 0),
            date.DateTime(2005, 1, 1, 11, 0, 0),
        )
        self.task1_1.addEffort(childEffort)
        events = test.ChangeRecorder(task.Task.timeSpentChangedEventType())
        childEffort.setStop(date.DateTime(2005, 1, 1, 12, 0, 0))
        self.assertTrue((self.task1.timeSpent(), self.task1) in events)

    def test_subtask_recurrence_change_names_the_chain(self):
        # A collapsed ancestor shows its subtasks' shortest recurrence
        self.registerObserver(task.Task.recurrenceChangedEventType())
        self.task1_1.set_recurrence(date.Recurrence("weekly"))
        self.assertEqual({self.task1_1, self.task1}, self.events[0].sources())

    def testRecursivePriorityNotification(self):
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task1_1.setPriority(10)
        sources = self.events[0].sources()
        self.assertIn(self.task1_1, sources)
        self.assertIn(self.task1, sources)

    def testPriorityNotification_WithLowerChildPriority(self):
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

    def testIsBeingTrackedRecursiveWhenChildIsNotTracked(self):
        self.assertFalse(self.task1.isBeingTracked(recursive=True))

    def testIsBeingTrackedRecursiveWhenChildIsTracked(self):
        self.assertFalse(self.task1.isBeingTracked(recursive=True))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        self.assertTrue(self.task1.isBeingTracked(recursive=True))

    def test_notification_when_child_is_being_tracked(self):
        events = test.ChangeRecorder(self.task1.trackingChangedEventType())
        activeEffort = effort.Effort(self.task1_1)
        self.task1_1.addEffort(activeEffort)
        self.assertEqual(
            set([(True, self.task1), (True, self.task1_1)]), set(events)
        )

    def test_notification_when_child_tracking_stops(self):
        activeEffort = effort.Effort(self.task1_1)
        self.task1_1.addEffort(activeEffort)
        events = test.ChangeRecorder(task.Task.trackingChangedEventType())
        activeEffort.setStop()
        self.assertEqual(
            set([(False, self.task), (False, self.task1_1)]), set(events)
        )

    def test_set_fixed_fee_of_child(self):
        self.record_changes(task.Task.fixedFeeChangedEventType())
        self.task1_1.set_fixed_fee(1000)
        self.assertTrue((1000, self.task1) in self.changes)

    def testGetFixedFeeRecursive(self):
        self.task.set_fixed_fee(2000)
        self.task1_1.set_fixed_fee(1000)
        self.assertEqual(3000, self.task.fixedFee(recursive=True))

    def testRecursiveRevenueFromFixedFee(self):
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

    def testChildUsesForegroundColorOfParentsCategory(self):
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
            task.completed.icon_id(self.settings),
            self.task1_1.shown_icon_id(),
        )
        self.assertEqual(
            self.task1_1.statusFgColor(), self.task1_1.shown_fg_color()
        )

    def test_child_of_a_tracked_task_shows_its_own_icon(self):
        self.task.addEffort(effort.Effort(self.task))
        self.assertEqual(
            task.active.icon_id(self.settings),
            test.styled(self.task1_1).shown_icon_id(),
        )

    def testPercentageCompleted(self):
        self.assertEqual(0, self.task.percentageComplete(recursive=True))

    def testPercentageCompletedWhenChildIs50ProcentComplete(self):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.task1_1.setPercentageComplete(50)
        self.assertEqual(50, self.task.percentageComplete(recursive=True))

    def testPercentageCompletedWhenChildIs50ProcentCompleteAndMarkCompletedWhenChildrenAreCompletedIsTurnedOff(
        self,
    ):
        self.task.set_should_mark_completed_when_all_children_completed(False)
        self.task1_1.setPercentageComplete(50)
        self.assertEqual(25, self.task.percentageComplete(recursive=True))

    def testPercentageCompletedWhenChildIs50ProcentCompleteAndGlobalMarkCompletedWhenChildrenAreCompletedIsTurnedOff(
        self,
    ):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", False
        )
        self.task1_1.setPercentageComplete(50)
        self.assertEqual(25, self.task.percentageComplete(recursive=True))

    def test_percentage_completed_notification_when_child_percentage_changes(
        self,
    ):
        self.settings.setboolean(
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
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.task1_1.setPercentageComplete(50)
        self.record_changes(task.Task.percentageCompleteChangedEventType())
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", False
        )
        self.assertEqual([(0, self.task)], self.changes)

    def testIcon(self):
        self.assertEqual(
            task.active.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testChildIcon(self):
        self.assertEqual(
            task.active.icon_id(self.settings),
            test.styled(self.task1_1).shown_icon_id(),
        )

    def test_chosen_icon_of_a_task_with_subtasks_is_shown_as_is(self):
        self.task.set_icon_id("nuvola_actions_ledgreen")
        self.assertEqual(
            "nuvola_actions_ledgreen", test.styled(self.task).shown_icon_id()
        )

    def testChildIsInactiveWhenParentHasPrerequisite(self):
        prerequisite = task.Task()
        self.task.add_prerequisites([prerequisite])
        self.assertTrue(self.task1_1.inactive())

    def testChildIsNotActiveWhenParentHasPrerequisite(self):
        prerequisite = task.Task()
        self.task.add_prerequisites([prerequisite])
        self.assertFalse(self.task1_1.active())

    def test_adding_prerequisite_to_parent_recomputes_child_appearance(self):
        # First make sure the icon is cached:
        self.assertEqual(
            task.active.icon_id(self.settings),
            test.styled(self.task1_1).shown_icon_id(),
        )
        prerequisite = task.Task()
        self.task.add_prerequisites([prerequisite])
        self.assertEqual(
            task.inactive.icon_id(self.settings),
            test.styled(self.task1_1).shown_icon_id(),
        )

    def test_setting_prerequisites_of_parent_recomputes_child_appearance(self):
        # First make sure the icon is cached:
        self.assertEqual(
            task.active.icon_id(self.settings),
            test.styled(self.task1_1).shown_icon_id(),
        )
        prerequisite = task.Task()
        self.task.set_prerequisites([prerequisite])
        self.assertEqual(
            task.inactive.icon_id(self.settings),
            test.styled(self.task1_1).shown_icon_id(),
        )

    def test_removing_prerequisite_from_parent_recomputes_child_appearance(
        self,
    ):
        prerequisite = task.Task()
        self.task.add_prerequisites([prerequisite])
        # First make sure the icon is cached:
        self.assertEqual(
            task.inactive.icon_id(self.settings),
            test.styled(self.task1_1).shown_icon_id(),
        )
        self.task.remove_prerequisites([prerequisite])
        # The child has an actual start date: active, not late
        self.assertEqual(
            task.active.icon_id(self.settings),
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
            task.inactive.icon_id(self.settings),
            test.styled(self.task1_1).shown_icon_id(),
        )
        prerequisite.set_completion_date_time(date.Now())
        # The child has an actual start date: active, not late
        self.assertEqual(
            task.active.icon_id(self.settings),
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

    def testRemoveLastActiveChildCompletesParent(self):
        self.task.set_should_mark_completed_when_all_children_completed(True)
        self.task1_1.set_completion_date_time()
        self.task.removeChild(self.task1_2)
        self.assertTrue(self.task.completed())

    def testPercentageCompletedWhenOneChildIs50ProcentComplete(self):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.task1_1.setPercentageComplete(50)
        self.assertEqual(25, self.task.percentageComplete(recursive=True))

    def testPercentageCompletedWhenOneChildIs50ProcentCompleteAndMarkCompletedWhenChildrenAreCompletedIsTurnedOff(
        self,
    ):
        self.task.set_should_mark_completed_when_all_children_completed(False)
        self.task1_1.setPercentageComplete(50)
        self.assertEqual(
            int(100 / 6.0), self.task.percentageComplete(recursive=True)
        )

    def testPercentageCompletedWhenOneChildIsComplete(self):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.task1_1.setPercentageComplete(100)
        self.assertEqual(50, self.task.percentageComplete(recursive=True))

    def testPercentageCompletedWhenOneChildCompleteAndMarkCompletedWhenChildrenAreCompletedIsTurnedOff(
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

    def testIcon(self):
        self.assertEqual(
            task.completed.icon_id(self.settings),
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

    def testIcon(self):
        self.assertEqual(
            task.overdue.icon_id(self.settings),
            test.styled(self.task).shown_icon_id(),
        )

    def testDueDateTime(self):
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

    def testIcon(self):
        self.assertEqual(
            task.duesoon.icon_id(self.settings),
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

    def testTimeSpentRecursivelyIsZero(self):
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

    def testTimeSpentOnTaskEqualsEffortDuration(self):
        self.assertEqual(self.task1effort1.timeSpent(), self.task.timeSpent())

    def testTimeSpentRecursivelyOnTaskEqualsEffortDuration(self):
        self.assertEqual(
            self.task1effort1.timeSpent(), self.task.timeSpent(recursive=True)
        )

    def testTimeSpentOnTaskIsZeroAfterRemovalOfEffort(self):
        self.task.removeEffort(self.task1effort1)
        self.assertEqual(date.TimeDelta(), self.task.timeSpent())

    def testTaskEffortListContainsTheOneEffortAdded(self):
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

    def testRevenueWithEffortButWithZeroFee(self):
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

    def testTimeSpentOnTaskEqualsEffortDuration(self):
        self.assertEqual(self.totalDuration, self.task.timeSpent())

    def testTimeSpentRecursivelyOnTaskEqualsEffortDuration(self):
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

    def testTaskIsBeingTracked(self):
        self.assertTrue(self.task.isBeingTracked())

    def testStopTracking(self):
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
        secondEffort = effort.Effort(self.task)
        self.task.addEffort(secondEffort)
        self.task.removeEffort(secondEffort)
        self.assertFalse(events)

    def test_remove_active_effort_should_cause_stop_tracking_event(self):
        events = test.ChangeRecorder(self.task.trackingChangedEventType())
        self.task.removeEffort(self.task1effort1)
        self.assertEqual([(False, self.task)], events)

    def test_stop_tracking_event(self):
        events = test.ChangeRecorder(self.task.trackingChangedEventType())
        self.task.stopTracking()
        self.assertEqual([(False, self.task)], events)

    def testIcon(self):
        self.assertEqual(
            "nuvola_apps_clock", test.styled(self.task).shown_icon_id()
        )

    def testIconAfterStopTracking(self):
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

    def testTimeSpentOnTaskEqualsEffortDuration(self):
        self.assertEqual(self.task1effort1.timeSpent(), self.task1.timeSpent())

    def testTimeSpentRecursivelyOnTaskEqualsTotalEffortDuration(self):
        self.assertEqual(
            self.task1effort1.timeSpent() + self.task1_1effort1.timeSpent(),
            self.task1.timeSpent(recursive=True),
        )

    def testEffortsRecursive(self):
        self.assertEqual(
            [self.task1effort1, self.task1_1effort1],
            self.task1.efforts(recursive=True),
        )

    def testRecursiveRevenue(self):
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

    def testTimeSpentRecursivelyOnTaskEqualsTotalEffortDuration(self):
        self.assertEqual(
            self.task1effort1.timeSpent()
            + self.task1_1effort1.timeSpent()
            + self.task1_1_1effort1.timeSpent(),
            self.task1.timeSpent(recursive=True),
        )

    def testEffortsRecursive(self):
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

    def testBudget(self):
        self.assertEqual(self.expectedBudget(), self.task.budget())

    def testBudgetLeft(self):
        self.assertEqual(self.expectedBudget(), self.task.budgetLeft())

    def testBudgetLeftAfterHalfSpent(self):
        self.addEffort(date.ONE_HOUR)
        self.assertEqual(date.ONE_HOUR, self.task.budgetLeft())

    def test_budget_left_notification(self):
        events = test.ChangeRecorder(task.Task.budgetLeftChangedEventType())
        self.addEffort(date.ONE_HOUR)
        self.assertEqual([(date.ONE_HOUR, self.task)], events)

    def testBudgetLeftAfterAllSpent(self):
        self.addEffort(date.TWO_HOURS)
        self.assertEqual(date.TimeDelta(), self.task.budgetLeft())

    def testBudgetLeftWhenOverBudget(self):
        self.addEffort(date.TimeDelta(hours=3))
        self.assertEqual(-date.ONE_HOUR, self.task.budgetLeft())

    def testRecursiveBudget(self):
        self.assertEqual(
            self.expectedBudget(), self.task.budget(recursive=True)
        )

    def testRecursiveBudgetWithChildWithoutBudget(self):
        self.task.addChild(task.Task())
        self.assertEqual(
            self.expectedBudget(), self.task.budget(recursive=True)
        )

    def testBudgetIsCopiedWhenTaskIsCopied(self):
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

    def testReminder(self):
        self.assertReminder(self.initialReminder())

    def testSetReminder(self):
        someOtherTime = date.DateTime(2005, 1, 2)
        self.task.set_reminder(someOtherTime)
        for recursive in (False, True):
            self.assertReminder(someOtherTime, recursive=recursive)

    def testCancelReminder(self):
        self.task.set_reminder()
        self.assertReminder(date.DateTime())

    def testSnoozeReminder(self):
        snoozePeriod = date.ONE_HOUR
        now = date.Now()
        self.task.snooze_reminder(snoozePeriod, now=lambda: now)
        self.assertReminder(now + snoozePeriod)

    def testSnoozeReminderTwice(self):
        snoozePeriod = date.ONE_HOUR
        now = date.Now()
        self.task.snooze_reminder(snoozePeriod, now=lambda: now)
        self.task.snooze_reminder(snoozePeriod, now=lambda: now + snoozePeriod)
        self.assertReminder(now + 2 * snoozePeriod)

    def testSnoozeWhenReminderNotSet(self):
        self.task.set_reminder()
        snoozePeriod = date.ONE_HOUR
        now = date.Now()
        self.task.snooze_reminder(snoozePeriod, now=lambda: now)
        self.assertReminder(now + snoozePeriod)

    def test_snooze_with_zero_time_delta(self):
        self.task.snooze_reminder(date.TimeDelta())
        # Not set is the latest date (docs/ATTRIBUTE_PATTERN.md)
        self.assertReminder(date.DateTime())
        self.assertEqual(
            date.DateTime(), self.task.reminder(include_snooze=False)
        )

    def testOriginalReminder(self):
        self.assertEqual(
            self.initialReminder(), self.task.reminder(include_snooze=False)
        )

    def testOriginalReminderAfterSnooze(self):
        self.task.snooze_reminder(date.ONE_HOUR)
        self.assertEqual(
            self.initialReminder(), self.task.reminder(include_snooze=False)
        )

    def testOriginalReminderAfterTwoSnoozes(self):
        self.task.snooze_reminder(date.ONE_HOUR)
        self.task.snooze_reminder(date.ONE_HOUR)
        self.assertEqual(
            self.initialReminder(), self.task.reminder(include_snooze=False)
        )

    def testOriginalReminderAfterCancel(self):
        self.task.set_reminder(None)
        self.assertEqual(
            date.DateTime(), self.task.reminder(include_snooze=False)
        )

    def testCancelReminderWithMaxDateTime(self):
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

    def testMarkCompletedCancelsReminder(self):
        self.task.set_completion_date_time()
        self.assertReminder(date.DateTime())

    def testRecursiveReminder(self):
        self.assertEqual(
            self.initialReminder(), self.task.reminder(recursive=True)
        )

    def testRecursiveReminderWithChildWithoutReminder(self):
        self.task.addChild(task.Task())
        self.assertEqual(
            self.initialReminder(), self.task.reminder(recursive=True)
        )

    def testRecursiveReminderWithChildWithLaterReminder(self):
        self.task.addChild(task.Task(reminder=date.DateTime(3000, 1, 1)))
        self.assertEqual(
            self.initialReminder(), self.task.reminder(recursive=True)
        )

    def testRecursiveReminderWithChildWithEarlierReminder(self):
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

    def testSetting(self):
        self.assertEqual(
            True, self.task.shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def testSetSetting(self):
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

    def testSetting(self):
        self.assertEqual(
            False, self.task.shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def testSetSetting(self):
        self.task.set_should_mark_completed_when_all_children_completed(True)
        self.assertEqual(
            True, self.task.shouldMarkCompletedWhenAllChildrenCompleted()
        )


class AttachmentTestCase(TaskTestCase, CommonTaskTestsMixin):
    eventTypes = [task.Task.attachmentsChangedEventType()]


class TaskWithoutAttachmentFixture(AttachmentTestCase):
    def testRemoveNonExistingAttachmentRaisesNoException(self):
        self.task.removeAttachments("Non-existing attachment")

    def testAddEmptyListOfAttachments(self):
        self.task.addAttachments()
        self.assertFalse(self.events, self.events)


class TaskWithAttachmentFixture(AttachmentTestCase):
    def taskCreationKeywordArguments(self):
        return [{"attachments": ["/home/frank/attachment.txt"]}]

    def testAttachments(self):
        for index, name in enumerate(
            self.taskCreationKeywordArguments()[0]["attachments"]
        ):
            self.assertEqual(name, self.task.attachments()[index].location())

    def testRemoveNonExistingAttachment(self):
        self.task.removeAttachments("Non-existing attachment")

        for index, name in enumerate(
            self.taskCreationKeywordArguments()[0]["attachments"]
        ):
            self.assertEqual(name, self.task.attachments()[index].location())

    def testCopy_CreatesNewListOfAttachments(self):
        copy = self.task.copy()

        def locations(item):
            return [each.location() for each in item.attachments()]

        self.assertEqual(locations(copy), locations(self.task))
        self.task.removeAttachments(self.task.attachments()[0])
        self.assertNotEqual(locations(copy), locations(self.task))

    def testCopy_CopiesIndividualAttachments(self):
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
    def testAddAttachment(self):
        self.assertTrue(self.attachment in self.task.attachments())

    def testNotification(self):
        self.assertTrue(self.events)


class TaskWithAttachmentRemovedFixture(TaskWithAttachmentAddedTestCase):
    def setUp(self):
        super().setUp()
        self.task.removeAttachments(self.attachment)

    def testRemoveAttachment(self):
        self.assertFalse(self.attachment in self.task.attachments())

    def testNotification(self):
        self.assertEqual(2, len(self.events))


class RecursivePriorityFixture(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"priority": 1, "children": [task.Task(priority=2)]}]

    def testPriority_RecursiveWhenChildHasLowestPriority(self):
        self.task1_1.setPriority(0)
        self.assertEqual(1, self.task1.priority(recursive=True))

    def testPriority_RecursiveWhenParentHasLowestPriority(self):
        self.assertEqual(2, self.task1.priority(recursive=True))

    def testPriority_RecursiveWhenChildHasHighestPriorityAndIsCompleted(self):
        self.task1_1.set_completion_date_time()
        self.assertEqual(1, self.task1.priority(recursive=True))

    def testPriorityNotificationWhenMarkingChildCompleted(self):
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task1_1.set_completion_date_time()
        self.assertIn(self.task1, self.events[0].sources())

    def testPriorityNotificationWhenMarkingChildUncompleted(self):
        self.task1_1.set_completion_date_time()
        self.registerObserver(task.Task.priorityChangedEventType())
        self.task1_1.set_completion_date_time(date.DateTime())
        self.assertIn(self.task1, self.events[0].sources())


class TaskWithFixedFeeFixture(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"fixedFee": 1000}]

    def testSetFixedFeeViaContructor(self):
        self.assertEqual(1000, self.task.fixedFee())

    def testRevenueFromFixedFee(self):
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

    def testSetHourlyFeeViaConstructor(self):
        self.assertEqual(100, self.task.hourlyFee())

    def testRevenue_WithoutEffort(self):
        self.assertEqual(0, self.task.revenue())

    def testRevenue_WithOneHourEffort(self):
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

    def testCategory(self):
        self.assertEqual(set([self.category]), self.task.categories())

    def testCategoryIcon(self):
        self.category.set_icon_id("icon")
        self.assertEqual("icon", test.styled(self.task).shown_icon_id())


class TaskColorTest(test.TestCase):
    def setUp(self):
        super().setUp()
        self.settings = task.Task.settings = config.Settings(load=False)
        self.yesterday = date.Yesterday()
        self.tomorrow = date.Tomorrow()

    def testDefaultTask(self):
        self.assertEqual(wx.Colour(192, 192, 192), task.Task().statusFgColor())

    def testCompletedTask(self):
        completed = task.Task()
        completed.set_completion_date_time()
        self.assertEqual(wx.GREEN, completed.statusFgColor())

    def testOverDueTask(self):
        overdue = task.Task(dueDateTime=self.yesterday)
        self.assertEqual(wx.RED, overdue.statusFgColor())

    def testDueTodayTask(self):
        duetoday = task.Task(dueDateTime=date.Now() + date.ONE_HOUR)
        self.assertEqual(wx.Colour(255, 128, 0), duetoday.statusFgColor())

    def testDueTomorrow(self):
        duetomorrow = task.Task(dueDateTime=self.tomorrow + date.ONE_HOUR)
        self.assertEqual(wx.Colour(192, 192, 192), duetomorrow.statusFgColor())

    def testActive(self):
        active = task.Task(actualStartDateTime=date.Now())
        self.assertEqual(
            wx.Colour(
                *ast.literal_eval(self.settings.get("fgcolor", "activetasks"))
            ),
            active.statusFgColor(),
        )

    def testActiveTaskWithCategory(self):
        activeTask = task.Task(actualStartDateTime=date.Now())
        redCategory = category.Category(subject="Red category", fgColor=wx.RED)
        activeTask.addCategory(redCategory)
        self.assertEqual(wx.RED, test.styled(activeTask).shown_fg_color())


class TaskWithPrerequisite(TaskTestCase):
    def taskCreationKeywordArguments(self):
        self.prerequisite = task.Task(
            subject="prerequisite"
        )  # pylint: disable=W0201
        return [dict(subject="task", prerequisites=[self.prerequisite])]

    def testTaskHasPrerequisite(self):
        self.assertTrue(self.prerequisite in self.task.prerequisites())

    def testDependencyHasNotBeenSetAutomatically(self):
        self.assertFalse(self.task in self.prerequisite.dependencies())

    def testRemovePrerequisite(self):
        self.task.remove_prerequisites([self.prerequisite])
        self.assertFalse(self.task.prerequisites())

    def testRemovePrerequisiteNotInPrerequisites(self):
        self.task.remove_prerequisites([task.Task()])
        self.assertTrue(self.prerequisite in self.task.prerequisites())

    def test_remove_prerequisite_notification(self):
        event_type = task.Task.prerequisitesChangedEventType()
        self.registerObserver(event_type)
        self.task.remove_prerequisites([self.prerequisite])
        self.assertEqual([{self.task}], self.sources_of(event_type))

    def testSetPrerequisitesRemovesOldPrerequisites(self):
        newPrerequisites = set([task.Task()])
        self.task.set_prerequisites(newPrerequisites)
        self.assertEqual(newPrerequisites, self.task.prerequisites())

    def testDontCopyPrerequisites(self):
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

    def testTaskHasDependency(self):
        self.assertTrue(self.dependency in self.task.dependencies())

    def testPrerequisiteHasNotBeenSetAutomatically(self):
        self.assertFalse(self.task in self.dependency.prerequisites())

    def testRemoveDependency(self):
        self.task.remove_dependencies([self.dependency])
        self.assertFalse(self.task.dependencies())

    def testRemoveDependencyNotInDependencies(self):
        self.task.remove_dependencies([task.Task()])
        self.assertTrue(self.dependency in self.task.dependencies())

    def test_remove_dependency_notification(self):
        event_type = task.Task.dependenciesChangedEventType()
        self.registerObserver(event_type)
        self.task.remove_dependencies([self.dependency])
        self.assertEqual([{self.task}], self.sources_of(event_type))

    def testSetDependenciesRemovesOldDependencies(self):
        newDependencies = set([task.Task()])
        self.task.set_dependencies(newDependencies)
        self.assertEqual(newDependencies, self.task.dependencies())

    def testDontCopyDependencies(self):
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
        self.settings = task.Task.settings = config.Settings(load=False)
        self.changeSettings()
        self.now = now = date.Now()
        tomorrow = now + date.ONE_DAY
        dayAfterTomorrow = tomorrow + date.ONE_DAY
        currentTimeKwArgs = dict(
            hour=now.hour,
            minute=now.minute,
            second=now.second,
        )
        nextFriday = tomorrow.endOfWorkWeek().replace(**currentTimeKwArgs)
        nextMonday = (
            (now + date.ONE_WEEK)
            .startOfWorkWeek()
            .replace(**currentTimeKwArgs)
        )
        startOfWorkingDayHour = self.settings.getint("view", "efforthourstart")
        startOfWorkingDayKwArgs = dict(
            hour=startOfWorkingDayHour, minute=0, second=0
        )
        endOfWorkingDayHour = self.settings.getint("view", "efforthourend")
        if endOfWorkingDayHour == 24:
            endOfWorkingDayHour = 23
            minute = 59
            second = 59
        else:
            minute = 0
            second = 0
        endOfWorkingDayKwArgs = dict(
            hour=endOfWorkingDayHour,
            minute=minute,
            second=second,
        )
        startOfWorkingDay = now.replace(**startOfWorkingDayKwArgs)
        endOfWorkingDay = now.replace(**endOfWorkingDayKwArgs)
        startOfWorkingTomorrow = tomorrow.replace(**startOfWorkingDayKwArgs)
        endOfWorkingTomorrow = tomorrow.replace(**endOfWorkingDayKwArgs)
        startOfWorkingDayAfterTomorrow = dayAfterTomorrow.replace(
            **startOfWorkingDayKwArgs
        )
        endOfWorkingDayAfterTomorrow = dayAfterTomorrow.replace(
            **endOfWorkingDayKwArgs
        )
        startOfWorkingNextFriday = nextFriday.replace(
            **startOfWorkingDayKwArgs
        )
        endOfWorkingNextFriday = nextFriday.replace(**endOfWorkingDayKwArgs)
        startOfWorkingNextMonday = nextMonday.replace(
            **startOfWorkingDayKwArgs
        )
        endOfWorkingNextMonday = nextMonday.replace(**endOfWorkingDayKwArgs)

        self.times = dict(
            today_startofday=now.startOfDay(),
            today_startofworkingday=startOfWorkingDay,
            today_currenttime=now,
            today_endofworkingday=endOfWorkingDay,
            today_endofday=now.endOfDay(),
            tomorrow_startofday=tomorrow.startOfDay(),
            tomorrow_startofworkingday=startOfWorkingTomorrow,
            tomorrow_currenttime=tomorrow,
            tomorrow_endofworkingday=endOfWorkingTomorrow,
            tomorrow_endofday=tomorrow.endOfDay(),
            dayaftertomorrow_startofday=dayAfterTomorrow.startOfDay(),
            dayaftertomorrow_startofworkingday=startOfWorkingDayAfterTomorrow,
            dayaftertomorrow_currenttime=dayAfterTomorrow,
            dayaftertomorrow_endofworkingday=endOfWorkingDayAfterTomorrow,
            dayaftertomorrow_endofday=dayAfterTomorrow.endOfDay(),
            nextfriday_startofday=nextFriday.startOfDay(),
            nextfriday_startofworkingday=startOfWorkingNextFriday,
            nextfriday_currenttime=nextFriday,
            nextfriday_endofworkingday=endOfWorkingNextFriday,
            nextfriday_endofday=nextFriday.endOfDay(),
            nextmonday_startofday=nextMonday.startOfDay(),
            nextmonday_startofworkingday=startOfWorkingNextMonday,
            nextmonday_currenttime=nextMonday,
            nextmonday_endofworkingday=endOfWorkingNextMonday,
            nextmonday_endofday=nextMonday.endOfDay(),
        )

    def changeSettings(self):
        pass

    def testSuggestedPlannedStartDateTime(self):
        for timeValue, expectedDateTime in list(self.times.items()):
            self.settings.set(
                "view", "defaultplannedstartdatetime", "preset_" + timeValue
            )
            self.assertEqual(
                expectedDateTime,
                task.Task.suggestedPlannedStartDateTime(lambda: self.now),
            )

    def testSuggestedActualStartDateTime(self):
        for timeValue, expectedDateTime in list(self.times.items()):
            self.settings.set(
                "view", "defaultactualstartdatetime", "preset_" + timeValue
            )
            self.assertEqual(
                expectedDateTime,
                task.Task.suggestedActualStartDateTime(lambda: self.now),
            )

    def testSuggestedDueDateTime(self):
        for timeValue, expectedDateTime in list(self.times.items()):
            self.settings.set(
                "view", "defaultduedatetime", "propose_" + timeValue
            )
            self.assertEqual(
                expectedDateTime,
                task.Task.suggestedDueDateTime(lambda: self.now),
            )

    def testSuggestedCompletionDateTime(self):
        for timeValue, expectedDateTime in list(self.times.items()):
            self.settings.set(
                "view", "defaultcompletiondatetime", "propose_" + timeValue
            )
            self.assertEqual(
                expectedDateTime,
                task.Task.suggestedCompletionDateTime(lambda: self.now),
                "Expected %s, but got %s, with default completion date time "
                "set to %s"
                % (
                    expectedDateTime,
                    task.Task.suggestedCompletionDateTime(lambda: self.now),
                    "preset_" + timeValue,
                ),
            )

    def testSuggestedReminderDateTime(self):
        for timeValue, expectedDateTime in list(self.times.items()):
            self.settings.set(
                "view", "defaultreminderdatetime", "propose_" + timeValue
            )
            self.assertEqual(
                expectedDateTime,
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
        self.settings.setint("view", "efforthourstart", 0)
        self.settings.setint("view", "efforthourend", 24)


class TaskConstructionTest(test.TestCase):
    def testActualStartDateTimeIsNotDeterminedByEffortsWhenMissing(self):
        newTask = task.Task(
            efforts=[effort.Effort(None, date.DateTime(2000, 1, 1))]
        )
        self.assertEqual(date.DateTime(), newTask.actualStartDateTime())

    def testActualStartDateTimeIsNotDeterminedByEffortsWhenPassingAnActualStartDateTime(
        self,
    ):
        newTask = task.Task(
            actualStartDateTime=date.DateTime(2010, 1, 1),
            efforts=[effort.Effort(None, date.DateTime(2000, 1, 1))],
        )
        self.assertEqual(
            date.DateTime(2010, 1, 1), newTask.actualStartDateTime()
        )


# NOTE (Scheduler Refactoring - 2024):
# TaskScheduledTest and TaskNotScheduledTest were removed because they tested
# the old scheduler-based status transitions. With the new GlobalTimer architecture,
# status changes are handled by polling rather than individual scheduled jobs.
# See docs/SCHEDULERS.md for details.
