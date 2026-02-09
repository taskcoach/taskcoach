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
    speak,
)
from taskcoachlib.domain import date
from taskcoachlib.i18n import _
from pubsub import pub
import wx


class ReminderDialog(patterns.Observer, wx.Dialog):
    """
    Reminder dialog with proper tab navigation.

    Uses wx.GridBagSizer for layout to ensure all controls are tabbable.
    Tab order: OK, then left-to-right, top-to-bottom.
    """
    FREEZE_DURATION_MS = 2000  # Freeze duration in milliseconds

    @classmethod
    def isOpenFor(cls, task):
        """Check if a reminder dialog is already open for this task.

        SSOT: Checks actual windows, not a tracking dict.
        Used by ReminderController to avoid duplicate dialogs.
        """
        for window in wx.GetTopLevelWindows():
            if isinstance(window, cls):
                if hasattr(window, 'task') and window.task is task:
                    if window.IsShown():
                        return True
        return False

    def __init__(self, task, taskList, effortList, settings, parent, *args, **kwargs):
        kwargs["title"] = _("%(name)s reminder - %(task)s") % dict(
            name=meta.name, task=task.subject(recursive=True)
        )
        kwargs["style"] = kwargs.get("style", wx.DEFAULT_DIALOG_STYLE)
        super().__init__(parent, *args, **kwargs)
        self._isFrozen = False
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

        # Main sizer
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        # Grid for form layout - all controls directly on dialog for proper tabbing
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)

        # Row 1: Task label and buttons
        grid.Add(wx.StaticText(self, label=_("Task") + ":"),
                 flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)

        taskButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.openTask = wx.Button(self, label=self.task.subject(recursive=True))
        self.openTask.Bind(wx.EVT_BUTTON, self.onOpenTask)
        taskButtonSizer.Add(self.openTask, flag=wx.ALIGN_CENTER_VERTICAL)
        taskButtonSizer.AddSpacer(3)
        self.startTracking = wx.BitmapButton(self)
        self.setTrackingIcon()
        self.startTracking.Bind(wx.EVT_BUTTON, self.onStartOrStopTracking)
        taskButtonSizer.Add(self.startTracking, flag=wx.ALIGN_CENTER_VERTICAL)
        grid.Add(taskButtonSizer, flag=wx.EXPAND)

        # Row 2: Reminder date/time label and value
        grid.Add(wx.StaticText(self, label=_("Reminder date/time") + ":"),
                 flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        grid.Add(wx.StaticText(self, label=render.dateTime(self.task.reminder())),
                 flag=wx.ALIGN_CENTER_VERTICAL)

        # Row 3: Snooze label and dropdown
        grid.Add(wx.StaticText(self, label=_("Snooze") + ":"),
                 flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.snoozeOptions = wx.Choice(self)
        snoozeTimesUserWantsToSee = [0] + self.settings.getlist(
            "view", "snoozetimes"
        )
        defaultSnoozeTime = self.settings.getint("view", "defaultsnoozetime")
        selectionIndex = 1
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
        grid.Add(self.snoozeOptions, flag=wx.ALIGN_CENTER_VERTICAL)

        # Row 4: Empty label and checkbox
        grid.Add(wx.StaticText(self, label=""), flag=wx.ALIGN_RIGHT)
        self.replaceDefaultSnoozeTime = wx.CheckBox(
            self,
            label=_(
                "Also make this the default snooze time for future "
                "reminders"
            ),
        )
        self.replaceDefaultSnoozeTime.SetValue(
            self.settings.getboolean("view", "replacedefaultsnoozetime")
        )
        grid.Add(self.replaceDefaultSnoozeTime, flag=wx.EXPAND)

        mainSizer.Add(grid, proportion=1, flag=wx.ALL | wx.EXPAND, border=10)

        # Button row
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.okButton = wx.Button(self, wx.ID_OK, _("OK"))
        self.okButton.Bind(wx.EVT_BUTTON, self.onOK)
        self.markCompleted = wx.Button(self, label=_("Mark task completed"))
        self.markCompleted.Bind(wx.EVT_BUTTON, self.onMarkTaskCompleted)
        if self.task.completed():
            self.markCompleted.Disable()

        # Right-align buttons (standard UX)
        buttonSizer.AddStretchSpacer()
        buttonSizer.Add(self.okButton, flag=wx.RIGHT, border=5)
        buttonSizer.Add(self.markCompleted)

        mainSizer.Add(buttonSizer, flag=wx.ALL | wx.EXPAND, border=10)

        self.SetSizer(mainSizer)
        self.Bind(wx.EVT_CLOSE, self.onClose)

        # Set tab order: OK first, then left-to-right, top-to-bottom
        # This ensures first Tab after unfreeze goes to OK button
        # Order: okButton -> markCompleted -> openTask -> startTracking ->
        #        snoozeOptions -> replaceDefaultSnoozeTime
        self.markCompleted.MoveAfterInTabOrder(self.okButton)
        self.openTask.MoveAfterInTabOrder(self.markCompleted)
        self.startTracking.MoveAfterInTabOrder(self.openTask)
        self.snoozeOptions.MoveAfterInTabOrder(self.startTracking)
        self.replaceDefaultSnoozeTime.MoveAfterInTabOrder(self.snoozeOptions)

        self.Fit()
        self.Layout()
        # Ensure minimum size
        size = self.GetSize()
        if size.height < 200:
            self.SetSize(size.width, 200)
            self.Layout()

        self.RequestUserAttention()
        self._freezeDialog()
        if self.settings.getboolean("feature", "sayreminder"):
            speak.Speaker().say('"%s: %s"' % (_("Reminder"), task.subject()))

    def _freezeDialog(self):
        """Freeze dialog to prevent accidental actions."""
        self._isFrozen = True
        self.Disable()
        self._freezeTimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._onFreezeTimer, self._freezeTimer)
        self._freezeTimer.StartOnce(self.FREEZE_DURATION_MS)

    def _onFreezeTimer(self, event):
        """Timer event handler to unfreeze dialog."""
        self._unfreezeDialog()

    def _unfreezeDialog(self):
        """Unfreeze dialog and re-enable interaction."""
        if not self._isFrozen:
            return
        self._isFrozen = False
        self.Enable()
        # Do NOT set focus on any control - let focus remain on background
        # This prevents accidental actions from keyboard input

    def onOpenTask(self, event):
        self.openTaskAfterClose = True
        self.Close()

    def onStartOrStopTracking(self, event):
        if self.task.isBeingTracked():
            command.StopEffortCommand(self.effortList).do()
        else:
            command.StartEffortCommand(self.taskList, [self.task]).do()
        self.setTrackingIcon()

    def onTrackingChanged(self, newValue, sender):
        self.setTrackingIcon()

    def setTrackingIcon(self):
        icon = (
            "clock_stop_icon" if self.task.isBeingTracked() else "clock_icon"
        )
        self.startTracking.SetBitmapLabel(
            wx.ArtProvider.GetBitmap(icon, wx.ART_TOOLBAR, (16, 16))
        )

    def onMarkTaskCompleted(self, event):
        self.ignoreSnoozeOption = True
        self.Close()
        command.MarkCompletedCommand(self.taskList, [self.task]).do()

    def onTaskRemoved(self, event):
        if self.task in list(event.values()):
            self.Close()

    def onTaskCompletionDateChanged(self, newValue, sender):
        if sender == self.task:
            if self.task.completed():
                self.Close()
            else:
                self.markCompleted.Enable()

    def onClose(self, event):
        # Block closing during freeze period to prevent accidental dismissal
        if self._isFrozen:
            event.Veto()
            return

        # Stop the freeze timer to prevent callbacks on destroyed dialog
        if hasattr(self, '_freezeTimer') and self._freezeTimer:
            self._freezeTimer.Stop()
            self._freezeTimer = None

        # Unsubscribe from pubsub events to prevent callbacks on destroyed dialog
        try:
            pub.unsubscribe(
                self.onTaskCompletionDateChanged,
                self.task.completionDateTimeChangedEventType(),
            )
        except Exception:
            pass
        try:
            pub.unsubscribe(self.onTrackingChanged, self.task.trackingChangedEventType())
        except Exception:
            pass

        event.Skip()
        # Safety check - verify controls exist before accessing
        if not hasattr(self, 'replaceDefaultSnoozeTime') or self.replaceDefaultSnoozeTime is None:
            self.removeInstance()
            return
        replace_default_snooze_time = self.replaceDefaultSnoozeTime.GetValue()
        if replace_default_snooze_time:
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
