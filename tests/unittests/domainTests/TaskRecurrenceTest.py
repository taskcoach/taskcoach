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
from taskcoachlib.domain import task, date


class RecurringTaskTestCase(test.TestCase):
    def setUp(self):
        self.now = date.Now()
        self.yesterday = self.now - date.ONE_DAY
        self.tomorrow = self.now + date.ONE_DAY
        kwargs_list = self.taskCreationKeywordArguments()
        self.tasks = [
            task.Task(**kwargs) for kwargs in kwargs_list
        ]  # pylint: disable=W0142
        self.task = self.tasks[0]
        for index, each_task in enumerate(self.tasks):
            task_label = "task%d" % (index + 1)
            setattr(self, task_label, each_task)

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
    def test_set_recurrence_via_constructor(self):
        self.assertEqual(self.createRecurrence(), self.task.recurrence())

    def test_mark_completed_sets_new_planned_start_date_if_one_was_set(
        self,
    ):
        planned_start_date_time = self.task.plannedStartDateTime()
        self.task.set_completion_date_time()
        self.assertEqual(
            self.createRecurrence()(planned_start_date_time),
            self.task.plannedStartDateTime(),
        )

    def test_no_actual_start_date_after_recurrence(self):
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.actualStartDateTime())

    def test_mark_completed_resets_actual_start_date_if_it_was_set_previously(
        self,
    ):
        self.task.set_actual_start_date_time(date.Now())
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.actualStartDateTime())

    def test_mark_completed_sets_new_due_date_if_it_was_set_previously(self):
        self.task.set_due_date_time(self.tomorrow)
        self.task.set_completion_date_time(self.tomorrow)
        self.assertEqual(
            self.createRecurrence()(self.tomorrow), self.task.dueDateTime()
        )

    def test_mark_completed_sets_no_planned_start_date_if_none_was_set(
        self,
    ):
        self.task.set_planned_start_date_time(date.DateTime())
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.plannedStartDateTime())

    def test_mark_completed_does_not_set_due_date_if_it_was_not_set_previously(
        self,
    ):
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.dueDateTime())

    def test_recurring_task_is_not_completed_when_marked_completed(self):
        self.task.set_completion_date_time()
        self.assertFalse(self.task.completed())

    def test_mark_completed_does_not_set_reminder_if_it_was_not_set_previously(
        self,
    ):
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.reminder())

    def test_mark_completed_sets_new_reminder_if_it_was_set_previously(self):
        reminder = self.now + date.TimeDelta(seconds=10)
        self.task.set_reminder(reminder)
        self.task.set_completion_date_time()
        self.assertEqual(
            self.createRecurrence()(reminder), self.task.reminder()
        )

    def test_mark_completed_ignores_snooze_when_setting_new_reminder(self):
        reminder = self.now + date.TimeDelta(seconds=10)
        self.task.set_reminder(reminder)
        self.task.snooze_reminder(
            date.TimeDelta(seconds=30), now=lambda: self.now
        )
        self.task.set_completion_date_time()
        self.assertEqual(
            self.createRecurrence()(reminder), self.task.reminder()
        )

    def test_mark_completed_reset_percentage_complete(self):
        self.task.setPercentageComplete(50)
        self.task.set_completion_date_time()
        self.assertEqual(0, self.task.percentageComplete())

    def test_copy_recurrence(self):
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

    def test_recur_less_than_max_recurrence_count(self):
        for _ in range(self.maxRecurrenceCount):
            self.task.set_completion_date_time()
        self.assertFalse(self.task.completed())

    def test_recur_exactly_max_recurrence_count(self):
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

    def test_no_dates(self):
        self.task.set_completion_date_time()
        self.assertEqual(date.DateTime(), self.task.plannedStartDateTime())
        self.assertEqual(date.DateTime(), self.task.dueDateTime())
        self.assertEqual(date.DateTime(), self.task.completionDateTime())

    def test_planned_start_date_day_before_yesterday(self):
        self.task.set_planned_start_date_time(
            self.now - date.TimeDelta(hours=48)
        )
        self.task.set_completion_date_time(self.now)
        self.assertEqual(
            self.now + date.ONE_DAY, self.task.plannedStartDateTime()
        )

    def test_planned_start_date_today(self):
        self.task.set_planned_start_date_time(self.now.startOfDay())
        self.task.set_completion_date_time(self.now)
        self.assertEqual(
            self.tomorrow.startOfDay(), self.task.plannedStartDateTime()
        )

    def test_planned_start_date_tomorrow(self):
        self.task.set_planned_start_date_time(self.tomorrow.startOfDay())
        self.task.set_completion_date_time(self.now)
        self.assertEqual(
            self.tomorrow.startOfDay(), self.task.plannedStartDateTime()
        )

    def test_due_date_today(self):
        self.task.set_due_date_time(self.now.endOfDay())
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.tomorrow.endOfDay(), self.task.dueDateTime())

    def test_due_date_yesterday(self):
        self.task.set_due_date_time(self.yesterday)
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.tomorrow, self.task.dueDateTime())

    def test_due_date_tomorrow(self):
        self.task.set_due_date_time(self.tomorrow)
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.tomorrow, self.task.dueDateTime())

    def test_planned_start_and_due_today(self):
        self.task.set_planned_start_date_time(self.now.startOfDay())
        self.task.set_due_date_time(self.now.endOfDay())
        self.task.set_completion_date_time(self.now)
        self.assertEqual(
            self.tomorrow.startOfDay(), self.task.plannedStartDateTime()
        )
        self.assertEqual(self.tomorrow.endOfDay(), self.task.dueDateTime())

    def test_planned_start_and_due_date_in_the_past(self):
        self.task.set_planned_start_date_time(
            self.now - date.TimeDelta(hours=48)
        )
        self.task.set_due_date_time(self.yesterday)
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.now, self.task.plannedStartDateTime())
        self.assertEqual(self.tomorrow, self.task.dueDateTime())

    def test_planned_start_in_the_past_and_due_in_the_future(self):
        self.task.set_planned_start_date_time(self.yesterday)
        self.task.set_due_date_time(self.tomorrow)
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.yesterday, self.task.plannedStartDateTime())
        self.assertEqual(self.tomorrow, self.task.dueDateTime())

    def test_planned_start_and_due_in_the_future(self):
        self.task.set_planned_start_date_time(self.tomorrow)
        self.task.set_due_date_time(self.tomorrow + date.ONE_DAY)
        self.task.set_completion_date_time(self.now)
        self.assertEqual(self.now, self.task.plannedStartDateTime())
        self.assertEqual(self.tomorrow, self.task.dueDateTime())


