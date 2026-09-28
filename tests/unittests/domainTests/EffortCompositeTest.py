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

from taskcoachlib import config, patterns
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

    def on_hourly_fee_changed(self, event):
        for sender in event.sources():
            self.onRevenueChanged(event.value(sender), sender)

    def on_time_spent_changed(self, event):
        for sender in event.sources():
            self.composite.onTimeSpentChanged(event.value(sender), sender)

    def onRevenueChanged(self, newValue, sender):
        self.composite.onRevenueChanged(newValue, sender)


class CompositeEffortWithRoundingTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
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
                recursive=True, rounding=60, roundUp=True
            ),
            date.TimeDelta(seconds=4 * 60),
        )


class CompositeEffortTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
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

    def testInitialLength(self):
        self.assertEqual(0, len(self.composite))

    def testInitialDuration(self):
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def testInitialTrackingState(self):
        self.assertFalse(self.composite.isBeingTracked())

    def testInitialTrackingStateWhenTaskIsTracked(self):
        self.task.addEffort(self.trackedEffort)
        composite = effort.CompositeEffort(
            self.task, self.composite.getStart(), self.composite.getStop()
        )
        self.assertTrue(composite.isBeingTracked())

    def testDurationForSingleEffort(self):
        self.task.addEffort(self.effort1)
        self.assertEqual(
            self.effort1.timeSpent(), self.composite.totalTimeSpent()
        )

    def testAddEffortOutsidePeriodToTask(self):
        effortOutsidePeriod = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 11, 13, 0, 0),
            date.DateTime(2004, 1, 11, 14, 0, 0),
        )
        self.task.addEffort(effortOutsidePeriod)
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def testAddEffortWithStartTimeEqualToStartOfPeriodToTask(self):
        effortSameStartTime = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 0, 0, 0),
            date.DateTime(2004, 1, 1, 14, 0, 0),
        )
        self.task.addEffort(effortSameStartTime)
        self.assertEqual(
            effortSameStartTime.timeSpent(), self.composite.totalTimeSpent()
        )

    def testAddEffortWithStartTimeEqualToEndOfPeriodToTask(self):
        effortSameStopTime = effort.Effort(
            self.task,
            date.DateTime(2004, 1, 1, 23, 59, 59),
            date.DateTime(2004, 1, 2, 1, 0, 0),
        )
        self.task.addEffort(effortSameStopTime)
        self.assertEqual(
            effortSameStopTime.timeSpent(), self.composite.totalTimeSpent()
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

    def testRemoveEffortFromTask(self):
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

    def testDuration(self):
        self.task.addEffort(self.effort1)
        self.assertEqual(
            self.effort1.timeSpent(), self.composite.totalTimeSpent()
        )

    def testDurationTwoEfforts(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.assertEqual(
            self.effort1.timeSpent() + self.effort2.timeSpent(),
            self.composite.totalTimeSpent(),
        )

    def testRevenue(self):
        self.task.set_hourly_fee(100)
        self.task.addEffort(self.effort1)
        self.assertEqual(100, self.composite.revenue())

    def testRevenueTwoEfforts(self):
        self.task.set_hourly_fee(100)
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.assertEqual(200, self.composite.revenue())

    def test_that_an_hourly_fee_change_causes_a_revenue_notification(self):
        self.task.addEffort(self.effort1)
        events = test.ChangeRecorder(effort.Effort.revenueChangedEventType())
        self.task.set_hourly_fee(100)
        self.assertTrue((100.0, self.composite) in events)

    def testIsBeingTracked(self):
        self.task.addEffort(self.effort1)
        self.effort1.setStop(date.DateTime())
        self.assertTrue(self.composite.isBeingTracked())

    def testChangeStartTimeOfEffort_KeepWithinPeriod(self):
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

    def testChangeStartTimeOfEffort_MoveOutsidePeriode(self):
        self.task.addEffort(self.effort1)
        self.effort1.setStart(self.effort1.getStart() + date.TimeDelta(days=2))
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def testChangeStopTimeOfEffort_KeepWithinPeriod(self):
        self.task.addEffort(self.effort1)
        self.effort1.setStop(self.effort1.getStop() + date.ONE_HOUR)
        self.assertEqual(
            self.effort1.timeSpent(), self.composite.totalTimeSpent()
        )

    def testChangeStopTimeOfEffort_MoveOutsidePeriod(self):
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

    def testChangeStartTimeOfEffort_MoveInsidePeriod(self):
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

    def testChangeTask(self):
        self.task.addEffort(self.effort1)
        self.effort1.setTask(task.Task())
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def test_change_task_empty_notification(self):
        events = test.ChangeRecorder(
            effort.CompositeEffort.compositeEmptyEventType()
        )
        self.task.addEffort(self.effort1)
        self.effort1.setTask(task.Task())
        self.assertEqual([self.composite], events)

    def testGetDescription_ZeroEfforts(self):
        self.assertEqual("", self.composite.description())

    def testGetDescription_OneEffort(self):
        self.task.addEffort(self.effort1)
        for description in ("", "Description"):
            self.effort1.setDescription(description)
            self.assertEqual(description, self.composite.description())

    def testGetDescription_TwoEfforts(self):
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
            expectedDescription = description1 + seperator + description2
            self.assertEqual(expectedDescription, self.composite.description())


class CompositeEffortWithSubTasksTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
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

    def testRemoveEffortFromChildTask(self):
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

    def testDuration(self):
        self.child.addEffort(self.childEffort)
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def testRecursiveDuration(self):
        self.child.addEffort(self.childEffort)
        self.assertEqual(
            self.childEffort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def testDurationWithTaskAndChildEffort(self):
        self.task.addEffort(self.taskEffort)
        self.child.addEffort(self.childEffort)
        self.assertEqual(
            self.taskEffort.timeSpent() + self.childEffort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def testAddEffortToNewChild(self):
        self.task.addChild(self.child2)
        self.child2.addEffort(self.child2Effort)
        self.assertEqual(
            self.child2Effort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def testAddChildWithEffort(self):
        self.child2.addEffort(self.child2Effort)
        self.task.addChild(self.child2)
        self.assertEqual(
            self.child2Effort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def testAddEffortToGrandChild(self):
        self.task.addChild(self.child2)
        grandChild = task.Task(subject="grandchild")
        self.child2.addChild(grandChild)
        grandChildEffort = effort.Effort(
            grandChild,
            self.composite.getStart(),
            self.composite.getStart() + date.ONE_HOUR,
        )
        grandChild.addEffort(grandChildEffort)
        self.assertEqual(
            grandChildEffort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def testAddGrandChildWithEffort(self):
        self.task.addChild(self.child2)
        grandChild = task.Task(subject="grandchild")
        grandChildEffort = effort.Effort(
            grandChild,
            self.composite.getStart(),
            self.composite.getStart() + date.ONE_HOUR,
        )
        grandChild.addEffort(grandChildEffort)
        self.child2.addChild(grandChild)
        self.assertEqual(
            grandChildEffort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def testRemoveEffortFromAddedChild(self):
        self.task.addChild(self.child2)
        self.child2.addEffort(self.child2Effort)
        self.child2.removeEffort(self.child2Effort)
        self.assertEqual(
            date.TimeDelta(), self.composite.totalTimeSpent(recursive=True)
        )

    def testRemoveChildWithEffort(self):
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

    def testChangeStartTimeOfChildEffort_MoveInsidePeriod(self):
        childEffort = effort.Effort(self.child)
        self.child.addEffort(childEffort)
        childEffort.setStart(self.composite.getStart())
        # Make sure the next assertEqual cannot fail due to duration() being
        # called twice:
        childEffort.setStop()
        self.assertEqual(
            childEffort.timeSpent(),
            self.composite.totalTimeSpent(recursive=True),
        )

    def testChangeTask(self):
        self.child.addEffort(self.childEffort)
        self.childEffort.setTask(task.Task())
        self.assertEqual(
            date.TimeDelta(), self.composite.totalTimeSpent(recursive=True)
        )


class CompositeEffortWithSubTasksRevenueTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
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

    def testRevenueWhenParentHasHourlyFee(self):
        self.task.set_hourly_fee(100)
        self.assertEqual(
            self.taskEffort.timeSpent().hours() * 100, self.composite.revenue()
        )

    def testRecursiveRevenueWhenParentHasHourlyFee(self):
        self.task.set_hourly_fee(100)
        self.assertEqual(
            self.taskEffort.timeSpent().hours() * 100,
            self.composite.revenue(recursive=True),
        )

    def testRevenueWhenChildHasHourlyFee(self):
        self.child.set_hourly_fee(100)
        self.assertEqual(0, self.composite.revenue())

    def testRecursiveRevenueWhenChildHasHourlyFee(self):
        self.child.set_hourly_fee(100)
        self.assertEqual(
            self.childEffort.timeSpent().hours() * 100,
            self.composite.revenue(recursive=True),
        )

    def testRevenueWhenChildAndParentHaveHourlyFees(self):
        self.child.set_hourly_fee(100)
        self.task.set_hourly_fee(200)
        self.assertEqual(
            self.taskEffort.timeSpent().hours() * 200, self.composite.revenue()
        )

    def testRecursiveRevenueWhenChildAndParentHaveHourlyFees(self):
        self.child.set_hourly_fee(100)
        self.task.set_hourly_fee(200)
        self.assertEqual(
            self.taskEffort.timeSpent().hours() * 200
            + self.childEffort.timeSpent().hours() * 100,
            self.composite.revenue(recursive=True),
        )

    def testRevenueWhenParentHasFixedFee(self):
        self.task.set_fixed_fee(1000)
        self.assertEqual(0, self.composite.revenue())

    def testRecursiveRevenueWhenParentHasFixedFee(self):
        self.task.set_fixed_fee(1000)
        self.assertEqual(0, self.composite.revenue(recursive=True))

    def testRevenueWhenChildHasFixedFee(self):
        self.child.set_fixed_fee(1000)
        self.assertEqual(0, self.composite.revenue())

    def testRecursiveRevenueWhenChildHasFixedFee(self):
        self.child.set_fixed_fee(1000)
        self.assertEqual(0, self.composite.revenue(recursive=True))

    def testRevenueWhenParentHasFixedFeeAndMultipleEfforts(self):
        self.task.set_fixed_fee(1000)
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2005, 12, 12, 10, 0, 0),
                date.DateTime(2005, 12, 12, 12, 0, 0),
            )
        )
        self.assertEqual(0, self.composite.revenue())

    def testRevenueWhenChildHasFixedFeeAndMultipleEfforts(self):
        self.child.set_fixed_fee(1000)
        self.child.addEffort(
            effort.Effort(
                self.child,
                date.DateTime(2005, 12, 12, 10, 0, 0),
                date.DateTime(2005, 12, 12, 12, 0, 0),
            )
        )
        self.assertEqual(0, self.composite.revenue())

    def testRecursiveRevenueWhenChildHasFixedFeeAndMultipleEfforts(self):
        self.child.set_fixed_fee(1000)
        self.child.addEffort(
            effort.Effort(
                self.child,
                date.DateTime(2005, 12, 12, 10, 0, 0),
                date.DateTime(2005, 12, 12, 12, 0, 0),
            )
        )
        self.assertEqual(0, self.composite.revenue(recursive=True))

    def testRevenueWithMixture(self):
        self.child.set_fixed_fee(100)
        self.task.set_hourly_fee(1000)
        self.assertEqual(1000, self.composite.revenue(recursive=True))

    def test_that_an_hourly_fee_change_causes_a_revenue_notification(self):
        events = test.ChangeRecorder(effort.Effort.revenueChangedEventType())
        self.child.set_hourly_fee(100)
        self.assertTrue((0.0, self.composite) in events)
