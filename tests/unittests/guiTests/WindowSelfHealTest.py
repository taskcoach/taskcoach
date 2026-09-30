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

from unittest import mock

import wx

import test
from taskcoachlib import command, config, gui, patterns, persistence
from taskcoachlib.domain import date, note, task
from taskcoachlib.gui.dialog import editor, reminder


class SelfHealTestCase(test.wxTestCase):
    """A window closes once its reason is gone, changing nothing: an
    editor once the file no longer holds its item, a reminder window
    once its reminder no longer stands (docs/UNDO_REDO.md, Windows)."""

    def setUp(self):
        super().setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        self.history = patterns.CommandHistory()
        self.history.clear()
        self.addCleanup(self.history.clear)
        self.task_file = persistence.TaskFile()
        self.addCleanup(self.task_file.stop)
        self.addCleanup(self.task_file.close)
        self.tasks = self.task_file.tasks()

    def steps(self):
        return [str(step) for step in self.history.get_history()]

    @staticmethod
    def settle():
        wx.Yield()


class ReminderWindowTest(SelfHealTestCase):
    def setUp(self):
        super().setUp()
        self.task = task.Task("Task")
        self.tasks.append(self.task)
        self.task.set_reminder(date.Now() - date.ONE_MINUTE)
        # Without a window manager it crashes GTK (ReminderDialogTest)
        patcher = mock.patch.object(
            reminder.ReminderDialog, "RequestUserAttention"
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch("taskcoachlib.sounds.play")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.controller = gui.remindercontroller.ReminderController(
            self.frame, self.tasks, self.task_file.efforts(), self.settings
        )
        self.addCleanup(self.controller.shutdown)
        self.controller.showReminderMessage(self.task)

    def tearDown(self):
        for window in wx.GetTopLevelWindows():
            if isinstance(window, reminder.ReminderDialog):
                window.Destroy()
        self.settle()
        super().tearDown()

    def is_open(self):
        return reminder.ReminderDialog.isOpenFor(self.task)

    def test_it_stays_while_its_reminder_is_due(self):
        command.EditSubjectCommand(
            self.tasks, [self.task], newValue="Renamed"
        ).do()
        self.settle()
        self.assertTrue(self.is_open())

    def test_it_closes_when_its_task_is_deleted(self):
        reminder_before = self.task.reminder()
        command.DeleteTaskCommand(self.tasks, [self.task]).do()
        self.settle()
        # Closed without snoozing: the task keeps its reminder
        self.assertEqual(
            (False, reminder_before), (self.is_open(), self.task.reminder())
        )

    def test_it_closes_when_its_task_is_completed_elsewhere(self):
        command.MarkCompletedCommand(self.tasks, [self.task]).do()
        self.settle()
        # Completing cleared the reminder; closing snoozed nothing
        self.assertEqual(
            (False, date.DateTime()), (self.is_open(), self.task.reminder())
        )

    def test_it_closes_when_undo_moves_its_reminder(self):
        # The reminder window of a reminder set earlier, then undone
        command.EditReminderDateTimeCommand(
            self.tasks, [self.task], newValue=date.Now() + date.ONE_HOUR
        ).do()
        self.settle()
        self.assertFalse(self.is_open())
        self.history.undo()
        self.settle()
        # Due again: the scheduler shows it again, not the undo
        self.assertFalse(self.is_open())
        self.assertEqual([], self.steps())


class EditorTest(SelfHealTestCase):
    def open(self, editor_class, items, container):
        window = editor_class(
            self.frame, items, self.settings, container, self.task_file
        )
        self.addCleanup(lambda: window and window.Destroy())
        window.Show()
        return window

    @staticmethod
    def is_open(window):
        return bool(window) and window.IsShown()

    def test_an_editor_closes_when_the_creation_of_its_item_is_undone(self):
        new = command.NewTaskCommand(self.tasks)
        new.do()
        window = self.open(editor.TaskEditor, new.items, self.tasks)
        self.history.undo()
        self.settle()
        self.assertFalse(self.is_open(window))
        # Redo brings the task back, not the window
        self.history.redo()
        self.settle()
        self.assertFalse(self.is_open(window))

    def test_a_note_editor_closes_when_its_owner_is_deleted(self):
        owner = task.Task("Owner")
        self.tasks.append(owner)
        owned = note.Note(subject="Owned")
        owner.addNote(owned)
        window = self.open(
            editor.NoteEditor, [owned], note.NoteContainer(owner.notes())
        )
        command.DeleteTaskCommand(self.tasks, [owner]).do()
        self.settle()
        self.assertFalse(self.is_open(window))

    def test_an_editor_stays_while_its_item_is_in_the_file(self):
        item = task.Task("Kept")
        self.tasks.append(item)
        window = self.open(editor.TaskEditor, [item], self.tasks)
        command.EditSubjectCommand(self.tasks, [item], newValue="New").do()
        self.settle()
        self.assertTrue(self.is_open(window))
