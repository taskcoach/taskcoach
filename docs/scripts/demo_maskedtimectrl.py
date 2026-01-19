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
app = wx.App()

from taskcoachlib.widgets.maskedtimectrl import (
    DurationCtrl, DurationCtrlVerbose, TimeCtrl, TimeWithSecondsCtrl,
    DateCtrl, DateTimeCombo
)


class DemoFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="DateTime Controls Demo", size=(900, 950))

        panel = wx.Panel(self)
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

        # Instructions
        instructions = wx.StaticText(panel, label=(
            "Dropdown List Behavior:\n"
            "- None: NO dropdown (Up/Down arrows still increment/decrement)\n"
            "- [1,2,3,...]: provides dropdown with those choices\n\n"
            "DateTimeCombo States (checkbox state determined by value):\n"
            "- value=datetime -> checkbox ON, fields editable\n"
            "- value=None -> checkbox OFF, fields disabled\n"
            "- SetEditable(False) -> checkbox ON but disabled, fields greyed (read-only)\n\n"
            "Constructor: DateTimeCombo(parent, value=None, hourChoices=None, minuteChoices=None)\n"
            "- value: datetime.datetime (checked) or None (unchecked)\n"
            "- When unchecked and user checks it, defaults to 'now'\n\n"
            "Layout: GetCheckBox(), GetDateCtrl(), GetTimeCtrl() for flexible table"
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
