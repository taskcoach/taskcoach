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

from taskcoachlib import config
from taskcoachlib.domain import task, effort, date
from pubsub import pub
from . import EffortCompositeTest
import test


class CompositeEffortPerPeriodTest(test.TestCase):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.taskList = task.TaskList()
        self.effortList = effort.EffortList(self.taskList)
        self.task = task.Task(subject="task")
        self.taskList.append(self.task)
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
        self.composite = effort.CompositeEffortPerPeriod(
            date.DateTime(2004, 1, 1, 0, 0, 0),
            date.DateTime(2004, 1, 1, 23, 59, 59),
            self.taskList,
        )
        self.reducer = EffortCompositeTest.FakeEffortAggregator(self.composite)

    def testInitialLength(self):
        self.assertEqual(0, len(self.composite))

    def testInitialDuration(self):
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def testInitialTrackingState(self):
        self.assertFalse(self.composite.isBeingTracked())

    def testInitialTrackingStateWhenTaskIsTracked(self):
        self.task.addEffort(self.trackedEffort)
        composite = effort.CompositeEffortPerPeriod(
            self.composite.getStart(),
            self.composite.getStop(),
            self.taskList,
            self.trackedEffort,
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

    def testRemoveEffortFromTask(self):
        self.task.addEffort(self.effort1)
        self.task.removeEffort(self.effort1)
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def testRemoveMultipleEffortsFromSamePeriodFromTask(self):
        events = []

        def onEvent(sender):
            events.append(sender)

        pub.subscribe(
            onEvent, effort.CompositeEffort.compositeEmptyEventType()
        )
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.task.setEfforts([])
        self.assertTrue(events)

    def testRemoveMultipleEffortsFromDifferentPeriodsFromTask(self):
        events = []

        def onEvent(sender):
            events.append(sender)

        pub.subscribe(
            onEvent, effort.CompositeEffort.compositeEmptyEventType()
        )
        self.task.addEffort(self.effort3)
        self.task.addEffort(self.effort1)
        self.task.setEfforts([])
        self.assertTrue(events)
