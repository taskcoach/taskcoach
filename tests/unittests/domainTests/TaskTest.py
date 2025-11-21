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
from taskcoachlib.domain.attribute.icon import getImagePlural, getImageOpen
from pubsub import pub
from unittests import asserts
import test
import wx

# pylint: disable=C0103,C0111


class TaskTestCase(test.TestCase):
    eventTypes = []

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


class CommonTaskTestsMixin(asserts.TaskAssertsMixin):
    """These tests should succeed for all tasks, regardless of state."""

    def testCopy(self):
        copy = self.task.copy()
        self.assertTaskCopy(copy, self.task)

    def testCopy_IdIsDifferent(self):
        copy = self.task.copy()
        self.assertNotEqual(copy.id(), self.task.id())

    def testCopy_statusIsNew(self):
        self.task.markDeleted()
        copy = self.task.copy()
        self.assertEqual(copy.getStatus(), copy.STATUS_NEW)


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
        self.assertEqual("", self.task.icon(recursive=False))

    def testDefaultRecursiveIcon(self):
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testDefaultOwnSelectedIcon(self):
        self.assertEqual("", self.task.selectedIcon(recursive=False))

    def testDefaultRecursiveSelectedIcon(self):
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
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
        self.task.setPlannedStartDateTime(self.yesterday)
        for recursive in (False, True):
            self.assertEqual(
                self.yesterday,
                self.task.plannedStartDateTime(recursive=recursive),
            )

    def testSetPlannedStartDateTimeNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(
            onEvent, task.Task.plannedStartDateTimeChangedEventType()
        )
        self.task.setPlannedStartDateTime(self.yesterday)
        self.assertEqual((self.yesterday, self.task), events[0])

    def testSetPlannedStartDateTimeUnchangedCausesNoNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(
            onEvent, task.Task.plannedStartDateTimeChangedEventType()
        )
        self.task.setPlannedStartDateTime(self.task.plannedStartDateTime())
        self.assertFalse(events)

    def testSetFuturePlannedStartDateTimeChangesIcon(self):
        self.task.setPlannedStartDateTime(self.tomorrow)
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testIconChangedAfterSetPlannedStartDateTimeHasPassed(self):
        self.task.setPlannedStartDateTime(self.tomorrow)
        now = self.tomorrow + date.ONE_SECOND
        oldNow = date.Now
        date.Now = lambda: now
        self.task.onTimeToStart()
        self.assertEqual(
            task.late.getBitmap(self.settings), self.task.icon(recursive=True)
        )
        date.Now = oldNow

    def testSetActualStartDateTime(self):
        self.task.setActualStartDateTime(self.yesterday)
        for recursive in (False, True):
            self.assertEqual(
                self.yesterday,
                self.task.actualStartDateTime(recursive=recursive),
            )

    def testSetActualStartDateTimeNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.actualStartDateTimeChangedEventType())
        self.task.setActualStartDateTime(self.yesterday)
        self.assertEqual((self.yesterday, self.task), events[0])

    def testSetActualStartDateTimeUnchangedCausesNoNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.actualStartDateTimeChangedEventType())
        self.task.setActualStartDateTime(self.task.actualStartDateTime())
        self.assertFalse(events)

    def testSetDueDateTime(self):
        self.task.setDueDateTime(self.tomorrow)
        for recursive in (False, True):
            self.assertEqual(
                self.tomorrow, self.task.dueDateTime(recursive=recursive)
            )

    def testSetDueDateTimeNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.dueDateTimeChangedEventType())
        self.task.setDueDateTime(self.tomorrow)
        self.assertEqual((self.tomorrow, self.task), events[0])

    def testSetDueDateTimeUnchangedCausesNoNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.dueDateTimeChangedEventType())
        self.task.setDueDateTime(self.task.dueDateTime())
        self.assertFalse(events)

    def testIconChangedAfterSetDueDateTimeHasPassed(self):
        self.task.setDueDateTime(self.tomorrow)
        now = self.tomorrow + date.ONE_SECOND
        oldNow = date.Now
        date.Now = lambda: now
        self.task.onOverDue()
        self.assertEqual(
            task.overdue.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )
        date.Now = oldNow

    def testIconChangedAfterTaskHasBecomeDueSoon(self):
        self.settings.setint("behavior", "duesoonhours", 1)
        self.task.setDueDateTime(self.tomorrow)
        now = self.tomorrow + date.ONE_SECOND - date.ONE_HOUR
        oldNow = date.Now
        date.Now = lambda: now
        self.task.onDueSoon()
        self.assertEqual(
            task.duesoon.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )
        date.Now = oldNow

    def testIconChangedAfterTaskHasBecomeDueSoonAccordingToNewDueSoonSetting(
        self,
    ):
        self.task.setDueDateTime(self.tomorrow)
        self.settings.setint("behavior", "duesoonhours", 1)
        now = self.tomorrow + date.ONE_SECOND - date.ONE_HOUR
        oldNow = date.Now
        date.Now = lambda: now
        self.task.onDueSoon()
        self.assertEqual(
            task.duesoon.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )
        date.Now = oldNow

    def testSetCompletionDateTime(self):
        now = date.Now()
        self.task.setCompletionDateTime(now)
        for recursive in (False, True):
            self.assertEqual(
                now, self.task.completionDateTime(recursive=recursive)
            )

    def testSetCompletionDateTimeNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.completionDateTimeChangedEventType())
        now = date.Now()
        self.task.setCompletionDateTime(now)
        self.assertEqual([(now, self.task)], events)

    def testSetCompletionDateTimeUnchangedCausesNoNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.completionDateTimeChangedEventType())
        self.task.setCompletionDateTime(date.DateTime())
        self.assertFalse(events)

    def testSetCompletionDateTimeMakesTaskCompleted(self):
        self.task.setCompletionDateTime()
        self.assertTrue(self.task.completed())

    def testSetCompletionDateTimeDefaultsToNow(self):
        self.task.setCompletionDateTime()
        self.assertAlmostEqual(
            date.Now().toordinal(), self.task.completionDateTime().toordinal()
        )

    def testSetPercentageComplete(self):
        self.task.setPercentageComplete(50)
        self.assertEqual(50, self.task.percentageComplete())

    def testSetPercentageCompleteWhenMarkCompletedWhenAllChildrenCompletedIsTrue(
        self,
    ):
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(True)
        self.task.setPercentageComplete(50)
        self.assertEqual(50, self.task.percentageComplete())

    def testSet100PercentComplete(self):
        self.task.setPercentageComplete(100)
        self.assertTrue(self.task.completed())

    def testPercentageCompleteNotificationViaCompletionDateTime(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.percentageCompleteChangedEventType())
        self.task.setCompletionDateTime()
        self.assertEqual([(100, self.task)], events)

    def testSetPercentageCompleteSetsActualStartDateTime(self):
        self.task.setPercentageComplete(50)
        self.assertNotEqual(date.DateTime(), self.task.actualStartDateTime())

    def testSetPercentageCompleteToZeroDoesNotSetActualStartDateTime(self):
        self.task.setPercentageComplete(50)
        self.task.setActualStartDateTime(date.DateTime())
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
        self.task.setBudget(budget)
        self.assertEqual(budget, self.task.budget())

    def testSetBudgetNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetChangedEventType())
        budget = date.ONE_HOUR
        self.task.setBudget(budget)
        self.assertEqual([(budget, self.task)], events)

    def testSetBudgetUnchangedCausesNoNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetChangedEventType())
        self.task.setBudget(self.task.budget())
        self.assertFalse(events)

    def testSetPriority(self):
        self.task.setPriority(10)
        self.assertEqual(10, self.task.priority())

    def testSetPriorityCausesNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.priorityChangedEventType())
        self.task.setPriority(10)
        self.assertEqual((10, self.task), events[0])

    def testSetPriorityUnchangedCausesNoNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.priorityChangedEventType())
        self.task.setPriority(self.task.priority())
        self.assertFalse(events)

    def testNegativePriority(self):
        self.task.setPriority(-1)
        self.assertEqual(-1, self.task.priority())

    def testSetFixedFee(self):
        self.task.setFixedFee(1000)
        self.assertEqual(1000, self.task.fixedFee())

    def testSetFixedFeeUnchangedCausesNoNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.fixedFeeChangedEventType())
        self.task.setFixedFee(self.task.fixedFee())
        self.assertFalse(events)

    def testSetFixedFeeCausesNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.fixedFeeChangedEventType())
        self.task.setFixedFee(1000)
        self.assertEqual([(1000, self.task)], events)

    def testSetFixedFeeCausesRevenueChangeNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.revenueChangedEventType())
        self.task.setFixedFee(1000)
        self.assertEqual([(1000, self.task)], events)

    def testSetHourlyFeeViaSetter(self):
        self.task.setHourlyFee(100)
        self.assertEqual(100, self.task.hourlyFee())

    def testSetHourlyFeeCausesNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.hourlyFeeChangedEventType())
        self.task.setHourlyFee(100)
        self.assertEqual([(100, self.task)], events)

    def testSetRecurrence(self):
        self.task.setRecurrence(date.Recurrence("weekly"))
        self.assertEqual(date.Recurrence("weekly"), self.task.recurrence())

    def testSetRecurrenceCausesNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.recurrenceChangedEventType())
        self.task.setRecurrence(date.Recurrence("weekly"))
        self.assertEqual([(date.Recurrence("weekly"), self.task)], events)

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
        self.task.setCompletionDateTime()
        child = task.Task()
        self.task.addChild(child)
        self.assertFalse(self.task.completed())

    def testAddChildWithLaterDueDateTimeDoesNotChangeParentDueDateTime(self):
        self.task.setDueDateTime(self.tomorrow)
        child = task.Task(dueDateTime=date.Now() + date.ONE_HOUR)
        self.task.addChild(child)
        self.assertEqual(self.tomorrow, self.task.dueDateTime())
        self.assertEqual(
            child.dueDateTime(), self.task.dueDateTime(recursive=True)
        )

    def testAddChildWithoutDueDateTimeDoesNotResetParentDueDateTime(self):
        dueDateTime = date.Now() + date.ONE_HOUR
        self.task.setDueDateTime(dueDateTime)
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
        child.setRecurrence(date.Recurrence("monthly"))
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
        child.setRecurrence(date.Recurrence("monthly"))
        self.task.addChild(child)
        self.assertEqual(
            originalActualStartDateTime, self.task.actualStartDateTime()
        )
        self.assertEqual(
            self.yesterday, self.task.actualStartDateTime(recursive=True)
        )
        self.assertEqual(self.yesterday, child.actualStartDateTime())

    def testAddChildWithBudgetCausesBudgetNotification(self):
        child = task.Task()
        child.setBudget(date.TimeDelta(100))
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetChangedEventType())
        self.task.addChild(child)
        self.assertEqual([(date.TimeDelta(), self.task)], events)

    def testAddChildWithoutBudgetCausesNoBudgetNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetChangedEventType())
        child = task.Task()
        self.task.addChild(child)
        self.assertFalse(events)

    def testAddChildWithEffortCausesBudgetLeftNotification(self):
        self.task.setBudget(date.TimeDelta(hours=100))
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
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

    def testAddChildWithoutEffortCausesNoBudgetLeftNotification(self):
        self.task.setBudget(date.TimeDelta(hours=100))
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
        self.task.addChild(task.Task())
        self.assertFalse(events)

    def testAddChildWithEffortToTaskWithoutBudgetCausesNoBudgetLeftNotification(
        self,
    ):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
        child = task.Task()
        child.addEffort(
            effort.Effort(
                child,
                date.DateTime(2000, 1, 1, 10, 0, 0),
                date.DateTime(2000, 1, 1, 11, 0, 0),
            )
        )
        self.task.addChild(child)
        self.assertFalse(events)

    def testAddChildWithBudgetCausesBudgetLeftNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
        self.task.addChild(task.Task(budget=date.TimeDelta(hours=100)))
        self.assertEqual([(date.TimeDelta(), self.task)], events)

    def testAddChildWithEffortCausesTimeSpentNotification(self):
        child = task.Task()
        childEffort = effort.Effort(
            child,
            date.DateTime(2000, 1, 1, 10, 0, 0),
            date.DateTime(2000, 1, 1, 11, 0, 0),
        )
        child.addEffort(childEffort)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.timeSpentChangedEventType())
        self.task.addChild(child)
        self.assertEqual([(self.task.timeSpent(), self.task)], events)

    def testAddChildWithoutEffortCausesNoTimeSpentNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.timeSpentChangedEventType())
        self.task.addChild(task.Task())
        self.assertFalse(events)

    def testAddChildWithHigherPriorityCausesPriorityNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.priorityChangedEventType())
        child = task.Task(priority=10)
        self.task.addChild(child)
        self.assertEqual([(0, self.task)], events)

    def testAddChildWithLowerPriorityCausesNoPriorityNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.priorityChangedEventType())
        self.task.addChild(task.Task(priority=-10))
        self.assertFalse(events)

    def testAddChildWithRevenueCausesRevenueNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.revenueChangedEventType())
        self.task.addChild(task.Task(fixedFee=1000))
        self.assertEqual([(0, self.task)], events)

    def testAddChildWithoutRevenueCausesNoRevenueNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.revenueChangedEventType())
        self.task.addChild(task.Task())
        self.assertFalse(events)

    def testAddTrackedChildCausesStartTrackingNotification(self):
        child = task.Task()
        child.addEffort(effort.Effort(child))
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, self.task.trackingChangedEventType())
        self.task.addChild(child)
        self.assertEqual([(True, self.task)], events)

    def testAddChildWithTwoTrackedEffortsCausesStartTrackingNotification(self):
        child = task.Task()
        child.addEffort(effort.Effort(child))
        child.addEffort(effort.Effort(child))
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, self.task.trackingChangedEventType())
        self.task.addChild(child)
        self.assertEqual([(True, self.task)], events)

    # Constructor

    def testNewChild_WithSubject(self):
        child = self.task.newChild(subject="Test")
        self.assertEqual("Test", child.subject())

    # Add effort

    def testAddEffortCausesNoBudgetLeftNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
        self.task.addEffort(effort.Effort(self.task))
        self.assertFalse(events)

    def testAddActiveEffortCausesStartTrackingNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, self.task.trackingChangedEventType())
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
        self.task.addPrerequisites(prerequisites)
        self.assertEqual(prerequisites, self.task.prerequisites())

    def testAddTwoPrerequisites(self):
        prerequisites = set([task.Task(), task.Task()])
        self.task.addPrerequisites(prerequisites)
        self.assertEqual(prerequisites, self.task.prerequisites())

    def testAddPrerequisiteCausesNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.prerequisitesChangedEventType())
        prerequisite = task.Task()
        self.task.addPrerequisites([prerequisite])
        self.assertEqual([(set([prerequisite]), self.task)], events)

    def testRemovePrerequisiteThatHasNotBeenAdded(self):
        prerequisite = task.Task()
        self.task.removePrerequisites([prerequisite])
        self.assertFalse(self.task.prerequisites())

    def testAddPrerequisiteKeepsTaskInactive(self):
        prerequisites = set([task.Task()])
        self.task.addPrerequisites(prerequisites)
        self.assertTrue(self.task.inactive())

    def testAddPrerequisiteResetsActualStartDateTime(self):
        self.task.setActualStartDateTime(date.Now())
        self.task.addPrerequisites([task.Task()])
        self.assertEqual(date.DateTime(), self.task.actualStartDateTime())

    # Dependencies

    def testAddOneDependency(self):
        dependencies = set([task.Task()])
        self.task.addDependencies(dependencies)
        self.assertEqual(dependencies, self.task.dependencies())

    def testAddTwoDependencies(self):
        dependencies = set([task.Task(), task.Task()])
        self.task.addDependencies(dependencies)
        self.assertEqual(dependencies, self.task.dependencies())

    def testAddDependencyCausesNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.dependenciesChangedEventType())
        dependency = task.Task()
        self.task.addDependencies([dependency])
        self.assertEqual([(set([dependency]), self.task)], events)

    def testRemoveDependencyThatHasNotBeenAdded(self):
        dependency = task.Task()
        self.task.removeDependencies([dependency])
        self.assertFalse(self.task.dependencies())

    # State (FIXME: need to test other attributes too)

    def testTaskStateIncludesPriority(self):
        state = self.task.__getstate__()
        self.task.setPriority(10)
        self.task.__setstate__(state)
        self.assertEqual(0, self.task.priority())

    def testTaskStateIncludesRecurrence(self):
        state = self.task.__getstate__()
        self.task.setRecurrence(date.Recurrence("weekly"))
        self.task.__setstate__(state)
        self.assertFalse(self.task.recurrence())

    def testTaskStateIncludesNotes(self):
        state = self.task.__getstate__()
        self.task.addNote(note.Note())
        self.task.__setstate__(state)
        self.assertFalse(self.task.notes())

    def testTaskStateIncludesReminder(self):
        state = self.task.__getstate__()
        self.task.setReminder(date.DateTime.now() + date.TimeDelta(seconds=10))
        self.task.__setstate__(state)
        self.assertFalse(self.task.reminder())

    def testTaskStateIncludesPlannedStartDateTime(self):
        previousPlannedStartDateTime = self.task.plannedStartDateTime()
        state = self.task.__getstate__()
        self.task.setPlannedStartDateTime(self.yesterday)
        self.task.__setstate__(state)
        self.assertEqual(
            previousPlannedStartDateTime, self.task.plannedStartDateTime()
        )

    def testTaskStateIncludesActualStartDateTime(self):
        previousActualStartDateTime = self.task.actualStartDateTime()
        state = self.task.__getstate__()
        self.task.setActualStartDateTime(self.yesterday)
        self.task.__setstate__(state)
        self.assertEqual(
            previousActualStartDateTime, self.task.actualStartDateTime()
        )

    def testTaskStateIncludesDueDateTime(self):
        previousDueDateTime = self.task.dueDateTime()
        state = self.task.__getstate__()
        self.task.setDueDateTime(self.yesterday)
        self.task.__setstate__(state)
        self.assertEqual(previousDueDateTime, self.task.dueDateTime())

    def testTaskStateIncludesCompletionDateTime(self):
        previousCompletionDateTime = self.task.completionDateTime()
        state = self.task.__getstate__()
        self.task.setCompletionDateTime(self.yesterday)
        self.task.__setstate__(state)
        self.assertEqual(
            previousCompletionDateTime, self.task.completionDateTime()
        )

    def testTaskStateIncludesPrerequisites(self):
        self.task.addPrerequisites([task.Task(subject="prerequisite1")])
        previousPrerequisites = self.task.prerequisites()
        state = self.task.__getstate__()
        self.task.addPrerequisites([task.Task(subject="prerequisite2")])
        self.task.__setstate__(state)
        self.assertEqual(previousPrerequisites, self.task.prerequisites())

    def testTaskStateIncludesDependencies(self):
        self.task.addDependencies([task.Task(subject="dependency1")])
        previousDependencies = self.task.dependencies()
        state = self.task.__getstate__()
        self.task.addDependencies([task.Task(subject="dependency2")])
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
            ],
            self.task.modificationEventTypes(),
        )


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
            expectedColor, self.task.foregroundColor(recursive=True)
        )

    def testColorWhenTaskHasOwnColor(self):
        color = wx.Colour(191, 128, 64, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, self.task.foregroundColor(recursive=True))

    def testIcon(self):
        self.assertEqual(
            task.duesoon.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testSelectedIcon(self):
        self.assertEqual(
            task.duesoon.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
        )

    def testIconAfterChangingDueSoonHours(self):
        self.settings.setint("behavior", "duesoonhours", 0)
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testAppearanceNotificationAfterChangingDueSoonHours(self):
        self.registerObserver(self.task.appearanceChangedEventType())
        self.settings.setint("behavior", "duesoonhours", 0)
        self.assertEvent(self.task.appearanceChangedEventType(), self.task)

    def testIconAfterDueDateTimeHasPassed(self):
        now = self.task.dueDateTime() + date.ONE_SECOND
        oldNow = date.Now
        date.Now = lambda: now
        self.task.onOverDue()
        self.assertEqual(
            task.overdue.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )
        date.Now = oldNow

    def testAppearanceNotificationAfterDueDateTimeHasPassed(self):
        self.registerObserver(self.task.appearanceChangedEventType())
        now = self.task.dueDateTime() + date.ONE_SECOND
        oldNow = date.Now
        date.Now = lambda: now
        self.task.onOverDue()
        self.assertEvent(self.task.appearanceChangedEventType(), self.task)
        date.Now = oldNow


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
            task.inactive.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testselectedIconNotDueSoon(self):
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
        )

    def testIconDueSoon(self):
        self.settings.setint("behavior", "duesoonhours", 48)
        self.assertEqual(
            task.duesoon.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testSelectedIconDueSoon(self):
        self.settings.setint("behavior", "duesoonhours", 48)
        self.assertEqual(
            task.duesoon.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
        )

    def testAppearanceNotificationAfterChangingDueSoonHours(self):
        self.registerObserver(self.task.appearanceChangedEventType())
        self.settings.setint("behavior", "duesoonhours", 48)
        self.assertEvent(self.task.appearanceChangedEventType(), self.task)


class OverdueTaskTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"dueDateTime": self.yesterday}]

    def testIsOverdue(self):
        self.assertTrue(self.task.overdue())

    def testCompletedOverdueTaskIsNoLongerOverdue(self):
        self.task.setCompletionDateTime()
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
            expectedColor, self.task.foregroundColor(recursive=True)
        )

    def testColorWhenTaskHasOwnColor(self):
        color = wx.Colour(191, 64, 64, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, self.task.foregroundColor(recursive=True))

    def testIcon(self):
        self.assertEqual(
            task.overdue.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testSelectedIcon(self):
        self.assertEqual(
            task.overdue.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
        )

    def testIconAfterChangingDueDateTime(self):
        self.task.setDueDateTime(date.Now() + date.TimeDelta(hours=72))
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testSelectedIconAfterChangingDueDateTime(self):
        self.task.setDueDateTime(date.Now() + date.TimeDelta(hours=72))
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
        )

    def testAppearanceNotificationAfterChangingDueDateTime(self):
        self.registerObserver(self.task.appearanceChangedEventType())
        self.task.setDueDateTime(date.Now() + date.TimeDelta(hours=72))
        self.assertEvent(self.task.appearanceChangedEventType(), self.task)

    def testIconAfterMarkingComplete(self):
        self.task.setCompletionDateTime()
        self.assertEqual(
            task.completed.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testSelectedIconAfterMarkingComplete(self):
        self.task.setCompletionDateTime()
        self.assertEqual(
            task.completed.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
        )

    def testAppearanceNotificationAfterMarkingComplete(self):
        self.registerObserver(self.task.appearanceChangedEventType())
        self.task.setCompletionDateTime()
        self.assertEvent(self.task.appearanceChangedEventType(), self.task)


class CompletedTaskTest(TaskTestCase, CommonTaskTestsMixin):
    def taskCreationKeywordArguments(self):
        return [{"completionDateTime": date.Now()}]

    def testATaskWithACompletionDateIsCompleted(self):
        self.assertTrue(self.task.completed())

    def testSettingTheCompletionDateTimeToInfiniteMakesTheTaskUncompleted(
        self,
    ):
        self.task.setCompletionDateTime(date.DateTime())
        self.assertFalse(self.task.completed())
        self.assertEqual(0, self.task.percentageComplete())

    def testSettingTheCompletionDateTimeToAnotherDateTimeLeavesTheTaskCompleted(
        self,
    ):
        self.task.setCompletionDateTime(self.yesterday)
        self.assertTrue(self.task.completed())

    def testCompletedTaskIsHundredProcentComplete(self):
        self.assertEqual(100, self.task.percentageComplete())

    def testSetPercentageCompleteToLessThan100MakesTaskUncompleted(self):
        self.task.setPercentageComplete(99)
        self.assertEqual(date.DateTime(), self.task.completionDateTime())
        self.assertEqual(99, self.task.percentageComplete())

    def testPercentageCompleteNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.percentageCompleteChangedEventType())
        self.task.setCompletionDateTime(date.DateTime.max)
        self.assertEqual([(0, self.task)], events)

    def testDefaultCompletedColor(self):
        expectedColor = wx.Colour(
            *ast.literal_eval(self.settings.get("fgcolor", "completedtasks"))
        )
        self.assertEqual(
            expectedColor, self.task.foregroundColor(recursive=True)
        )

    def testColorWhenTaskHasOwnColor(self):
        color = wx.Colour(64, 191, 64, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, self.task.foregroundColor(recursive=True))

    def testIcon(self):
        self.assertEqual(
            task.completed.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testSelectedIcon(self):
        self.assertEqual(
            task.completed.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
        )

    def testIconAfterMarkingUncomplete(self):
        self.task.setCompletionDateTime(date.DateTime.max)
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testSelectedIconAfterMarkingUncomplete(self):
        self.task.setCompletionDateTime(date.DateTime.max)
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
        )

    def testAppearanceNotificationAfterMarkingUncomplete(self):
        self.registerObserver(self.task.appearanceChangedEventType())
        self.task.setCompletionDateTime(date.DateTime.max)
        self.assertEvent(self.task.appearanceChangedEventType(), self.task)


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
        self.task.addPrerequisites([self.task2])
        self.task2.addDependencies([self.task])
        self.task2.setCompletionDateTime()
        self.assertTrue(self.task.inactive())

    def testACompletedTaskWithPlannedStartDateTimeInTheFutureIsNotInactive(
        self,
    ):
        self.task.setCompletionDateTime()
        self.assertFalse(self.task.inactive())

    def testPlannedStartDateTime(self):
        self.assertEqual(self.tomorrow, self.task.plannedStartDateTime())

    def testSetActualStartDateTimeToTodayMakesTaskActive(self):
        self.task.setActualStartDateTime(date.Now())
        self.assertTrue(self.task.active())

    def testDefaultInactiveColor(self):
        expectedColor = wx.Colour(
            *ast.literal_eval(self.settings.get("fgcolor", "inactivetasks"))
        )
        self.assertEqual(
            expectedColor, self.task.foregroundColor(recursive=True)
        )

    def testColorWhenTaskHasOwnColor(self):
        color = wx.Colour(160, 160, 160, 255)
        self.task.setForegroundColor(color)
        self.assertEqual(color, self.task.foregroundColor(recursive=True))

    def testIcon(self):
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testSelectedIcon(self):
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
        )

    def testIconAfterPlannedStartDateTimeHasPassed(self):
        now = self.task.plannedStartDateTime() + date.ONE_SECOND
        oldNow = date.Now
        date.Now = lambda: now
        wx.Yield()
        self.assertEqual(
            task.late.getBitmap(self.settings), self.task.icon(recursive=True)
        )
        date.Now = oldNow

    def testAppearanceNotificationAfterPlannedStartDateTimeHasPassed(self):
        self.registerObserver(self.task.appearanceChangedEventType())
        now = self.task.plannedStartDateTime() + date.ONE_SECOND
        oldNow = date.Now
        date.Now = lambda: now
        self.task.onTimeToStart()
        self.assertEvent(self.task.appearanceChangedEventType(), self.task)
        date.Now = oldNow

    def testIconAfterMarkingComplete(self):
        self.task.setCompletionDateTime()
        self.assertEqual(
            task.completed.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testSelectedIconAfterMarkingComplete(self):
        self.task.setCompletionDateTime()
        self.assertEqual(
            task.completed.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
        )

    def testAppearanceNotificationAfterMarkingComplete(self):
        self.registerObserver(self.task.appearanceChangedEventType())
        self.task.setCompletionDateTime()
        self.assertEvent(self.task.appearanceChangedEventType(), self.task)

    def testIconAfterChangingPlannedStartDateTime(self):
        self.task.setPlannedStartDateTime(
            date.Now() - date.TimeDelta(hours=72)
        )
        self.assertEqual(
            task.late.getBitmap(self.settings), self.task.icon(recursive=True)
        )

    def testSelectedIconAfterChangingPlannedStartDateTime(self):
        self.task.setPlannedStartDateTime(
            date.Now() - date.TimeDelta(hours=72)
        )
        self.assertEqual(
            task.late.getBitmap(self.settings),
            self.task.selectedIcon(recursive=True),
        )

    def testAppearanceNotificationAfterChangingPlannedStartDateTime(self):
        self.registerObserver(self.task.appearanceChangedEventType())
        self.task.setPlannedStartDateTime(
            date.Now() - date.TimeDelta(hours=72)
        )
        self.assertEvent(self.task.appearanceChangedEventType(), self.task)


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
        self.task.addPrerequisites([self.task2])
        self.task2.addDependencies([self.task])
        self.assertTrue(self.task.inactive())

    def testAppearanceNotificationWhenAddingAnUncompletedPrerequisite(self):
        # pylint: disable=E1101
        self.registerObserver(self.task.appearanceChangedEventType())
        self.task.addPrerequisites([self.task2])
        self.task2.addDependencies([self.task])
        self.assertEvent(self.task.appearanceChangedEventType(), self.task)

    def testTaskBecomesActiveWhenUncompletedPrerequisiteIsCompleted(self):
        # pylint: disable=E1101
        self.task.addPrerequisites([self.task2])
        self.task2.addDependencies([self.task])
        self.task2.setCompletionDateTime()
        self.assertFalse(self.task.inactive())

    def testAppearanceNotificationWhenUncompletedPrerequisiteIsCompleted(self):
        # pylint: disable=E1101
        self.task.addPrerequisites([self.task2])
        self.task2.addDependencies([self.task])
        self.registerObserver(
            self.task.appearanceChangedEventType(), eventSource=self.task
        )
        self.task2.setCompletionDateTime()
        self.assertEvent(self.task.appearanceChangedEventType(), self.task)


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
        self.task.addPrerequisites([self.task2])
        self.task2.addDependencies([self.task])
        self.task2.setCompletionDateTime()
        self.assertTrue(self.task.inactive())
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task.icon(recursive=True),
        )

    def testNoAppearanceNotificationWhenUncompletedPrerequisiteIsCompleted(
        self,
    ):
        # pylint: disable=E1101
        self.task.addPrerequisites([self.task2])
        self.task2.addDependencies([self.task])
        self.registerObserver(
            self.task.appearanceChangedEventType(), eventSource=self.task
        )
        self.task2.setCompletionDateTime()
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
            getImagePlural(task.inactive.getBitmap(self.settings)),
            self.task.icon(recursive=True),
        )

    def testSelectedIcon(self):
        self.assertEqual(
            getImageOpen(
                getImagePlural(task.inactive.getBitmap(self.settings))
            ),
            self.task.selectedIcon(recursive=True),
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

    def testEqualStatesDoesNotImplyEqualTasks(self):
        state = self.task1.__getstate__()
        self.task2.__setstate__(state)
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

    def testRemoveChildWithBudgetCausesBudgetNotification(self):
        self.task1_1.setBudget(date.TimeDelta(hours=100))
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual([(date.TimeDelta(), self.task1)], events)

    def testRemoveChildWithBudgetAndEffortCausesBudgetNotification(self):
        self.task1_1.setBudget(date.TimeDelta(hours=10))
        self.task1_1.addEffort(
            effort.Effort(
                self.task1_1,
                date.DateTime(2009, 1, 1, 1, 0, 0),
                date.DateTime(2009, 1, 1, 11, 0, 0),
            )
        )
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual([(date.TimeDelta(), self.task1)], events)

    def testRemoveChildWithoutBudgetCausesNoBudgetNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertFalse(events)

    def testRemoveChildWithEffortFromTaskWithBudgetCausesBudgetLeftNotification(
        self,
    ):
        self.task1.setBudget(date.TimeDelta(hours=100))
        self.task1_1.addEffort(
            effort.Effort(
                self.task1_1,
                date.DateTime(2005, 1, 1, 11, 0, 0),
                date.DateTime(2005, 1, 1, 12, 0, 0),
            )
        )
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertTrue((date.TimeDelta(hours=100), self.task1) in events)

    def testRemoveChildWithEffortFromTaskWithoutBudgetCausesNoBudgetLeftNotification(
        self,
    ):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
        self.task1_1.addEffort(
            effort.Effort(
                self.task1_1,
                date.DateTime(2005, 1, 1, 11, 0, 0),
                date.DateTime(2005, 1, 1, 12, 0, 0),
            )
        )
        self.task1.removeChild(self.task1_1)
        self.assertFalse(events)

    def testRemoveChildWithEffortCausesTimeSpentNotification(self):
        childEffort = effort.Effort(
            self.task1_1,
            date.DateTime(2005, 1, 1, 11, 0, 0),
            date.DateTime(2005, 1, 1, 12, 0, 0),
        )
        self.task1_1.addEffort(childEffort)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.timeSpentChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual(
            [(self.task1.timeSpent(recursive=True), self.task1)], events
        )

    def testRemoveChildWithoutEffortCausesNoTimeSpentNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.timeSpentChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertFalse(events)

    def testRemoveChildWithHighPriorityCausesPriorityNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        self.task1_1.setPriority(10)
        pub.subscribe(onEvent, task.Task.priorityChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual([(0, self.task1)], events)

    def testRemoveChildWithLowPriorityCausesNoTotalPriorityNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        self.task1_1.setPriority(-10)
        pub.subscribe(onEvent, task.Task.priorityChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertFalse(events)

    def testRemoveChildWithRevenueCausesTotalRevenueNotification(self):
        self.task1_1.setFixedFee(1000)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.revenueChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual([(0, self.task1)], events)

    def testRemoveChildWithoutRevenueCausesNoRevenueNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.revenueChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertFalse(events)

    def testRemoveTrackedChildCausesStopTrackingNotification(self):
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.trackingChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertEqual([(False, self.task1)], events)

    def testRemoveTrackedChildWhenParentIsTrackedTooCausesNoStopTrackingNotification(
        self,
    ):
        self.task1.addEffort(effort.Effort(self.task1))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.trackingChangedEventType())
        self.task1.removeChild(self.task1_1)
        self.assertFalse(events)

    def testSettingParentDueDateTimeEarlierThanChildDueDateTimeDoesNotChangeChildDueDateTime(
        self,
    ):
        childDueDateTime = date.Now() + date.TWO_HOURS
        self.task1_1.setDueDateTime(childDueDateTime)
        parentDueDateTime = date.Now() + date.ONE_HOUR
        self.task1.setDueDateTime(parentDueDateTime)
        self.assertEqual(childDueDateTime, self.task1_1.dueDateTime())

    def testSettingChildDueDateTimeLaterThanParentDueDateTimeDoesNotChangeParentDueDateTime(
        self,
    ):
        parentDueDateTime = date.Now() + date.ONE_HOUR
        self.task1.setDueDateTime(parentDueDateTime)
        childDueDateTime = date.Now() + date.TWO_HOURS
        self.task1_1.setDueDateTime(childDueDateTime)
        self.assertEqual(parentDueDateTime, self.task1.dueDateTime())

    def testRecursiveDueDateTime(self):
        self.assertEqual(
            date.DateTime(), self.task1.dueDateTime(recursive=True)
        )

    def testRecursiveDueDateTimeWhenChildDueToday(self):
        now = date.Now()
        self.task1_1.setDueDateTime(now)
        self.assertEqual(now, self.task1.dueDateTime(recursive=True))

    def testNotificationWhenRecursiveDueDateTimeChanges(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.dueDateTimeChangedEventType())
        now = date.Now()
        self.task1_1.setDueDateTime(now)
        self.assertEqual(
            set([(now, self.task1), (now, self.task1_1)]), set(events)
        )

    def testRecursiveDueDateTimeWhenChildDueTodayAndCompleted(self):
        self.task1_1.setDueDateTime(date.Now())
        self.task1_1.setCompletionDateTime(date.Now())
        self.assertEqual(
            date.DateTime(), self.task1.dueDateTime(recursive=True)
        )

    def testSettingPlannedStartDateTimeLaterThanChildPlannedStartDateTime(
        self,
    ):
        childPlannedStartDateTime = self.task1_1.plannedStartDateTime()
        self.task1.setPlannedStartDateTime(self.tomorrow)
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
        self.task1_1.setPlannedStartDateTime(self.yesterday)
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

    def testNotificationWhenRecursivePlannedStartDateTimeChanges(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(
            onEvent, task.Task.plannedStartDateTimeChangedEventType()
        )
        now = date.Now()
        self.task1_1.setPlannedStartDateTime(now)
        self.assertEqual(
            set([(now, self.task1), (now, self.task1_1)]), set(events)
        )

    def testRecursivePlannedStartDateTimeWhenChildStartsYesterday(self):
        self.task1_1.setPlannedStartDateTime(self.yesterday)
        self.assertEqual(
            self.yesterday, self.task1.plannedStartDateTime(recursive=True)
        )

    def testRecursiveActualStartDateTime(self):
        self.assertAlmostEqual(
            date.Now().toordinal(),
            self.task1.actualStartDateTime(recursive=True).toordinal(),
            places=2,
        )

    def testNotificationWhenRecursiveActualStartDateTimeChanges(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.actualStartDateTimeChangedEventType())
        now = date.Now()
        self.task1_1.setActualStartDateTime(now)
        self.assertEqual(
            set([(now, self.task1), (now, self.task1_1)]), set(events)
        )

    def testRecursiveActualStartDateTimeWhenChildStartsYesterday(self):
        self.task1_1.setActualStartDateTime(self.yesterday)
        self.assertEqual(
            self.yesterday, self.task1.actualStartDateTime(recursive=True)
        )

    def testRecursiveCompletionDateTime(self):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.task1_1.setCompletionDateTime(self.tomorrow)
        self.assertEqual(
            self.tomorrow, self.task1.completionDateTime(recursive=True)
        )

    def testNotificationWhenRecursiveCompletionDateTimeChanges(self):
        self.task1_1.setCompletionDateTime(self.yesterday)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.completionDateTimeChangedEventType())
        now = date.Now()
        self.task1_1.setCompletionDateTime(now)
        self.assertEqual(
            set([(now, self.task1), (now, self.task1_1)]), set(events)
        )

    def testRecursiveCompletionDateTimeWhenChildIsCompletedYesterday(self):
        self.task1_1.setCompletionDateTime(self.yesterday)
        now = date.Now()
        self.task1.setCompletionDateTime(now)
        self.assertEqual(now, self.task1.completionDateTime(recursive=True))

    def testNotificationWhenRecursiveReminderDateTimeChanges(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.reminderChangedEventType())
        now = date.Now()
        self.task1_1.setReminder(now)
        self.assertEqual(
            set([(now, self.task1), (now, self.task1_1)]), set(events)
        )

    def testNotAllChildrenAreCompleted(self):
        self.assertFalse(self.task1.allChildrenCompleted())

    def testAllChildrenAreCompletedAfterMarkingTheOnlyChildAsCompleted(self):
        self.task1_1.setCompletionDateTime()
        self.assertTrue(self.task1.allChildrenCompleted())

    def testTimeLeftRecursivelyIsInfinite(self):
        self.assertEqual(
            date.TimeDelta.max, self.task1.timeLeft(recursive=True)
        )

    def testTimeSpentRecursivelyIsZero(self):
        self.assertEqual(date.TimeDelta(), self.task.timeSpent(recursive=True))

    def testRecursiveBudgetWhenParentHasNoBudgetWhileChildDoes(self):
        self.task1_1.setBudget(date.ONE_HOUR)
        self.assertEqual(date.ONE_HOUR, self.task.budget(recursive=True))

    def testRecursiveBudgetLeftWhenParentHasNoBudgetWhileChildDoes(self):
        self.task1_1.setBudget(date.ONE_HOUR)
        self.assertEqual(date.ONE_HOUR, self.task.budgetLeft(recursive=True))

    def testRecursiveBudgetWhenBothHaveBudget(self):
        self.task1_1.setBudget(date.ONE_HOUR)
        self.task.setBudget(date.ONE_HOUR)
        self.assertEqual(date.TWO_HOURS, self.task.budget(recursive=True))

    def testRecursiveBudgetLeftWhenBothHaveBudget(self):
        self.task1_1.setBudget(date.ONE_HOUR)
        self.task.setBudget(date.ONE_HOUR)
        self.assertEqual(date.TWO_HOURS, self.task.budgetLeft(recursive=True))

    def testRecursiveBudgetLeftWhenChildBudgetIsAllSpent(self):
        self.task1_1.setBudget(date.ONE_HOUR)
        self.addEffort(date.ONE_HOUR, self.task1_1)
        self.assertEqual(
            date.TimeDelta(), self.task.budgetLeft(recursive=True)
        )

    def testBudgetNotification_WhenChildBudgetChanges(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetChangedEventType())
        self.task1_1.setBudget(date.ONE_HOUR)
        self.assertTrue((date.ONE_HOUR, self.task1) in events)

    def testBudgetNotification_WhenRemovingChildWithBudget(self):
        self.task1_1.setBudget(date.ONE_HOUR)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetChangedEventType())
        self.task.removeChild(self.task1_1)
        self.assertTrue((date.TimeDelta(0), self.task1) in events)

    def testBudgetLeftNotification_WhenChildBudgetChanges(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
        self.task1_1.setBudget(date.ONE_HOUR)
        self.assertTrue((date.ONE_HOUR, self.task1) in events)

    def testBudgetLeftNotification_WhenChildTimeSpentChanges(self):
        self.task1_1.setBudget(date.TWO_HOURS)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
        self.task1_1.addEffort(
            effort.Effort(
                self.task1_1,
                date.DateTime(2005, 1, 1, 10, 0, 0),
                date.DateTime(2005, 1, 1, 11, 0, 0),
            )
        )
        self.assertTrue((date.ONE_HOUR, self.task1) in events)

    def testBudgetLeftNotification_WhenParentHasNoBudget(self):
        self.task1_1.setBudget(date.TWO_HOURS)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
        self.task1.addEffort(
            effort.Effort(
                self.task1,
                date.DateTime(2005, 1, 1, 10, 0, 0),
                date.DateTime(2005, 1, 1, 11, 0, 0),
            )
        )
        self.assertTrue((date.TimeDelta(), self.task1) in events)

    def testNoBudgetLeftNotification_WhenChildTimeSpentChangesButNoBudget(
        self,
    ):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
        self.task1_1.addEffort(
            effort.Effort(
                self.task1_1,
                date.DateTime(2005, 1, 1, 10, 0, 0),
                date.DateTime(2005, 1, 1, 11, 0, 0),
            )
        )
        self.assertFalse(events)

    def testTimeSpentNotification_WhenChildTimeSpentChanges(self):
        childEffort = effort.Effort(
            self.task1_1,
            date.DateTime(2005, 1, 1, 10, 0, 0),
            date.DateTime(2005, 1, 1, 11, 0, 0),
        )
        self.task1_1.addEffort(childEffort)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.timeSpentChangedEventType())
        childEffort.setStop(date.DateTime(2005, 1, 1, 12, 0, 0))
        self.assertTrue((self.task1.timeSpent(), self.task1) in events)

    def testRecursivePriorityNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.priorityChangedEventType())
        self.task1_1.setPriority(10)
        self.assertEqual([(10, self.task1_1), (0, self.task1)], events)

    def testPriorityNotification_WithLowerChildPriority(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.priorityChangedEventType())
        self.task1_1.setPriority(-1)
        self.assertEqual([(-1, self.task1_1), (0, self.task1)], events)

    def testRevenueNotificationWhenChildHasEffortAdded(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.revenueChangedEventType())
        self.task1_1.setHourlyFee(100)
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

    def testNotificationWhenChildIsBeingTracked(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, self.task1.trackingChangedEventType())
        activeEffort = effort.Effort(self.task1_1)
        self.task1_1.addEffort(activeEffort)
        self.assertEqual(
            set([(True, self.task1), (True, self.task1_1)]), set(events)
        )

    def testNotificationWhenChildTrackingStops(self):
        activeEffort = effort.Effort(self.task1_1)
        self.task1_1.addEffort(activeEffort)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.trackingChangedEventType())
        activeEffort.setStop()
        self.assertEqual(
            set([(False, self.task), (False, self.task1_1)]), set(events)
        )

    def testSetFixedFeeOfChild(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.fixedFeeChangedEventType())
        self.task1_1.setFixedFee(1000)
        self.assertTrue((1000, self.task1) in events)

    def testGetFixedFeeRecursive(self):
        self.task.setFixedFee(2000)
        self.task1_1.setFixedFee(1000)
        self.assertEqual(3000, self.task.fixedFee(recursive=True))

    def testRecursiveRevenueFromFixedFee(self):
        self.task.setFixedFee(2000)
        self.task1_1.setFixedFee(1000)
        self.assertEqual(3000, self.task.revenue(recursive=True))

    def testForegroundColorChangeNotificationOfEfforts(self):
        self.registerObserver(effort.Effort.appearanceChangedEventType())
        self.task.addEffort(effort.Effort(self.task))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        self.task.setForegroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testBackgroundColorChangeNotificationOfEfforts(self):
        self.registerObserver(effort.Effort.appearanceChangedEventType())
        self.task.addEffort(effort.Effort(self.task))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        self.task.setBackgroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testForegroundColorChangeNotificationOfEfforts_ViaCategory(self):
        self.registerObserver(effort.Effort.appearanceChangedEventType())
        self.task.addEffort(effort.Effort(self.task))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        cat = category.Category("Cat")
        cat.addCategorizable(self.task)
        self.task.addCategory(cat)
        cat.setForegroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testBackgroundColorChangeNotificationOfEfforts_ViaCategory(self):
        self.registerObserver(effort.Effort.appearanceChangedEventType())
        self.task.addEffort(effort.Effort(self.task))
        self.task1_1.addEffort(effort.Effort(self.task1_1))
        cat = category.Category("Cat")
        cat.addCategorizable(self.task)
        self.task.addCategory(cat)
        cat.setBackgroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testChildUsesForegroundColorOfParentsCategory(self):
        cat = category.Category("Cat", fgColor=wx.RED)
        cat.addCategorizable(self.task)
        self.task.addCategory(cat)
        self.assertEqual(wx.RED, self.task1_1.foregroundColor(recursive=True))

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
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(False)
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

    def testPercentageCompletedNotificationWhenChildPercentageChanges(self):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.percentageCompleteChangedEventType())
        self.task1_1.setPercentageComplete(50)
        self.assertEqual([(50, self.task1_1), (50, self.task)], events)

    def testPercentageCompletedNotificationWhenMarkCompletedSettingChanges(
        self,
    ):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        self.task1_1.setPercentageComplete(50)
        pub.subscribe(onEvent, task.Task.percentageCompleteChangedEventType())
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", False
        )
        self.assertEqual([(0, self.task)], events)

    def testIcon(self):
        self.assertEqual(
            getImagePlural(task.active.getBitmap(self.settings)),
            self.task.icon(recursive=True),
        )

    def testSelectedIcon(self):
        self.assertEqual(
            getImageOpen(getImagePlural(task.active.getBitmap(self.settings))),
            self.task.selectedIcon(recursive=True),
        )

    def testChildIcon(self):
        self.assertEqual(
            task.active.getBitmap(self.settings),
            self.task1_1.icon(recursive=True),
        )

    def testChildSelectedIcon(self):
        self.assertEqual(
            task.active.getBitmap(self.settings),
            self.task1_1.selectedIcon(recursive=True),
        )

    def testIconWithPluralVersion(self):
        self.task.setIcon("books_icon")
        self.assertEqual("books_icon", self.task.icon(recursive=True))

    def testIconWithSingularVersion(self):
        self.task.setIcon("book_icon")
        self.assertEqual("books_icon", self.task.icon(recursive=True))

    def testChildIsInactiveWhenParentHasPrerequisite(self):
        prerequisite = task.Task()
        self.task.addPrerequisites([prerequisite])
        self.assertTrue(self.task1_1.inactive())

    def testChildIsNotActiveWhenParentHasPrerequisite(self):
        prerequisite = task.Task()
        self.task.addPrerequisites([prerequisite])
        self.assertFalse(self.task1_1.active())

    def testAddingPrerequisiteToParentRecomputesChildAppearance(self):
        # First make sure the icon is cached:
        self.assertEqual(
            task.active.getBitmap(self.settings),
            self.task1_1.icon(recursive=True),
        )
        prerequisite = task.Task()
        self.task.addPrerequisites([prerequisite])
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task1_1.icon(recursive=True),
        )

    def testSettingPrerequisitesOfParentRecomputesChildAppearance(self):
        # First make sure the icon is cached:
        self.assertEqual(
            task.active.getBitmap(self.settings),
            self.task1_1.icon(recursive=True),
        )
        prerequisite = task.Task()
        self.task.setPrerequisites([prerequisite])
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task1_1.icon(recursive=True),
        )

    def testRemovingPrerequisiteFromParentRecomputesChildAppearance(self):
        prerequisite = task.Task()
        self.task.addPrerequisites([prerequisite])
        # First make sure the icon is cached:
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task1_1.icon(recursive=True),
        )
        self.task.removePrerequisites([prerequisite])
        self.assertEqual(
            task.late.getBitmap(self.settings),
            self.task1_1.icon(recursive=True),
        )

    def testCompletingPrerequisiteOfParentRecomputesChildAppearance(self):
        prerequisite = task.Task()
        self.task.addPrerequisites([prerequisite])
        prerequisite.addDependencies([self.task])
        # First make sure the icon is cached:
        self.assertEqual(
            task.inactive.getBitmap(self.settings),
            self.task1_1.icon(recursive=True),
        )
        prerequisite.setCompletionDateTime(date.Now())
        self.assertEqual(
            task.late.getBitmap(self.settings),
            self.task1_1.icon(recursive=True),
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
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(True)
        self.task1_1.setCompletionDateTime()
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
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(False)
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
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(False)
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
            getImagePlural(task.completed.getBitmap(self.settings)),
            self.task.icon(recursive=True),
        )

    def testSelectedIcon(self):
        self.assertEqual(
            getImagePlural(task.completed.getBitmap(self.settings)),
            self.task.selectedIcon(recursive=True),
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
            getImagePlural(task.overdue.getBitmap(self.settings)),
            self.task.icon(recursive=True),
        )

    def testSelectedIcon(self):
        self.assertEqual(
            getImageOpen(
                getImagePlural(task.overdue.getBitmap(self.settings))
            ),
            self.task.selectedIcon(recursive=True),
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
            getImagePlural(task.duesoon.getBitmap(self.settings)),
            self.task.icon(recursive=True),
        )

    def testSelectedIcon(self):
        self.assertEqual(
            getImageOpen(
                getImagePlural(task.duesoon.getBitmap(self.settings))
            ),
            self.task.selectedIcon(recursive=True),
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
        self.assertEqual(self.task1effort1.duration(), self.task.timeSpent())

    def testTimeSpentRecursivelyOnTaskEqualsEffortDuration(self):
        self.assertEqual(
            self.task1effort1.duration(), self.task.timeSpent(recursive=True)
        )

    def testTimeSpentOnTaskIsZeroAfterRemovalOfEffort(self):
        self.task.removeEffort(self.task1effort1)
        self.assertEqual(date.TimeDelta(), self.task.timeSpent())

    def testTaskEffortListContainsTheOneEffortAdded(self):
        self.assertEqual([self.task1effort1], self.task.efforts())

    def testStartTrackingEffort(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, self.task.trackingChangedEventType())
        self.task1effort1.setStop(date.DateTime.max)
        self.assertEqual([(True, self.task)], events)

    def testStopTrackingEffort(self):
        self.task1effort1.setStop(date.DateTime.max)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, self.task.trackingChangedEventType())
        self.task1effort1.setStop()
        self.assertEqual([(False, self.task)], events)

    def testRevenueWithEffortButWithZeroFee(self):
        self.assertEqual(0, self.task.revenue())

    def testNotifyEffortOfBackgroundColorChange(self):
        self.registerObserver(effort.Effort.appearanceChangedEventType())
        self.task.setBackgroundColor(wx.RED)
        self.assertEvent(
            effort.Effort.appearanceChangedEventType(), self.task1effort1
        )


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
            self.task1effort1.duration() + self.task1effort2.duration()
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
                "icon": "bomb_icon",
            }
        ]

    def testTaskIsBeingTracked(self):
        self.assertTrue(self.task.isBeingTracked())

    def testStopTracking(self):
        self.task.stopTracking()
        self.assertFalse(self.task.isBeingTracked())

    def testNoStartTrackingEventBecauseActiveEffortWasAddedViaConstructor(
        self,
    ):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.trackingChangedEventType())
        task.Task(efforts=[effort.Effort(None)])
        self.assertFalse(events)

    def testNoStartTrackingEventAfterAddingASecondActiveEffort(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.trackingChangedEventType())
        self.task.addEffort(effort.Effort(self.task))
        self.assertFalse(events)

    def testNoStopTrackingEventAfterRemovingFirstOfTwoActiveEfforts(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.trackingChangedEventType())
        secondEffort = effort.Effort(self.task)
        self.task.addEffort(secondEffort)
        self.task.removeEffort(secondEffort)
        self.assertFalse(events)

    def testRemoveActiveEffortShouldCauseStopTrackingEvent(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, self.task.trackingChangedEventType())
        self.task.removeEffort(self.task1effort1)
        self.assertEqual([(False, self.task)], events)

    def testStopTrackingEvent(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, self.task.trackingChangedEventType())
        self.task.stopTracking()
        self.assertEqual([(False, self.task)], events)

    def testIcon(self):
        self.assertEqual("clock_icon", self.task.icon(recursive=True))

    def testSelectedIcon(self):
        self.assertEqual("clock_icon", self.task.selectedIcon(recursive=True))

    def testIconAfterStopTracking(self):
        self.task.stopTracking()
        self.assertNotEqual("clock_icon", self.task.icon(recursive=True))

    def testSelectedIconAfterStopTracking(self):
        self.task.stopTracking()
        self.assertNotEqual(
            "clock_icon", self.task.selectedIcon(recursive=True)
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
        self.assertEqual(self.task1effort1.duration(), self.task1.timeSpent())

    def testTimeSpentRecursivelyOnTaskEqualsTotalEffortDuration(self):
        self.assertEqual(
            self.task1effort1.duration() + self.task1_1effort1.duration(),
            self.task1.timeSpent(recursive=True),
        )

    def testEffortsRecursive(self):
        self.assertEqual(
            [self.task1effort1, self.task1_1effort1],
            self.task1.efforts(recursive=True),
        )

    def testRecursiveRevenue(self):
        self.task.setHourlyFee(100)
        self.task1_1.setHourlyFee(100)
        self.assertEqual(4800, self.task.revenue(recursive=True))

    def testChildEffortBackgroundColorNotification(self):
        eventType = self.task1_1effort1.appearanceChangedEventType()
        self.registerObserver(eventType, self.task1_1effort1)
        self.task.setBackgroundColor(wx.RED)
        self.assertEvent(eventType, self.task1_1effort1)


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
            self.task1effort1.duration()
            + self.task1_1effort1.duration()
            + self.task1_1_1effort1.duration(),
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

    def testBudgetLeftNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.budgetLeftChangedEventType())
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
        self.task.setBudget(date.ONE_HOUR)
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
        self.task.setReminder(someOtherTime)
        for recursive in (False, True):
            self.assertReminder(someOtherTime, recursive=recursive)

    def testCancelReminder(self):
        self.task.setReminder()
        self.assertReminder(None)

    def testSnoozeReminder(self):
        snoozePeriod = date.ONE_HOUR
        now = date.Now()
        self.task.snoozeReminder(snoozePeriod, now=lambda: now)
        self.assertReminder(now + snoozePeriod)

    def testSnoozeReminderTwice(self):
        snoozePeriod = date.ONE_HOUR
        now = date.Now()
        self.task.snoozeReminder(snoozePeriod, now=lambda: now)
        self.task.snoozeReminder(snoozePeriod, now=lambda: now + snoozePeriod)
        self.assertReminder(now + 2 * snoozePeriod)

    def testSnoozeWhenReminderNotSet(self):
        self.task.setReminder()
        snoozePeriod = date.ONE_HOUR
        now = date.Now()
        self.task.snoozeReminder(snoozePeriod, now=lambda: now)
        self.assertReminder(now + snoozePeriod)

    def testSnoozeWithZeroTimeDelta(self):
        self.task.snoozeReminder(date.TimeDelta())
        self.assertReminder(None)
        self.assertEqual(None, self.task.reminder(includeSnooze=False))

    def testOriginalReminder(self):
        self.assertEqual(
            self.initialReminder(), self.task.reminder(includeSnooze=False)
        )

    def testOriginalReminderAfterSnooze(self):
        self.task.snoozeReminder(date.ONE_HOUR)
        self.assertEqual(
            self.initialReminder(), self.task.reminder(includeSnooze=False)
        )

    def testOriginalReminderAfterTwoSnoozes(self):
        self.task.snoozeReminder(date.ONE_HOUR)
        self.task.snoozeReminder(date.ONE_HOUR)
        self.assertEqual(
            self.initialReminder(), self.task.reminder(includeSnooze=False)
        )

    def testOriginalReminderAfterCancel(self):
        self.task.setReminder(None)
        self.assertEqual(None, self.task.reminder(includeSnooze=False))

    def testCancelReminderWithMaxDateTime(self):
        self.task.setReminder(date.DateTime.max)
        self.assertReminder(None)

    def testTaskNotifiesObserverOfNewReminder(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.reminderChangedEventType())
        newReminder = self.initialReminder() + date.ONE_SECOND
        self.task.setReminder(newReminder)
        self.assertEqual([(newReminder, self.task)], events)

    def testNewReminderCancelsPreviousReminder(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.reminderChangedEventType())
        self.task.setReminder()
        self.assertEqual([(None, self.task)], events)

    def testMarkCompletedCancelsReminder(self):
        self.task.setCompletionDateTime()
        self.assertReminder(None)

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
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(False)
        self.assertEqual(
            False, self.task.shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def testSetSettingCausesNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(
            onEvent,
            task.Task.shouldMarkCompletedWhenAllChildrenCompletedChangedEventType(),
        )
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(False)
        self.assertEqual([(False, self.task)], events)

    def testSetSettingCausesPercentageCompleteNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.percentageCompleteChangedEventType())
        # The calculation of the total percentage complete depends on whether
        # a task is marked completed when all its children are completed
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(False)
        self.assertEqual([(0, self.task)], events)


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
        self.task.setShouldMarkCompletedWhenAllChildrenCompleted(True)
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
            self.assertEqual(
                attachment.FileAttachment(name), self.task.attachments()[index]
            )

    def testRemoveNonExistingAttachment(self):
        self.task.removeAttachments("Non-existing attachment")

        for index, name in enumerate(
            self.taskCreationKeywordArguments()[0]["attachments"]
        ):
            self.assertEqual(
                attachment.FileAttachment(name), self.task.attachments()[index]
            )

    def testCopy_CreatesNewListOfAttachments(self):
        copy = self.task.copy()
        self.assertEqual(copy.attachments(), self.task.attachments())
        self.task.removeAttachments(self.task.attachments()[0])
        self.assertNotEqual(copy.attachments(), self.task.attachments())

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
        self.task1_1.setCompletionDateTime()
        self.assertEqual(1, self.task1.priority(recursive=True))

    def testPriorityNotificationWhenMarkingChildCompleted(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.priorityChangedEventType())
        self.task1_1.setCompletionDateTime()
        self.assertEqual((1, self.task1), events[0])

    def testPriorityNotificationWhenMarkingChildUncompleted(self):
        self.task1_1.setCompletionDateTime()
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.priorityChangedEventType())
        self.task1_1.setCompletionDateTime(date.DateTime())
        self.assertEqual((1, self.task1), events[0])


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

    def testRevenue_Notification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.revenueChangedEventType())
        self.task.addEffort(self.effort)
        self.assertEqual([(100, self.task)], events)

    def testRecursiveRevenue_Notification(self):
        child = task.Task("child", hourlyFee=100)
        self.task.addChild(child)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.revenueChangedEventType())
        child.addEffort(
            effort.Effort(
                child,
                date.DateTime(2005, 1, 1, 10, 0, 0),
                date.DateTime(2005, 1, 1, 11, 0, 0),
            )
        )
        self.assertTrue((100, self.task) in events)

    def testAddingEffortDoesNotTriggerRevenueNotificationForEffort(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, effort.Effort.revenueChangedEventType())
        self.task.addEffort(self.effort)
        self.assertFalse(events)

    def testTaskNotifiesEffortObserversOfRevenueChange(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, effort.Effort.revenueChangedEventType())
        self.task.addEffort(self.effort)
        self.task.setHourlyFee(200)
        self.assertEqual([(200, self.effort)], events)


