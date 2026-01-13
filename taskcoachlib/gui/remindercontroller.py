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
Reminder Controller - Simplified polling-based implementation.

This module checks for due reminders every second via the global timer,
replacing the previous complex per-task scheduling system.

See docs/SCHEDULERS.md for architecture documentation.
"""

from taskcoachlib import meta, notify
from taskcoachlib.domain import date, task
from taskcoachlib.gui.dialog import reminder, editor
from taskcoachlib.i18n import _
from taskcoachlib.tools import wxhelper
from pubsub import pub
import wx


class ReminderController(object):
    """
    Controller for showing task reminders.

    Uses simple polling via global timer instead of per-task scheduling.
    Checks all tasks every second and shows reminders for those that are due.
    """

    def __init__(self, mainWindow, taskList, effortList, settings):
        super().__init__()
        self.__mainWindow = mainWindow
        self.__mainWindowWasHidden = False
        self.settings = settings
        self.taskList = taskList
        self.effortList = effortList

        # Track shown reminders to avoid duplicates (replaces __tasksWithReminders)
        self._shownReminders = set()

        # Subscribe to timer for polling
        pub.subscribe(self._onTimerSecond, 'timer.second')

        # Subscribe to reminder changes to clear shown status when snoozed
        pub.subscribe(self._onReminderChanged, task.Task.reminderChangedEventType())

    def _onTimerSecond(self, timestamp):
        """
        Check for due reminders every second.

        Args:
            timestamp: DateTime from global timer (reuse, don't call now())
        """
        self._checkReminders(timestamp)

    def _onReminderChanged(self, newValue, sender):
        """
        Handle reminder change (e.g., snooze).
        Clear from shown set so it can fire again at new time.
        """
        self._shownReminders.discard(sender)

    def _checkReminders(self, now):
        """
        Check all tasks for due reminders.

        Args:
            now: Current timestamp from timer
        """
        # Add small buffer to not miss reminders (consistent with old behavior)
        checkTime = now + date.TimeDelta(seconds=2)

        tasksToRemind = []

        for task in self.taskList:
            # Skip completed tasks - no point reminding about finished work
            if task.completed():
                continue
            reminderTime = task.reminder()
            if reminderTime and reminderTime <= checkTime:
                if task not in self._shownReminders:
                    tasksToRemind.append(task)
                    self._shownReminders.add(task)

        # Show reminders (outside loop for safety)
        if tasksToRemind:
            for taskWithReminder in tasksToRemind:
                self.showReminderMessage(taskWithReminder)
            self.requestUserAttention()

    def showReminderMessage(
        self, taskWithReminder, ReminderDialog=reminder.ReminderDialog
    ):
        """Show reminder for a task."""
        if self._useOwnReminderDialog():
            self._showReminderDialog(taskWithReminder, ReminderDialog)
        else:
            self._showReminderViaNotifier(taskWithReminder)
            self._snooze(taskWithReminder)

    def _useOwnReminderDialog(self):
        """Check if we should use Task Coach's own reminder dialog."""
        notifier = self.settings.get("feature", "notifier")
        return (
            notifier == "Task Coach"
            or notify.AbstractNotifier.get(notifier) is None
        )

    def _showReminderDialog(self, taskWithReminder, ReminderDialog):
        """Show Task Coach's reminder dialog."""
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

    def _showReminderViaNotifier(self, taskWithReminder):
        """Show reminder via external notifier."""
        notifier = notify.AbstractNotifier.get(
            self.settings.get("feature", "notifier")
        )
        notifier.notify(
            _("%s Reminder") % meta.name,
            taskWithReminder.subject(),
            wx.ArtProvider.GetBitmap("taskcoach", size=wx.Size(32, 32)),
            windowId=self.__mainWindow.GetHandle(),
        )

    def _snooze(self, taskWithReminder):
        """Apply default snooze to a task."""
        minutesToSnooze = self.settings.getint("view", "defaultsnoozetime")
        taskWithReminder.snoozeReminder(
            date.TimeDelta(minutes=minutesToSnooze)
        )

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
                bitmap="edit",
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
        notifier = self.settings.get("feature", "notifier")
        if (
            notifier != "Task Coach"
            and notify.AbstractNotifier.get(notifier) is not None
        ):
            # When using an external notifier, requesting user attention is not necessary
            return
        self.__mainWindowWasHidden = not self.__mainWindow.IsShown()
        if self.__mainWindowWasHidden:
            self.__mainWindow.Show()
        if not self.__mainWindow.IsActive():
            self.__mainWindow.RequestUserAttention()

    def shutdown(self):
        """Cleanup subscriptions."""
        pub.unsubscribe(self._onTimerSecond, 'timer.second')
        pub.unsubscribe(self._onReminderChanged, task.Task.reminderChangedEventType())
