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

from taskcoachlib import patterns, config
from taskcoachlib.domain import task, effort, date
import test


class EffortAggregatorTestCase(test.TestCase):
    aggregation = "One of: day, week, or month (override in subclass)"

    def setUp(self):
        self.taskList = task.TaskList()
        self.effortAggregator = effort.EffortAggregator(
            self.taskList, aggregation=self.aggregation
        )
        patterns.Publisher().registerObserver(
            self.onEvent,
            eventType=self.effortAggregator.addItemEventType(),
            eventSource=self.effortAggregator,
        )
        patterns.Publisher().registerObserver(
            self.onEvent,
            eventType=self.effortAggregator.removeItemEventType(),
            eventSource=self.effortAggregator,
        )
        self.task1 = task.Task(subject="task 1")
        self.task2 = task.Task(subject="task 2")
        self.task3 = task.Task(subject="child")
        self.task1.addChild(self.task3)
        self.task3.set_parent(self.task1)
        self.effort1period1a = effort.Effort(
            self.task1,
            date.DateTime(2004, 1, 1, 11, 0, 0),
            date.DateTime(2004, 1, 1, 12, 0, 0),
        )
        self.effort2period1a = effort.Effort(
            self.task2,
            date.DateTime(2004, 1, 1, 11, 0, 0),
            date.DateTime(2004, 1, 1, 12, 0, 0),
        )
        self.effort1period1b = effort.Effort(
            self.task1,
            date.DateTime(2004, 1, 1, 13, 0, 0),
            date.DateTime(2004, 1, 1, 14, 0, 0),
        )
        self.effort2period1b = effort.Effort(
            self.task2,
            date.DateTime(2004, 1, 1, 13, 0, 0),
            date.DateTime(2004, 1, 1, 14, 0, 0),
        )
        self.effort1period2 = effort.Effort(
            self.task1,
            date.DateTime(2004, 2, 2, 13, 0, 0),
            date.DateTime(2004, 2, 2, 14, 0, 0),
        )
        self.effort1period3 = effort.Effort(
            self.task1,
            date.DateTime(2004, 1, 1, 10, 0, 0),
            date.DateTime(2005, 1, 1, 10, 0, 0),
        )
        self.effort3period1a = effort.Effort(
            self.task3,
            date.DateTime(2004, 1, 1, 14, 0, 0),
            date.DateTime(2004, 1, 1, 15, 0, 0),
        )
        self.events = []

    def onEvent(self, event):
        self.events.append(event)


