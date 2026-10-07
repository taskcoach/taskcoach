"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 Rob McMullen <rob.mcmullen@gmail.com>
Copyright (C) 2008 Carl Zmola <zmola@acm.org>

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

from taskcoachlib import widgets, operating_system
from taskcoachlib.config import settings
from taskcoachlib.domain import date
from taskcoachlib.i18n import _
from wx.lib import combotreebox, newevent
import wx
import wx.adv

# Helper functions to get suggested time choices from preferences
# These are used by both entry.py and editor.py for datetime controls
#
# For dynamic updates when preferences change, pass as lambda:
#   hour_choices=get_suggested_hour_choices


def get_suggested_hour_choices(override=None):
    """Get hour choices list for dropdowns.

    Args:
        override: Optional override value:
            - None (default): Use preferences (efforthourstart to efforthourend)
            - list: Use that specific list of hours
            - False: Return None (no dropdown)

    Returns:
        List of hour choices, or None if disabled

    Note: In 12-hour time format mode, returns 1-12 instead of working hours,
    since the AM/PM is controlled separately by the period field.
    """
    if override is False:
        return None
    if override is not None:
        return override
    # Check time format - in 12-hour mode, return 1-12
    from taskcoachlib.widgets.maskedtimectrl import getEffectiveTimeFormat

    if getEffectiveTimeFormat() == "12":
        return list(range(1, 13))
    # 24-hour mode: use working hours from preferences
    start = settings.view.efforthourstart
    end = settings.view.efforthourend
    # Cap at 23 to handle legacy settings that may have sentinel value 24
    return list(range(start, min(end + 1, 24)))


def get_suggested_minute_choices(override=None):
    """Get minute choices list for dropdowns.

    Args:
        override: Optional override value:
            - None (default): Use preferences (based on effortminuteinterval)
            - list: Use that specific list of minutes
            - False: Return None (no dropdown)

    Returns:
        List of minute choices, or None if disabled
    """
    if override is False:
        return None
    if override is not None:
        return override
    interval = settings.view.effortminuteinterval
    return list(range(0, 60, interval))


def get_suggested_second_choices(override=None):
    """Get second choices list for dropdowns.

    Args:
        override: Optional override value:
            - None (default): Use preferences (based on effortsecondinterval)
            - list: Use that specific list of seconds
            - False: Return None (no dropdown)

    Returns:
        List of second choices, or None if disabled
    """
    if override is False:
        return None
    if override is not None:
        return override
    interval = settings.view.effortsecondinterval
    return list(range(0, 60, interval))


class AmountEntry(widgets.PanelWithBoxSizer):
    def __init__(self, parent, amount=0.0, readonly=False, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._entry = self.createEntry(amount)
        if readonly:
            self._entry.Disable()
            # Set grey background to clearly indicate non-editable
            self._entry.SetBackgroundColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
            )
        self.add(self._entry)
        self.fit()

    def createEntry(self, amount):
        return widgets.CurrencyCtrl(self, amount)

    def NavigateBook(self, event):
        self.GetParent().NavigateBook(not event.ShiftDown())
        return True

    def GetValue(self):
        return self._entry.GetValue()

    def SetValue(self, value):
        self._entry.SetValue(value)

    def Bind(self, *args, **kwargs):  # pylint: disable=W0221
        self._entry.Bind(*args, **kwargs)


PercentageEntryEvent, EVT_PERCENTAGEENTRY = newevent.NewEvent()


