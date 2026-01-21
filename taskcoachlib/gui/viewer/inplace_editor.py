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
In place editors for viewers.
"""  # pylint: disable=W0105

import wx
from wx.lib.agw import hypertreelist
from taskcoachlib import widgets
from taskcoachlib.domain import date
from taskcoachlib.gui.dialog.entry import (
    get_suggested_hour_choices,
    get_suggested_minute_choices,
)


class KillFocusAcceptsEditsMixin(object):
    """Mixin class to let in place editors accept changes whenever the user
    clicks outside the edit control instead of cancelling the changes."""

    def StopEditing(self):
        try:
            if self.__has_focus():
                # User hit Escape
                super().StopEditing()
            else:
                # User clicked outside edit window
                self.AcceptChanges()
                self.Finish()
        except RuntimeError:
            pass

    def __has_focus(self):
        """Return whether this control has the focus.

        Also returns True if a popup (calendar or dropdown) is open from any
        child control, since the user is still interacting with the editor.
        """
        def window_and_all_children(window):
            window_and_children = [window]
            for child in window.GetChildren():
                window_and_children.extend(window_and_all_children(child))
            return window_and_children

        if wx.Window.FindFocus() in window_and_all_children(self):
            return True

        # Check if any DateTimeCombo has an open popup
        if hasattr(self, '_dateTimeCombo') and self._dateTimeCombo.HasOpenPopup():
            return True

        return False


class SubjectCtrl(KillFocusAcceptsEditsMixin, hypertreelist.EditTextCtrl):
    """Single line inline control for editing item subjects."""

    pass


class DescriptionCtrl(KillFocusAcceptsEditsMixin, hypertreelist.EditTextCtrl):
    """Multiline inline text control for editing item descriptions."""

    def __init__(self, *args, **kwargs):
        kwargs["style"] = kwargs.get("style", 0) | wx.TE_MULTILINE
        super().__init__(*args, **kwargs)


class EscapeKeyMixin(object):
    """Mixin class for text(like) controls to properly handle the Escape key.
    The inheriting class needs to bind to the event handler. For example:
    self._spinCtrl.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)"""

    def OnKeyDown(self, event):
        keyCode = event.GetKeyCode()
        if keyCode == wx.WXK_ESCAPE:
            self.StopEditing()
        elif (
            keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER)
            and not event.ShiftDown()
        ):
            # Notify the owner about the changes
            self.AcceptChanges()
            # Even if vetoed, close the control (consistent with MSW)
            wx.CallAfter(self.Finish)
        else:
            event.Skip()


class _SpinCtrl(
    EscapeKeyMixin,
    KillFocusAcceptsEditsMixin,
    hypertreelist.EditCtrl,
    widgets.SpinCtrl,
):
    """Base spin control class."""

    def __init__(
        self, parent, wxId, item, column, owner, value, *args, **kwargs
    ):
        super().__init__(
            parent, wxId, item, column, owner, str(value), *args, **kwargs
        )
        self._textCtrl.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)


class PriorityCtrl(_SpinCtrl):
    """Spin control for priority. Since priorities can be any negative or
    positive integer we don't need to set an allowed range."""

    pass


class PercentageCtrl(_SpinCtrl):
    """Spin control for percentages."""

    def __init__(self, *args, **kwargs):
        super().__init__(min=0, max=100, *args, **kwargs)


class Panel(wx.Panel):
    """Panel class for inline controls that need to be put into a panel."""

    def __init__(
        self, parent, wxId, value, *args, **kwargs
    ):  # pylint: disable=W0613
        # Don't pass the value argument to the wx.Panel since it doesn't take
        # a value argument
        super().__init__(parent, wxId, *args, **kwargs)

    def makeSizer(self, control):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(control, flag=wx.EXPAND)
        self.SetSizerAndFit(sizer)


class BudgetCtrl(
    EscapeKeyMixin, KillFocusAcceptsEditsMixin, hypertreelist.EditCtrl, Panel
):
    """Masked inline text control for editing budgets:
    <hours>:<minutes>:<seconds>."""

    def __init__(self, parent, wxId, item, column, owner, value):
        super().__init__(parent, wxId, item, column, owner)
        hours, minutes, seconds = value.hoursMinutesSeconds()
        # Can't inherit from TimeDeltaCtrl because we need to override GetValue,
        # so we use composition instead
        self.__timeDeltaCtrl = widgets.masked.TimeDeltaCtrl(
            self, hours, minutes, seconds
        )
        self.__timeDeltaCtrl.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.makeSizer(self.__timeDeltaCtrl)

    def GetValue(self):
        return date.parseTimeDelta(self.__timeDeltaCtrl.GetValue())


