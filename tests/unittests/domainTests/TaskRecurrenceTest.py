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


class RecurringTaskTestCase(test.TestCase):
    def setUp(self):
        self.settings = task.Task.settings = config.Settings(load=False)
        self.now = date.Now()
        self.yesterday = self.now - date.ONE_DAY
        self.tomorrow = self.now + date.ONE_DAY
        kwargs_list = self.taskCreationKeywordArguments()
        self.tasks = [
            task.Task(**kwargs) for kwargs in kwargs_list
        ]  # pylint: disable=W0142
        self.task = self.tasks[0]
        for index, eachTask in enumerate(self.tasks):
            taskLabel = "task%d" % (index + 1)
            setattr(self, taskLabel, eachTask)

    def taskCreationKeywordArguments(self):
        return [dict(recurrence=self.createRecurrence())]

    def createRecurrence(self):
        raise NotImplementedError  # pragma: no cover


class RecurringTaskWithChildTestCase(RecurringTaskTestCase):
    def taskCreationKeywordArguments(self):
        kwargs_list = super(
            RecurringTaskWithChildTestCase, self
        ).taskCreationKeywordArguments()
        kwargs_list[0]["children"] = [task.Task(subject="child")]
        return kwargs_list

    def createRecurrence(self):
        raise NotImplementedError  # pragma: no cover


class RecurringTaskWithRecurringChildTestCase(RecurringTaskTestCase):
    def taskCreationKeywordArguments(self):
        kwargs_list = super(
            RecurringTaskWithRecurringChildTestCase, self
        ).taskCreationKeywordArguments()
        kwargs_list[0]["children"] = [
            task.Task(subject="child", recurrence=self.createRecurrence())
        ]
        return kwargs_list

    def createRecurrence(self):
        raise NotImplementedError  # pragma: no cover


class CommonRecurrenceTestsMixin(object):
    def testSetRecurrenceViaConstructor(self):
        self.assertEqual(self.createRecurrence(), self.task.recurrence())

    def testMarkCompletedSetsNewPlannedStartDateIfItWasSetPreviously(self):
        plannedStartDateTime = self.task.plannedStartDateTime()
        self.task.set_completion_date_time()
        self.assertEqual(
            self.createRecurrence()(plannedStartDateTime),
            self.task.plannedStartDateTime(),
        )

    def testNoActualStartDateAfterRecurrence(self):
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.actualStartDateTime())

    def testMarkCompletedResetsActualStartDateIfItWasSetPreviously(self):
        self.task.set_actual_start_date_time(date.Now())
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.actualStartDateTime())

    def testMarkCompletedSetsNewDueDateIfItWasSetPreviously(self):
        self.task.set_due_date_time(self.tomorrow)
        self.task.set_completion_date_time(self.tomorrow)
        self.assertEqual(
            self.createRecurrence()(self.tomorrow), self.task.dueDateTime()
        )

    def testMarkCompletedDoesNotSetPlannedStartDateIfItWasNotSetPreviously(
        self,
    ):
        self.task.set_planned_start_date_time(date.DateTime())
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.plannedStartDateTime())

    def testMarkCompletedDoesNotSetDueDateIfItWasNotSetPreviously(self):
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.dueDateTime())

    def testRecurringTaskIsNotCompletedWhenMarkedCompleted(self):
        self.task.set_completion_date_time()
        self.assertFalse(self.task.completed())

    def testMarkCompletedDoesNotSetReminderIfItWasNotSetPreviously(self):
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.reminder())

    def testMarkCompletedSetsNewReminderIfItWasSetPreviously(self):
        reminder = self.now + date.TimeDelta(seconds=10)
        self.task.set_reminder(reminder)
        self.task.set_completion_date_time()
        self.assertEqual(
            self.createRecurrence()(reminder), self.task.reminder()
        )

    def testMarkCompletedIgnoresSnoozeWhenSettingNewReminder(self):
        reminder = self.now + date.TimeDelta(seconds=10)
        self.task.set_reminder(reminder)
        self.task.snooze_reminder(
            date.TimeDelta(seconds=30), now=lambda: self.now
        )
        self.task.set_completion_date_time()
        self.assertEqual(
            self.createRecurrence()(reminder), self.task.reminder()
        )

    def testMarkCompletedResetPercentageComplete(self):
        self.task.setPercentageComplete(50)
        self.task.set_completion_date_time()
        self.assertEqual(0, self.task.percentageComplete())

    def testCopyRecurrence(self):
        self.assertEqual(self.task.copy().recurrence(), self.task.recurrence())


