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

from taskcoachlib import (
    meta,
    patterns,
    command,
    render,
    operating_system,
    speak,
)
from taskcoachlib.domain import date
from taskcoachlib.i18n import _
from pubsub import pub
from wx.lib import sized_controls
import subprocess
import wx


class ReminderDialog(patterns.Observer, sized_controls.SizedDialog):
    def __init__(self, task, taskList, effortList, settings, *args, **kwargs):
        kwargs["title"] = _("%(name)s reminder - %(task)s") % dict(
            name=meta.name, task=task.subject(recursive=True)
        )
        super().__init__(*args, **kwargs)
        self.SetIcon(
            wx.ArtProvider.GetIcon("taskcoach", wx.ART_FRAME_ICON, (16, 16))
        )
        self.task = task
        self.taskList = taskList
        self.effortList = effortList
        self.settings = settings
        self.registerObserver(
            self.onTaskRemoved,
            eventType=self.taskList.removeItemEventType(),
            eventSource=self.taskList,
        )
        pub.subscribe(
            self.onTaskCompletionDateChanged,
            task.completionDateTimeChangedEventType(),
        )
        pub.subscribe(self.onTrackingChanged, task.trackingChangedEventType())
        self.openTaskAfterClose = self.ignoreSnoozeOption = False
        pane = self.GetContentsPane()
        pane.SetSizerType("form")

        wx.StaticText(pane, label=_("Task") + ":")
        panel = wx.Panel(pane)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.openTask = wx.Button(
            panel, label=self.task.subject(recursive=True)
        )
        self.openTask.Bind(wx.EVT_BUTTON, self.onOpenTask)
        sizer.Add(self.openTask, flag=wx.ALIGN_CENTER_VERTICAL)
        self.startTracking = wx.BitmapButton(panel)
        self.setTrackingIcon()
        self.startTracking.Bind(wx.EVT_BUTTON, self.onStartOrStopTracking)
        sizer.Add((3, -1), flag=wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.startTracking, flag=wx.ALIGN_CENTER_VERTICAL)
        panel.SetSizerAndFit(sizer)

        for label in (
            _("Reminder date/time") + ":",
            render.dateTime(self.task.reminder()),
            _("Snooze") + ":",
        ):
            wx.StaticText(pane, label=label)

        self.snoozeOptions = wx.ComboBox(pane, style=wx.CB_READONLY)
        snoozeTimesUserWantsToSee = [0] + self.settings.getlist(
            "view", "snoozetimes"
        )
        defaultSnoozeTime = self.settings.getint("view", "defaultsnoozetime")
        # Use the 1st non-zero option if we don't find the last snooze time:
        selectionIndex = 1
        # pylint: disable=E1101
        for minutes, label in date.snoozeChoices:
            if minutes in snoozeTimesUserWantsToSee:
                self.snoozeOptions.Append(
                    label, date.TimeDelta(minutes=minutes)
                )
                if minutes == defaultSnoozeTime:
                    selectionIndex = self.snoozeOptions.Count - 1
        self.snoozeOptions.SetSelection(
            min(selectionIndex, self.snoozeOptions.Count - 1)
        )

        wx.StaticText(pane, label="")
        self.replaceDefaultSnoozeTime = wx.CheckBox(
            pane,
            label=_(
                "Also make this the default snooze time for future "
                "reminders"
            ),
        )
        self.replaceDefaultSnoozeTime.SetValue(
            self.settings.getboolean("view", "replacedefaultsnoozetime")
        )

        buttonSizer = self.CreateStdDialogButtonSizer(wx.OK)
        self.markCompleted = wx.Button(self, label=_("Mark task completed"))
        self.markCompleted.Bind(wx.EVT_BUTTON, self.onMarkTaskCompleted)
        if self.task.completed():
            self.markCompleted.Disable()
        buttonSizer.Add(self.markCompleted, flag=wx.ALIGN_CENTER_VERTICAL)
        self.SetButtonSizer(buttonSizer)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Bind(wx.EVT_BUTTON, self.onOK, id=self.GetAffirmativeId())
        self.Fit()
        self.RequestUserAttention()
        if self.settings.getboolean("feature", "sayreminder"):
            speak.Speaker().say('"%s: %s"' % (_("Reminder"), task.subject()))

    def onOpenTask(self, event):  # pylint: disable=W0613
        self.openTaskAfterClose = True
        self.Close()

    def onStartOrStopTracking(self, event):  # pylint: disable=W0613
        if self.task.isBeingTracked():
            command.StopEffortCommand(self.effortList).do()
        else:
            command.StartEffortCommand(self.taskList, [self.task]).do()
        self.setTrackingIcon()

    def onTrackingChanged(self, newValue, sender):  # pylint: disable=W0613
        self.setTrackingIcon()

    def setTrackingIcon(self):
        icon = (
            "clock_stop_icon" if self.task.isBeingTracked() else "clock_icon"
        )
        self.startTracking.SetBitmapLabel(
            wx.ArtProvider.GetBitmap(icon, wx.ART_TOOLBAR, (16, 16))
        )

    def onMarkTaskCompleted(self, event):  # pylint: disable=W0613
        self.ignoreSnoozeOption = True
        self.Close()
        command.MarkCompletedCommand(self.taskList, [self.task]).do()

    def onTaskRemoved(self, event):
        if self.task in list(event.values()):
            self.Close()

    def onTaskCompletionDateChanged(
        self, newValue, sender
    ):  # pylint: disable=W0613
        if sender == self.task:
            if self.task.completed():
                self.Close()
            else:
                self.markCompleted.Enable()

    def onClose(self, event):
        event.Skip()
        replace_default_snooze_time = self.replaceDefaultSnoozeTime.GetValue()
        if replace_default_snooze_time:
            # pylint: disable=E1101
            selection = self.snoozeOptions.Selection
            minutes = self.snoozeOptions.GetClientData(selection).minutes()
            self.settings.set("view", "defaultsnoozetime", str(int(minutes)))
        self.settings.setboolean(
            "view", "replacedefaultsnoozetime", replace_default_snooze_time
        )
        self.removeInstance()

    def onOK(self, event):
        event.Skip()
        self.Close()
