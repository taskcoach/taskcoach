#!/usr/bin/env python
"""
Demo app for maskedtimectrl controls.
Shows different dropdown list scenarios: with choices, without choices, and calendar popup.
Also demonstrates DateTimeCombo for flexible table layouts.
"""

import sys
import os
import datetime

# Add taskcoachlib to path (go up two levels from docs/scripts/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import wx first and create App before importing controls
import wx
import wx.adv
app = wx.App()

from taskcoachlib.widgets import maskedtimectrl
from taskcoachlib.widgets.maskedtimectrl import (
    DurationCtrl, DurationCtrlVerbose, TimeCtrl, TimeWithSecondsCtrl,
    DateCtrl, DateTimeCombo, _PopupWindow,
    PopupDismissEvent, _CalendarComboPopup
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

    print("[Wayland] Patch applied. Test dropdown positioning below.")


class DemoFrame(wx.Frame):
    def __init__(self):
        displayH = wx.Display().GetClientArea().height
        super().__init__(None, title="DateTime Controls Demo", size=(900, int(displayH * 0.90)))

        scrolled = wx.ScrolledWindow(self)
        scrolled.SetScrollRate(0, 10)

        panel = scrolled
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        # Title
        title = wx.StaticText(panel, label="maskedtimectrl Demo - Dropdown List Sources")
        title.SetFont(title.GetFont().Bold().Scaled(1.5))
        mainSizer.Add(title, 0, wx.ALL | wx.EXPAND, 15)

        # =============================================================
        # Section 1: Individual Controls
        # =============================================================
        sec1Title = wx.StaticText(panel, label="1. Individual Controls")
        sec1Title.SetFont(sec1Title.GetFont().Bold().Scaled(1.3))
        mainSizer.Add(sec1Title, 0, wx.ALL | wx.EXPAND, 10)

        # Grid for controls
        grid = wx.FlexGridSizer(cols=3, hgap=15, vgap=10)
        grid.AddGrowableCol(2)

        # 1.1 DurationCtrl with NO choices (no dropdowns)
        grid.Add(wx.StaticText(panel, label="1.1 DurationCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.ctrl1 = DurationCtrl(panel, days=1, hours=2, minutes=30)
        grid.Add(self.ctrl1, 0, wx.ALIGN_CENTER_VERTICAL)
        lbl1 = wx.StaticText(panel, label="None = NO dropdowns")
        lbl1.SetForegroundColour(wx.RED)
        grid.Add(lbl1, 0, wx.ALIGN_CENTER_VERTICAL)

        # 1.2 DurationCtrl WITH choices (has dropdowns)
        grid.Add(wx.StaticText(panel, label="1.2 DurationCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.ctrl2 = DurationCtrl(
            panel, days=7, hours=8, minutes=0,
            dayChoices=[1, 7, 14, 21, 28],
            hourChoices=[8, 9, 10, 17, 18],
            minuteChoices=[0, 30]
        )
        grid.Add(self.ctrl2, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="WITH choices: [1,7,14,21,28], [8,9,10,17,18], [0,30]"), 0, wx.ALIGN_CENTER_VERTICAL)

        # 1.3 TimeCtrl with NO choices
        grid.Add(wx.StaticText(panel, label="1.3 TimeCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.ctrl3 = TimeCtrl(panel, hours=14, minutes=30)
        grid.Add(self.ctrl3, 0, wx.ALIGN_CENTER_VERTICAL)
        lbl3 = wx.StaticText(panel, label="None = NO dropdowns")
        lbl3.SetForegroundColour(wx.RED)
        grid.Add(lbl3, 0, wx.ALIGN_CENTER_VERTICAL)

        # 1.4 TimeCtrl WITH choices
        grid.Add(wx.StaticText(panel, label="1.4 TimeCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.ctrl4 = TimeCtrl(
            panel, hours=9, minutes=0,
            hourChoices=[9, 10, 11, 13, 14, 15, 16],
            minuteChoices=[0, 15, 30, 45]
        )
        grid.Add(self.ctrl4, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="WITH choices: [9,10,11,13,14,15,16], [0,15,30,45]"), 0, wx.ALIGN_CENTER_VERTICAL)

        # 1.5 TimeWithSecondsCtrl with NO choices
        grid.Add(wx.StaticText(panel, label="1.5 TimeWithSecondsCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.ctrl5 = TimeWithSecondsCtrl(panel, hours=10, minutes=45, seconds=30)
        grid.Add(self.ctrl5, 0, wx.ALIGN_CENTER_VERTICAL)
        lbl5 = wx.StaticText(panel, label="None = NO dropdowns")
        lbl5.SetForegroundColour(wx.RED)
        grid.Add(lbl5, 0, wx.ALIGN_CENTER_VERTICAL)

        # 1.6 TimeWithSecondsCtrl with MIXED (some with choices, some without)
        grid.Add(wx.StaticText(panel, label="1.6 TimeWithSecondsCtrl:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.ctrl6 = TimeWithSecondsCtrl(
            panel, hours=0, minutes=5, seconds=0,
            hourChoices=[0, 1, 2],
            minuteChoices=None,  # No dropdown for minutes
            secondChoices=[0, 15, 30, 45]
        )
        grid.Add(self.ctrl6, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="MIXED: hours=[0,1,2], mins=None, secs=[0,15,30,45]"), 0, wx.ALIGN_CENTER_VERTICAL)

        # 1.7 DurationCtrlVerbose with choices
        grid.Add(wx.StaticText(panel, label="1.7 DurationCtrlVerbose:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.ctrl7 = DurationCtrlVerbose(
            panel, days=3, hours=5, minutes=45,
            dayChoices=[0, 1, 2, 3, 5, 7, 14, 30],
            hourChoices=list(range(24)),
            minuteChoices=[0, 15, 30, 45]
        )
        grid.Add(self.ctrl7, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(panel, label="WITH choices: [0-30], [0-23], [0,15,30,45]"), 0, wx.ALIGN_CENTER_VERTICAL)

        mainSizer.Add(grid, 0, wx.ALL | wx.EXPAND, 20)

        # Separator
        mainSizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)

        # =====================================================================
        # Section 2: ComboCtrl-Based Date Controls
        # =====================================================================
        dc2Title = wx.StaticText(panel, label="2. ComboCtrl-Based Date Controls")
        dc2Title.SetFont(dc2Title.GetFont().Bold().Scaled(1.3))
        mainSizer.Add(dc2Title, 0, wx.ALL | wx.EXPAND, 10)

        dc2Grid = wx.FlexGridSizer(cols=3, hgap=15, vgap=10)
        dc2Grid.AddGrowableCol(2)

        # 2.0 Standard ComboBox baseline reference
        dc2Grid.Add(wx.StaticText(panel, label="2.0 Baseline:"), 0,
                     wx.ALIGN_CENTER_VERTICAL)
        self.dc2Baseline = wx.ComboBox(panel, value="Standard ComboBox (reference)",
            choices=["Standard ComboBox (reference)", "Option 2", "Option 3"],
            style=wx.CB_DROPDOWN)
        dc2Grid.Add(self.dc2Baseline, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        lbl_baseline = wx.StaticText(panel, label="(standard height baseline)")
        lbl_baseline.SetForegroundColour(wx.Colour(128, 128, 128))
        dc2Grid.Add(lbl_baseline, 0, wx.ALIGN_CENTER_VERTICAL)

        # 2.1 DateCtrl standalone (no checkbox, no time)
        self.dc2EmbedDate = DateCtrl(panel,
            year=2026, month=1, day=31)
        dc2Grid.Add(wx.StaticText(panel, label="2.1 DateCtrl:"), 0,
                     wx.ALIGN_CENTER_VERTICAL)
        dc2Grid.Add(self.dc2EmbedDate, 0, wx.ALIGN_CENTER_VERTICAL)
        lbl_31 = wx.StaticText(panel, label="(standalone DateCtrl, no checkbox/time)")
        lbl_31.SetForegroundColour(wx.Colour(0, 128, 0))
        dc2Grid.Add(lbl_31, 0, wx.ALIGN_CENTER_VERTICAL)

        # 2.2 DateCtrl standalone read-only
        self.dc2EmbedDateRO = DateCtrl(panel,
            year=2026, month=1, day=19)
        self.dc2EmbedDateRO.SetReadOnly(True)
        dc2Grid.Add(wx.StaticText(panel, label="2.2 DateCtrl:"), 0,
                     wx.ALIGN_CENTER_VERTICAL)
        dc2Grid.Add(self.dc2EmbedDateRO, 0, wx.ALIGN_CENTER_VERTICAL)
        lbl_32 = wx.StaticText(panel, label="(standalone DateCtrl, read-only)")
        lbl_32.SetForegroundColour(wx.Colour(128, 128, 128))
        dc2Grid.Add(lbl_32, 0, wx.ALIGN_CENTER_VERTICAL)

        mainSizer.Add(dc2Grid, 0, wx.ALL | wx.EXPAND, 20)

        # --- 3.3-3.6 DateTimeCombo (DateCtrl-based, same API as section 1) ---
        dc3Grid = wx.FlexGridSizer(cols=5, hgap=10, vgap=8)

        # Header row
        dc3Grid.Add(wx.StaticText(panel, label=""), 0)
        dc3Grid.Add(wx.StaticText(panel, label=""), 0)
        hdrDate3 = wx.StaticText(panel, label="Date")
        hdrDate3.SetFont(hdrDate3.GetFont().Bold())
        dc3Grid.Add(hdrDate3, 0, wx.ALIGN_CENTER)
        hdrTime3 = wx.StaticText(panel, label="Time")
        hdrTime3.SetFont(hdrTime3.GetFont().Bold())
        dc3Grid.Add(hdrTime3, 0, wx.ALIGN_CENTER)
        dc3Grid.Add(wx.StaticText(panel, label=""), 0)

        # 2.3 Planned Start (checked, with dropdowns)
        self.dc3PlannedStartCombo = DateTimeCombo(
            panel,
            value=datetime.datetime(2026, 1, 20, 9, 0),
            hourChoices=[8, 9, 10, 11, 12],
            minuteChoices=[0, 15, 30, 45]
        )
        dc3Grid.Add(wx.StaticText(panel, label="2.3 Planned Start:"), 0,
                     wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3PlannedStartCombo.GetCheckBox(), 0, wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3PlannedStartCombo.GetDateCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3PlannedStartCombo.GetTimeCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(wx.StaticText(panel, label="(checked, with time dropdowns)"), 0,
                     wx.ALIGN_CENTER_VERTICAL)

        # 2.4 Due Date (unchecked)
        self.dc3DueDateCombo = DateTimeCombo(
            panel,
            value=None,
            hourChoices=[17, 18, 19, 20, 21],
            minuteChoices=[0, 30]
        )
        dc3Grid.Add(wx.StaticText(panel, label="2.4 Due Date:"), 0,
                     wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3DueDateCombo.GetCheckBox(), 0, wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3DueDateCombo.GetDateCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3DueDateCombo.GetTimeCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(wx.StaticText(panel, label="(unchecked, fields disabled)"), 0,
                     wx.ALIGN_CENTER_VERTICAL)

        # 2.5 Completed (read-only / editable toggle)
        self.dc3CompletedCombo = DateTimeCombo(
            panel,
            value=datetime.datetime(2026, 1, 19, 14, 30)
        )
        self.dc3CompletedCombo.SetReadOnly()
        dc3Grid.Add(wx.StaticText(panel, label="2.5 Completed:"), 0,
                     wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3CompletedCombo.GetCheckBox(), 0, wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3CompletedCombo.GetDateCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3CompletedCombo.GetTimeCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        lbl_dc3_ro = wx.StaticText(panel, label="(Read-Only / Editable - Toggle Button below)")
        lbl_dc3_ro.SetForegroundColour(wx.RED)
        dc3Grid.Add(lbl_dc3_ro, 0, wx.ALIGN_CENTER_VERTICAL)

        # 2.6 Reminder (checked, no time dropdowns)
        self.dc3ReminderCombo = DateTimeCombo(
            panel,
            value=datetime.datetime(2026, 1, 21, 8, 0)
        )
        dc3Grid.Add(wx.StaticText(panel, label="2.6 Reminder:"), 0,
                     wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3ReminderCombo.GetCheckBox(), 0, wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3ReminderCombo.GetDateCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(self.dc3ReminderCombo.GetTimeCtrl(), 0, wx.ALIGN_CENTER_VERTICAL)
        dc3Grid.Add(wx.StaticText(panel, label="(checked, no time dropdowns)"), 0,
                     wx.ALIGN_CENTER_VERTICAL)

        mainSizer.Add(dc3Grid, 0, wx.ALL | wx.EXPAND, 20)

        # Toggle button to test read-only/editable state on 3.5
        dc3ToggleBtn = wx.Button(panel, label="Toggle 2.5 'Completed' Read-Only / Editable")
        dc3ToggleBtn.Bind(wx.EVT_BUTTON, self._onToggleDc3Completed)
        mainSizer.Add(dc3ToggleBtn, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        # Separator
        mainSizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)

        # =====================================================================
        # Section 3: Standard wxPython Date/Calendar Controls
        # =====================================================================
        stdTitle = wx.StaticText(panel, label="3. Standard wxPython Date/Calendar Controls")
        stdTitle.SetFont(stdTitle.GetFont().Bold().Scaled(1.3))
        mainSizer.Add(stdTitle, 0, wx.ALL | wx.EXPAND, 10)

        stdGrid = wx.FlexGridSizer(cols=3, hgap=15, vgap=10)
        stdGrid.AddGrowableCol(2)

        # 3.1 DatePickerCtrl - Native dropdown (week start from locale)
        stdGrid.Add(wx.StaticText(panel, label="3.1 DatePickerCtrl:"), 0,
                     wx.ALIGN_CENTER_VERTICAL)
        self.stdDatePickerDD = wx.adv.DatePickerCtrl(panel, style=wx.adv.DP_DROPDOWN)
        stdGrid.Add(self.stdDatePickerDD, 0, wx.ALIGN_CENTER_VERTICAL)
        stdGrid.Add(wx.StaticText(panel, label="DP_DROPDOWN — native popup, week start from locale"), 0,
                     wx.ALIGN_CENTER_VERTICAL)

        # 3.2 DatePickerCtrlGeneric - locale week start
        stdGrid.Add(wx.StaticText(panel, label="3.2 DatePickerCtrlGeneric:"), 0,
                     wx.ALIGN_CENTER_VERTICAL)
        self.stdDatePickerGen = wx.adv.DatePickerCtrlGeneric(
            panel, style=wx.adv.DP_DROPDOWN)
        stdGrid.Add(self.stdDatePickerGen, 0, wx.ALIGN_CENTER_VERTICAL)
        stdGrid.Add(wx.StaticText(panel, label="Generic popup, week start from locale"), 0,
                     wx.ALIGN_CENTER_VERTICAL)

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
            "Standard wxPython Date Pickers:\n"
            "- DatePickerCtrl (DP_DROPDOWN): Native popup, week start from locale only\n"
            "- DatePickerCtrlGeneric: Generic popup, week start from locale"
        ))
        mainSizer.Add(instructions, 0, wx.ALL | wx.EXPAND, 20)

        panel.SetSizer(mainSizer)
        self.Centre()

    def _onToggleDc3Completed(self, event):
        """Toggle read-only/editable on the 2.5 Completed DateTimeCombo."""
        if self.dc3CompletedCombo.IsEditable():
            self.dc3CompletedCombo.SetReadOnly()
        else:
            self.dc3CompletedCombo.SetEditable()


def main():
    frame = DemoFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