class TaskWithWeeklyRecurrenceFixture(
    RecurringTaskTestCase, CommonRecurrenceTestsMixin
):
    def createRecurrence(self):
        return date.Recurrence("weekly")


class TaskWithDailyRecurrenceFixture(
    RecurringTaskTestCase, CommonRecurrenceTestsMixin
):
    def createRecurrence(self):
        return date.Recurrence("daily")


class TaskWithMonthlyRecurrenceFixture(
    RecurringTaskTestCase, CommonRecurrenceTestsMixin
):
    def createRecurrence(self):
        return date.Recurrence("monthly")


class TaskWithYearlyRecurrenceFixture(
    RecurringTaskTestCase, CommonRecurrenceTestsMixin
):
    def createRecurrence(self):
        return date.Recurrence("yearly")


class TaskWithDailyRecurrenceThatHasRecurredFixture(
    RecurringTaskTestCase, CommonRecurrenceTestsMixin
):
    initialRecurrenceCount = 3

    def createRecurrence(self):
        return date.Recurrence("daily", count=self.initialRecurrenceCount)


class TaskWithDailyRecurrenceThatHasMaxRecurrenceCountFixture(
    RecurringTaskTestCase, CommonRecurrenceTestsMixin
):
    maxRecurrenceCount = 2

    def createRecurrence(self):
        return date.Recurrence("daily", maximum=self.maxRecurrenceCount)

    def testRecurLessThanMaxRecurrenceCount(self):
        for _ in range(self.maxRecurrenceCount):
            self.task.set_completion_date_time()
        self.assertFalse(self.task.completed())

    def testRecurExactlyMaxRecurrenceCount(self):
        for _ in range(self.maxRecurrenceCount + 1):
            self.task.set_completion_date_time()
        self.assertTrue(self.task.completed())

    def test_recurring_saves_the_count_through_the_setter(self):
        before = self.task.recurrence()
        self.task.set_modification_datetime(date.DateTime.min)
        self.task.set_completion_date_time()
        self.assertEqual((0, 1), (before.count, self.task.recurrence().count))
        self.assertTrue(date.DateTime.min < self.task.modificationDateTime())


class TaskWithDailyRecurrenceBasedOnCompletionFixture(
    RecurringTaskTestCase, CommonRecurrenceTestsMixin
):
    def createRecurrence(self):
        return date.Recurrence("daily", recurBasedOnCompletion=True)

    def testNoDates(self):
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.plannedStartDateTime())
        self.assertEqual(date.DateTime(), self.task.dueDateTime())
        self.assertEqual(date.DateTime(), self.task.completionDateTime())

    def testPlannedStartDateDayBeforeYesterday(self):
        self.task.set_planned_start_date_time(
            self.now - date.TimeDelta(hours=48)
        )
        self.task.set_completion_date_time(self.now)
        self.assertEqual(
            self.now + date.ONE_DAY, self.task.plannedStartDateTime()
        )

    def testPlannedStartDateToday(self):
        self.task.set_planned_start_date_time(self.now.startOfDay())
        self.task.set_completion_date_time(self.now)
        self.assertEqual(
            self.tomorrow.startOfDay(), self.task.plannedStartDateTime()
        )

    def testPlannedStartDateTomorrow(self):
        self.task.set_planned_start_date_time(self.tomorrow.startOfDay())
        self.task.set_completion_date_time(self.now)
        self.assertEqual(
            self.tomorrow.startOfDay(), self.task.plannedStartDateTime()
        )

    def testDueDateToday(self):
        self.task.set_due_date_time(self.now.endOfDay())
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.tomorrow.endOfDay(), self.task.dueDateTime())

    def testDueDateYesterday(self):
        self.task.set_due_date_time(self.yesterday)
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.tomorrow, self.task.dueDateTime())

    def testDueDateTomorrow(self):
        self.task.set_due_date_time(self.tomorrow)
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.tomorrow, self.task.dueDateTime())

    def testPlannedStartAndDueToday(self):
        self.task.set_planned_start_date_time(self.now.startOfDay())
        self.task.set_due_date_time(self.now.endOfDay())
        self.task.set_completion_date_time(self.now)
        self.assertEqual(
            self.tomorrow.startOfDay(), self.task.plannedStartDateTime()
        )
        self.assertEqual(self.tomorrow.endOfDay(), self.task.dueDateTime())

    def testPlannedStartAndDueDateInThePast(self):
        self.task.set_planned_start_date_time(
            self.now - date.TimeDelta(hours=48)
        )
        self.task.set_due_date_time(self.yesterday)
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.now, self.task.plannedStartDateTime())
        self.assertEqual(self.tomorrow, self.task.dueDateTime())

    def testPlannedStartInThePastAndDueInTheFuture(self):
        self.task.set_planned_start_date_time(self.yesterday)
        self.task.set_due_date_time(self.tomorrow)
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.yesterday, self.task.plannedStartDateTime())
        self.assertEqual(self.tomorrow, self.task.dueDateTime())

    def testPlannedStartAndDueInTheFuture(self):
        self.task.set_planned_start_date_time(self.tomorrow)
        self.task.set_due_date_time(self.tomorrow + date.ONE_DAY)
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.now, self.task.plannedStartDateTime())
        self.assertEqual(self.tomorrow, self.task.dueDateTime())


