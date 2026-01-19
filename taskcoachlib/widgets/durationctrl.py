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
Duration control with DDDd HH:MM format and preset dropdown.

Provides a control for entering/displaying durations with:
- Subfield navigation (days, hours, minutes) via arrow keys
- Preset dropdown for quick selection
- Configurable preset list
- Visual style matching existing time controls (Entry-based)
"""

import wx
import datetime

from taskcoachlib.i18n import _
from taskcoachlib.thirdparty import smartdatetimectrl as sdtc


# Event types
wxEVT_DURATION_CHANGE = wx.NewEventType()
EVT_DURATION_CHANGE = wx.PyEventBinder(wxEVT_DURATION_CHANGE)

wxEVT_DURATION_CHOICES_CHANGE = wx.NewEventType()
EVT_DURATION_CHOICES_CHANGE = wx.PyEventBinder(wxEVT_DURATION_CHOICES_CHANGE)


class DurationChangeEvent(wx.PyCommandEvent):
    """Event fired when duration value changes."""

    def __init__(self, owner, value):
        super().__init__(wxEVT_DURATION_CHANGE)
        self.__value = value
        self.SetEventObject(owner)

    def Clone(self):
        return DurationChangeEvent(self.GetEventObject(), self.__value)

    def GetValue(self):
        return self.__value


class DurationChoicesChangedEvent(wx.PyCommandEvent):
    """Event fired when preset choices are modified."""

    def __init__(self, owner, value):
        super().__init__(wxEVT_DURATION_CHOICES_CHANGE)
        self.__value = value
        self.SetEventObject(owner)

    def Clone(self):
        return DurationChoicesChangedEvent(self.GetEventObject(), self.__value)

    def GetValue(self):
        return self.__value


class DurationDayField(sdtc.NumericField):
    """Field for duration days (0-999), 3 digits wide."""
    pass


class DurationEntry(sdtc.Entry):
    """Duration entry widget with DDDd HH:MM format, reusing existing Entry system.

    Uses:
    - New 'D' format character for days (3-digit, 0-999)
    - Existing 'H' format character from TimeEntry for hours (2-digit, 0-23)
    - Existing 'M' format character from TimeEntry for minutes (2-digit, 0-59)
    """

    # Only register D for days - reuse existing H and M from TimeEntry
    class DayFormatCharacter(sdtc.SingleFormatCharacter):
        character = "D"
        valueName = "day"

        def createField(self, *args, **kwargs):
            kwargs["width"] = 3
            # Note: min/max validation handled in ValidateChange, not field constructor
            return DurationDayField(*args, **kwargs)

    # Register only the D format character (H and M already exist from TimeEntry)
    sdtc.Entry.addFormat(DayFormatCharacter)

    def __init__(self, parent, days=0, hours=0, minutes=0, readonly=False,
                 minuteDelta=15, **kwargs):
        # Use format pattern "DDD\d HH:MM" (\d escapes 'd' as literal display)
        # D = our new day format, H and M = existing TimeEntry formats
        kwargs["format"] = "DDD\\d HH:MM"
        kwargs["day"] = days
        kwargs["hour"] = hours
        kwargs["minute"] = minutes

        self.__minuteDelta = minuteDelta

        super().__init__(parent, **kwargs)

        self.__readonly = readonly
        if readonly:
            self.Enable(False)
        else:
            # Enable dropdown choices by default (like DateTimeCtrl does for TimeEntry)
            self.EnableChoices(True)

    def GetDuration(self):
        """Get duration as timedelta."""
        return datetime.timedelta(
            days=self.Field("day").GetValue(),
            hours=self.Field("hour").GetValue(),
            minutes=self.Field("minute").GetValue()
        )

    def SetDuration(self, duration, notify=False):
        """Set duration from timedelta."""
        if duration is None:
            duration = datetime.timedelta()

        total_seconds = int(duration.total_seconds())
        days = total_seconds // 86400
        remaining = total_seconds % 86400
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60

        self.Field("day").SetValue(days, notify=False)
        self.Field("hour").SetValue(hours, notify=False)
        self.Field("minute").SetValue(minutes, notify=False)

        self.Refresh()

        if notify:
            self.ProcessEvent(DurationChangeEvent(self, self.GetDuration()))

    def ValidateChange(self, field, value):
        """Handle field value changes and fire events."""
        fieldName = None
        for name in ["day", "hour", "minute"]:
            if field == self.Field(name):
                fieldName = name
                break

        if fieldName == "day":
            if value < 0 or value > 999:
                wx.Bell()
                return None
        elif fieldName == "hour":
            if value < 0 or value > 23:
                wx.Bell()
                return None
        elif fieldName == "minute":
            if value < 0 or value > 59:
                wx.Bell()
                return None

        field.SetValue(value, notify=False)
        self.Refresh()
        self.ProcessEvent(DurationChangeEvent(self, self.GetDuration()))
        return None

    def ValidateIncrement(self, field, value):
        """Handle up arrow - wrap around at limits."""
        return self._handleIncDec(field, 1)

    def ValidateDecrement(self, field, value):
        """Handle down arrow - wrap around at limits."""
        return self._handleIncDec(field, -1)

    def _handleIncDec(self, field, delta):
        """Common increment/decrement logic with wrapping."""
        for name, minVal, maxVal in [("day", 0, 999), ("hour", 0, 23), ("minute", 0, 59)]:
            if field == self.Field(name):
                newVal = field.GetValue() + delta
                if newVal < minVal:
                    newVal = maxVal
                elif newVal > maxVal:
                    newVal = minVal
                field.SetValue(newVal, notify=False)
                self.Refresh()
                self.ProcessEvent(DurationChangeEvent(self, self.GetDuration()))
                return newVal
        return None

    def Enable(self, enable=True):
        super().Enable(enable)
        self.__readonly = not enable

    def Disable(self):
        self.Enable(False)

    def EnableChoices(self, enabled=True):
        """Enable dropdown choices for fields, similar to TimeEntry."""
        if enabled:
            # Days: 0-999 (show common values)
            self.Field("day").SetChoices(
                [("%d" % day, day) for day in [0, 1, 2, 3, 5, 7, 14, 30, 60, 90]]
            )
            # Hours: 0-23
            self.Field("hour").SetChoices(
                [("%d" % hour, hour) for hour in range(0, 24)]
            )
            # Minutes: based on minuteDelta setting
            self.Field("minute").SetChoices(
                [("%d" % minute, minute) for minute in range(0, 60, self.__minuteDelta)]
            )
        else:
            self.Field("day").SetChoices(None)
            self.Field("hour").SetChoices(None)
            self.Field("minute").SetChoices(None)
            self.DismissPopup()


class DurationCtrl(wx.Panel):
    """Duration control with DDDd HH:MM entry and preset dropdown button."""

    DEFAULT_UNITS = [
        (_("Minute(s)"), 60),
        (_("Hour(s)"), 3600),
        (_("Day(s)"), 86400),
        (_("Week(s)"), 7 * 86400),
    ]

    def __init__(self, parent, days=0, hours=0, minutes=0,
                 readonly=False, showPresets=True, units=None,
                 minuteDelta=15, **kwargs):
        super().__init__(parent, **kwargs)

        self.__units = units or self.DEFAULT_UNITS
        self.__choices = []  # List of timedelta presets
        self.__popup = None
        self.__readonly = readonly

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.__entry = DurationEntry(self, days, hours, minutes, readonly,
                                     minuteDelta=minuteDelta)
        sizer.Add(self.__entry, 1, wx.EXPAND)

        if showPresets and not readonly:
            self.__presetBtn = wx.BitmapButton(
                self, wx.ID_ANY,
                wx.ArtProvider.GetBitmap(wx.ART_LIST_VIEW, wx.ART_BUTTON, (16, 16))
            )
            self.__presetBtn.SetToolTip(_("Select from presets"))
            self.__presetBtn.Bind(wx.EVT_BUTTON, self.__OnShowPresets)
            sizer.Add(self.__presetBtn, 0, wx.LEFT | wx.ALIGN_CENTER, 2)
        else:
            self.__presetBtn = None

        self.SetSizer(sizer)

        # Forward events from entry
        self.__entry.Bind(EVT_DURATION_CHANGE, self.__OnEntryChange)

    def __OnEntryChange(self, event):
        # Re-emit from this control
        self.ProcessEvent(DurationChangeEvent(self, event.GetValue()))

    def __OnShowPresets(self, event):
        if self.__popup is not None:
            return

        self.__popup = _PresetPopup(self, self.__choices, self.__units)

        # Position below the control
        pos = self.ClientToScreen(wx.Point(0, self.GetSize().height))
        self.__popup.Position(pos, (0, 0))
        self.__popup.Popup()

        self.__popup.Bind(wx.EVT_WINDOW_DESTROY, self.__OnPopupDestroy)

    def __OnPopupDestroy(self, event):
        self.__popup = None
        event.Skip()

    def OnChoicesChanged(self, popup):
        """Called by popup when choices are modified."""
        self.__choices = popup.GetChoices()
        # Fire event for external listeners
        choices_str = popup.SaveChoices()
        self.ProcessEvent(DurationChoicesChangedEvent(self, choices_str))

    def LoadChoices(self, choices_str):
        """Load choices from comma-separated minutes string."""
        if not choices_str:
            self.__choices = []
            return

        self.__choices = []
        for minutes_str in choices_str.split(","):
            try:
                minutes = int(minutes_str.strip())
                self.__choices.append(datetime.timedelta(minutes=minutes))
            except ValueError:
                pass

        self.__choices.sort(key=lambda d: d.total_seconds())

    def GetDuration(self):
        return self.__entry.GetDuration()

    def SetDuration(self, duration, notify=False):
        self.__entry.SetDuration(duration, notify)

    def Enable(self, enable=True):
        super().Enable(enable)
        self.__entry.Enable(enable)
        self.__readonly = not enable
        if self.__presetBtn:
            self.__presetBtn.Enable(enable)

    def Disable(self):
        self.Enable(False)


class _PresetPopup(wx.PopupTransientWindow):
    """Popup window for duration presets."""

    def __init__(self, parent, choices, units):
        super().__init__(parent, wx.BORDER_SIMPLE)

        self.__parent = parent
        self.__choices = list(choices)  # List of timedelta
        self.__units = units

        panel = wx.Panel(self)
        self.__sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(self.__sizer)

        self.__panel = panel
        self.__Populate()

        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

    def __Populate(self):
        # Clear existing
        self.__sizer.Clear(True)

        # Add controls row
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.__amountCtrl = wx.SpinCtrl(self.__panel, wx.ID_ANY, "1", min=1, max=999, size=(60, -1))
        hbox.Add(self.__amountCtrl, 0, wx.ALL, 2)

        self.__unitCtrl = wx.Choice(self.__panel, wx.ID_ANY)
        for name, seconds in self.__units:
            idx = self.__unitCtrl.Append(name)
            self.__unitCtrl.SetClientData(idx, seconds)
        self.__unitCtrl.SetSelection(0)
        hbox.Add(self.__unitCtrl, 1, wx.ALL | wx.EXPAND, 2)

        self.__addBtn = wx.Button(self.__panel, wx.ID_ANY, _("Add"))
        self.__addBtn.SetBitmap(
            wx.ArtProvider.GetBitmap("symbol_plus_icon", wx.ART_BUTTON, (16, 16))
        )
        self.__addBtn.Bind(wx.EVT_BUTTON, self.OnAdd)
        hbox.Add(self.__addBtn, 0, wx.ALL, 2)

        self.__sizer.Add(hbox, 0, wx.EXPAND)

        # Add separator
        self.__sizer.Add(wx.StaticLine(self.__panel), 0, wx.EXPAND | wx.ALL, 2)

        # Add preset items
        self.__itemButtons = []
        for delta in sorted(self.__choices, key=lambda d: d.total_seconds()):
            self.__addPresetRow(delta)

        self.__panel.Layout()
        self.Fit()

    def __addPresetRow(self, delta):
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        # Preset button
        label = self.__formatDelta(delta)
        btn = wx.Button(self.__panel, wx.ID_ANY, label, style=wx.BU_LEFT)
        btn.delta = delta
        btn.Bind(wx.EVT_BUTTON, self.OnChoose)
        hbox.Add(btn, 1, wx.EXPAND | wx.ALL, 1)

        # Delete button (red)
        delBtn = wx.Button(self.__panel, wx.ID_ANY, "-", size=(24, -1))
        delBtn.SetForegroundColour(wx.Colour(180, 0, 0))
        delBtn.delta = delta
        delBtn.Bind(wx.EVT_BUTTON, self.OnDelete)
        hbox.Add(delBtn, 0, wx.ALL, 1)

        self.__sizer.Add(hbox, 0, wx.EXPAND)
        self.__itemButtons.append((btn, delBtn))

    def __formatDelta(self, delta):
        """Format timedelta as human-readable string."""
        total_seconds = int(delta.total_seconds())

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        parts = []
        if days > 0:
            if days == 1:
                parts.append(_("1 day"))
            elif days == 7:
                parts.append(_("1 week"))
            elif days % 7 == 0:
                weeks = days // 7
                parts.append(_("%d weeks") % weeks)
            else:
                parts.append(_("%d days") % days)
        if hours > 0:
            if hours == 1:
                parts.append(_("1 hour"))
            else:
                parts.append(_("%d hours") % hours)
        if minutes > 0:
            if minutes == 1:
                parts.append(_("1 minute"))
            else:
                parts.append(_("%d minutes") % minutes)

        return ", ".join(parts) if parts else _("0 minutes")

    def OnChoose(self, event):
        btn = event.GetEventObject()
        self.__parent.SetDuration(btn.delta, notify=True)
        self.Dismiss()

    def OnAdd(self, event):
        amount = self.__amountCtrl.GetValue()
        unit_seconds = self.__unitCtrl.GetClientData(self.__unitCtrl.GetSelection())

        new_delta = datetime.timedelta(seconds=amount * unit_seconds)

        # Check for duplicates
        for existing in self.__choices:
            if abs(existing.total_seconds() - new_delta.total_seconds()) < 1:
                return  # Already exists

        self.__choices.append(new_delta)
        self.__choices.sort(key=lambda d: d.total_seconds())

        # Rebuild UI
        self.__sizer.Clear(True)
        self.__Populate()

        # Notify parent
        self.__parent.OnChoicesChanged(self)

    def OnDelete(self, event):
        btn = event.GetEventObject()
        delta_to_remove = btn.delta

        self.__choices = [d for d in self.__choices
                         if abs(d.total_seconds() - delta_to_remove.total_seconds()) >= 1]

        # Rebuild UI
        self.__sizer.Clear(True)
        self.__Populate()

        # Notify parent
        self.__parent.OnChoicesChanged(self)

    def OnKeyDown(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Dismiss()
        else:
            event.Skip()

    def SaveChoices(self):
        """Return choices as comma-separated minutes string."""
        return ",".join(str(int(d.total_seconds() / 60)) for d in self.__choices)

    def GetChoices(self):
        return self.__choices