class CommonTestsMixin(object):
    def test_empty_task_list(self):
        self.assertEqual(0, len(self.effortAggregator))

    def test_add_task_without_effort(self):
        self.taskList.append(self.task1)
        self.assertEqual(0, len(self.effortAggregator))

    def test_add_task_with_effort(self):
        self.task1.addEffort(self.effort1period1a)
        self.taskList.append(self.task1)
        self.assertEqual(2, len(self.effortAggregator))

    def test_add_effort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(effort.Effort(self.task1))
        self.assertEqual(2, len(self.effortAggregator))

    def test_add_two_efforts_on_same_day(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.assertEqual(2, len(self.effortAggregator))

    def test_add_task_with_two_efforts_on_same_day(self):
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.taskList.append(self.task1)
        self.assertEqual(2, len(self.effortAggregator))

    def test_add_task_with_two_efforts_on_same_day_and_check_total_effort(
        self,
    ):
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.taskList.append(self.task1)
        expected_duration = (
            self.effort1period1a.timeSpent() + self.effort1period1b.timeSpent()
        )
        self.assertEqual(
            expected_duration, list(self.effortAggregator)[0].totalTimeSpent()
        )

    def test_add_two_efforts_in_different_periods(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period2)
        self.assertEqual(4, len(self.effortAggregator))

    def test_add_two_efforts_on_the_same_day_to_two_different_tasks(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addEffort(self.effort1period1a)
        self.task2.addEffort(self.effort2period1a)
        self.assertEqual(3, len(self.effortAggregator))

    def test_add_effort_to_child(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addChild(self.task2)
        self.task2.addEffort(self.effort2period1a)
        self.assertEqual(3, len(self.effortAggregator))

    def test_add_child_with_effort(self):
        self.taskList.extend([self.task1, self.task2])
        self.task2.addEffort(self.effort2period1a)
        self.task1.addChild(self.task2)
        self.assertEqual(3, len(self.effortAggregator))

    def test_add_parent_and_child_with_effort_to_task_list(self):
        self.task3.addEffort(self.effort3period1a)
        self.taskList.append(self.task1)
        self.assertEqual(3, len(self.effortAggregator))

    def test_add_effort_to_grand_child(self):
        self.taskList.extend([self.task1, self.task2])
        self.task3.addChild(self.task2)
        self.task2.addEffort(self.effort2period1a)
        self.assertEqual(4, len(self.effortAggregator))

    def test_add_grand_child_with_effort(self):
        self.taskList.extend([self.task1, self.task2])
        self.task2.addEffort(self.effort2period1a)
        self.task3.addChild(self.task2)
        self.assertEqual(4, len(self.effortAggregator))

    def test_remove_child_with_effort_from_parent(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addChild(self.task2)
        self.task2.addEffort(self.effort2period1a)
        self.task2.set_parent(None)
        self.task1.removeChild(self.task2)
        self.assertEqual(2, len(self.effortAggregator))

    def test_remove_effort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.removeEffort(self.effort1period1a)
        self.assertEqual(0, len(self.effortAggregator))

    def test_remove_one_of_two_efforts(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.task1.removeEffort(self.effort1period1a)
        self.assertEqual(2, len(self.effortAggregator))

    def test_remove_one_of_two_efforts_of_different_tasks(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addEffort(self.effort1period1a)
        self.task2.addEffort(self.effort2period1a)
        self.task1.removeEffort(self.effort1period1a)
        self.assertEqual(2, len(self.effortAggregator))

    def test_remove_two_of_two_efforts(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.task1.removeEffort(self.effort1period1a)
        self.task1.removeEffort(self.effort1period1b)
        self.assertEqual(0, len(self.effortAggregator))

    def test_remove_effort_from_child(self):
        self.taskList.extend([self.task1, self.task2])
        self.task2.addEffort(self.effort2period1a)
        self.task1.addChild(self.task2)
        self.task2.removeEffort(self.effort2period1a)
        self.assertEqual(0, len(self.effortAggregator))

    def test_remove_tasks(self):
        self.taskList.extend([self.task1, self.task3])
        self.task3.addEffort(self.effort3period1a)
        self.taskList.removeItems([self.task1, self.task3])
        self.assertEqual(0, len(self.effortAggregator))

    def test_remove_tasks_with_overlapping_effort(self):
        self.taskList.extend([self.task1, self.task3])
        self.task3.addEffort(self.effort3period1a)
        self.task1.addEffort(self.effort1period1a)
        self.taskList.removeItems([self.task1, self.task3])
        self.assertEqual(0, len(self.effortAggregator))

    def test_remove_all_tasks(self):
        self.taskList.extend([self.task1, self.task2, self.task3])
        self.task3.addEffort(self.effort3period1a)
        self.taskList.removeItems([self.task1, self.task2, self.task3])
        self.assertEqual(0, len(self.effortAggregator))

    def test_remove_child_task(self):
        self.taskList.extend([self.task1])
        self.task3.addEffort(self.effort3period1a)
        self.taskList.removeItems([self.task3])
        self.assertEqual(0, len(self.effortAggregator))

    def test_change_start(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.effort1period1a.setStart(date.DateTime.now())
        self.assertEqual(2, len(self.effortAggregator))

    def test_change_start_of_one_of_two_efforts(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.effort1period1a.setStart(date.DateTime.now())
        self.assertEqual(4, len(self.effortAggregator))

    def test_change_start_within_period(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.effort1period1a.setStart(
            self.effort1period1a.getStart() + date.ONE_SECOND
        )
        self.assertEqual(2, len(self.effortAggregator))

    def test_change_stop_does_not_affect_period(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        composite = list(self.effortAggregator)[0]
        start = composite.getStart()
        self.effort1period1a.setStop(date.DateTime.now())
        self.assertEqual(start, composite.getStart())

    def test_change_start_of_one_of_two_efforts_to_one_year_later(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.effort1period1a.setStart(date.DateTime(2005, 1, 1, 11, 0, 0))
        self.assertEqual(4, len(self.effortAggregator))

    def test_notification_add(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.assertEqual(1, len(self.events))
        self.assertTrue(self.events[0].value() in self.effortAggregator)

    def test_notification_remove(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.removeEffort(self.effort1period1a)
        self.assertEqual(3, len(self.events))

    def test_create_with_initial_effort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        aggregator = effort.EffortAggregator(
            self.taskList, aggregation=self.aggregation
        )
        self.assertEqual(2, len(aggregator))

    def test_long_effort_is_still_one_composite_effort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period3)
        self.assertEqual(2, len(self.effortAggregator))

    def test_change_task(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addEffort(self.effort1period1a)
        self.effort1period1a.set_task(self.task2)
        self.assertEqual(2, len(self.effortAggregator))
        self.assertTrue(
            self.task2 in [item.task() for item in self.effortAggregator]
        )

    def test_change_task_of_child_effort(self):
        self.taskList.extend([self.task1, self.task2])
        self.task3.addEffort(self.effort3period1a)
        self.effort3period1a.set_task(self.task2)
        self.assertEqual(2, len(self.effortAggregator))
        self.assertTrue(
            self.task2 in [item.task() for item in self.effortAggregator]
        )

    def test_remove_task_after_change_task_of_effort(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addEffort(self.effort1period1a)
        self.effort1period1a.set_task(self.task2)
        self.taskList.remove(self.task1)
        self.assertEqual(2, len(self.effortAggregator))
        self.assertTrue(
            self.task2 in [item.task() for item in self.effortAggregator]
        )

    def test_remove_and_add_effort_to_same_period(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.removeEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1a)
        self.assertEqual(2, len(self.effortAggregator))
        self.assertEqual(
            self.effort1period1a, list(self.effortAggregator)[0][0]
        )

    def test_max_date_time(self):
        self.assertEqual(None, self.effortAggregator.maxDateTime())

    def test_max_date_time_one_effort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.assertEqual(
            self.effort1period1a.getStop(), self.effortAggregator.maxDateTime()
        )

    def test_max_date_time_one_tracking_effort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(effort.Effort(self.task1))
        self.assertEqual(None, self.effortAggregator.maxDateTime())

    def test_max_date_time_two_efforts(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        now = date.DateTime.now()
        self.task1.addEffort(
            effort.Effort(self.task1, self.effort1period1a.getStart(), now)
        )
        self.assertEqual(now, self.effortAggregator.maxDateTime())

    def test_nr_tracking(self):
        self.assertEqual(0, self.effortAggregator.nr_being_tracked())

    def test_original_length(self):
        self.assertEqual(0, self.effortAggregator.original_length())


class EffortPerDayTest(EffortAggregatorTestCase, CommonTestsMixin):
    aggregation = "day"


class EffortPerWeekTest(EffortAggregatorTestCase, CommonTestsMixin):
    aggregation = "week"


class EffortPerMonthTest(EffortAggregatorTestCase, CommonTestsMixin):
    aggregation = "month"


class MultipleAggregatorsTest(test.TestCase):
    def setUp(self):
        self.taskList = task.TaskList()
        self.effortPerDay = effort.EffortSorter(
            effort.EffortAggregator(self.taskList, aggregation="day")
        )
        self.effortPerWeek = effort.EffortSorter(
            effort.EffortAggregator(self.taskList, aggregation="week")
        )

    def test_delete_effort_start_of_both_periods(self):
        a_task = task.Task()
        self.taskList.append(a_task)
        # Make sure the start of the day and week are the same,
        # in other words, use a Monday
        an_effort = effort.Effort(
            a_task, date.DateTime(2006, 8, 28), date.DateTime(2006, 8, 29)
        )
        a_task.addEffort(an_effort)
        a_task.removeEffort(an_effort)
        self.assertFalse(self.effortPerDay)