class CommonRecurrenceTestsMixinWithChild(CommonRecurrenceTestsMixin):
    # pylint: disable=E1101

    def testChildPlannedStartDateRecursToo(self):
        self.task.set_completion_date_time()
        self.assertAlmostEqual(
            self.task.plannedStartDateTime().toordinal(),
            self.task.children()[0].plannedStartDateTime().toordinal(),
        )

    def testChildDueDateRecursToo_ParentAndChildHaveNoDueDate(self):
        self.task.set_completion_date_time()
        self.assertAlmostEqual(
            self.task.dueDateTime().toordinal(),
            self.task.children()[0].dueDateTime().toordinal(),
        )

    def testChildDueDateRecursToo_ParentAndChildHaveSameDueDate(self):
        child = self.task.children()[0]
        self.task.set_due_date_time(self.tomorrow)
        child.set_due_date_time(self.tomorrow)
        self.task.set_completion_date_time()
        self.assertAlmostEqual(
            self.task.dueDateTime().toordinal(),
            self.task.children()[0].dueDateTime().toordinal(),
        )

    def testChildDueDateRecursToo_ChildHasEarlierDueDate(self):
        child = self.task.children()[0]
        self.task.set_due_date_time(self.tomorrow)
        child.set_due_date_time(self.now)
        self.task.set_completion_date_time()
        self.assertEqual(
            self.createRecurrence()(self.now),
            self.task.children()[0].dueDateTime(),
        )


class CommonRecurrenceTestsMixinWithRecurringChild(CommonRecurrenceTestsMixin):
    # pylint: disable=E1101

    def testChildDoesNotRecurWhenParentDoes(self):
        origPlannedStartDateTime = self.task.children()[
            0
        ].plannedStartDateTime()
        self.task.set_completion_date_time()
        self.assertEqual(
            origPlannedStartDateTime,
            self.task.children()[0].plannedStartDateTime(),
        )

    def testDownwardsRecursiveRecurrence(self):
        expectedRecurrence = min(
            [self.task.recurrence(), self.task.children()[0].recurrence()]
        )
        self.assertEqual(
            expectedRecurrence,
            self.task.recurrence(recursive=True, upwards=False),
        )


class TaskWithWeeklyRecurrenceWithChildFixture(
    RecurringTaskWithChildTestCase, CommonRecurrenceTestsMixinWithChild
):
    def createRecurrence(self):
        return date.Recurrence("weekly")


class TaskWithDailyRecurrenceWithChildFixture(
    RecurringTaskWithChildTestCase, CommonRecurrenceTestsMixinWithChild
):
    def createRecurrence(self):
        return date.Recurrence("daily")


class TaskWithWeeklyRecurrenceWithRecurringChildFixture(
    RecurringTaskWithRecurringChildTestCase,
    CommonRecurrenceTestsMixinWithRecurringChild,
):

    def createRecurrence(self):
        return date.Recurrence("weekly")


class TaskWithDailyRecurrenceWithRecurringChildFixture(
    RecurringTaskWithRecurringChildTestCase,
    CommonRecurrenceTestsMixinWithRecurringChild,
):

    def createRecurrence(self):
        return date.Recurrence("daily")