class TaskWithCategoryTestCase(TaskTestCase):
    def taskCreationKeywordArguments(self):
        self.category = category.Category("category")  # pylint: disable=W0201
        return [dict(categories=set([self.category]))]

    def setUp(self):
        super().setUp()
        self.category.addCategorizable(self.task)

    def testCategory(self):
        self.assertEqual(set([self.category]), self.task.categories())

    def testCategoryIcon(self):
        self.category.setIcon("icon")
        self.assertEqual("icon", self.task.icon(recursive=True))

    def testCategorySelectedIcon(self):
        self.category.setSelectedIcon("icon")
        self.assertEqual("icon", self.task.selectedIcon(recursive=True))


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
        completed.setCompletionDateTime()
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
            wx.Colour(*ast.literal_eval(self.settings.get("fgcolor", "activetasks"))),
            active.statusFgColor(),
        )

    def testActiveTaskWithCategory(self):
        activeTask = task.Task(actualStartDateTime=date.Now())
        redCategory = category.Category(subject="Red category", fgColor=wx.RED)
        activeTask.addCategory(redCategory)
        redCategory.addCategorizable(activeTask)
        self.assertEqual(wx.RED, activeTask.foregroundColor(recursive=True))


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
        self.task.removePrerequisites([self.prerequisite])
        self.assertFalse(self.task.prerequisites())

    def testRemovePrerequisiteNotInPrerequisites(self):
        self.task.removePrerequisites([task.Task()])
        self.assertTrue(self.prerequisite in self.task.prerequisites())

    def testRemovePrerequisiteNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.prerequisitesChangedEventType())
        self.task.removePrerequisites([self.prerequisite])
        self.assertEqual([(set([]), self.task)], events)

    def testSetPrerequisitesRemovesOldPrerequisites(self):
        newPrerequisites = set([task.Task()])
        self.task.setPrerequisites(newPrerequisites)
        self.assertEqual(newPrerequisites, self.task.prerequisites())

    def testDontCopyPrerequisites(self):
        self.assertFalse(self.prerequisite in self.task.copy().prerequisites())

    def testPrerequisiteSubjectChangedNotification(self):
        self.prerequisite.addDependencies([self.task])
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.prerequisitesChangedEventType())
        self.prerequisite.setSubject("New subject")
        self.assertEqual([(set([self.prerequisite]), self.task)], events)

    def testAppearanceNotificationAfterMarkingPrerequisiteCompleted(self):
        self.prerequisite.addDependencies([self.task])
        eventType = self.task.appearanceChangedEventType()
        self.registerObserver(eventType, eventSource=self.task)
        self.prerequisite.setCompletionDateTime(date.Now())
        self.assertEvent(eventType, self.task)


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
        self.task.removeDependencies([self.dependency])
        self.assertFalse(self.task.dependencies())

    def testRemoveDependencyNotInDependencies(self):
        self.task.removeDependencies([task.Task()])
        self.assertTrue(self.dependency in self.task.dependencies())

    def testRemoveDependencyNotification(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.dependenciesChangedEventType())
        self.task.removeDependencies([self.dependency])
        self.assertEqual([(set(), self.task)], events)

    def testSetDependenciesRemovesOldDependencies(self):
        newDependencies = set([task.Task()])
        self.task.setDependencies(newDependencies)
        self.assertEqual(newDependencies, self.task.dependencies())

    def testDontCopyDependencies(self):
        self.assertFalse(self.dependency in self.task.copy().dependencies())

    def testDependencySubjectChangedNotification(self):
        self.dependency.addPrerequisites([self.task])
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, task.Task.dependenciesChangedEventType())
        self.dependency.setSubject("New subject")
        self.assertEqual([(set([self.dependency]), self.task)], events)


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
            microsecond=now.microsecond,
        )
        nextFriday = tomorrow.endOfWorkWeek().replace(**currentTimeKwArgs)
        nextMonday = (
            (now + date.ONE_WEEK)
            .startOfWorkWeek()
            .replace(**currentTimeKwArgs)
        )
        startOfWorkingDayHour = self.settings.getint("view", "efforthourstart")
        startOfWorkingDayKwArgs = dict(
            hour=startOfWorkingDayHour, minute=0, second=0, microsecond=0
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
            microsecond=0,
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
                "view", "defaultcompletiondatetime", "preset_" + timeValue
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


class TaskScheduledTest(TaskTestCase):
    def setUp(self):
        super().setUp([("behavior", "duesoonhours", 1)])

    def taskCreationKeywordArguments(self):
        return [
            {
                "dueDateTime": date.Now() + date.TWO_HOURS,
                "plannedStartDateTime": date.Now() + date.ONE_HOUR,
            }
        ]

    def testOverDueIsScheduled(self):
        self.assertTrue(date.Scheduler().is_scheduled(self.task.onOverDue))

    def testStartedIsScheduled(self):
        self.assertTrue(date.Scheduler().is_scheduled(self.task.onTimeToStart))

    def testDueSoonIsScheduled(self):
        self.assertTrue(date.Scheduler().is_scheduled(self.task.onDueSoon))


class TaskNotScheduledTest(TaskTestCase):
    def setUp(self):
        super().setUp([("behavior", "duesoonhours", 1)])

    def taskCreationKeywordArguments(self):
        return [
            {"subject": "Task"},
            {"dueDateTime": date.Now() - date.ONE_HOUR},
        ]

    def testOverDueIsNotScheduled(self):
        self.assertFalse(date.Scheduler().is_scheduled(self.task.onOverDue))

    def testOverdueIsNotScheduledBecauseTooLate(self):
        self.assertFalse(
            date.Scheduler().is_scheduled(self.tasks[1].onOverDue)
        )

    def testStartedIsNotScheduled(self):
        self.assertFalse(
            date.Scheduler().is_scheduled(self.task.onTimeToStart)
        )

    def testDueSoonIsNotScheduled(self):
        self.assertFalse(date.Scheduler().is_scheduled(self.task.onDueSoon))
