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
)
from taskcoachlib.config import settings
from taskcoachlib.domain import date
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from taskcoachlib.i18n import _
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
                if hasattr(window, "task") and window.task is task:
                    if window.IsShown():
                        return True
        return False

    def __init__(self, task, task_list, effort_list, parent, *args, **kwargs):
        kwargs["title"] = _("%(name)s reminder - %(task)s") % dict(
            name=meta.name, task=task.subject(recursive=True)
        )
        kwargs["style"] = kwargs.get("style", wx.DEFAULT_DIALOG_STYLE)
        super().__init__(parent, *args, **kwargs)
        self._isFrozen = False
        self.SetIcon(
            icon_catalog.get_wx_icon("nuvola_apps_korganizer", LIST_ICON_SIZE)
        )
        self.task = task
        self.taskList = task_list
        self.effortList = effort_list
        # Self-heal: whatever changes the task, the file or its
        # reminder, the window checks it is still due
        # (docs/UNDO_REDO.md, Windows)
        self.registerObserver(
            self.on_reminder_may_be_gone,
            eventType=self.taskList.removeItemEventType(),
            eventSource=self.taskList,
        )
        for event_type in (
            task.completionDateTimeChangedEventType(),
            task.reminderChangedEventType(),
        ):
            self.registerObserver(
                self.on_reminder_may_be_gone,
                eventType=event_type,
                eventSource=task,
            )
        self.registerObserver(
            self.on_reminder_may_be_gone, eventType="commandhistory.changed"
        )
        self.registerObserver(
            self.on_tracking_changed,
            eventType=task.trackingChangedEventType(),
            eventSource=task,
        )
        self.openTaskAfterClose = self.ignoreSnoozeOption = False

        # Main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Grid for form layout - all controls directly on dialog for proper tabbing
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)

        # Row 1: Task label and buttons
        grid.Add(
            wx.StaticText(self, label=_("Task") + ":"),
            flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT,
        )

        task_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.openTask = wx.Button(
            self, label=self.task.subject(recursive=True)
        )
        self.openTask.Bind(wx.EVT_BUTTON, self.onOpenTask)
        task_button_sizer.Add(self.openTask, flag=wx.ALIGN_CENTER_VERTICAL)
        task_button_sizer.AddSpacer(3)
        self.startTracking = wx.BitmapButton(self)
        self.setTrackingIcon()
        self.startTracking.Bind(wx.EVT_BUTTON, self.onStartOrStopTracking)
        task_button_sizer.Add(
            self.startTracking, flag=wx.ALIGN_CENTER_VERTICAL
        )
        grid.Add(task_button_sizer, flag=wx.EXPAND)

        # Row 2: Reminder date/time label and value
        grid.Add(
            wx.StaticText(self, label=_("Reminder date/time") + ":"),
            flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT,
        )
        grid.Add(
            wx.StaticText(self, label=render.dateTime(self.task.reminder())),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )

        # Row 3: Snooze label and dropdown
        grid.Add(
            wx.StaticText(self, label=_("Snooze") + ":"),
            flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT,
        )
        self.snoozeOptions = wx.Choice(self)
        snooze_times = [0] + settings.view.snoozetimes
        default_snooze_time = settings.view.defaultsnoozetime
        selection_index = 1
        for minutes, label in date.snoozeChoices:
            if minutes in snooze_times:
                self.snoozeOptions.Append(
                    label, date.TimeDelta(minutes=minutes)
                )
                if minutes == default_snooze_time:
                    selection_index = self.snoozeOptions.Count - 1
        self.snoozeOptions.SetSelection(
            min(selection_index, self.snoozeOptions.Count - 1)
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
            settings.view.replacedefaultsnoozetime
        )
        grid.Add(self.replaceDefaultSnoozeTime, flag=wx.EXPAND)

        main_sizer.Add(grid, proportion=1, flag=wx.ALL | wx.EXPAND, border=10)

        # Button row
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.okButton = wx.Button(self, wx.ID_OK, _("OK"))
        self.okButton.Bind(wx.EVT_BUTTON, self.onOK)
        self.markCompleted = wx.Button(self, label=_("Mark task completed"))
        self.markCompleted.Bind(wx.EVT_BUTTON, self.onMarkTaskCompleted)
        if self.task.completed():
            self.markCompleted.Disable()

        # Right-align buttons (standard UX)
        button_sizer.AddStretchSpacer()
        button_sizer.Add(self.okButton, flag=wx.RIGHT, border=5)
        button_sizer.Add(self.markCompleted)

        main_sizer.Add(button_sizer, flag=wx.ALL | wx.EXPAND, border=10)

        self.SetSizer(main_sizer)
        self.Bind(wx.EVT_CLOSE, self.on_close)

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
        self._freeze_dialog()
        # Play reminder sound
        from taskcoachlib import sounds

        sounds.play(settings.feature.reminder_sound)

    def _freeze_dialog(self):
        """Freeze dialog to prevent accidental actions."""
        self._isFrozen = True
        self.Disable()
        patterns.later.call(
            self, self.FREEZE_DURATION_MS, self._unfreeze_dialog
        )

    def _unfreeze_dialog(self):
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

    def on_tracking_changed(self, event):  # pylint: disable=W0613
        self.setTrackingIcon()

    def setTrackingIcon(self):
        icon_id = (
            "taskcoach_actions_clock_stop_icon"
            if self.task.isBeingTracked()
            else "nuvola_apps_clock"
        )
        self.startTracking.SetBitmapLabel(
            icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE)
        )

    def onMarkTaskCompleted(self, event):
        self.ignoreSnoozeOption = True
        self.Close()
        command.MarkCompletedCommand(self.taskList, [self.task]).do()

    def on_reminder_may_be_gone(self, event):  # pylint: disable=W0613
        patterns.later.soon(self, self.__close_unless_due)

    def is_due(self):
        """Whether the reminder that opened the window still stands: its
        task in the file, not completed, its reminder not moved past
        now (snoozed, changed or cleared)."""
        return (
            any(each is self.task for each in self.taskList)
            and not self.task.completed()
            and self.task.reminder() <= date.Now()
        )

    def __close_unless_due(self):
        """Close quietly, changing nothing: no snooze."""
        if self.is_due():
            return
        self.ignoreSnoozeOption = True
        self._isFrozen = False  # A freeze guards the user's clicks only
        self.Close()

    def on_close(self, event):
        # Block closing during freeze period to prevent accidental dismissal
        if self._isFrozen:
            event.Veto()
            return

        # Stop listening, to prevent callbacks on the destroyed dialog
        self.removeObserver(self.on_reminder_may_be_gone)
        self.removeObserver(self.on_tracking_changed)

        event.Skip()
        # Safety check - verify controls exist before accessing
        if (
            not hasattr(self, "replaceDefaultSnoozeTime")
            or self.replaceDefaultSnoozeTime is None
        ):
            self.removeInstance()
            return
        replace_default_snooze_time = self.replaceDefaultSnoozeTime.GetValue()
        if replace_default_snooze_time:
            selection = self.snoozeOptions.Selection
            minutes = self.snoozeOptions.GetClientData(selection).minutes()
            settings.view.defaultsnoozetime = int(minutes)
        settings.view.replacedefaultsnoozetime = replace_default_snooze_time
        self.removeInstance()

    def onOK(self, event):
        event.Skip()
        self.Close()
