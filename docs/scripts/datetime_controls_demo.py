#!/usr/bin/env python
"""
Demo app for maskedtimectrl controls.
Shows different dropdown list scenarios: with choices, without choices, and calendar popup.
Also demonstrates DateTimeCombo for flexible table layouts.
"""

import sys
import os

# Add taskcoachlib to path (go up two levels from docs/scripts/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import wx first and create App before importing controls
import wx
import wx.adv
app = wx.App()

from taskcoachlib.widgets import maskedtimectrl
from taskcoachlib.widgets.maskedtimectrl import (
    DurationCtrl, DurationCtrlVerbose, TimeCtrl, TimeWithSecondsCtrl,
    DateCtrl, DateTimeCombo, _PopupWindow, PopupDismissEvent
)

# =============================================================================
# Wayland test patch: Replace _PopupWindow base class with wx.PopupWindow
# on Wayland so dropdowns use xdg_popup (compositor-positioned) instead of
# wx.Dialog (xdg_toplevel, which ignores Move()/SetPosition()).
# =============================================================================
def _is_wayland():
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"

if _is_wayland():
    print("[Wayland] Patching _PopupWindow to use wx.PopupWindow (xdg_popup)")

    # wx.PopupWindow is a real C++ type — we can't just swap __bases__ on
    # _PopupWindow(wx.Dialog) because the C++ object type is fixed at
    # construction. Instead, create a proper wx.PopupWindow subclass with
    # the same interface and swap it as the base of the popup subclasses.

    class _WaylandPopupWindow(wx.PopupWindow):
        """wx.PopupWindow-based replacement for _PopupWindow on Wayland."""

        def __init__(self, *args, **kwargs):
            # Accept and ignore style/title kwargs from wx.Dialog interface
            kwargs.pop('style', None)
            kwargs.pop('title', None)
            parent = args[0] if args else kwargs.pop('parent', None)
            wx.PopupWindow.__init__(self, parent, style=wx.BORDER_NONE)

            style = wx.BORDER_NONE
            if "__WXMSW__" in wx.PlatformInfo:
                style |= wx.WANTS_CHARS
            self.__interior = wx.Panel(self, style=style)
            self._dismissed = False

            self.__interior.Bind(wx.EVT_CHAR, self._onChar)

            self.Fill(self.__interior)

            sizer = wx.BoxSizer()
            sizer.Add(self.__interior, 1, wx.EXPAND)
            self.SetSizer(sizer)

        def interior(self):
            return self.__interior

        def Fill(self, interior):
            pass

        def Popup(self, position):
            self.Position(position, (0, 0))
            self.Show()

        def Dismiss(self):
            if self._dismissed:
                return
            self._dismissed = True
            self.Hide()
            try:
                interior = self.interior()
                if interior:
                    interior.Unbind(wx.EVT_CHAR)
                    interior.Unbind(wx.EVT_PAINT)
                    interior.Unbind(wx.EVT_LEFT_UP)
            except RuntimeError:
                pass
            self.ProcessEvent(PopupDismissEvent(self))
            wx.CallLater(100, self._safeDestroy)

        def _safeDestroy(self):
            try:
                if self:
                    self.Destroy()
            except RuntimeError:
                pass

        def _onChar(self, event):
            if not self.HandleKey(event):
                self.GetParent().OnChar(event)

        def HandleKey(self, event):
            return False

    # wxPython bakes C++ type info into class objects at creation time, so
    # __bases__ swap doesn't work. We must create entirely new classes using
    # type() that inherit from _WaylandPopupWindow and copy all methods from
    # the original subclasses.

    _OrigChoicesPopup = maskedtimectrl._ChoicesPopup
    _OrigCalendarPopup = maskedtimectrl._CalendarPopup

    # Collect all methods/attrs defined directly on each original class
    def _get_class_attrs(cls):
        attrs = {}
        for name in cls.__dict__:
            if name != '__dict__' and name != '__weakref__':
                attrs[name] = cls.__dict__[name]
        return attrs

    maskedtimectrl._ChoicesPopup = type(
        '_ChoicesPopup',
        (_WaylandPopupWindow,),
        _get_class_attrs(_OrigChoicesPopup)
    )

    maskedtimectrl._CalendarPopup = type(
        '_CalendarPopup',
        (_WaylandPopupWindow,),
        _get_class_attrs(_OrigCalendarPopup)
    )

    print("[Wayland] Patch applied. Test dropdown positioning below.")


