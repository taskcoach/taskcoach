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
from taskcoachlib.domain import task, effort, date
import test


class FakeEffortAggregator(object):
    def __init__(self, composite):
        self.composite = composite
        patterns.Publisher().registerObserver(
            self.on_time_spent_changed, task.Task.timeSpentChangedEventType()
        )
        patterns.Publisher().registerObserver(
            self.on_hourly_fee_changed, task.Task.hourlyFeeChangedEventType()
        )

    def on_hourly_fee_changed(self, event):  # pylint: disable=W0613
        self.composite.revenue_changed()

    def on_time_spent_changed(self, event):  # pylint: disable=W0613
        self.composite.time_spent_changed()


class CompositeEffortWithRoundingTest(test.TestCase):
    def setUp(self):
        self.task = task.Task(subject="task")
        self.effort1 = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 11, 0, 0),
            date.DateTime(2004, 1, 1, 11, 0, 45),
        )
        self.effort2 = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 12, 0, 0),
            date.DateTime(2004, 1, 1, 12, 0, 45),
        )
        self.effort3 = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 13, 0, 0),
            date.DateTime(2004, 1, 1, 13, 0, 45),
        )
        self.effort4 = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 13, 0, 0),
            date.DateTime(2004, 1, 1, 13, 0, 10),
        )
        self.composite = effort.CompositeEffort(
            self.task,
            date.DateTime(2004, 1, 1, 0, 0, 0),
            date.DateTime(2004, 1, 1, 23, 59, 59),
        )
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.task.addEffort(self.effort3)
        self.task.addEffort(self.effort4)

    def test_round_total(self):
        self.assertEqual(
            self.composite.totalTimeSpent(recursive=True, rounding=60),
            date.TimeDelta(seconds=3 * 60),
        )

    def test_round_total_up(self):
        self.assertEqual(
            self.composite.totalTimeSpent(
                recursive=True, rounding=60, round_up=True
            ),
            date.TimeDelta(seconds=4 * 60),
        )