class PercentageEntry(widgets.PanelWithBoxSizer):
    def __init__(self, parent, percentage=0, *args, **kwargs):
        kwargs["orientation"] = wx.HORIZONTAL
        super().__init__(parent, *args, **kwargs)
        self._entry = self._createSpinCtrl(percentage)
        self._slider = self._createSlider(percentage)
        self.add(self._entry, flag=wx.ALIGN_LEFT, proportion=0)
        self.add((5, -1), flag=wx.ALIGN_LEFT, proportion=0)
        self.add(self._slider, flag=wx.ALL | wx.EXPAND, proportion=1)
        self.fit()

    def _createSlider(self, percentage):
        slider = wx.Slider(
            self,
            value=int(percentage),
            style=wx.SL_AUTOTICKS,
            minValue=0,
            maxValue=100,
            size=(150, -1),
        )
        slider.SetTickFreq(25)
        slider.Bind(wx.EVT_SCROLL, self.onSliderScroll)
        return slider

    def _createSpinCtrl(self, percentage):
        entry = widgets.SpinCtrl(
            self,
            value=percentage,
            min=0,
            max=100,
            size=(60 if operating_system.isMac() else 50, -1),
        )
        for event_type in wx.EVT_SPINCTRL, wx.EVT_KILL_FOCUS:
            entry.Bind(event_type, self.onSpin)
        return entry

    def GetValue(self):
        return self._entry.GetValue()

    def SetValue(self, value):
        self._entry.SetValue(value)
        self._slider.SetValue(value)

    def onSliderScroll(self, event):  # pylint: disable=W0613
        self.syncControl(self._entry, self._slider)

    def onSpin(self, event):  # pylint: disable=W0613
        self.syncControl(self._slider, self._entry)

    def syncControl(self, control_to_write, control_to_read):
        value = control_to_read.GetValue()
        # Prevent potential endless loop by checking that we really need to set
        # the value:
        if control_to_write.GetValue() != value:
            control_to_write.SetValue(value)
        wx.PostEvent(self, PercentageEntryEvent())


FontEntryEvent, EVT_FONTENTRY = newevent.NewEvent()


class FontEntry(widgets.PanelWithBoxSizer):
    def __init__(
        self,
        parent,
        current_font,
        current_color,
        current_bg_color=None,
        *args,
        **kwargs
    ):
        kwargs["orientation"] = wx.HORIZONTAL
        super().__init__(parent, *args, **kwargs)
        self._fontCheckBox = self._create_check_box(current_font)
        self._fontPicker = self._create_font_picker(
            current_font, current_color, current_bg_color
        )
        self.add(
            self._fontCheckBox,
            flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            border=15,
            proportion=0,
        )
        self.add(
            self._fontPicker,
            flag=wx.ALIGN_CENTER_VERTICAL,
            border=0,
            proportion=1,
        )
        self.fitNoMinSize()

    def _create_check_box(self, current_font):
        check_box = wx.CheckBox(self, label="")
        check_box.SetValue(current_font is not None)
        check_box.Bind(wx.EVT_CHECKBOX, self.onChecked)
        return check_box

    def _create_font_picker(
        self, current_font, current_color, current_bg_color
    ):
        default_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        picker = widgets.FontPickerCtrl(
            self,
            font=current_font or default_font,
            colour=current_color,
            bgColour=current_bg_color,
        )
        picker.Bind(wx.EVT_FONTPICKER_CHANGED, self.onFontPicked)
        return picker

    def setEffectiveFont(self, font):
        """Set the effective font to display when unchecked."""
        if font is None:
            return
        self._effectiveFont = font
        if not self._fontCheckBox.IsChecked():
            self._fontPicker.SetSelectedFont(self._effectiveFont)

    def onChecked(self, event):
        event.Skip()
        checked = self._fontCheckBox.IsChecked()
        if (
            not checked
            and hasattr(self, "_effectiveFont")
            and self._effectiveFont
        ):
            self._fontPicker.SetSelectedFont(self._effectiveFont)
        wx.PostEvent(self, FontEntryEvent())

    def onFontPicked(self, event):
        event.Skip()
        self._fontCheckBox.SetValue(True)
        wx.PostEvent(self, FontEntryEvent())

    def GetValue(self):
        return (
            self._fontPicker.GetSelectedFont()
            if self._fontCheckBox.IsChecked()
            else None
        )

    def SetValue(self, new_font):
        checked = new_font is not None
        self._fontCheckBox.SetValue(checked)
        if checked:
            self._fontPicker.SetSelectedFont(new_font)

    def GetColor(self):
        return self._fontPicker.GetSelectedColour()

    def SetColor(self, new_color):
        self._fontPicker.SetSelectedColour(new_color)

    def SetBgColor(self, new_color):
        self._fontPicker.SetSelectedBgColour(new_color)


ColorEntryEvent, EVT_COLORENTRY = newevent.NewEvent()