class CommonRecurrenceTestsMixinWithChild(CommonRecurrenceTestsMixin):
    # pylint: disable=E1101

    def test_child_planned_start_date_recurs_too(self):
        self.task.set_completion_date_time()
        self.assertAlmostEqual(
            self.task.plannedStartDateTime().toordinal(),
            self.task.children()[0].plannedStartDateTime().toordinal(),
        )

    def test_child_due_date_recurs_too_parent_and_child_have_no_due_date(self):
        self.task.set_completion_date_time()
        self.assertAlmostEqual(
            self.task.dueDateTime().toordinal(),
            self.task.children()[0].dueDateTime().toordinal(),
        )

    def test_child_due_date_recurs_too_parent_and_child_have_same_due_date(
        self,
    ):
        child = self.task.children()[0]
        self.task.set_due_date_time(self.tomorrow)
        child.set_due_date_time(self.tomorrow)
        self.task.set_completion_date_time()
        self.assertAlmostEqual(
            self.task.dueDateTime().toordinal(),
            self.task.children()[0].dueDateTime().toordinal(),
        )

    def test_child_due_date_recurs_too_child_has_earlier_due_date(self):
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

    def test_child_does_not_recur_when_parent_does(self):
        orig_planned_start_date_time = self.task.children()[
            0
        ].plannedStartDateTime()
        self.task.set_completion_date_time()
        self.assertEqual(
            orig_planned_start_date_time,
            self.task.children()[0].plannedStartDateTime(),
        )

    def test_downwards_recursive_recurrence(self):
        expected_recurrence = min(
            [self.task.recurrence(), self.task.children()[0].recurrence()]
        )
        self.assertEqual(
            expected_recurrence,
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
