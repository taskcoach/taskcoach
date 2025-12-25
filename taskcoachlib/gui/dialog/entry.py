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
from taskcoachlib.domain import date
from taskcoachlib.gui import artprovider
from taskcoachlib.i18n import _
import datetime
from wx.lib import combotreebox, newevent
import wx
import wx.adv


DateTimeEntryEvent, EVT_DATETIMEENTRY = newevent.NewEvent()


class DateTimeEntry(widgets.DateTimeCtrl):
    defaultDateTime = date.DateTime()

    def __init__(
        self,
        parent,
        settings,
        initialDateTime=defaultDateTime,
        readonly=False,
        noneAllowed=True,
        showSeconds=False,
        suggestedDateTime=None,
        showRelative=False,
        adjustEndOfDay=False,
        units=None,
        *args,
        **kwargs
    ):
        starthour = settings.getint("view", "efforthourstart")
        endhour = settings.getint("view", "efforthourend")
        interval = settings.getint("view", "effortminuteinterval")
        super().__init__(
            parent,
            noneAllowed=noneAllowed,
            starthour=starthour,
            endhour=endhour,
            interval=interval,
            showSeconds=showSeconds,
            showRelative=showRelative,
            adjustEndOfDay=adjustEndOfDay,
            units=units,
        )
        if readonly:
            self.Disable()
        # First set the initial value and then set the callback so that the
        # callback is not triggered for the initial value
        if initialDateTime == date.DateTime() and suggestedDateTime:
            self.setSuggested(suggestedDateTime)
        else:
            self.SetValue(initialDateTime)
        self.setCallback(self.onDateTimeCtrlEdited)

    def SetValue(self, newValue=None):
        super().SetValue(newValue or self.defaultDateTime)

    def setSuggested(self, suggestedDateTime):
        super().SetValue(suggestedDateTime)
        super().SetNone()

    def onDateTimeCtrlEdited(self, *args, **kwargs):  # pylint: disable=W0613
        wx.PostEvent(self, DateTimeEntryEvent())


