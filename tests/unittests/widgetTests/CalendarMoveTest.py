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
import wx
from taskcoachlib import persistence
from taskcoachlib.domain import date, task
from taskcoachlib.widgets.calendarwidget import TaskSchedule


class CalendarMoveTest(test.wxTestCase):
    """A task moved in the calendar keeps its duration whatever its
    duration mode (docs/DURATION_CALCULATIONS.md, Stored Duration)."""

    def setUp(self):
        super().setUp()
        self.task_file = persistence.TaskFile()
        self.addCleanup(self.task_file.stop)
        self.addCleanup(self.task_file.close)
        self.start = date.DateTime(2026, 1, 30, 9, 0, 0)
        self.task = task.Task(
            "task",
            plannedStartDateTime=self.start,
            dueDateTime=self.start + date.ONE_DAY,
            plannedDuration=date.ONE_DAY,
        )
        self.task_file.tasks().append(self.task)

    def test_a_move_takes_both_dates(self):
        for mode in ("implicit", "adjdue", "adjstart"):
            self.task.setPlannedDurationMode(mode)
            TaskSchedule(self.task).Offset(wx.TimeSpan.Hours(2))
            self.assertEqual(
                (
                    self.start + date.TWO_HOURS,
                    self.start + date.ONE_DAY + date.TWO_HOURS,
                    date.ONE_DAY,
                ),
                (
                    self.task.plannedStartDateTime(),
                    self.task.dueDateTime(),
                    self.task.plannedDuration(),
                ),
                mode,
            )
            TaskSchedule(self.task).Offset(wx.TimeSpan.Hours(-2))
