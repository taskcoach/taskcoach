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
from . import EffortCompositeTest
import test


class CompositeEffortPerPeriodTest(test.TestCase):
    def setUp(self):
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

    def test_initial_length(self):
        self.assertEqual(0, len(self.composite))

    def test_initial_duration(self):
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def test_initial_tracking_state(self):
        self.assertFalse(self.composite.isBeingTracked())

    def test_initial_tracking_state_when_task_is_tracked(self):
        self.task.addEffort(self.trackedEffort)
        composite = effort.CompositeEffortPerPeriod(
            self.composite.getStart(),
            self.composite.getStop(),
            self.taskList,
            self.trackedEffort,
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

    def test_remove_effort_from_task(self):
        self.task.addEffort(self.effort1)
        self.task.removeEffort(self.effort1)
        self.assertEqual(date.TimeDelta(), self.composite.totalTimeSpent())

    def test_remove_multiple_efforts_from_same_period_from_task(self):
        events = test.ChangeRecorder(
            effort.CompositeEffort.compositeEmptyEventType()
        )
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.task.setEfforts([])
        self.assertTrue(events)

    def test_remove_multiple_efforts_from_different_periods_from_task(self):
        events = test.ChangeRecorder(
            effort.CompositeEffort.compositeEmptyEventType()
        )
        self.task.addEffort(self.effort3)
        self.task.addEffort(self.effort1)
        self.task.setEfforts([])
        self.assertTrue(events)
