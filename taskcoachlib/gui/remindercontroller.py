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

Reminder Controller: responds to the reminders Task.processReminder()
fires, which MasterScheduler calls in its pass at a reminder's second
(docs/SCHEDULERS.md).
"""

from taskcoachlib import patterns
from taskcoachlib.i18n import _
from taskcoachlib.gui.dialog import reminder, editor
from taskcoachlib.tools import wxhelper
import wx


class ReminderController(object):
    """
    Controller for showing task reminders.

    Subscribes to task.reminder.trigger events fired by Task.processReminder().
    MasterScheduler calls processReminder() for all tasks in its pass,
    which runs at the seconds its timer list holds (a reminder's too).

    Note: As of January 2026, only the built-in Task Coach reminder dialog is used.
    External notification system support (KNotify, Growl) has been removed.
    """

    def __init__(self, main_window, task_list, effort_list):
        super().__init__()
        self.__mainWindow = main_window
        self.__mainWindowWasHidden = False
        self.taskList = task_list
        self.effortList = effort_list

        # Subscribe to reminder trigger events from Task.processReminder()
        patterns.Publisher().registerObserver(
            self._on_reminder_trigger, eventType="task.reminder.trigger"
        )

    def _on_reminder_trigger(self, event):
        """
        Handle reminder trigger from Task.processReminder().

        Idempotent - safe to receive multiple triggers for same task.
        Only shows dialog if not already open (checked via ReminderDialog.isOpenFor).

        Args:
            event: its source is the task whose reminder is due
        """
        for task in event.sources():
            # After the scheduler pass that fired it: the dialog asks
            # for attention, which runs wx's event loop and would draw
            # the views mid-pass (docs/WINDOW_GEOMETRY.md, Opening the
            # File)
            patterns.later.soon(self.__mainWindow, self.__show, task)

    def __show(self, task):
        # Check if dialog already open for this task (SSOT check)
        if not reminder.ReminderDialog.isOpenFor(task):
            self.showReminderMessage(task)
            self.requestUserAttention()

    def showReminderMessage(
        self, task_with_reminder, ReminderDialog=reminder.ReminderDialog
    ):
        """Show Task Coach's reminder dialog for a task."""
        # If the dialog has self.__mainWindow as parent, it steals the focus when
        # returning to Task Coach through Alt+Tab; we don't want that for
        # reminders.
        reminder_dialog = ReminderDialog(
            task_with_reminder,
            self.taskList,
            self.effortList,
            None,
        )
        # Position on app's monitor even though it has no parent
        wxhelper.centre_on_app_monitor(reminder_dialog)
        reminder_dialog.Bind(wx.EVT_CLOSE, self.on_close_reminder_dialog)
        reminder_dialog.Show()

    def on_close_reminder_dialog(self, event, show=True):
        """Handle reminder dialog close."""
        event.Skip()
        dialog = event.EventObject
        task_with_reminder = dialog.task

        if not dialog.ignoreSnoozeOption:
            snooze_options = dialog.snoozeOptions
            snooze_time_delta = snooze_options.GetClientData(
                snooze_options.Selection
            )
            # An undo step, as every change to the file
            # (docs/UNDO_REDO.md, Design Intent)
            with patterns.CommandHistory().action(_("Snooze")):
                task_with_reminder.snooze_reminder(snooze_time_delta)

        if dialog.openTaskAfterClose:
            edit_task = editor.TaskEditor(
                self.__mainWindow,
                [task_with_reminder],
                self.taskList,
                self.__mainWindow.taskFile,
                icon_id="nuvola_actions_edit",
            )
            edit_task.Show(show)
        else:
            edit_task = None

        dialog.Destroy()

        if self.__mainWindowWasHidden:
            self.__mainWindow.Hide()

        return edit_task  # For unit testing purposes

    def requestUserAttention(self):
        """Request user attention when showing reminders."""
        self.__mainWindowWasHidden = not self.__mainWindow.IsShown()
        if self.__mainWindowWasHidden:
            self.__mainWindow.Show()
        if not self.__mainWindow.IsActive():
            self.__mainWindow.RequestUserAttention()

    def shutdown(self):
        """Cleanup subscriptions."""
        patterns.Publisher().removeObserver(
            self._on_reminder_trigger, eventType="task.reminder.trigger"
        )