# =============================================================================
# Custom date picker with configurable week start day.
# Uses PopupTransientWindow + GenericCalendarCtrl to bypass the
# CAL_MONDAY_FIRST / DP_SPIN flag collision (both are 0x1).
# PopupTransientWindow is Wayland-safe (compositor-positioned xdg_popup).
# =============================================================================

class _CalendarPopupTransient(wx.PopupTransientWindow):
    """Popup containing a GenericCalendarCtrl."""

    def __init__(self, parent, dt, cal_style):
        super().__init__(parent, wx.BORDER_SIMPLE)
        panel = wx.Panel(self)
        self._calendar = wx.adv.GenericCalendarCtrl(
            panel, date=dt, style=cal_style)
        self._calendar.Bind(wx.adv.EVT_CALENDAR, self._onDateSelected)
        sizer = wx.BoxSizer()
        sizer.Add(self._calendar, 1, wx.EXPAND)
        panel.SetSizer(sizer)
        sizer.Fit(panel)
        self.SetSize(panel.GetBestSize())

    def _onDateSelected(self, event):
        parent = self.GetParent()
        if isinstance(parent, _CalendarDatePicker):
            parent._setDate(self._calendar.GetDate())
        self.Dismiss()


class _CalendarDatePicker(wx.Panel):
    """Date field with a dropdown button that opens a GenericCalendarCtrl popup.

    Accepts cal_style to pass CAL_MONDAY_FIRST or CAL_SUNDAY_FIRST directly
    to the calendar, avoiding the flag collision with DP_SPIN.
    """

    def __init__(self, parent, cal_style=0):
        super().__init__(parent)
        self._cal_style = cal_style
        self._date = wx.DateTime.Now()

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._text = wx.TextCtrl(self, style=wx.TE_READONLY, size=(120, -1))
        self._btn = wx.Button(self, label="\u25BC", size=(24, -1))
        sizer.Add(self._text, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self._btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 2)
        self.SetSizer(sizer)

        self._btn.Bind(wx.EVT_BUTTON, self._onDropdown)
        self._text.Bind(wx.EVT_LEFT_DOWN, self._onDropdown)
        self._updateDisplay()

    def _updateDisplay(self):
        self._text.SetValue(self._date.Format("%Y-%m-%d"))

    def _setDate(self, dt):
        self._date = dt
        self._updateDisplay()

    def _onDropdown(self, event):
        popup = _CalendarPopupTransient(self, self._date, self._cal_style)
        pos = self.ClientToScreen(wx.Point(0, self.GetSize().height))
        popup.SetPosition(pos)
        popup.Popup()

    def GetValue(self):
        return self._date

    def SetValue(self, dt):
        self._date = dt
        self._updateDisplay()


class DemoFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="DateTime Controls Demo", size=(900, 1100))

        scrolled = wx.ScrolledWindow(self)
        scrolled.SetScrollRate(0, 10)

        panel = scrolled
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        # Title
        title = wx.StaticText(panel, label="maskedtimectrl Demo - Dropdown List Sources")
        title.SetFont(title.GetFont().Bold().Scaled(1.5))
        mainSizer.Add(title, 0, wx.ALL | wx.ALIGN_CENTER, 15)

        # Grid for controls
        grid = wx.FlexGridSizer(cols=3, hgap=15, vgap=10)
        grid.AddGrowableCol(2)

        # 1. DurationCtrl with NO choices (no dropdowns)
        grid.Add(wx.StaticText(panel, label="DurationCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.ctrl1 = DurationCtrl(panel, days=1, hours=2, minutes=30)
        grid.Add(self.ctrl1, 0, wx.ALIGN_CENTER_VERTICAL)
        lbl1 = wx.StaticText(panel, label="None = NO dropdowns")
        lbl1.SetForegroundColour(wx.RED)
        grid.Add(lbl1, 0, wx.ALIGN_CENTER_VERTICAL)

        # 2. DurationCtrl WITH choices (has dropdowns)
        grid.Add(wx.StaticText(panel, label="DurationCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.ctrl2 = DurationCtrl(
            panel, days=7, hours=8, minutes=0,
            dayChoices=[1, 7, 14, 21, 28],
            hourChoices=[8, 9, 10, 17, 18],
            minuteChoices=[0, 30]
        )
        grid.Add(self.ctrl2, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="WITH choices: [1,7,14,21,28], [8,9,10,17,18], [0,30]"), 0, wx.ALIGN_CENTER_VERTICAL)

        # 3. TimeCtrl with NO choices
        grid.Add(wx.StaticText(panel, label="TimeCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.ctrl3 = TimeCtrl(panel, hours=14, minutes=30)
        grid.Add(self.ctrl3, 0, wx.ALIGN_CENTER_VERTICAL)
        lbl3 = wx.StaticText(panel, label="None = NO dropdowns")
        lbl3.SetForegroundColour(wx.RED)
        grid.Add(lbl3, 0, wx.ALIGN_CENTER_VERTICAL)

        # 4. TimeCtrl WITH choices
        grid.Add(wx.StaticText(panel, label="TimeCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.ctrl4 = TimeCtrl(
            panel, hours=9, minutes=0,
            hourChoices=[9, 10, 11, 13, 14, 15, 16],
            minuteChoices=[0, 15, 30, 45]
        )
        grid.Add(self.ctrl4, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="WITH choices: [9,10,11,13,14,15,16], [0,15,30,45]"), 0, wx.ALIGN_CENTER_VERTICAL)

        # 5. TimeWithSecondsCtrl with NO choices
        grid.Add(wx.StaticText(panel, label="TimeWithSecondsCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.ctrl5 = TimeWithSecondsCtrl(panel, hours=10, minutes=45, seconds=30)
        grid.Add(self.ctrl5, 0, wx.ALIGN_CENTER_VERTICAL)
        lbl5 = wx.StaticText(panel, label="None = NO dropdowns")
        lbl5.SetForegroundColour(wx.RED)
        grid.Add(lbl5, 0, wx.ALIGN_CENTER_VERTICAL)

        # 6. TimeWithSecondsCtrl with MIXED (some with choices, some without)
        grid.Add(wx.StaticText(panel, label="TimeWithSecondsCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.ctrl6 = TimeWithSecondsCtrl(
            panel, hours=0, minutes=5, seconds=0,
            hourChoices=[0, 1, 2],
            minuteChoices=None,  # No dropdown for minutes
            secondChoices=[0, 15, 30, 45]
        )
        grid.Add(self.ctrl6, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="MIXED: hours=[0,1,2], mins=None, secs=[0,15,30,45]"), 0, wx.ALIGN_CENTER_VERTICAL)

        # 7. DurationCtrlVerbose with choices
        grid.Add(wx.StaticText(panel, label="DurationCtrlVerbose:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.ctrl7 = DurationCtrlVerbose(
            panel, days=3, hours=5, minutes=45,
            dayChoices=[0, 1, 2, 3, 5, 7, 14, 30],
            hourChoices=list(range(24)),
            minuteChoices=[0, 15, 30, 45]
        )
        grid.Add(self.ctrl7, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="WITH choices: [0-30], [0-23], [0,15,30,45]"), 0, wx.ALIGN_CENTER_VERTICAL)

        # 8. DateCtrl (calendar popup)
        grid.Add(wx.StaticText(panel, label="DateCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.ctrl8 = DateCtrl(panel)
        grid.Add(self.ctrl8, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="calendar popup (click or Enter)"), 0, wx.ALIGN_CENTER_VERTICAL)

        mainSizer.Add(grid, 0, wx.ALL | wx.EXPAND, 20)

        # Separator
        mainSizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)

        # DateTimeCombo Section
        comboTitle = wx.StaticText(panel, label="DateTimeCombo - Flexible Table Layout")
        comboTitle.SetFont(comboTitle.GetFont().Bold().Scaled(1.3))
        mainSizer.Add(comboTitle, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        # Create a table grid showing aligned DateTimeCombos
        # 5 columns: Label, Checkbox, Date, Time, Description
        comboGrid = wx.FlexGridSizer(cols=5, hgap=10, vgap=8)

        # Header row
        comboGrid.Add(wx.StaticText(panel, label=""), 0)
        comboGrid.Add(wx.StaticText(panel, label=""), 0)
        hdrDate = wx.StaticText(panel, label="Date")
        hdrDate.SetFont(hdrDate.GetFont().Bold())
        comboGrid.Add(hdrDate, 0, wx.ALIGN_CENTER)
        hdrTime = wx.StaticText(panel, label="Time")
        hdrTime.SetFont(hdrTime.GetFont().Bold())
        comboGrid.Add(hdrTime, 0, wx.ALIGN_CENTER)
        comboGrid.Add(wx.StaticText(panel, label=""), 0)

        # Row 1: Planned Start (value=datetime means checked)
        import datetime
        self.plannedStartCombo = DateTimeCombo(
            panel,
            value=datetime.datetime(2026, 1, 20, 9, 0),
            hourChoices=[8, 9, 10, 11, 12],
            minuteChoices=[0, 15, 30, 45]
        )
        comboGrid.Add(wx.StaticText(panel, label="Planned Start:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        comboGrid.Add(self.plannedStartCombo.GetCheckBox(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(self.plannedStartCombo.GetDateCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(self.plannedStartCombo.GetTimeCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(wx.StaticText(panel, label="(value=datetime -> checked)"), 0, wx.ALIGN_CENTER_VERTICAL)

        # Row 2: Due Date (value=None means unchecked)
        self.dueDateCombo = DateTimeCombo(
            panel,
            value=None,  # None = unchecked, defaults to "now" when user checks it
            hourChoices=[17, 18, 19, 20, 21],
            minuteChoices=[0, 30]
        )
        comboGrid.Add(wx.StaticText(panel, label="Due Date:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        comboGrid.Add(self.dueDateCombo.GetCheckBox(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(self.dueDateCombo.GetDateCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(self.dueDateCombo.GetTimeCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(wx.StaticText(panel, label="(value=None -> unchecked)"), 0, wx.ALIGN_CENTER_VERTICAL)

        # Row 3: Actual Start (another checked example)
        self.actualStartCombo = DateTimeCombo(
            panel,
            value=datetime.datetime(2026, 6, 15, 9, 30)
        )
        comboGrid.Add(wx.StaticText(panel, label="Actual Start:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        comboGrid.Add(self.actualStartCombo.GetCheckBox(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(self.actualStartCombo.GetDateCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(self.actualStartCombo.GetTimeCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(wx.StaticText(panel, label="(value=2026-06-15 09:30)"), 0, wx.ALIGN_CENTER_VERTICAL)

        # Row 4: Completed (inactive/read-only - values visible but greyed)
        self.completedCombo = DateTimeCombo(
            panel,
            value=datetime.datetime(2026, 1, 19, 14, 30)
        )
        self.completedCombo.SetEditable(False)  # Inactive: values visible but greyed
        comboGrid.Add(wx.StaticText(panel, label="Completed:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        comboGrid.Add(self.completedCombo.GetCheckBox(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(self.completedCombo.GetDateCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(self.completedCombo.GetTimeCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        lbl_inactive = wx.StaticText(panel, label="(INACTIVE - values greyed, not editable)")
        lbl_inactive.SetForegroundColour(wx.RED)
        comboGrid.Add(lbl_inactive, 0, wx.ALIGN_CENTER_VERTICAL)

        # Row 5: Reminder (enabled, no time dropdowns)
        self.reminderCombo = DateTimeCombo(
            panel,
            value=datetime.datetime(2026, 1, 21, 8, 0)
            # No hourChoices/minuteChoices = no dropdowns
        )
        comboGrid.Add(wx.StaticText(panel, label="Reminder:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        comboGrid.Add(self.reminderCombo.GetCheckBox(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(self.reminderCombo.GetDateCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(self.reminderCombo.GetTimeCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        comboGrid.Add(wx.StaticText(panel, label="(no time dropdowns)"), 0, wx.ALIGN_CENTER_VERTICAL)

        mainSizer.Add(comboGrid, 0, wx.ALL | wx.EXPAND, 20)

        # Toggle button to test inactive/editable state
        toggleBtn = wx.Button(panel, label="Toggle 'Completed' Editable State")
        toggleBtn.Bind(wx.EVT_BUTTON, self._onToggleCompleted)
        mainSizer.Add(toggleBtn, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        # Separator
        mainSizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)

        # =====================================================================
        # Section 3: Standard wxPython Date/Calendar Controls
        # =====================================================================
        stdTitle = wx.StaticText(panel, label="Standard wxPython Date/Calendar Controls")
        stdTitle.SetFont(stdTitle.GetFont().Bold().Scaled(1.3))
        mainSizer.Add(stdTitle, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        stdGrid = wx.FlexGridSizer(cols=3, hgap=15, vgap=10)
        stdGrid.AddGrowableCol(2)

        # 1. DatePickerCtrl - Native dropdown (week start from locale)
        stdGrid.Add(wx.StaticText(panel, label="DatePickerCtrl:"), 0,
                     wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.stdDatePickerDD = wx.adv.DatePickerCtrl(panel, style=wx.adv.DP_DROPDOWN)
        stdGrid.Add(self.stdDatePickerDD, 0, wx.ALIGN_CENTER_VERTICAL)
        stdGrid.Add(wx.StaticText(panel, label="DP_DROPDOWN — native popup, week start from locale"), 0,
                     wx.ALIGN_CENTER_VERTICAL)

        # 2. DatePickerCtrlGeneric - locale week start
        stdGrid.Add(wx.StaticText(panel, label="DatePickerCtrlGeneric:"), 0,
                     wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.stdDatePickerGen = wx.adv.DatePickerCtrlGeneric(
            panel, style=wx.adv.DP_DROPDOWN)
        stdGrid.Add(self.stdDatePickerGen, 0, wx.ALIGN_CENTER_VERTICAL)
        stdGrid.Add(wx.StaticText(panel, label="Generic popup, week start from locale"), 0,
                     wx.ALIGN_CENTER_VERTICAL)

        # 3. DatePickerCtrlGeneric - Sunday first
        stdGrid.Add(wx.StaticText(panel, label="DatePickerCtrlGeneric:"), 0,
                     wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.stdDatePickerGenSun = wx.adv.DatePickerCtrlGeneric(
            panel, style=wx.adv.DP_DROPDOWN | wx.adv.CAL_SUNDAY_FIRST)
        stdGrid.Add(self.stdDatePickerGenSun, 0, wx.ALIGN_CENTER_VERTICAL)
        lbl_dpg_sun = wx.StaticText(panel, label="CAL_SUNDAY_FIRST — generic popup, Sunday start")
        lbl_dpg_sun.SetForegroundColour(wx.Colour(0, 128, 0))
        stdGrid.Add(lbl_dpg_sun, 0, wx.ALIGN_CENTER_VERTICAL)

        # 4. Custom Monday-first date picker
        # CAL_MONDAY_FIRST (0x1) == DP_SPIN (0x1) — flag collision prevents
        # passing it to DatePickerCtrlGeneric. Workaround: custom widget using
        # PopupTransientWindow + GenericCalendarCtrl(CAL_MONDAY_FIRST).
        # PopupTransientWindow is Wayland-safe (compositor-positioned xdg_popup).
        stdGrid.Add(wx.StaticText(panel, label="Custom (Monday):"), 0,
                     wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.stdDatePickerMon = _CalendarDatePicker(
            panel, cal_style=wx.adv.CAL_MONDAY_FIRST | wx.adv.CAL_SHOW_HOLIDAYS)
        stdGrid.Add(self.stdDatePickerMon, 0, wx.ALIGN_CENTER_VERTICAL)
        lbl_mon = wx.StaticText(
            panel, label="CAL_MONDAY_FIRST — custom PopupTransientWindow (Wayland-safe)")
        lbl_mon.SetForegroundColour(wx.Colour(0, 128, 0))
        stdGrid.Add(lbl_mon, 0, wx.ALIGN_CENTER_VERTICAL)

        # 5. Custom Sunday-first date picker (same technique)
        stdGrid.Add(wx.StaticText(panel, label="Custom (Sunday):"), 0,
                     wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.stdDatePickerSun = _CalendarDatePicker(
            panel, cal_style=wx.adv.CAL_SUNDAY_FIRST | wx.adv.CAL_SHOW_HOLIDAYS)
        stdGrid.Add(self.stdDatePickerSun, 0, wx.ALIGN_CENTER_VERTICAL)
        lbl_sun = wx.StaticText(
            panel, label="CAL_SUNDAY_FIRST — custom PopupTransientWindow (Wayland-safe)")
        lbl_sun.SetForegroundColour(wx.Colour(0, 128, 0))
        stdGrid.Add(lbl_sun, 0, wx.ALIGN_CENTER_VERTICAL)

        mainSizer.Add(stdGrid, 0, wx.ALL | wx.EXPAND, 20)

        # Instructions
        instructions = wx.StaticText(panel, label=(
            "Dropdown List Behavior:\n"
            "- None: NO dropdown (Up/Down arrows still increment/decrement)\n"
            "- [1,2,3,...]: provides dropdown with those choices\n\n"
            "DateTimeCombo States (checkbox state determined by value):\n"
            "- value=datetime -> checkbox ON, fields editable\n"
            "- value=None -> checkbox OFF, fields disabled\n"
            "- SetEditable(False) -> checkbox ON but disabled, fields greyed (read-only)\n\n"
            "Standard wxPython Date Pickers (all with calendar dropdown):\n"
            "- DatePickerCtrl (DP_DROPDOWN): Native popup, week start from locale only\n"
            "- DatePickerCtrlGeneric: Generic popup, supports CAL_SUNDAY_FIRST\n"
            "  CAL_MONDAY_FIRST (0x1) collides with DP_SPIN (0x1) — can't be passed\n"
            "- Custom picker: PopupTransientWindow + GenericCalendarCtrl\n"
            "  Supports CAL_MONDAY_FIRST / CAL_SUNDAY_FIRST, Wayland-safe (xdg_popup)"
        ))
        mainSizer.Add(instructions, 0, wx.ALL | wx.EXPAND, 20)

        panel.SetSizer(mainSizer)
        self.Centre()

    def _onToggleCompleted(self, event):
        """Toggle the editable state of the 'Completed' DateTimeCombo."""
        currentState = self.completedCombo.IsEditable()
        self.completedCombo.SetEditable(not currentState)


def main():
    frame = DemoFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
