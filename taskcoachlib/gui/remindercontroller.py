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

"""
Reminder Controller - Event-based implementation.

This module responds to reminder trigger events fired by Task.processReminder(),
which is called by MasterScheduler every second.

See docs/SCHEDULERS.md for architecture documentation.
"""

from taskcoachlib.gui.dialog import reminder, editor
from taskcoachlib.tools import wxhelper
from pubsub import pub
import wx


class ReminderController(object):
    """
    Controller for showing task reminders.

    Subscribes to task.reminder.trigger events fired by Task.processReminder().
    MasterScheduler calls processReminder() every second for all tasks.

    Note: As of January 2026, only the built-in Task Coach reminder dialog is used.
    External notification system support (KNotify, Growl) has been removed.
    """

    def __init__(self, mainWindow, taskList, effortList, settings):
        super().__init__()
        self.__mainWindow = mainWindow
        self.__mainWindowWasHidden = False
        self.settings = settings
        self.taskList = taskList
        self.effortList = effortList

        # Subscribe to reminder trigger events from Task.processReminder()
        pub.subscribe(self._onReminderTrigger, 'task.reminder.trigger')

    def _onReminderTrigger(self, task):
        """
        Handle reminder trigger from Task.processReminder().

        Idempotent - safe to receive multiple triggers for same task.
        Only shows dialog if not already open (checked via ReminderDialog.isOpenFor).

        Args:
            task: The task whose reminder is due
        """
        # Check if dialog already open for this task (SSOT check)
        if not reminder.ReminderDialog.isOpenFor(task):
            self.showReminderMessage(task)
            self.requestUserAttention()

    def showReminderMessage(
        self, taskWithReminder, ReminderDialog=reminder.ReminderDialog
    ):
        """Show Task Coach's reminder dialog for a task."""
        # If the dialog has self.__mainWindow as parent, it steals the focus when
        # returning to Task Coach through Alt+Tab; we don't want that for
        # reminders.
        reminderDialog = ReminderDialog(
            taskWithReminder,
            self.taskList,
            self.effortList,
            self.settings,
            None,
        )
        # Position on app's monitor even though it has no parent
        wxhelper.centerOnAppMonitor(reminderDialog)
        reminderDialog.Bind(wx.EVT_CLOSE, self.onCloseReminderDialog)
        reminderDialog.Show()

    def onCloseReminderDialog(self, event, show=True):
        """Handle reminder dialog close."""
        event.Skip()
        dialog = event.EventObject
        taskWithReminder = dialog.task

        if not dialog.ignoreSnoozeOption:
            snoozeOptions = dialog.snoozeOptions
            snoozeTimeDelta = snoozeOptions.GetClientData(
                snoozeOptions.Selection
            )
            taskWithReminder.snoozeReminder(
                snoozeTimeDelta
            )  # Note that this is not undoable
            # Undoing the snoozing makes little sense, because it would set the
            # reminder back to its original date-time, which is now in the past.

        if dialog.openTaskAfterClose:
            editTask = editor.TaskEditor(
                self.__mainWindow,
                [taskWithReminder],
                self.settings,
                self.taskList,
                self.__mainWindow.taskFile,
                icon_id="nuvola_actions_edit",
            )
            editTask.Show(show)
        else:
            editTask = None

        dialog.Destroy()

        if self.__mainWindowWasHidden:
            self.__mainWindow.Hide()

        return editTask  # For unit testing purposes

    def requestUserAttention(self):
        """Request user attention when showing reminders."""
        self.__mainWindowWasHidden = not self.__mainWindow.IsShown()
        if self.__mainWindowWasHidden:
            self.__mainWindow.Show()
        if not self.__mainWindow.IsActive():
            self.__mainWindow.RequestUserAttention()

    def shutdown(self):
        """Cleanup subscriptions."""
        pub.unsubscribe(self._onReminderTrigger, 'task.reminder.trigger')