class TimeDeltaEntry(widgets.PanelWithBoxSizer):
    # We can't inherit from widgets.masked.TextCtrl because that class expects
    # GetValue to return a string and we want to return a TimeDelta.

    defaultTimeDelta = date.TimeDelta()

    def __init__(
        self,
        parent,
        timeDelta=defaultTimeDelta,
        readonly=False,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        hours, minutes, seconds = timeDelta.hoursMinutesSeconds()
        self._entry = widgets.masked.TimeDeltaCtrl(
            self,
            hours,
            minutes,
            seconds,
            readonly,
            timeDelta < self.defaultTimeDelta,
        )
        if readonly:
            self._entry.Disable()
        self.add(self._entry, flag=wx.EXPAND | wx.ALL, proportion=1)
        self.fit()

    def NavigateBook(self, event):
        self.GetParent().NavigateBook(not event.ShiftDown())
        return True

    def GetValue(self):
        return date.parseTimeDelta(self._entry.GetValue())

    def SetValue(self, newTimeDelta):
        hours, minutes, seconds = newTimeDelta.hoursMinutesSeconds()
        negative = newTimeDelta < self.defaultTimeDelta
        self._entry.set_value(hours, minutes, seconds, negative)

    def Bind(self, *args, **kwargs):  # pylint: disable=W0221
        self._entry.Bind(*args, **kwargs)


class AmountEntry(widgets.PanelWithBoxSizer):
    def __init__(self, parent, amount=0.0, readonly=False, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._entry = self.createEntry(amount)
        if readonly:
            self._entry.Disable()
        self.add(self._entry)
        self.fit()

    def createEntry(self, amount):
        return widgets.masked.AmountCtrl(self, amount)

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
        for eventType in wx.EVT_SPINCTRL, wx.EVT_KILL_FOCUS:
            entry.Bind(eventType, self.onSpin)
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

    def syncControl(self, controlToWrite, controlToRead):
        value = controlToRead.GetValue()
        # Prevent potential endless loop by checking that we really need to set
        # the value:
        if controlToWrite.GetValue() != value:
            controlToWrite.SetValue(value)
        wx.PostEvent(self, PercentageEntryEvent())


FontEntryEvent, EVT_FONTENTRY = newevent.NewEvent()


class FontEntry(widgets.PanelWithBoxSizer):
    def __init__(self, parent, currentFont, currentColor, *args, **kwargs):
        kwargs["orientation"] = wx.HORIZONTAL
        super().__init__(parent, *args, **kwargs)
        self._fontCheckBox = self._createCheckBox(currentFont)
        self._fontPicker = self._createFontPicker(currentFont, currentColor)
        self.add(
            self._fontCheckBox,
            flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
            proportion=0,
        )
        self.add(
            self._fontPicker,
            flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
            proportion=1,
        )
        self.fit()

    def _createCheckBox(self, currentFont):
        checkBox = wx.CheckBox(self, label=_("Use font:"))
        checkBox.SetValue(currentFont is not None)
        checkBox.Bind(wx.EVT_CHECKBOX, self.onChecked)
        return checkBox

    def _createFontPicker(self, currentFont, currentColor):
        defaultFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        picker = widgets.FontPickerCtrl(
            self, font=currentFont or defaultFont, colour=currentColor
        )
        picker.Bind(wx.EVT_FONTPICKER_CHANGED, self.onFontPicked)
        return picker

    def onChecked(self, event):
        event.Skip()
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

    def SetValue(self, newFont):
        checked = newFont is not None
        self._fontCheckBox.SetValue(checked)
        if checked:
            self._fontPicker.SetSelectedFont(newFont)

    def GetColor(self):
        return self._fontPicker.GetSelectedColour()

    def SetColor(self, newColor):
        self._fontPicker.SetSelectedColour(newColor)


ColorEntryEvent, EVT_COLORENTRY = newevent.NewEvent()


class ColorEntry(widgets.PanelWithBoxSizer):
    def __init__(self, parent, currentColor, defaultColor, *args, **kwargs):
        kwargs["orientation"] = wx.HORIZONTAL
        super().__init__(parent, *args, **kwargs)
        self._colorCheckBox = self._createCheckBox(currentColor)
        self._colorPicker = self._createColorPicker(currentColor, defaultColor)
        self.add(
            self._colorCheckBox,
            flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
            proportion=0,
        )
        self.add(
            self._colorPicker,
            flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
            proportion=1,
        )
        self.fit()

    def _createCheckBox(self, currentColor):
        checkBox = wx.CheckBox(self, label=_("Use color:"))
        checkBox.SetValue(currentColor is not None)
        checkBox.Bind(wx.EVT_CHECKBOX, self.onChecked)
        return checkBox

    def _createColorPicker(self, currentColor, defaultColor):
        # wx.ColourPickerCtrl on Mac OS X expects a wx.Colour and fails on tuples
        # so convert the tuples to a wx.Colour:
        currentColor = (
            wx.Colour(*currentColor) if currentColor else defaultColor
        )  # pylint: disable=W0142
        picker = wx.ColourPickerCtrl(self, colour=currentColor)
        picker.Bind(wx.EVT_COLOURPICKER_CHANGED, self.onColorPicked)
        return picker

    def onChecked(self, event):
        event.Skip()
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

    def SetValue(self, newColor):
        checked = newColor is not None
        self._colorCheckBox.SetValue(checked)
        if checked:
            self._colorPicker.SetColour(newColor)


IconEntryEvent, EVT_ICONENTRY = newevent.NewEvent()


class IconEntry(wx.adv.BitmapComboBox):
    def __init__(self, parent, currentIcon, *args, **kwargs):
        kwargs["style"] = wx.CB_READONLY
        super().__init__(parent, *args, **kwargs)
        imageNames = sorted(artprovider.chooseableItemImages.keys())
        size = (16, 16)
        for imageName in imageNames:
            label = artprovider.chooseableItemImages[imageName]
            bitmap = wx.ArtProvider.GetBitmap(imageName, wx.ART_MENU, size)
            item = self.Append(label, bitmap)
            self.SetClientData(item, imageName)
        self.SetSelection(imageNames.index(currentIcon))
        # GTK's native BitmapComboBox clips icons in the closed state.
        # Oversizing the control gives the renderer more space to work with.
        if operating_system.isGTK():
            longestLabel = max(
                (artprovider.chooseableItemImages[name] for name in imageNames),
                key=len
            )
            textWidth, _ = self.GetTextExtent(longestLabel)
            # icon (16) + text + extra padding (16) + dropdown button (30)
            minWidth = 16 + textWidth + 16 + 30
            self.SetMinSize(wx.Size(minWidth, -1))
        self.Bind(wx.EVT_COMBOBOX, self.onIconPicked)

    def onIconPicked(self, event):
        event.Skip()
        wx.PostEvent(self, IconEntryEvent())

    def GetValue(self):
        return self.GetClientData(self.GetSelection())

    def SetValue(self, newValue):
        for index in range(self.GetCount()):
            if newValue == self.GetClientData(index):
                self.SetSelection(index)
                break


ChoiceEntryEvent, EVT_CHOICEENTRY = newevent.NewEvent()


class ChoiceEntry(wx.Choice):
    def __init__(self, parent, choices, currentChoiceValue, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        for choiceValue, choiceText in choices:
            self.Append(choiceText, choiceValue)
            if choiceValue == currentChoiceValue:
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

    def __init__(self, parent, rootTasks, selectedTask):
        """Initialize the ComboTreeBox, add the root tasks recursively and
        set the selection."""
        super().__init__(parent)
        self._createInterior()
        self._addTasksRecursively(rootTasks)
        self.SetValue(selectedTask)
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
        boxSizer = wx.BoxSizer()
        boxSizer.Add(self._comboTreeBox, flag=wx.EXPAND, proportion=1)
        self.SetSizerAndFit(boxSizer)

    def _addTasksRecursively(self, tasks, parentItem=None):
        """Add tasks to the ComboTreeBox and then recursively add their
        subtasks."""
        for task in tasks:
            self._addTaskRecursively(task, parentItem)

    def _addTaskRecursively(self, task, parentItem=None):
        """Add a task to the ComboTreeBox and then recursively add its
        subtasks."""
        if not task.isDeleted():
            item = self._comboTreeBox.Append(task.subject(), parent=parentItem)
            self._comboTreeBox.SetClientData(item, task)
            self._addTasksRecursively(task.children(), item)

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
            popupFrame = self._comboTreeBox._popupFrame
            if popupFrame:
                try:
                    popupFrame._unbindKillFocus()
                except (RuntimeError, AttributeError):
                    pass  # Already destroyed or doesn't have the method
                # Hide the popup if it's showing
                if popupFrame.IsShown():
                    try:
                        popupFrame.Hide()
                    except RuntimeError:
                        pass  # Already destroyed
        except (RuntimeError, AttributeError):
            pass  # ComboTreeBox already destroyed


RecurrenceEntryEvent, EVT_RECURRENCEENTRY = newevent.NewEvent()


class RecurrenceEntry(wx.Panel):
    horizontalSpace = (3, -1)
    verticalSpace = (-1, 3)

    def __init__(self, parent, recurrence, settings, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        recurrenceFrequencyPanel = wx.Panel(self)
        self._recurrencePeriodEntry = wx.Choice(
            recurrenceFrequencyPanel,
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
            recurrenceFrequencyPanel, size=(120, -1), value=1, min=1
        )
        self._recurrenceFrequencyEntry.Bind(
            wx.EVT_SPINCTRL, self.onRecurrenceEdited
        )
        self._recurrenceStaticText = wx.StaticText(
            recurrenceFrequencyPanel, label="reserve some space"
        )
        self._recurrenceSameWeekdayCheckBox = wx.CheckBox(
            recurrenceFrequencyPanel,
            label=_("keeping dates on the same weekday"),
        )
        self._recurrenceSameWeekdayCheckBox.Bind(
            wx.EVT_CHECKBOX, self.onRecurrenceEdited
        )
        panelSizer = wx.BoxSizer(wx.HORIZONTAL)
        panelSizer.Add(
            self._recurrencePeriodEntry, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panelSizer.Add(self.horizontalSpace)
        panelSizer.Add(
            wx.StaticText(recurrenceFrequencyPanel, label=_(", every")),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        panelSizer.Add(self.horizontalSpace)
        panelSizer.Add(
            self._recurrenceFrequencyEntry, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panelSizer.Add(self.horizontalSpace)
        panelSizer.Add(
            self._recurrenceStaticText, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panelSizer.Add(self.horizontalSpace)
        panelSizer.Add(
            self._recurrenceSameWeekdayCheckBox,
            proportion=1,
            flag=wx.EXPAND,
        )
        recurrenceFrequencyPanel.SetSizerAndFit(panelSizer)
        self._recurrenceSizer = panelSizer

        maxPanel = wx.Panel(self)
        panelSizer = wx.BoxSizer(wx.HORIZONTAL)

        self._maxRecurrenceCheckBox = wx.CheckBox(maxPanel)
        self._maxRecurrenceCheckBox.Bind(
            wx.EVT_CHECKBOX, self.onMaxRecurrenceChecked
        )
        self._maxRecurrenceCountEntry = widgets.SpinCtrl(
            maxPanel, size=(120, -1), value=1, min=1
        )
        self._maxRecurrenceCountEntry.Bind(
            wx.EVT_SPINCTRL, self.onRecurrenceEdited
        )
        panelSizer.Add(
            self._maxRecurrenceCheckBox, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panelSizer.Add(self.horizontalSpace)
        panelSizer.Add(
            wx.StaticText(maxPanel, label=_("Stop after")),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        panelSizer.Add(self.horizontalSpace)
        panelSizer.Add(
            self._maxRecurrenceCountEntry, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panelSizer.Add(self.horizontalSpace)
        panelSizer.Add(
            wx.StaticText(maxPanel, label=_("recurrences")),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        maxPanel.SetSizerAndFit(panelSizer)

        schedulePanel = wx.Panel(self)
        panelSizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(
            schedulePanel, label=_("Schedule each next recurrence based on")
        )
        panelSizer.Add(label, flag=wx.ALIGN_CENTER_VERTICAL)
        panelSizer.Add((3, -1))
        self._scheduleChoice = wx.Choice(
            schedulePanel,
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
        panelSizer.Add(self._scheduleChoice, flag=wx.ALIGN_CENTER_VERTICAL)
        schedulePanel.SetSizerAndFit(panelSizer)

        stopPanel = wx.Panel(self)
        panelSizer = wx.BoxSizer(wx.HORIZONTAL)

        self._stopDateTimeCheckBox = wx.CheckBox(stopPanel)
        self._stopDateTimeCheckBox.Bind(
            wx.EVT_CHECKBOX, self.onRecurrenceStopDateTimeChecked
        )
        # Since None is not allowed, we need an initial value...
        self._recurrenceStopDateTimeEntry = DateTimeEntry(
            stopPanel,
            settings,
            noneAllowed=False,
            initialDateTime=datetime.datetime.combine(
                date.LastDayOfCurrentMonth(), datetime.time(0, 0, 0)
            ),
        )
        self._recurrenceStopDateTimeEntry.Bind(
            EVT_DATETIMEENTRY, self.onRecurrenceEdited
        )
        panelSizer.Add(
            self._stopDateTimeCheckBox, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panelSizer.Add(self.horizontalSpace)
        panelSizer.Add(
            wx.StaticText(stopPanel, label=_("Stop after")),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        panelSizer.Add(self.horizontalSpace)
        panelSizer.Add(
            self._recurrenceStopDateTimeEntry, flag=wx.ALIGN_CENTER_VERTICAL
        )
        panelSizer.Add(self.horizontalSpace)
        stopPanel.SetSizerAndFit(panelSizer)

        panelSizer = wx.BoxSizer(wx.VERTICAL)
        panelSizer.Add(recurrenceFrequencyPanel)
        panelSizer.Add(self.verticalSpace)
        panelSizer.Add(schedulePanel)
        panelSizer.Add(self.verticalSpace)
        panelSizer.Add(maxPanel)
        panelSizer.Add(stopPanel)
        self.SetSizerAndFit(panelSizer)
        self.SetValue(recurrence)

    def updateRecurrenceLabel(self):
        recurrenceDict = {
            0: _("period,"),
            1: _("day(s),"),
            2: _("week(s),"),
            3: _("month(s),"),
            4: _("year(s),"),
        }
        recurrenceLabel = recurrenceDict[self._recurrencePeriodEntry.Selection]
        self._recurrenceStaticText.SetLabel(recurrenceLabel)
        self._recurrenceSameWeekdayCheckBox.Enable(
            self._recurrencePeriodEntry.Selection in (3, 4)
        )
        self._recurrenceSizer.Layout()

    def onRecurrencePeriodEdited(self, event):
        recurrenceOn = event.String != _("None")
        self._maxRecurrenceCheckBox.Enable(recurrenceOn)
        self._stopDateTimeCheckBox.Enable(recurrenceOn)
        self._recurrenceFrequencyEntry.Enable(recurrenceOn)
        self._scheduleChoice.Enable(recurrenceOn)
        self._maxRecurrenceCountEntry.Enable(
            recurrenceOn and self._maxRecurrenceCheckBox.IsChecked()
        )
        self._recurrenceStopDateTimeEntry.Enable(
            recurrenceOn and self._stopDateTimeCheckBox.IsChecked()
        )
        self.updateRecurrenceLabel()
        self.onRecurrenceEdited()

    def onMaxRecurrenceChecked(self, event):
        maxRecurrenceOn = event.IsChecked()
        self._maxRecurrenceCountEntry.Enable(maxRecurrenceOn)
        self.onRecurrenceEdited()

    def onRecurrenceStopDateTimeChecked(self, event):
        stopRecurrenceOn = event.IsChecked()
        self._recurrenceStopDateTimeEntry.Enable(stopRecurrenceOn)
        self.onRecurrenceEdited()

    def onRecurrenceEdited(self, event=None):  # pylint: disable=W0613
        wx.PostEvent(self, RecurrenceEntryEvent())

    def SetValue(self, recurrence):
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
        self._scheduleChoice.Selection = (
            1 if recurrence.recurBasedOnCompletion else 0
        )
        self._scheduleChoice.Enable(bool(recurrence))
        self._stopDateTimeCheckBox.Enable(bool(recurrence))
        has_stop_datetime = recurrence.stop_datetime != date.DateTime()
        self._stopDateTimeCheckBox.SetValue(has_stop_datetime)
        self._recurrenceStopDateTimeEntry.Enable(has_stop_datetime)
        if has_stop_datetime:
            self._recurrenceStopDateTimeEntry.SetValue(
                recurrence.stop_datetime
            )
        self.updateRecurrenceLabel()

    def GetValue(self):
        recurrenceDict = {
            0: "",
            1: "daily",
            2: "weekly",
            3: "monthly",
            4: "yearly",
        }
        kwargs = dict(
            unit=recurrenceDict[self._recurrencePeriodEntry.Selection]
        )
        if self._maxRecurrenceCheckBox.IsChecked():
            kwargs["maximum"] = self._maxRecurrenceCountEntry.Value
        kwargs["amount"] = self._recurrenceFrequencyEntry.Value
        kwargs["sameWeekday"] = self._recurrenceSameWeekdayCheckBox.IsChecked()
        kwargs["recurBasedOnCompletion"] = bool(self._scheduleChoice.Selection)
        if self._stopDateTimeCheckBox.IsChecked():
            kwargs["stop_datetime"] = (
                self._recurrenceStopDateTimeEntry.GetValue()
            )
        return date.Recurrence(**kwargs)  # pylint: disable=W0142
