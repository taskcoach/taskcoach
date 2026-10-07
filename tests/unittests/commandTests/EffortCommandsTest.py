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

from unittests import asserts
from .CommandTestCase import CommandTestCase
from taskcoachlib import command
from taskcoachlib.domain import task, effort, date


class EffortCommandTestCase(CommandTestCase, asserts.CommandAssertsMixin):
    def setUp(self):
        super().setUp()
        self.taskList = self.task_file.tasks()
        self.effortList = self.task_file.efforts()
        self.originalTask = task.Task()
        self.taskList.append(self.originalTask)
        self.originalStop = date.DateTime.now()
        self.originalStart = self.originalStop - date.ONE_HOUR
        self.effort = effort.Effort(
            self.originalTask, self.originalStart, self.originalStop
        )
        self.originalTask.addEffort(self.effort)


class NewEffortCommandTest(EffortCommandTestCase):
    def test_new_effort(self):
        new_effort_command = command.NewEffortCommand(
            self.effortList, [self.originalTask]
        )
        new_effort_command.do()
        new_effort = new_effort_command.efforts[0]
        self.assertDoUndoRedo(
            lambda: self.assertTrue(new_effort in self.originalTask.efforts()),
            lambda: self.assertEqual(
                [self.effort], self.originalTask.efforts()
            ),
        )

    def test_adding_new_effort_sets_actual_start_date_time_of_task(self):
        new_task = task.Task()
        self.taskList.append(new_task)
        new_effort_command = command.NewEffortCommand(
            self.effortList, [new_task]
        )
        new_effort_command.do()
        new_effort = new_effort_command.efforts[0]
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                new_effort.getStart(), new_task.actualStartDateTime()
            ),
            lambda: self.assertEqual(
                date.DateTime(), new_task.actualStartDateTime()
            ),
        )

    def test_new_effort_when_user_edits_task(self):
        second_task = task.Task()
        self.taskList.append(second_task)
        new_effort_command = command.NewEffortCommand(
            self.effortList, [self.originalTask]
        )
        new_effort_command.do()
        new_effort = new_effort_command.efforts[0]
        # The effort editor moves it: a step of its own
        command.EditTaskCommand(None, [new_effort], newValue=second_task).do()
        self.assertDoUndoRedo(
            lambda: self.assertTrue(
                new_effort in second_task.efforts()
                and new_effort not in self.originalTask.efforts()
            ),
            lambda: self.assertTrue(
                new_effort in self.originalTask.efforts()
                and new_effort not in second_task.efforts()
            ),
        )
        self.undo()
        self.undo()
        self.assertTrue(
            new_effort not in second_task.efforts()
            and new_effort not in self.originalTask.efforts()
        )


class StartAndStopEffortCommandTest(EffortCommandTestCase):
    def setUp(self):
        super().setUp()
        self.start = command.StartEffortCommand(
            self.taskList, [self.originalTask]
        )
        self.start.do()
        self.task2 = task.Task()

    def test_start(self):
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.originalTask.isBeingTracked()),
            lambda: self.assertFalse(self.originalTask.isBeingTracked()),
        )

    def test_stop(self):
        stop = command.StopEffortCommand(self.effortList)
        stop.do()
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.originalTask.isBeingTracked()),
            lambda: self.assertTrue(self.originalTask.isBeingTracked()),
        )

    def test_start_stops_previous_start(self):
        start = command.StartEffortCommand(self.taskList, [self.task2])
        start.do()
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.originalTask.isBeingTracked()),
            lambda: self.assertTrue(self.originalTask.isBeingTracked()),
        )

    def test_start_tracking_inactive_task_sets_actual_start_date(self):
        start = command.StartEffortCommand(self.taskList, [self.task2])
        start.do()
        now = date.Now()
        self.assertDoUndoRedo(
            lambda: self.assertTrue(
                now - date.ONE_SECOND
                <= self.task2.actualStartDateTime()
                < now + date.ONE_SECOND
            ),
            lambda: self.assertEqual(
                date.DateTime(), self.task2.actualStartDateTime()
            ),
        )

    def test_start_tracking_inactive_task_with_future_actual_start_date(self):
        future_start_date_time = date.Tomorrow()
        self.task2.set_actual_start_date_time(future_start_date_time)
        start = command.StartEffortCommand(self.taskList, [self.task2])
        start.do()
        now = date.Now()
        self.assertDoUndoRedo(
            lambda: self.assertTrue(
                now - date.ONE_SECOND
                <= self.task2.actualStartDateTime()
                < now + date.ONE_SECOND
            ),
            lambda: self.assertEqual(
                future_start_date_time, self.task2.actualStartDateTime()
            ),
        )


class EditEffortStartDateTimeCommandTest(EffortCommandTestCase):
    def test_new_start_date_time(self):
        old_start = self.effort.getStart()
        new_start = date.DateTime(2000, 1, 1)
        edit = command.EditEffortStartDateTimeCommand(
            self.effortList, [self.effort], newValue=new_start
        )
        edit.do()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(new_start, self.effort.getStart()),
            lambda: self.assertEqual(old_start, self.effort.getStart()),
        )

    def test_new_start_date_time_sets_actual_start_of_task(self):
        old_start = self.effort.task().actualStartDateTime()
        new_start = date.DateTime(2000, 1, 1)
        edit = command.EditEffortStartDateTimeCommand(
            self.effortList, [self.effort], newValue=new_start
        )
        edit.do()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                new_start, self.effort.task().actualStartDateTime()
            ),
            lambda: self.assertEqual(
                old_start, self.effort.task().actualStartDateTime()
            ),
        )


class EditEffortStopDateTimeCommandTest(EffortCommandTestCase):
    def test_new_stop_date_time(self):
        old_stop = self.effort.getStop()
        new_stop = old_stop + date.ONE_HOUR
        edit = command.EditEffortStopDateTimeCommand(
            self.effortList, [self.effort], newValue=new_stop
        )
        edit.do()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(new_stop, self.effort.getStop()),
            lambda: self.assertEqual(old_stop, self.effort.getStop()),
        )