class ColorEntry(widgets.PanelWithBoxSizer):
    """Color entry with checkbox for override colors.

    When unchecked: shows effective color (set via setEffectiveColor).
    When checked: user can pick a custom color.
    Editor provides derived color (inherited value or system theme fallback).
    """

    def __init__(self, parent, current_color, default_color, *args, **kwargs):
        kwargs["orientation"] = wx.HORIZONTAL
        super().__init__(parent, *args, **kwargs)
        self._effectiveColor = (
            None  # Set via setEffectiveColor() after construction
        )
        self._colorCheckBox = self._create_check_box(current_color)
        self._colorPicker = self._create_color_picker(
            current_color, default_color
        )
        self.add(
            self._colorCheckBox,
            flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            border=15,
            proportion=0,
        )
        self.add(
            self._colorPicker,
            flag=wx.ALIGN_CENTER_VERTICAL,
            border=0,
            proportion=1,
        )
        self.fit()

    def _create_check_box(self, current_color):
        check_box = wx.CheckBox(self, label="")
        check_box.SetValue(current_color is not None)
        check_box.Bind(wx.EVT_CHECKBOX, self.onChecked)
        return check_box

    def _create_color_picker(self, current_color, default_color):
        # ColourPickerCtrl on Mac OS X expects a wx.Colour and fails on tuples
        # so convert the tuples to a wx.Colour:
        if current_color:
            display_color = wx.Colour(*current_color)
        else:
            # No override - show system theme initially (derived color set later)
            if default_color == wx.BLACK:
                display_color = wx.SystemSettings.GetColour(
                    wx.SYS_COLOUR_WINDOWTEXT
                )
            elif default_color == wx.WHITE:
                display_color = wx.SystemSettings.GetColour(
                    wx.SYS_COLOUR_WINDOW
                )
            else:
                display_color = default_color
        picker = widgets.ColourPickerCtrl(self, colour=display_color)
        picker.Bind(wx.EVT_COLOURPICKER_CHANGED, self.onColorPicked)
        return picker

    def setEffectiveColor(self, color):
        """Set the effective color to display when unchecked.

        Editor provides the effective color from the SSOT model.
        """
        if color is None or (
            isinstance(color, wx.Colour) and not color.IsOk()
        ):
            return
        if not isinstance(color, wx.Colour):
            color = wx.Colour(*color)
        self._effectiveColor = color
        if not self._colorCheckBox.IsChecked():
            self._colorPicker.SetColour(self._effectiveColor)

    def onChecked(self, event):
        event.Skip()
        checked = self._colorCheckBox.IsChecked()
        if not checked and self._effectiveColor:
            self._colorPicker.SetColour(self._effectiveColor)
        wx.PostEvent(self, ColorEntryEvent())

    def onColorPicked(self, event):
        event.Skip()
        self._colorCheckBox.SetValue(True)
        wx.PostEvent(self, ColorEntryEvent())

    def GetValue(self):
        return (
            self._colorPicker.GetColour()
            if self._colorCheckBox.IsChecked()
            else None
        )

    def SetValue(self, new_color):
        checked = new_color is not None
        self._colorCheckBox.SetValue(checked)
        if checked:
            self._colorPicker.SetColour(new_color)


IconEntryEvent, EVT_ICONENTRY = newevent.NewEvent()


class IconEntry(widgets.PanelWithBoxSizer):
    """Icon entry with checkbox. When unchecked, returns empty string (no icon)."""

    def __init__(self, parent, current_icon_id, exclude=None, *args, **kwargs):
        kwargs["orientation"] = wx.HORIZONTAL
        super().__init__(parent, *args, **kwargs)
        self._iconCheckBox = self._create_check_box(current_icon_id)
        self._iconPicker = self._create_icon_picker(
            parent, current_icon_id, exclude
        )
        self.add(
            self._iconCheckBox,
            flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            border=15,
            proportion=0,
        )
        self.add(
            self._iconPicker,
            flag=wx.ALIGN_CENTER_VERTICAL,
            border=0,
            proportion=1,
        )
        self.fitNoMinSize()

    def _create_check_box(self, current_icon_id):
        check_box = wx.CheckBox(self, label="")
        check_box.SetValue(current_icon_id != "")
        check_box.Bind(wx.EVT_CHECKBOX, self.onChecked)
        return check_box

    def _create_icon_picker(self, parent, current_icon_id, exclude):
        picker = widgets.IconPicker(
            self, current_icon_id or "", exclude=exclude
        )
        picker.Bind(wx.EVT_COMBOBOX, self.onIconPicked)
        return picker

    def onChecked(self, event):
        event.Skip()
        if not self._iconCheckBox.IsChecked():
            self._iconPicker.SetValue("")
        wx.PostEvent(self, IconEntryEvent())

    def onIconPicked(self, event):
        event.Skip()
        selected = self._iconPicker.GetValue()
        # Auto-uncheck if "No icon" selected, auto-check otherwise
        self._iconCheckBox.SetValue(selected != "")
        wx.PostEvent(self, IconEntryEvent())

    def GetValue(self):
        if self._iconCheckBox.IsChecked():
            return self._iconPicker.GetValue()
        return ""

    def SetValue(self, newValue):
        checked = newValue != ""
        self._iconCheckBox.SetValue(checked)
        self._iconPicker.SetValue(newValue)


