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
from taskcoachlib import command, config
from taskcoachlib.domain import task, effort, date


class EffortCommandTestCase(CommandTestCase, asserts.CommandAssertsMixin):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.taskList = task.TaskList()
        self.effortList = effort.EffortList(self.taskList)
        self.originalTask = task.Task()
        self.taskList.append(self.originalTask)
        self.originalStop = date.DateTime.now()
        self.originalStart = self.originalStop - date.ONE_HOUR
        self.effort = effort.Effort(
            self.originalTask, self.originalStart, self.originalStop
        )
        self.originalTask.addEffort(self.effort)


class NewEffortCommandTest(EffortCommandTestCase):
    def testNewEffort(self):
        newEffortCommand = command.NewEffortCommand(
            self.effortList, [self.originalTask]
        )
        newEffortCommand.do()
        newEffort = newEffortCommand.efforts[0]
        self.assertDoUndoRedo(
            lambda: self.assertTrue(newEffort in self.originalTask.efforts()),
            lambda: self.assertEqual(
                [self.effort], self.originalTask.efforts()
            ),
        )

    def testAddingNewEffortSetsActualStartDateTimeOfTask(self):
        newTask = task.Task()
        self.taskList.append(newTask)
        newEffortCommand = command.NewEffortCommand(self.effortList, [newTask])
        newEffortCommand.do()
        newEffort = newEffortCommand.efforts[0]
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                newEffort.getStart(), newTask.actualStartDateTime()
            ),
            lambda: self.assertEqual(
                date.DateTime(), newTask.actualStartDateTime()
            ),
        )

    def testNewEffortWhenUserEditsTask(self):
        secondTask = task.Task()
        self.taskList.append(secondTask)
        newEffortCommand = command.NewEffortCommand(
            self.effortList, [self.originalTask]
        )
        newEffort = newEffortCommand.efforts[0]
        newEffort.set_task(secondTask)
        newEffortCommand.do()
        self.assertDoUndoRedo(
            lambda: self.assertTrue(
                newEffort in secondTask.efforts()
                and newEffort not in self.originalTask.efforts()
            ),
            lambda: self.assertTrue(
                newEffort not in secondTask.efforts()
                and newEffort not in self.originalTask.efforts()
            ),
        )


class StartAndStopEffortCommandTest(EffortCommandTestCase):
    def setUp(self):
        super().setUp()
        self.start = command.StartEffortCommand(
            self.taskList, [self.originalTask]
        )
        self.start.do()
        self.task2 = task.Task()

    def testStart(self):
        self.assertDoUndoRedo(
            lambda: self.assertTrue(self.originalTask.isBeingTracked()),
            lambda: self.assertFalse(self.originalTask.isBeingTracked()),
        )

    def testStop(self):
        stop = command.StopEffortCommand(self.effortList)
        stop.do()
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.originalTask.isBeingTracked()),
            lambda: self.assertTrue(self.originalTask.isBeingTracked()),
        )

    def testStartStopsPreviousStart(self):
        start = command.StartEffortCommand(self.taskList, [self.task2])
        start.do()
        self.assertDoUndoRedo(
            lambda: self.assertFalse(self.originalTask.isBeingTracked()),
            lambda: self.assertTrue(self.originalTask.isBeingTracked()),
        )

    def testStartTrackingInactiveTaskSetsActualStartDate(self):
        start = command.StartEffortCommand(self.taskList, [self.task2])
        start.do()
        now = date.Now()
        self.assertDoUndoRedo(
            lambda: self.assertTrue(
                now - date.ONE_SECOND
                < self.task2.actualStartDateTime()
                < now + date.ONE_SECOND
            ),
            lambda: self.assertEqual(
                date.DateTime(), self.task2.actualStartDateTime()
            ),
        )

    def testStartTrackingInactiveTaskWithFutureActualStartDate(self):
        futureStartDateTime = date.Tomorrow()
        self.task2.set_actual_start_date_time(futureStartDateTime)
        start = command.StartEffortCommand(self.taskList, [self.task2])
        start.do()
        now = date.Now()
        self.assertDoUndoRedo(
            lambda: self.assertTrue(
                now - date.ONE_SECOND
                < self.task2.actualStartDateTime()
                < now + date.ONE_SECOND
            ),
            lambda: self.assertEqual(
                futureStartDateTime, self.task2.actualStartDateTime()
            ),
        )


class EditEffortStartDateTimeCommandTest(EffortCommandTestCase):
    def testNewStartDateTime(self):
        oldStart = self.effort.getStart()
        newStart = date.DateTime(2000, 1, 1)
        edit = command.EditEffortStartDateTimeCommand(
            self.effortList, [self.effort], newValue=newStart
        )
        edit.do()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(newStart, self.effort.getStart()),
            lambda: self.assertEqual(oldStart, self.effort.getStart()),
        )

    def testNewStartDateTimeSetsActualStartOfTask(self):
        oldStart = self.effort.task().actualStartDateTime()
        newStart = date.DateTime(2000, 1, 1)
        edit = command.EditEffortStartDateTimeCommand(
            self.effortList, [self.effort], newValue=newStart
        )
        edit.do()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(
                newStart, self.effort.task().actualStartDateTime()
            ),
            lambda: self.assertEqual(
                oldStart, self.effort.task().actualStartDateTime()
            ),
        )


class EditEffortStopDateTimeCommandTest(EffortCommandTestCase):
    def testNewStopDateTime(self):
        oldStop = self.effort.getStop()
        newStop = oldStop + date.ONE_HOUR
        edit = command.EditEffortStopDateTimeCommand(
            self.effortList, [self.effort], newValue=newStop
        )
        edit.do()
        self.assertDoUndoRedo(
            lambda: self.assertEqual(newStop, self.effort.getStop()),
            lambda: self.assertEqual(oldStop, self.effort.getStop()),
        )