class AmountCtrl(
    EscapeKeyMixin, KillFocusAcceptsEditsMixin, hypertreelist.EditCtrl, Panel
):
    """Masked inline text control for editing amounts (floats >= 0)."""

    def __init__(self, parent, wxId, item, column, owner, value):
        super().__init__(parent, wxId, item, column, owner)
        self.__floatCtrl = widgets.masked.AmountCtrl(self, value)
        self.__floatCtrl.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.makeSizer(self.__floatCtrl)

    def GetValue(self):
        return self.__floatCtrl.GetValue()


class DateTimeCtrl(
    EscapeKeyMixin, KillFocusAcceptsEditsMixin, hypertreelist.EditCtrl, Panel
):
    """Inline date and time picker control using DateTimeCombo."""

    def __init__(self, parent, wxId, item, column, owner, value, **kwargs):
        # TODO: The "relative" preset offset dropdown (showing durations like
        # "+1 day", "+1 week" relative to planned start) is not yet implemented
        # in DateTimeCombo. This would need to be added as a duration field
        # with duration presets. For now, we ignore the relative parameter.
        kwargs.pop("relative", False)
        kwargs.pop("startDateTime", None)
        super().__init__(parent, wxId, item, column, owner)
        settings = kwargs["settings"]

        # Convert empty DateTime to None for DateTimeCombo (unchecked state)
        combo_value = None if value == date.DateTime() else value

        self._dateTimeCombo = widgets.DateTimeCombo(
            self,
            value=combo_value,
            hourChoices=lambda: get_suggested_hour_choices(settings),
            minuteChoices=lambda: get_suggested_minute_choices(settings),
        )

        # Get widgets directly (they're children of self) - don't use CreateRowPanel
        # which creates a nested panel that breaks tab sequence and focus handling
        self._checkbox = self._dateTimeCombo.GetCheckBox()
        self._dateCtrl = self._dateTimeCombo.GetDateCtrl()
        self._timeCtrl = self._dateTimeCombo.GetTimeCtrl()

        # Tab order for cycling within the editor
        self._tabOrder = [self._checkbox, self._dateCtrl, self._timeCtrl]

        # Arrange horizontally
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self._checkbox, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        sizer.Add(self._dateCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        sizer.Add(self._timeCtrl, 0, wx.ALIGN_CENTER_VERTICAL)
        self.SetSizerAndFit(sizer)

        # Bind key events - handle Tab ourselves to stay within the editor
        self._checkbox.Bind(wx.EVT_KEY_DOWN, self._onKeyDown)
        self._dateCtrl.Bind(wx.EVT_KEY_DOWN, self._onKeyDown)
        self._timeCtrl.Bind(wx.EVT_KEY_DOWN, self._onKeyDown)

        # Bind focus loss events to detect click-away (save on click outside)
        self._checkbox.Bind(wx.EVT_KILL_FOCUS, self._onChildKillFocus)
        self._dateCtrl.Bind(wx.EVT_KILL_FOCUS, self._onChildKillFocus)
        self._timeCtrl.Bind(wx.EVT_KILL_FOCUS, self._onChildKillFocus)

    def _onKeyDown(self, event):
        """Handle key events, including Tab for internal navigation."""
        keyCode = event.GetKeyCode()
        if keyCode == wx.WXK_TAB:
            # Navigate within the editor's controls, don't let it escape
            self._navigateTab(event.ShiftDown())
        elif keyCode == wx.WXK_ESCAPE:
            self.StopEditing()
        elif keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and not event.ShiftDown():
            self.AcceptChanges()
            wx.CallAfter(self.Finish)
        else:
            event.Skip()

    def _navigateTab(self, backward=False):
        """Navigate Tab within the editor's child controls."""
        focused = wx.Window.FindFocus()
        try:
            idx = self._tabOrder.index(focused)
        except ValueError:
            # Focus not on a known control, go to first
            idx = -1 if not backward else len(self._tabOrder)

        if backward:
            idx -= 1
            if idx < 0:
                idx = len(self._tabOrder) - 1
        else:
            idx += 1
            if idx >= len(self._tabOrder):
                idx = 0

        self._tabOrder[idx].SetFocus()

    def _onChildKillFocus(self, event):
        """Handle focus loss from child controls."""
        event.Skip()  # Allow default processing
        # Check focus after it settles (allows tab between children)
        wx.CallAfter(self._maybeAcceptAndClose)

    def _maybeAcceptAndClose(self):
        """Accept changes and close if focus has left the control entirely."""
        try:
            if not self._hasFocusOrPopup():
                self.AcceptChanges()
                self.Finish()
        except RuntimeError:
            pass  # Control may be destroyed

    def _hasFocusOrPopup(self):
        """Check if focus is in this control or a popup is open."""
        def window_and_all_children(window):
            result = [window]
            for child in window.GetChildren():
                result.extend(window_and_all_children(child))
            return result

        if wx.Window.FindFocus() in window_and_all_children(self):
            return True
        if self._dateTimeCombo.HasOpenPopup():
            return True
        return False

    def GetValue(self):
        value = self._dateTimeCombo.GetValue()
        # Convert None back to empty DateTime for domain compatibility
        return value if value is not None else date.DateTime()