class CompositeEffortTest(test.TestCase):
    def setUp(self):
        self.task = task.Task(subject="task")
        self.effort1 = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 11, 0, 0),
            date.DateTime(2004, 1, 1, 12, 0, 0),
        )
        self.effort2 = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 13, 0, 0),
            date.DateTime(2004, 1, 1, 14, 0, 0),
        )
        self.effort3 = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 11, 13, 0, 0),
            date.DateTime(2004, 1, 11, 14, 0, 0),
        )
        self.trackedEffort = effort.Effort(
            self.task, date.DateTime(2004, 1, 1, 9, 0, 0)
        )
        self.composite = effort.CompositeEffort(
            self.task,
            date.DateTime(2004, 1, 1, 0, 0, 0),
            date.DateTime(2004, 1, 1, 23, 59, 59),
        )
        self.fakeAggregator = FakeEffortAggregator(self.composite)

    def test_initial_length(self):
        self.assertEqual(0, len(self.composite))

    def test_initial_duration(self):
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def test_initial_tracking_state(self):
        self.assertFalse(self.composite.isBeingTracked())

    def test_initial_tracking_state_when_task_is_tracked(self):
        self.task.addEffort(self.trackedEffort)
        composite = effort.CompositeEffort(
            self.task, self.composite.getStart(), self.composite.getStop()
        )
        self.assertTrue(composite.isBeingTracked())

    def test_duration_for_single_effort(self):
        self.task.addEffort(self.effort1)
        self.assertEqual(
            self.effort1.timeSpent(), self.composite.totalTimeSpent()
        )

    def test_add_effort_outside_period_to_task(self):
        effort_outside_period = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 11, 13, 0, 0),
            date.DateTime(2004, 1, 11, 14, 0, 0),
        )
        self.task.addEffort(effort_outside_period)
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def test_add_effort_with_start_time_equal_to_start_of_period_to_task(self):
        effort_same_start_time = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 0, 0, 0),
            date.DateTime(2004, 1, 1, 14, 0, 0),
        )
        self.task.addEffort(effort_same_start_time)
        self.assertEqual(
            effort_same_start_time.timeSpent(), self.composite.totalTimeSpent()
        )

    def test_add_effort_with_start_time_equal_to_end_of_period_to_task(self):
        effort_same_stop_time = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 23, 59, 59),
            date.DateTime(2004, 1, 2, 1, 0, 0),
        )
        self.task.addEffort(effort_same_stop_time)
        self.assertEqual(
            effort_same_stop_time.timeSpent(), self.composite.totalTimeSpent()
        )

    def test_add_tracked_effort_to_task_does_not_cause_list_empty_notification(
        self,
    ):
        events = test.ChangeRecorder(
            effort.CompositeEffort.compositeEmptyEventType()
        )
        self.task.addEffort(
            effort.Effort(self.task, self.composite.getStart())
        )
        self.assertFalse(events)

    def test_add_effort_notification(self):
        events = test.ChangeRecorder(effort.Effort.durationChangedEventType())
        self.task.addEffort(self.effort1)
        self.assertEqual(
            [(self.composite.totalTimeSpent(), self.composite)], events
        )

    def test_remove_effort_from_task(self):
        self.task.addEffort(self.effort1)
        self.task.removeEffort(self.effort1)
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def test_remove_effort_notification(self):
        self.task.addEffort(self.effort1)
        events = test.ChangeRecorder(
            effort.CompositeEffort.compositeEmptyEventType()
        )
        self.task.removeEffort(self.effort1)
        self.assertEqual([self.composite], events)

    def test_duration(self):
        self.task.addEffort(self.effort1)
        self.assertEqual(
            self.effort1.timeSpent(), self.composite.totalTimeSpent()
        )

    def test_duration_two_efforts(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.assertEqual(
            self.effort1.timeSpent() + self.effort2.timeSpent(),
            self.composite.totalTimeSpent(),
        )

    def test_revenue(self):
        self.task.set_hourly_fee(100)
        self.task.addEffort(self.effort1)
        self.assertEqual(100, self.composite.revenue())

    def test_revenue_two_efforts(self):
        self.task.set_hourly_fee(100)
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.assertEqual(200, self.composite.revenue())

    def test_that_an_hourly_fee_change_causes_a_revenue_notification(self):
        self.task.addEffort(self.effort1)
        events = test.ChangeRecorder(effort.Effort.revenueChangedEventType())
        self.task.set_hourly_fee(100)
        self.assertTrue((100.0, self.composite) in events)

    def test_is_being_tracked(self):
        self.task.addEffort(self.effort1)
        self.effort1.setStop(date.DateTime())
        self.assertTrue(self.composite.isBeingTracked())

    def test_change_start_time_of_effort_keep_within_period(self):
        self.task.addEffort(self.effort1)
        self.effort1.setStart(self.effort1.getStart() + date.ONE_HOUR)
        self.assertEqual(
            self.effort1.timeSpent(), self.composite.totalTimeSpent()
        )

    def test_change_start_time_of_effort_keep_within_period_no_notification(
        self,
    ):
        self.task.addEffort(self.effort1)
        events = test.ChangeRecorder(effort.Effort.durationChangedEventType())
        self.effort1.setStart(self.effort1.getStart() + date.ONE_HOUR)
        self.assertFalse(
            (self.composite.totalTimeSpent(), self.composite) in events
        )

    def test_change_start_time_of_effort_move_outside_periode(self):
        self.task.addEffort(self.effort1)
        self.effort1.setStart(self.effort1.getStart() + date.TimeDelta(days=2))
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def test_change_stop_time_of_effort_keep_within_period(self):
        self.task.addEffort(self.effort1)
        self.effort1.setStop(self.effort1.getStop() + date.ONE_HOUR)
        self.assertEqual(
            self.effort1.timeSpent(), self.composite.totalTimeSpent()
        )

    def test_change_stop_time_of_effort_move_outside_period(self):
        self.task.addEffort(self.effort1)
        self.effort1.setStop(self.effort1.getStop() + date.TimeDelta(days=2))
        self.assertEqual(
            self.effort1.timeSpent(), self.composite.totalTimeSpent()
        )

    def test_change_stop_time_of_effort_move_outside_period_notification(self):
        self.task.addEffort(self.effort1)
        events = test.ChangeRecorder(effort.Effort.durationChangedEventType())
        self.effort1.setStop(self.effort1.getStop() + date.TimeDelta(days=2))
        self.assertFalse(
            (self.composite.totalTimeSpent(), self.composite) in events
        )

    def test_change_stop_time_of_effort_no_notification(self):
        self.task.addEffort(self.effort1)
        events = test.ChangeRecorder(effort.Effort.durationChangedEventType())
        self.effort1.setStop(self.effort1.getStop() + date.ONE_HOUR)
        self.assertFalse(
            (self.composite.totalTimeSpent(), self.composite) in events
        )

    def test_change_start_time_of_effort_move_inside_period(self):
        self.task.addEffort(self.effort3)
        self.effort3.setStart(self.composite.getStart())
        self.assertEqual(
            self.effort3.timeSpent(), self.composite.totalTimeSpent()
        )

    def test_empty_notification(self):
        events = test.ChangeRecorder(
            effort.CompositeEffort.compositeEmptyEventType()
        )
        self.task.addEffort(self.effort1)
        self.task.removeEffort(self.effort1)
        self.assertEqual([self.composite], events)

    def test_change_task(self):
        self.task.addEffort(self.effort1)
        self.effort1.set_task(task.Task())
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def test_change_task_empty_notification(self):
        events = test.ChangeRecorder(
            effort.CompositeEffort.compositeEmptyEventType()
        )
        self.task.addEffort(self.effort1)
        self.effort1.set_task(task.Task())
        self.assertEqual([self.composite], events)

    def test_get_description_zero_efforts(self):
        self.assertEqual("", self.composite.description())

    def test_get_description_one_effort(self):
        self.task.addEffort(self.effort1)
        for description in ("", "Description"):
            self.effort1.setDescription(description)
            self.assertEqual(description, self.composite.description())

    def test_get_description_two_efforts(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        for description1, description2 in (
            ("", ""),
            ("descripion1", ""),
            ("", "description2"),
            ("description1", "description2"),
        ):
            self.effort1.setDescription(description1)
            self.effort2.setDescription(description2)
            if description1 and description2:
                seperator = "\n"
            else:
                seperator = ""
            expected_description = description1 + seperator + description2
            self.assertEqual(
                expected_description, self.composite.description()
            )


class CompositeEffortWithSubTasksTest(test.TestCase):
    def setUp(self):
        self.task = task.Task(subject="task")
        self.child = task.Task(subject="child")
        self.child2 = task.Task(subject="child2")
        self.task.addChild(self.child)
        self.taskEffort = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 11, 0, 0),
            date.DateTime(2004, 1, 1, 12, 0, 0),
        )
        self.childEffort = effort.Effort(
            self.child,
            date.DateTime(2004, 1, 1, 11, 0, 0),
            date.DateTime(2004, 1, 1, 12, 0, 0),
        )
        self.child2Effort = effort.Effort(
            self.child2,
            date.DateTime(2004, 1, 1, 11, 0, 0),
            date.DateTime(2004, 1, 1, 12, 0, 0),
        )
        self.trackedEffort = effort.Effort(
            self.child, date.DateTime(2004, 1, 1, 9, 0, 0)
        )
        self.composite = effort.CompositeEffort(
            self.task,
            date.DateTime(2004, 1, 1, 0, 0, 0),
            date.DateTime(2004, 1, 1, 23, 59, 59),
        )
        self.fakeAggregator = FakeEffortAggregator(self.composite)

    def test_add_effort_to_child_task_notification(self):
        events = test.ChangeRecorder(effort.Effort.durationChangedEventType())
        self.child.addEffort(self.childEffort)
        self.assertTrue(
            (self.composite.totalTimeSpent(), self.composite) in events
        )

    def test_remove_effort_from_child_task(self):
        self.child.addEffort(self.childEffort)
        self.child.removeEffort(self.childEffort)
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def test_remove_effort_from_child_notification(self):
        self.child.addEffort(self.childEffort)
        events = test.ChangeRecorder(
            effort.CompositeEffort.compositeEmptyEventType()
        )
        self.child.removeEffort(self.childEffort)
        self.assertEqual([self.composite], events)

    def test_duration(self):
        self.child.addEffort(self.childEffort)
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def test_recursive_duration(self):
        self.child.addEffort(self.childEffort)
        self.assertEqual(
            self.childEffort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def test_duration_with_task_and_child_effort(self):
        self.task.addEffort(self.taskEffort)
        self.child.addEffort(self.childEffort)
        self.assertEqual(
            self.taskEffort.timeSpent() + self.childEffort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def test_add_effort_to_new_child(self):
        self.task.addChild(self.child2)
        self.child2.addEffort(self.child2Effort)
        self.assertEqual(
            self.child2Effort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def test_add_child_with_effort(self):
        self.child2.addEffort(self.child2Effort)
        self.task.addChild(self.child2)
        self.assertEqual(
            self.child2Effort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def test_add_effort_to_grand_child(self):
        self.task.addChild(self.child2)
        grand_child = task.Task(subject="grandchild")
        self.child2.addChild(grand_child)
        grand_child_effort = effort.Effort(
            grand_child,
            self.composite.getStart(),
            self.composite.getStart() + date.ONE_HOUR,
        )
        grand_child.addEffort(grand_child_effort)
        self.assertEqual(
            grand_child_effort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def test_add_grand_child_with_effort(self):
        self.task.addChild(self.child2)
        grand_child = task.Task(subject="grandchild")
        grand_child_effort = effort.Effort(
            grand_child,
            self.composite.getStart(),
            self.composite.getStart() + date.ONE_HOUR,
        )
        grand_child.addEffort(grand_child_effort)
        self.child2.addChild(grand_child)
        self.assertEqual(
            grand_child_effort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def test_remove_effort_from_added_child(self):
        self.task.addChild(self.child2)
        self.child2.addEffort(self.child2Effort)
        self.child2.removeEffort(self.child2Effort)
        self.assertEqual(
            date.TimeDelta(), self.composite.totalTimeSpent(recursive=True)
        )

    def test_remove_child_with_effort(self):
        self.child.addEffort(self.childEffort)
        self.task.removeChild(self.child)
        self.assertEqual(
            date.TimeDelta(), self.composite.totalTimeSpent(recursive=True)
        )

    def test_remove_child_with_effort_causes_empty_notification(self):
        events = test.ChangeRecorder(
            effort.CompositeEffort.compositeEmptyEventType()
        )
        self.child.addEffort(self.childEffort)
        self.task.removeChild(self.child)
        self.assertEqual([self.composite], events)

    def test_change_start_time_of_child_effort_move_inside_period(self):
        child_effort = effort.Effort(self.child)
        self.child.addEffort(child_effort)
        child_effort.setStart(self.composite.getStart())
        # Make sure the next assertEqual cannot fail due to duration() being
        # called twice:
        child_effort.setStop()
        self.assertEqual(
            child_effort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def test_change_task(self):
        self.child.addEffort(self.childEffort)
        self.childEffort.set_task(task.Task())
        self.assertEqual(
            date.TimeDelta(), self.composite.totalTimeSpent(recursive=True)
        )


class CompositeEffortWithSubTasksRevenueTest(test.TestCase):
    def setUp(self):
        self.task = task.Task(subject="task")
        self.child = task.Task(subject="child")
        self.task.addChild(self.child)
        self.taskEffort = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 11, 0, 0),
            date.DateTime(2004, 1, 1, 12, 0, 0),
        )
        self.childEffort = effort.Effort(
            self.child,
            date.DateTime(2004, 1, 1, 11, 0, 0),
            date.DateTime(2004, 1, 1, 12, 0, 0),
        )
        self.composite = effort.CompositeEffort(
            self.task,
            date.DateTime(2004, 1, 1, 0, 0, 0),
            date.DateTime(2004, 1, 1, 23, 59, 59),
        )
        self.fakeAggregator = FakeEffortAggregator(self.composite)
        self.task.addEffort(self.taskEffort)
        self.child.addEffort(self.childEffort)

    def test_revenue_when_parent_has_hourly_fee(self):
        self.task.set_hourly_fee(100)
        self.assertEqual(
            self.taskEffort.timeSpent().hours() * 100, self.composite.revenue()
        )

    def test_recursive_revenue_when_parent_has_hourly_fee(self):
        self.task.set_hourly_fee(100)
        self.assertEqual(
            self.taskEffort.timeSpent().hours() * 100,
            self.composite.revenue(recursive=True),
        )

    def test_revenue_when_child_has_hourly_fee(self):
        self.child.set_hourly_fee(100)
        self.assertEqual(0, self.composite.revenue())

    def test_recursive_revenue_when_child_has_hourly_fee(self):
        self.child.set_hourly_fee(100)
        self.assertEqual(
            self.childEffort.timeSpent().hours() * 100,
            self.composite.revenue(recursive=True),
        )

    def test_revenue_when_child_and_parent_have_hourly_fees(self):
        self.child.set_hourly_fee(100)
        self.task.set_hourly_fee(200)
        self.assertEqual(
            self.taskEffort.timeSpent().hours() * 200, self.composite.revenue()
        )

    def test_recursive_revenue_when_child_and_parent_have_hourly_fees(self):
        self.child.set_hourly_fee(100)
        self.task.set_hourly_fee(200)
        self.assertEqual(
            self.taskEffort.timeSpent().hours() * 200
            + self.childEffort.timeSpent().hours() * 100,
            self.composite.revenue(recursive=True),
        )

    def test_revenue_when_parent_has_fixed_fee(self):
        self.task.set_fixed_fee(1000)
        self.assertEqual(0, self.composite.revenue())

    def test_recursive_revenue_when_parent_has_fixed_fee(self):
        self.task.set_fixed_fee(1000)
        self.assertEqual(0, self.composite.revenue(recursive=True))

    def test_revenue_when_child_has_fixed_fee(self):
        self.child.set_fixed_fee(1000)
        self.assertEqual(0, self.composite.revenue())

    def test_recursive_revenue_when_child_has_fixed_fee(self):
        self.child.set_fixed_fee(1000)
        self.assertEqual(0, self.composite.revenue(recursive=True))

    def test_revenue_when_parent_has_fixed_fee_and_multiple_efforts(self):
        self.task.set_fixed_fee(1000)
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2005, 12, 12, 10, 0, 0),
                date.DateTime(2005, 12, 12, 12, 0, 0),
            )
        )
        self.assertEqual(0, self.composite.revenue())

    def test_revenue_when_child_has_fixed_fee_and_multiple_efforts(self):
        self.child.set_fixed_fee(1000)
        self.child.addEffort(
            effort.Effort(
                self.child,
                date.DateTime(2005, 12, 12, 10, 0, 0),
                date.DateTime(2005, 12, 12, 12, 0, 0),
            )
        )
        self.assertEqual(0, self.composite.revenue())

    def test_recursive_revenue_when_child_has_fixed_fee_and_multiple_efforts(
        self,
    ):
        self.child.set_fixed_fee(1000)
        self.child.addEffort(
            effort.Effort(
                self.child,
                date.DateTime(2005, 12, 12, 10, 0, 0),
                date.DateTime(2005, 12, 12, 12, 0, 0),
            )
        )
        self.assertEqual(0, self.composite.revenue(recursive=True))

    def test_revenue_with_mixture(self):
        self.child.set_fixed_fee(100)
        self.task.set_hourly_fee(1000)
        self.assertEqual(1000, self.composite.revenue(recursive=True))

    def test_that_an_hourly_fee_change_causes_a_revenue_notification(self):
        events = test.ChangeRecorder(effort.Effort.revenueChangedEventType())
        self.child.set_hourly_fee(100)
        self.assertTrue((0.0, self.composite) in events)