ChoiceEntryEvent, EVT_CHOICEENTRY = newevent.NewEvent()


class ChoiceEntry(wx.Choice):
    def __init__(self, parent, choices, current_choice_value, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        for choice_value, choice_text in choices:
            self.Append(choice_text, choice_value)
            if choice_value == current_choice_value:
                self.SetSelection(self.GetCount() - 1)
        if self.GetSelection() == wx.NOT_FOUND:
            # Force a selection if necessary:
            self.SetSelection(0)
        self.Bind(wx.EVT_CHOICE, self.onChoice)

    def onChoice(self, event):
        event.Skip()
        wx.PostEvent(self, ChoiceEntryEvent())

    def GetValue(self):
        return self.GetClientData(self.GetSelection())

    def SetValue(self, newValue):
        for index in range(self.GetCount()):
            if newValue == self.GetClientData(index):
                self.SetSelection(index)
                break


TaskEntryEvent, EVT_TASKENTRY = newevent.NewEvent()


class TaskEntry(wx.Panel):
    """A ComboTreeBox with tasks. This class does not inherit from the
    ComboTreeBox widget, because that widget is created using a
    factory function."""

    def __init__(self, parent, root_tasks, selected_task):
        """Initialize the ComboTreeBox, add the root tasks recursively and
        set the selection."""
        super().__init__(parent)
        self._createInterior()
        self._add_tasks_recursively(root_tasks)
        self.SetValue(selected_task)
        # Bind to window close to properly clean up the popup
        self.Bind(wx.EVT_WINDOW_DESTROY, self._onDestroy)

    def __getattr__(self, attr):
        """Delegate unknown attributes to the ComboTreeBox. This is needed
        since we cannot inherit from ComboTreeBox, but have to use
        delegation."""
        return getattr(self._comboTreeBox, attr)

    def _createInterior(self):
        """Create the ComboTreebox widget."""
        # pylint: disable=W0201
        self._comboTreeBox = combotreebox.ComboTreeBox(
            self, style=wx.CB_READONLY | wx.CB_SORT | wx.TAB_TRAVERSAL
        )
        self._comboTreeBox.Bind(wx.EVT_COMBOBOX, self.onTaskSelected)
        box_sizer = wx.BoxSizer()
        box_sizer.Add(self._comboTreeBox, flag=wx.EXPAND, proportion=1)
        self.SetSizerAndFit(box_sizer)

    def _add_tasks_recursively(self, tasks, parent_item=None):
        """Add tasks to the ComboTreeBox and then recursively add their
        subtasks."""
        for task in tasks:
            self._add_task_recursively(task, parent_item)

    def _add_task_recursively(self, task, parent_item=None):
        """Add a task to the ComboTreeBox and then recursively add its
        subtasks."""
        item = self._comboTreeBox.Append(task.subject(), parent=parent_item)
        self._comboTreeBox.SetClientData(item, task)
        self._add_tasks_recursively(task.children(), item)

    def onTaskSelected(self, event):  # pylint: disable=W0613
        wx.PostEvent(self, TaskEntryEvent())

    def SetValue(self, task):
        """Select the given task."""
        self._comboTreeBox.SetClientDataSelection(task)

    def GetValue(self):
        """Return the selected task."""
        selection = self._comboTreeBox.GetSelection()
        return self._comboTreeBox.GetClientData(selection)

    def _onDestroy(self, event):
        """Clean up the popup frame before destruction to avoid RuntimeErrors.

        The wx.lib.combotreebox has issues where focus events fire during
        destruction, causing RuntimeErrors when C++ objects are already deleted.
        """
        event.Skip()
        # Only handle destruction of this specific window
        if event.GetEventObject() is not self:
            return
        try:
            # Try to unbind the kill focus handler before destruction
            popup_frame = self._comboTreeBox._popupFrame
            if popup_frame:
                try:
                    popup_frame._unbindKillFocus()
                except (RuntimeError, AttributeError):
                    pass  # Already destroyed or doesn't have the method
                # Hide the popup if it's showing
                if popup_frame.IsShown():
                    try:
                        popup_frame.Hide()
                    except RuntimeError:
                        pass  # Already destroyed
        except (RuntimeError, AttributeError):
            pass  # ComboTreeBox already destroyed


RecurrenceEntryEvent, EVT_RECURRENCEENTRY = newevent.NewEvent()


class RecurrenceEntry(wx.Panel):
    horizontalSpace = (3, -1)

    def __init__(self, parent, recurrence, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        recurrence_frequency_panel = wx.Panel(self)
        self._recurrencePeriodEntry = wx.Choice(
            recurrence_frequency_panel,
            choices=[
                _("None"),
                _("Daily"),
                _("Weekly"),
                _("Monthly"),
                _("Yearly"),
            ],
        )
        self._recurrencePeriodEntry.Bind(
            wx.EVT_CHOICE, self.onRecurrencePeriodEdited
        )
        self._recurrenceFrequencyEntry = widgets.SpinCtrl(
            recurrence_frequency_panel, size=(120, -1), value=1, min=1
        )
        self._recurrenceFrequencyEntry.Bind(
            wx.EVT_SPINCTRL, self.onRecurrenceEdited
        )
        self._recurrenceStaticText = wx.StaticText(
            recurrence_frequency_panel, label="reserve some space"
        )
        self._recurrenceSameWeekdayCheckBox = wx.CheckBox(
            recurrence_frequency_panel,
            label=_("keeping dates on the same weekday"),
        )
        self._recurrenceSameWeekdayCheckBox.Bind(
            wx.EVT_CHECKBOX, self.onRecurrenceEdited
        )
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(
            self._recurrencePeriodEntry, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panel_sizer.Add(self.horizontalSpace)
        panel_sizer.Add(
            wx.StaticText(recurrence_frequency_panel, label=_(", every")),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        panel_sizer.Add(self.horizontalSpace)
        panel_sizer.Add(
            self._recurrenceFrequencyEntry, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panel_sizer.Add(self.horizontalSpace)
        panel_sizer.Add(
            self._recurrenceStaticText, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panel_sizer.Add(self.horizontalSpace)
        panel_sizer.Add(
            self._recurrenceSameWeekdayCheckBox,
            proportion=1,
            flag=wx.EXPAND,
        )
        recurrence_frequency_panel.SetSizerAndFit(panel_sizer)
        self._recurrenceSizer = panel_sizer

        # Weekday selector panel for weekly recurrence
        weekday_panel = wx.Panel(self)
        weekday_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        weekday_panel_sizer.Add(
            wx.StaticText(weekday_panel, label=_("On days:")),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        weekday_panel_sizer.Add((6, -1))
        # Weekday names starting from Monday (0) to Sunday (6)
        weekday_names = [
            _("Mon"),
            _("Tue"),
            _("Wed"),
            _("Thu"),
            _("Fri"),
            _("Sat"),
            _("Sun"),
        ]
        self._weekdayCheckBoxes = []
        for i, day_name in enumerate(weekday_names):
            cb = wx.CheckBox(weekday_panel, label=day_name)
            cb.Bind(wx.EVT_CHECKBOX, self.onRecurrenceEdited)
            self._weekdayCheckBoxes.append(cb)
            weekday_panel_sizer.Add(cb, flag=wx.ALIGN_CENTER_VERTICAL)
            if i < len(weekday_names) - 1:
                weekday_panel_sizer.Add((6, -1))
        weekday_panel.SetSizerAndFit(weekday_panel_sizer)
        self._weekdayPanel = weekday_panel

        # schedulePanel created before maxPanel for correct tab order (top-to-bottom)
        schedule_panel = wx.Panel(self)
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(
            schedule_panel, label=_("Schedule each next recurrence based on")
        )
        panel_sizer.Add(label, flag=wx.ALIGN_CENTER_VERTICAL)
        panel_sizer.Add((3, -1))
        self._scheduleChoice = wx.Choice(
            schedule_panel,
            choices=[
                _("previous planned start and/or due date"),
                _("last completion date"),
            ],
        )
        self._scheduleChoice.Bind(wx.EVT_CHOICE, self.onRecurrenceEdited)
        if operating_system.isMac():
            # On Mac OS X, the wx.Choice gets too little vertical space by
            # default
            size = self._scheduleChoice.GetSize()
            self._scheduleChoice.SetMinSize((size[0], size[1] + 1))
        panel_sizer.Add(self._scheduleChoice, flag=wx.ALIGN_CENTER_VERTICAL)
        schedule_panel.SetSizerAndFit(panel_sizer)

        max_panel = wx.Panel(self)
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self._maxRecurrenceCheckBox = wx.CheckBox(max_panel)
        self._maxRecurrenceCheckBox.Bind(
            wx.EVT_CHECKBOX, self.onMaxRecurrenceChecked
        )
        self._maxRecurrenceCountEntry = widgets.SpinCtrl(
            max_panel, size=(120, -1), value=1, min=1
        )
        self._maxRecurrenceCountEntry.Bind(
            wx.EVT_SPINCTRL, self.onRecurrenceEdited
        )
        panel_sizer.Add(
            self._maxRecurrenceCheckBox, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panel_sizer.Add(self.horizontalSpace)
        panel_sizer.Add(
            wx.StaticText(max_panel, label=_("Stop after")),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        panel_sizer.Add(self.horizontalSpace)
        panel_sizer.Add(
            self._maxRecurrenceCountEntry, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panel_sizer.Add(self.horizontalSpace)
        panel_sizer.Add(
            wx.StaticText(max_panel, label=_("recurrences")),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        max_panel.SetSizerAndFit(panel_sizer)

        # Stop after date using DateTimeComboCtrl
        stop_panel = wx.Panel(self)
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # value=None means unchecked (no stop date); when user checks it, defaults to "now"
        self._recurrenceStopDateTimeCombo = widgets.DateTimeComboCtrl(
            stop_panel,
            value=None,  # unchecked by default
            hour_choices=get_suggested_hour_choices,
            minute_choices=get_suggested_minute_choices,
        )
        # Bind value change — fires on checkbox toggle AND date/time edits
        self._recurrenceStopDateTimeCombo.Bind(
            widgets.EVT_VALUE_CHANGED, self.onRecurrenceEdited
        )
        panel_sizer.Add(
            self._recurrenceStopDateTimeCombo.GetCheckBox(),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        panel_sizer.Add(self.horizontalSpace)
        panel_sizer.Add(
            wx.StaticText(stop_panel, label=_("Stop after")),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        panel_sizer.Add(self.horizontalSpace)
        panel_sizer.Add(
            self._recurrenceStopDateTimeCombo.GetDateCtrl(),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        panel_sizer.Add(self.horizontalSpace)
        panel_sizer.Add(
            self._recurrenceStopDateTimeCombo.GetTimeCtrl(),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        stop_panel.SetSizerAndFit(panel_sizer)

        # Store sub-panels for external layout (DatesPage places them as
        # separate grid rows so they get the same spacing as other entries).
        self._subPanels = [
            recurrence_frequency_panel,
            self._weekdayPanel,
            schedule_panel,
            max_panel,
            stop_panel,
        ]
        self.Hide()  # RecurrenceEntry itself is invisible; sub-panels are reparented
        self.SetValue(recurrence)

    def getSubPanels(self):
        """Return the list of sub-panels for external layout."""
        return list(self._subPanels)

    def updateRecurrenceLabel(self):
        recurrence_dict = {
            0: _("period,"),
            1: _("day(s),"),
            2: _("week(s),"),
            3: _("month(s),"),
            4: _("year(s),"),
        }
        recurrence_label = recurrence_dict[
            self._recurrencePeriodEntry.Selection
        ]
        self._recurrenceStaticText.SetLabel(recurrence_label)
        self._recurrenceSameWeekdayCheckBox.Enable(
            self._recurrencePeriodEntry.Selection in (3, 4)
        )
        # Enable weekday checkboxes only when weekly is selected (index 2)
        weekly_selected = self._recurrencePeriodEntry.Selection == 2
        for cb in self._weekdayCheckBoxes:
            cb.Enable(weekly_selected)
        self._recurrenceSizer.Layout()

    def onRecurrencePeriodEdited(self, event):
        recurrence_on = event.String != _("None")
        self._maxRecurrenceCheckBox.Enable(recurrence_on)
        if recurrence_on:
            self._recurrenceStopDateTimeCombo.SetEditable()
        else:
            self._recurrenceStopDateTimeCombo.DeactivateValue()
            self._recurrenceStopDateTimeCombo.SetReadOnly()
        self._recurrenceFrequencyEntry.Enable(recurrence_on)
        self._scheduleChoice.Enable(recurrence_on)
        self._maxRecurrenceCountEntry.Enable(
            recurrence_on and self._maxRecurrenceCheckBox.IsChecked()
        )
        self.updateRecurrenceLabel()
        self.onRecurrenceEdited()

    def onMaxRecurrenceChecked(self, event):
        max_recurrence_on = event.IsChecked()
        self._maxRecurrenceCountEntry.Enable(max_recurrence_on)
        self.onRecurrenceEdited()

    def onRecurrenceEdited(self, event=None):  # pylint: disable=W0613
        wx.PostEvent(self, RecurrenceEntryEvent())

    def SetValue(self, recurrence):
        # How many times the task has recurred: no field shows it, and
        # "Stop after" counts it
        self._count = recurrence.count
        index = {"": 0, "daily": 1, "weekly": 2, "monthly": 3, "yearly": 4}[
            recurrence.unit
        ]
        self._recurrencePeriodEntry.Selection = index
        self._maxRecurrenceCheckBox.Enable(bool(recurrence))
        self._maxRecurrenceCheckBox.SetValue(recurrence.max > 0)
        self._maxRecurrenceCountEntry.Enable(recurrence.max > 0)
        if recurrence.max > 0:
            self._maxRecurrenceCountEntry.Value = recurrence.max
        self._recurrenceFrequencyEntry.Enable(bool(recurrence))
        self._recurrenceFrequencyEntry.Value = recurrence.amount
        self._recurrenceSameWeekdayCheckBox.Value = (
            recurrence.sameWeekday
            if recurrence.unit in ("monthly", "yearly")
            else False
        )
        # Set weekday checkboxes
        for i, cb in enumerate(self._weekdayCheckBoxes):
            cb.SetValue(i in recurrence.weekdays)
        self._scheduleChoice.Selection = (
            1 if recurrence.recurBasedOnCompletion else 0
        )
        self._scheduleChoice.Enable(bool(recurrence))
        if bool(recurrence):
            self._recurrenceStopDateTimeCombo.SetEditable()
            has_stop_datetime = recurrence.stop_datetime != date.DateTime()
            if has_stop_datetime:
                self._recurrenceStopDateTimeCombo.SetValue(
                    recurrence.stop_datetime
                )
            else:
                self._recurrenceStopDateTimeCombo.DeactivateValue()
        else:
            self._recurrenceStopDateTimeCombo.DeactivateValue()
            self._recurrenceStopDateTimeCombo.SetReadOnly()
        self.updateRecurrenceLabel()

    def GetValue(self):
        recurrence_dict = {
            0: "",
            1: "daily",
            2: "weekly",
            3: "monthly",
            4: "yearly",
        }
        kwargs = dict(
            unit=recurrence_dict[self._recurrencePeriodEntry.Selection],
            count=self._count,
        )
        if self._maxRecurrenceCheckBox.IsChecked():
            kwargs["maximum"] = self._maxRecurrenceCountEntry.Value
        kwargs["amount"] = self._recurrenceFrequencyEntry.Value
        kwargs["sameWeekday"] = self._recurrenceSameWeekdayCheckBox.IsChecked()
        kwargs["recurBasedOnCompletion"] = bool(self._scheduleChoice.Selection)
        if self._recurrenceStopDateTimeCombo.IsActive():
            kwargs["stop_datetime"] = (
                self._recurrenceStopDateTimeCombo.GetValue()
            )
        # Get selected weekdays (0-6 for Mon-Sun)
        kwargs["weekdays"] = [
            i for i, cb in enumerate(self._weekdayCheckBoxes) if cb.IsChecked()
        ]
        return date.Recurrence(**kwargs)  # pylint: disable=W0142
