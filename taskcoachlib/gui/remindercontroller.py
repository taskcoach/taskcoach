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

from taskcoachlib import patterns, meta, notify
from taskcoachlib.domain import date, task
from taskcoachlib.gui.dialog import reminder, editor
from taskcoachlib.i18n import _
from taskcoachlib.tools import wxhelper
from pubsub import pub
import wx


class ReminderController(object):
    lastId = 0

    @classmethod
    def nextId(cls):
        cls.lastId += 1
        return cls.lastId

    def __init__(self, mainWindow, taskList, effortList, settings):
        super().__init__()
        pub.subscribe(self.onSetReminder, task.Task.reminderChangedEventType())
        patterns.Publisher().registerObserver(
            self.onAddTask,
            eventType=taskList.addItemEventType(),
            eventSource=taskList,
        )
        patterns.Publisher().registerObserver(
            self.onRemoveTask,
            eventType=taskList.removeItemEventType(),
            eventSource=taskList,
        )
        self.__tasksWithReminders = {}  # {task: reminderDateTime}
        self.__mainWindow = mainWindow
        self.__mainWindowWasHidden = False
        self.__registerRemindersForTasks(taskList)
        self.settings = settings
        self.taskList = taskList
        self.effortList = effortList

    def onAddTask(self, event):
        self.__registerRemindersForTasks(list(event.values()))

    def onRemoveTask(self, event):
        self.__removeRemindersForTasks(list(event.values()))

    def onSetReminder(self, newValue, sender):  # pylint: disable=W0613
        self.__removeRemindersForTasks([sender])
        self.__registerRemindersForTasks([sender])

    def onReminder(self):
        self.showReminderMessages(date.DateTime.now())

    def showReminderMessages(self, now):
        now += date.TimeDelta(seconds=5)  # Be sure not to miss reminders
        requestUserAttention = False
        for taskWithReminder in self.__tasksWithReminders.copy():
            if taskWithReminder.reminder() <= now:
                requestUserAttention = True
                self.showReminderMessage(taskWithReminder)
        if requestUserAttention:
            self.requestUserAttention()

    def showReminderMessage(
        self, taskWithReminder, ReminderDialog=reminder.ReminderDialog
    ):
        if self.__useOwnReminderDialog():
            self.__showReminderDialog(taskWithReminder, ReminderDialog)
            self.__removeReminder(taskWithReminder)
        else:
            self.__showReminderViaNotifier(taskWithReminder)
            self.__removeReminder(taskWithReminder)
            self.__snooze(taskWithReminder)

    def __useOwnReminderDialog(self):
        notifier = self.settings.get("feature", "notifier")
        return (
            notifier == "Task Coach"
            or notify.AbstractNotifier.get(notifier) is None
        )

    def __showReminderDialog(self, taskWithReminder, ReminderDialog):
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

    def __showReminderViaNotifier(self, taskWithReminder):
        notifier = notify.AbstractNotifier.get(
            self.settings.get("feature", "notifier")
        )
        notifier.notify(
            _("%s Reminder") % meta.name,
            taskWithReminder.subject(),
            wx.ArtProvider.GetBitmap("taskcoach", size=wx.Size(32, 32)),
            windowId=self.__mainWindow.GetHandle(),
        )

    def __snooze(self, taskWithReminder):
        minutesToSnooze = self.settings.getint("view", "defaultsnoozetime")
        taskWithReminder.snoozeReminder(
            date.TimeDelta(minutes=minutesToSnooze)
        )

    def onCloseReminderDialog(self, event, show=True):
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
        notifier = self.settings.get("feature", "notifier")
        if (
            notifier != "Task Coach"
            and notify.AbstractNotifier.get(notifier) is not None
        ):
            # When using Growl/Snarl, this is not necessary. Even when not using Growl, it's
            # annoying as hell. Anyway.
            return
        self.__mainWindowWasHidden = not self.__mainWindow.IsShown()
        if self.__mainWindowWasHidden:
            self.__mainWindow.Show()
        if not self.__mainWindow.IsActive():
            self.__mainWindow.RequestUserAttention()

    def __registerRemindersForTasks(self, tasks):
        for eachTask in tasks:
            if eachTask.reminder() and eachTask.reminder() < date.DateTime():
                self.__registerReminder(eachTask)

    def __removeRemindersForTasks(self, tasks):
        for eachTask in tasks:
            if eachTask in self.__tasksWithReminders:
                self.__removeReminder(eachTask)

    def __registerReminder(self, taskWithReminder):
        reminderDateTime = taskWithReminder.reminder()
        now = date.DateTime.now()
        if reminderDateTime < now:
            reminderDateTime = now + date.TimeDelta(seconds=10)
        job = self.__tasksWithReminders[taskWithReminder] = (
            date.Scheduler().schedule(self.onReminder, reminderDateTime)
        )
        job.setId(self.nextId())

    def __removeReminder(self, taskWithReminder):
        job = self.__tasksWithReminders[taskWithReminder]
        date.Scheduler().unschedule(job)
        del self.__tasksWithReminders[taskWithReminder]
