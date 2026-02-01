# -*- coding: UTF-8 -*-

"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2012 Nicola Chiapolini <nicola.chiapolini@physik.uzh.ch>
Copyright (C) 2008 Rob McMullen <rob.mcmullen@gmail.com>

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

from taskcoachlib import meta, widgets, operating_system, render
from taskcoachlib.application.application import detect_dark_theme
from taskcoachlib.domain import date, task
from taskcoachlib.gui import artprovider
from taskcoachlib.meta import data
from taskcoachlib.i18n import _
from wx.lib.agw.hyperlink import HyperLinkCtrl
from pubsub import pub
import ast
import wx, calendar
import wx.lib.scrolledpanel
from wx.lib.agw import ultimatelistctrl as ULC


class BitmapOwnerDrawnComboBox(wx.adv.OwnerDrawnComboBox):
    """A ComboBox that displays bitmaps with text, supporting SetPopupMinWidth.

    Unlike wx.adv.BitmapComboBox, this inherits from OwnerDrawnComboBox which
    provides SetPopupMinWidth for making the dropdown wider than the control.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._bitmaps = []  # Store bitmaps for each item
        self._clientData = []  # Store client data for each item

    def Append(self, label, bitmap=None):
        """Add an item with optional bitmap."""
        index = super().Append(label)
        # Ensure lists are long enough
        while len(self._bitmaps) <= index:
            self._bitmaps.append(None)
        while len(self._clientData) <= index:
            self._clientData.append(None)
        self._bitmaps[index] = bitmap
        return index

    def SetClientData(self, index, data):
        """Store client data for an item."""
        while len(self._clientData) <= index:
            self._clientData.append(None)
        self._clientData[index] = data

    def GetClientData(self, index):
        """Get client data for an item."""
        if 0 <= index < len(self._clientData):
            return self._clientData[index]
        return None

    def OnDrawItem(self, dc, rect, item, flags):
        """Draw an item with bitmap and text."""
        if item == wx.NOT_FOUND:
            return

        r = wx.Rect(*rect)
        r.Deflate(2, 2)

        # Draw bitmap if available
        x_offset = r.x + 2
        if item < len(self._bitmaps) and self._bitmaps[item]:
            bitmap = self._bitmaps[item]
            y_pos = r.y + (r.height - bitmap.GetHeight()) // 2
            dc.DrawBitmap(bitmap, x_offset, y_pos, True)
            x_offset += bitmap.GetWidth() + 4

        # Draw text
        text = self.GetString(item)
        y_pos = r.y + (r.height - dc.GetCharHeight()) // 2
        dc.DrawText(text, x_offset, y_pos)

    def OnMeasureItem(self, item):
        """Return height of an item."""
        return 22

    def OnMeasureItemWidth(self, item):
        """Return width of an item (use -1 for default)."""
        return -1


class FontColorSyncer(object):
    """The font color can be changed via the font color buttons and via the
    font button. The FontColorSyncer updates the one when the font color
    is changed via the other and vice versa."""

    def __init__(self, fgColorButton, bgColorButton, fontButton):
        self._fgColorButton = fgColorButton
        self._bgColorButton = bgColorButton
        self._fontButton = fontButton
        fgColorButton.Bind(wx.EVT_COLOURPICKER_CHANGED, self.onFgColorPicked)
        bgColorButton.Bind(wx.EVT_COLOURPICKER_CHANGED, self.onBgColorPicked)
        fontButton.Bind(wx.EVT_FONTPICKER_CHANGED, self.onFontPicked)

    def onFgColorPicked(self, event):  # pylint: disable=W0613
        self._fontButton.SetSelectedColour(self._fgColorButton.GetColour())

    def onBgColorPicked(self, event):  # pylint: disable=W0613
        self._fontButton.SetSelectedBgColour(self._bgColorButton.GetColour())

    def onFontPicked(self, event):  # pylint: disable=W0613
        fontColor = self._fontButton.GetSelectedColour()
        if (
            fontColor != self._fgColorButton.GetColour()
            and fontColor != wx.BLACK
        ):
            self._fgColorButton.SetColour(self._fontButton.GetSelectedColour())
        else:
            self._fontButton.SetSelectedColour(self._fgColorButton.GetColour())


class SettingsPageBase(widgets.ScrolledBookPage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._booleanSettings = []
        self._choiceSettings = []
        self._multipleChoiceSettings = []
        self._integerSettings = []
        self._colorSettings = []
        self._fontSettings = []
        self._iconSettings = []
        self._pathSettings = []
        self._textSettings = []
        self._syncers = []

    def addBooleanSetting(self, section, setting, text, helpText="", **kwargs):
        checkBox = wx.CheckBox(self, -1)
        checkBox.SetValue(self.getboolean(section, setting))
        self.addEntry(text, checkBox, helpText=helpText, **kwargs)
        self._booleanSettings.append((section, setting, checkBox))
        return checkBox

    def addChoiceSetting(
        self, section, setting, text, helpText, *listsOfChoices, **kwargs
    ):
        choiceCtrls = []
        currentValue = self.gettext(section, setting)
        sep = kwargs.pop("sep", "_")
        for choices, currentValuePart in zip(
            listsOfChoices, currentValue.split(sep)
        ):
            choiceCtrl = wx.Choice(self)
            choiceCtrls.append(choiceCtrl)
            for choiceValue, choiceText in choices:
                choiceCtrl.Append(choiceText, choiceValue)
                if choiceValue == currentValuePart:
                    choiceCtrl.SetSelection(choiceCtrl.GetCount() - 1)
            # Force a selection if necessary:
            if choiceCtrl.GetSelection() == wx.NOT_FOUND:
                choiceCtrl.SetSelection(0)
        # pylint: disable=W0142
        self.addEntry(
            text,
            *choiceCtrls,
            helpText=helpText,
            flags=kwargs.get("flags", None)
        )
        self._choiceSettings.append((section, setting, choiceCtrls))
        return choiceCtrls

    def enableChoiceSetting(self, section, setting, enabled):
        for theSection, theSetting, ctrls in self._choiceSettings:
            if theSection == section and theSetting == setting:
                for ctrl in ctrls:
                    ctrl.Enable(enabled)
                break

    def addMultipleChoiceSettings(
        self, section, setting, text, choices, helpText="", **kwargs
    ):
        # choices is a list of (number, text) tuples.
        multipleChoice = wx.CheckListBox(
            self, choices=[choice[1] for choice in choices]
        )
        checkedNumbers = self.getlist(section, setting)
        for index, choice in enumerate(choices):
            multipleChoice.Check(index, choice[0] in checkedNumbers)
        self.addEntry(
            text,
            multipleChoice,
            helpText=helpText,
            growable=kwargs.get("growable", True),
            flags=kwargs.get("flags", None),
        )
        self._multipleChoiceSettings.append(
            (
                section,
                setting,
                multipleChoice,
                [choice[0] for choice in choices],
            )
        )

    def addIntegerSetting(
        self,
        section,
        setting,
        text,
        minimum=0,
        maximum=100,
        helpText="",
        flags=None,
    ):
        intValue = self.getint(section, setting)
        spin = widgets.SpinCtrl(
            self, min=minimum, max=maximum, size=(65, -1), value=intValue
        )
        self.addEntry(text, spin, helpText=helpText, flags=flags)
        self._integerSettings.append((section, setting, spin))

    def addWorkingHoursSetting(self, text, helpText=""):
        """Add a working hours setting with start/end dropdowns and end-of-day checkbox."""
        startHour = self.getint("view", "efforthourstart")
        endHour = self.getint("view", "efforthourend")
        endOfDay = self.getboolean("view", "efforthourend_endofday")

        # Migrate old sentinel value: if endHour >= 24, convert to new format
        if endHour >= 24:
            endHour = 23
            endOfDay = True

        # Create panel to hold the controls
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        hours = [str(h) for h in range(24)]

        # Start hour dropdown (0-23)
        self._workingHourStartChoice = wx.Choice(panel, choices=hours)
        self._workingHourStartChoice.SetSelection(startHour)
        self._workingHourStartChoice.Bind(wx.EVT_CHOICE, self._onWorkingHourStartChanged)
        sizer.Add(self._workingHourStartChoice, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(wx.StaticText(panel, label=_(" to ")), 0, wx.ALIGN_CENTER_VERTICAL)

        # End hour dropdown (0-23)
        self._workingHourEndChoice = wx.Choice(panel, choices=hours)
        self._workingHourEndChoice.SetSelection(endHour)
        self._workingHourEndChoice.Bind(wx.EVT_CHOICE, self._onWorkingHourEndChanged)
        sizer.Add(self._workingHourEndChoice, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add((10, -1))  # Spacer

        # End of day checkbox
        self._workingHourEndOfDayCheck = wx.CheckBox(panel, label=_("End of day"))
        self._workingHourEndOfDayCheck.SetValue(endOfDay)
        self._workingHourEndOfDayCheck.Bind(wx.EVT_CHECKBOX, self._onEndOfDayChecked)
        sizer.Add(self._workingHourEndOfDayCheck, 0, wx.ALIGN_CENTER_VERTICAL)

        panel.SetSizer(sizer)

        # Apply initial state
        if endOfDay:
            self._workingHourEndChoice.SetSelection(23)
            self._workingHourEndChoice.Enable(False)

        self.addEntry(
            text,
            panel,
            helpText=helpText,
        )

    def _onWorkingHourStartChanged(self, event):
        """Ensure at least 1 hour gap when start hour changes."""
        if self._workingHourEndOfDayCheck.IsChecked():
            return  # End of day means midnight, any start hour is valid
        startHour = self._workingHourStartChoice.GetSelection()
        endHour = self._workingHourEndChoice.GetSelection()
        if startHour >= endHour:
            self._workingHourEndChoice.SetSelection(min(startHour + 1, 23))

    def _onWorkingHourEndChanged(self, event):
        """Ensure at least 1 hour gap when end hour changes."""
        startHour = self._workingHourStartChoice.GetSelection()
        endHour = self._workingHourEndChoice.GetSelection()
        if endHour <= startHour:
            self._workingHourStartChoice.SetSelection(max(endHour - 1, 0))

    def _onEndOfDayChecked(self, event):
        """Handle end of day checkbox toggle."""
        if event.IsChecked():
            self._workingHourEndChoice.SetSelection(23)
            self._workingHourEndChoice.Enable(False)
        else:
            self._workingHourEndChoice.Enable(True)

    def _saveWorkingHoursSettings(self):
        """Save working hours settings. Called from ok()."""
        if hasattr(self, '_workingHourStartChoice'):
            self.setint("view", "efforthourstart", self._workingHourStartChoice.GetSelection())
            self.setint("view", "efforthourend", self._workingHourEndChoice.GetSelection())
            self.setboolean("view", "efforthourend_endofday", self._workingHourEndOfDayCheck.IsChecked())

    def addFontSetting(self, section, setting, text):
        default_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        native_info_string = self.gettext(section, setting)
        current_font = (
            wx.FontFromNativeInfoString(native_info_string)
            if native_info_string
            else None
        )
        font_button = widgets.FontPickerCtrl(
            self, font=current_font or default_font, colour=(0, 0, 0, 255),
            bgColour=(255, 255, 255, 255), fixedWidth=75
        )
        self.addEntry(
            text,
            font_button,
            flags=(
                wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL
                | wx.ALIGN_CENTER_VERTICAL,  # wx.EXPAND causes the button to be top aligned on Mac OS X
            ),
        )
        self._fontSettings.append((section, setting, font_button))

    def addAppearanceHeader(self):
        # Row 0: Group headers - "" | Light (spanning 4) | Dark (spanning 4) | ""
        emptyLabel = wx.StaticText(self, label="")
        lightLabel = wx.StaticText(self, label=_("Light Theme"))
        darkLabel = wx.StaticText(self, label=_("Dark Theme"))
        boldFont = lightLabel.GetFont().Bold()
        lightLabel.SetFont(boldFont)
        darkLabel.SetFont(boldFont)

        pos = self._position.next(1)
        self._sizer.Add(emptyLabel, pos, span=(1, 1),
                        flag=wx.ALL | wx.ALIGN_CENTER, border=self._borderWidth)
        pos = self._position.next(4)
        self._sizer.Add(lightLabel, pos, span=(1, 4),
                        flag=wx.ALL | wx.ALIGN_CENTER, border=self._borderWidth)
        pos = self._position.next(4)
        self._sizer.Add(darkLabel, pos, span=(1, 4),
                        flag=wx.ALL | wx.ALIGN_CENTER, border=self._borderWidth)
        # Empty cell for reset column
        self._position.next(1)

        # Row 1: Partial horizontal lines under Light and Dark headers
        self._sizer.Add(wx.StaticLine(self), (1, 1), span=(1, 4),
                        flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=self._borderWidth)
        self._sizer.Add(wx.StaticLine(self), (1, 5), span=(1, 4),
                        flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=self._borderWidth)
        # Advance cursor past the line row
        self._position.next(10)

        # Row 2: Sub-headers
        self.addEntry(
            "",
            _("Foreground"),
            _("Background"),
            _("Font"),
            _("Icon"),
            _("Foreground"),
            _("Background"),
            _("Font"),
            _("Icon"),
            "",
            flags=[wx.ALL | wx.ALIGN_CENTER] * 10,
        )

    def _createIconEntry(self, excluded_icons=None):
        """Create a searchable icon picker with fixed 120px width."""
        excluded = excluded_icons or set()
        iconEntry = widgets.IconPicker(self, "", excluded_icons=excluded, fixedWidth=120)
        # imageNames returned for backward compatibility (unused)
        imageNames = sorted(artprovider.chooseableItems.keys(), key=lambda k: artprovider.chooseableItems[k]["name"])
        return iconEntry, imageNames

    def _createAppearanceControls(self, fgColorSection, fgColorSetting,
                                   bgColorSection, bgColorSetting,
                                   fontSection, fontSetting,
                                   iconSection, iconSetting):
        """Create a set of appearance controls (fg, bg, font, icon) for one theme."""
        currentFgColor = self.getvalue(fgColorSection, fgColorSetting)
        fgColorButton = widgets.ColourPickerCtrl(self, colour=wx.Colour(*currentFgColor))
        currentBgColor = self.getvalue(bgColorSection, bgColorSetting)
        bgColorButton = widgets.ColourPickerCtrl(self, colour=wx.Colour(*currentBgColor))
        defaultFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        nativeInfoString = self.gettext(fontSection, fontSetting)
        currentFont = (
            wx.FontFromNativeInfoString(nativeInfoString)
            if nativeInfoString
            else None
        )
        fontButton = widgets.FontPickerCtrl(
            self, font=currentFont or defaultFont, colour=currentFgColor,
            bgColour=currentBgColor, fixedWidth=75
        )
        excluded = getattr(self, '_objectIcons', None)
        iconEntry, imageNames = self._createIconEntry(excluded_icons=excluded)
        currentIcon = self.gettext(iconSection, iconSetting)
        iconEntry.SetValue(currentIcon)

        self._colorSettings.append((fgColorSection, fgColorSetting, fgColorButton))
        self._colorSettings.append((bgColorSection, bgColorSetting, bgColorButton))
        self._iconSettings.append((iconSection, iconSetting, iconEntry))
        self._fontSettings.append((fontSection, fontSetting, fontButton))
        self._syncers.append(FontColorSyncer(fgColorButton, bgColorButton, fontButton))

        return fgColorButton, bgColorButton, fontButton, iconEntry

    def addAppearanceSetting(
        self,
        fgColorSection,
        fgColorSetting,
        bgColorSection,
        bgColorSetting,
        fontSection,
        fontSetting,
        iconSection,
        iconSetting,
        text,
    ):
        # Light controls
        lightFg, lightBg, lightFont, lightIcon = self._createAppearanceControls(
            fgColorSection, fgColorSetting,
            bgColorSection, bgColorSetting,
            fontSection, fontSetting,
            iconSection, iconSetting,
        )
        # Dark controls
        darkFg, darkBg, darkFont, darkIcon = self._createAppearanceControls(
            fgColorSection + "_dark", fgColorSetting,
            bgColorSection + "_dark", bgColorSetting,
            fontSection + "_dark", fontSetting,
            iconSection + "_dark", iconSetting,
        )

        # Reset button
        resetBtn = wx.Button(self, label=_("Reset"), size=(60, -1))
        resetBtn.Bind(wx.EVT_BUTTON, lambda evt, s=fgColorSetting,
                      lf=lightFg, lb=lightBg, lfn=lightFont, li=lightIcon,
                      df=darkFg, db=darkBg, dfn=darkFont, di=darkIcon:
                      self._onResetAppearanceRow(s, lf, lb, lfn, li, df, db, dfn, di))

        self.addEntry(
            text,
            lightFg, lightBg, lightFont, lightIcon,
            darkFg, darkBg, darkFont, darkIcon,
            resetBtn,
            flags=(
                wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER_VERTICAL,
            ),
        )

    def _onResetAppearanceRow(self, setting, lightFg, lightBg, lightFont, lightIcon,
                              darkFg, darkBg, darkFont, darkIcon):
        """Reset all appearance controls in a row to their defaults."""
        import ast
        from taskcoachlib.config import defaults as defaults_mod
        defs = defaults_mod.defaults
        defaultSysFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)

        # Reset light theme
        lfgColor = wx.Colour(*ast.literal_eval(defs["fgcolor"][setting]))
        lbgColor = wx.Colour(*ast.literal_eval(defs["bgcolor"][setting]))
        lightFg.SetColour(lfgColor)
        lightBg.SetColour(lbgColor)
        lightFont.SetSelectedFont(defaultSysFont)
        lightFont.SetSelectedColour(lfgColor)
        lightFont.SetSelectedBgColour(lbgColor)
        lightIcon.SetValue(defs["icon"][setting])

        # Reset dark theme
        dfgColor = wx.Colour(*ast.literal_eval(defs["fgcolor_dark"][setting]))
        dbgColor = wx.Colour(*ast.literal_eval(defs["bgcolor_dark"][setting]))
        darkFg.SetColour(dfgColor)
        darkBg.SetColour(dbgColor)
        darkFont.SetSelectedFont(defaultSysFont)
        darkFont.SetSelectedColour(dfgColor)
        darkFont.SetSelectedBgColour(dbgColor)
        darkIcon.SetValue(defs["icon_dark"][setting])

    def addPathSetting(self, section, setting, text, helpText="", **kwargs):
        pathChooser = widgets.DirectoryChooser(self, wx.ID_ANY)
        pathChooser.SetPath(self.gettext(section, setting))
        self.addEntry(text, pathChooser, helpText=helpText, **kwargs)
        self._pathSettings.append((section, setting, pathChooser))

    def addTextSetting(self, section, setting, text, helpText="", **kwargs):
        textChooser = wx.TextCtrl(
            self, wx.ID_ANY, self.gettext(section, setting)
        )
        self.addEntry(text, textChooser, helpText=helpText, **kwargs)
        self._textSettings.append((section, setting, textChooser))

    def setTextSetting(self, section, setting, value):
        for theSection, theSetting, textChooser in self._textSettings:
            if theSection == section and theSetting == setting:
                textChooser.SetValue(value)

    def enableTextSetting(self, section, setting, enabled):
        for theSection, theSetting, textChooser in self._textSettings:
            if theSection == section and theSetting == setting:
                textChooser.Enable(enabled)
                break

    def addText(self, label, text, **kwargs):
        self.addEntry(label, text, **kwargs)

    def ok(self):
        for section, setting, checkBox in self._booleanSettings:
            self.setboolean(section, setting, checkBox.IsChecked())
        for section, setting, choiceCtrls in self._choiceSettings:
            value = "_".join(
                [
                    choice.GetClientData(choice.GetSelection())
                    for choice in choiceCtrls
                ]
            )
            self.settext(section, setting, value)
        for (
            section,
            setting,
            multipleChoice,
            choices,
        ) in self._multipleChoiceSettings:
            self.setlist(
                section,
                setting,
                [
                    choices[index]
                    for index in range(len(choices))
                    if multipleChoice.IsChecked(index)
                ],
            )
        for section, setting, spin in self._integerSettings:
            self.setint(section, setting, spin.GetValue())
        for section, setting, colorButton in self._colorSettings:
            self.setvalue(section, setting, colorButton.GetColour())
        for section, setting, fontButton in self._fontSettings:
            selectedFont = fontButton.GetSelectedFont()
            defaultFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            fontInfoDesc = (
                ""
                if selectedFont == defaultFont
                else selectedFont.GetNativeFontInfoDesc()
            )
            self.settext(section, setting, fontInfoDesc)
        for section, setting, iconEntry in self._iconSettings:
            iconName = iconEntry.GetValue()
            self.settext(section, setting, iconName)
        for section, setting, btn in self._pathSettings:
            self.settext(section, setting, btn.GetPath())
        for section, setting, txt in self._textSettings:
            self.settext(section, setting, txt.GetValue())

    def get(self, section, name):
        raise NotImplementedError

    def set(self, section, name, value):
        raise NotImplementedError

    def getint(self, section, name):
        return int(self.get(section, name))

    def setint(self, section, name, value):
        self.set(section, name, str(value))

    def setboolean(self, section, name, value):
        self.set(section, name, str(value))

    def getboolean(self, section, name):
        return self.get(section, name) == "True"

    def settext(self, section, name, value):
        self.set(section, name, value)

    def gettext(self, section, name):
        return self.get(section, name)

    def getlist(self, section, name):
        return ast.literal_eval(self.get(section, name))

    def setlist(self, section, name, value):
        self.set(section, name, str(value))

    def getvalue(self, section, name):
        return ast.literal_eval(self.get(section, name))

    def setvalue(self, section, name, value):
        self.set(section, name, str(value))


class SettingsPage(SettingsPageBase):
    _labelWidth = 300
    _helpWidth = None  # Subclasses can set to wrap help text at fixed width

    def __init__(self, settings=None, taskFile=None, *args, **kwargs):
        self.settings = settings
        self.taskFile = taskFile
        super().__init__(*args, **kwargs)

    def fit(self):
        """Wrap column 0 labels at fixed width before layout."""
        for item in self._sizer.GetChildren():
            pos = item.GetPos()
            if pos.GetCol() == 0 and item.GetSpan().GetColspan() == 1:
                window = item.GetWindow()
                if window and isinstance(window, wx.StaticText):
                    window.Wrap(self._labelWidth)
        super().fit()

    def addEntry(self, text, *controls, **kwargs):  # pylint: disable=W0221
        helpText = kwargs.pop("helpText", "")
        if helpText == "restart":
            helpText = (
                _("This setting will take effect after you restart %s")
                % meta.name
            )
        elif helpText == "override":
            helpText = _(
                "This setting can be overridden for individual tasks "
                "in the task edit dialog."
            )
        if helpText:
            helpCtrl = wx.StaticText(self, label=helpText)
            helpCtrl.SetForegroundColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            if self._helpWidth:
                helpCtrl.Wrap(self._helpWidth)
            controls = controls + (helpCtrl,)
        super().addEntry(text, *controls, **kwargs)

    def get(self, section, name):
        return self.settings.get(section, name)

    def set(self, section, name, value):
        if section is not None:
            self.settings.set(section, name, value)

    def getint(self, section, name):
        return self.settings.getint(section, name)

    def setint(self, section, name, value):
        self.settings.setint(section, name, value)

    def getboolean(self, section, name):
        return self.settings.getboolean(section, name)

    def setboolean(self, section, name, value):
        if section is not None:
            self.settings.setboolean(section, name, value)

    def settext(self, section, name, value):
        self.settings.settext(section, name, value)

    def gettext(self, section, name):
        return self.settings.gettext(section, name)

    def setvalue(self, section, name, value):
        self.settings.setvalue(section, name, value)

    def getvalue(self, section, name):
        return self.settings.getvalue(section, name)

    def setlist(self, section, name, value):
        self.settings.setlist(section, name, value)

    def getlist(self, section, name):
        return self.settings.getlist(section, name)


class SavePage(SettingsPage):
    pageName = "save"
    pageTitle = _("Files")
    pageIcon = "save"
    _helpWidth = 500

    def __init__(self, *args, **kwargs):
        super().__init__(columns=3, *args, **kwargs)
        self.addBooleanSetting(
            "file",
            "autosave",
            _("Auto save after every change"),
        )
        self.addBooleanSetting(
            "file",
            "autoload",
            _("Auto load when the file changes on disk"),
        )
        self.addBooleanSetting(
            "file",
            "fspoll",
            _("Use polling for file monitoring"),
            _(
                "Use slow polling (every 10s) instead of efficient OS notifications. Enable this if your task file is on a network share. You must restart %s after changing this."
            )
            % meta.name,
        )
        self.addBooleanSetting(
            "file",
            "saveinifileinprogramdir",
            _(
                "Save settings (%s.ini) in the same "
                "directory as the program"
            )
            % meta.filename,
            _("For running %s from a removable medium") % meta.name,
        )
        self.addPathSetting(
            "file",
            "attachmentbase",
            _("Attachment base directory"),
            _(
                "When adding an attachment, try to make "
                "its path relative to this one."
            ),
        )
        self.addMultipleChoiceSettings(
            "file",
            "autoimport",
            _("Before saving, automatically import from"),
            [("Todo.txt", _("Todo.txt format"))],
            helpText=_(
                "Before saving, %s automatically imports tasks "
                "from a Todo.txt file with the same name as the task file, "
                "but with extension .txt"
            )
            % meta.name,
            growable=False,
        )
        self.addMultipleChoiceSettings(
            "file",
            "autoexport",
            _("When saving, automatically export to"),
            [("Todo.txt", _("Todo.txt format"))],
            helpText=_(
                "When saving, %s automatically exports tasks "
                "to a Todo.txt file with the same name as the task file, "
                "but with extension .txt"
            )
            % meta.name,
            growable=False,
        )
        self.fit()


class WindowBehaviorPage(SettingsPage):
    pageName = "window"
    pageTitle = _("Windows")
    pageIcon = "windows"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, growableColumn=-1, *args, **kwargs)
        self.addBooleanSetting(
            "window",
            "tips",
            _("Show tips window on startup"),
        )
        self.addChoiceSetting(
            "window",
            "starticonized",
            _("Start with the main window iconized"),
            "",
            [
                ("Never", _("Never")),
                ("Always", _("Always")),
                ("WhenClosedIconized", _("If it was iconized last session")),
            ],
        )
        self.addBooleanSetting(
            "version",
            "notify",
            _("Check for new version of %(name)s on startup")
            % meta.data.metaDict,
        )
        self.addBooleanSetting(
            "view",
            "developermessages",
            _("Check for messages from the %(name)s developers on startup")
            % meta.data.metaDict,
        )
        self.addBooleanSetting(
            "window",
            "hidewheniconized",
            _("Hide main window when iconized"),
        )
        self.addBooleanSetting(
            "window",
            "hidewhenclosed",
            _("Minimize main window when closed"),
        )
        self.addBooleanSetting(
            "window",
            "blinktaskbariconwhentrackingeffort",
            _("Make clock in the task bar tick when tracking effort"),
        )
        self.fit()


class ThemePage(SettingsPage):
    pageName = "theme"
    pageTitle = _("Theme")
    pageIcon = "fsview_icon"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=6, growableColumn=-1, *args, **kwargs)

        # --- Mode Dropdown ---
        is_dark = detect_dark_theme()
        self._isDark = is_dark
        detected = _("Dark") if is_dark else _("Light")

        themeChoice = wx.Choice(self)
        currentTheme = self.gettext("window", "theme")
        for choiceValue, choiceText in [
            ("light", _("Light Theme (Forced)")),
            ("dark", _("Dark Theme (Forced)")),
            ("automatic", _("Automatic (detect from system)")),
        ]:
            themeChoice.Append(choiceText, choiceValue)
            if choiceValue == currentTheme:
                themeChoice.SetSelection(themeChoice.GetCount() - 1)
        if themeChoice.GetSelection() == wx.NOT_FOUND:
            themeChoice.SetSelection(0)

        self._detectedThemeLabel = wx.StaticText(self, label=_("(Detected: %s)") % detected)
        self._detectedThemeLabel.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        modePanel = wx.Panel(self)
        modeSizer = wx.BoxSizer(wx.HORIZONTAL)
        themeChoice.Reparent(modePanel)
        self._detectedThemeLabel.Reparent(modePanel)
        modeSizer.Add(themeChoice, 0, wx.ALIGN_CENTER_VERTICAL)
        modeSizer.Add(self._detectedThemeLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        modePanel.SetSizer(modeSizer)

        self.addEntry(
            _("Mode"),
            modePanel,
            flags=[
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
            ],
        )
        self._choiceSettings.append(("window", "theme", [themeChoice]))

        self.addLine()

        # --- Section: Calendar ---
        self.addEntry(
            _("Calendar"),
            _("System"),
            _("Light"),
            _("System"),
            _("Dark"),
            "",
            flags=[
                wx.ALL | wx.ALIGN_LEFT,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL,
            ],
        )

        from taskcoachlib.config import defaults as defaults_mod

        calendarRowsBefore = [
            ("weekday_header_bg", _("Weekday Header Background")),
            ("weekday_header_fg", _("Weekday Header Foreground")),
        ]
        calendarRowsAfter = [
            ("weekend_day_fg", _("Weekend Day Foreground")),
            ("today_border", _("Today Border")),
        ]

        for settingKey, labelText in calendarRowsBefore:
            lightColor = self.getvalue("calendar_light", settingKey)
            darkColor = self.getvalue("calendar_dark", settingKey)

            lightPicker = widgets.ColourPickerCtrl(self, colour=wx.Colour(*lightColor))
            darkPicker = widgets.ColourPickerCtrl(self, colour=wx.Colour(*darkColor))

            lightPicker.Bind(wx.EVT_COLOURPICKER_CHANGED,
                lambda evt, s="calendar_light", k=settingKey, p=lightPicker:
                    self._onColourChanged(s, k, p))
            darkPicker.Bind(wx.EVT_COLOURPICKER_CHANGED,
                lambda evt, s="calendar_dark", k=settingKey, p=darkPicker:
                    self._onColourChanged(s, k, p))

            resetBtn = wx.Button(self, label=_("Reset"), size=(60, -1))
            lightDefault = ast.literal_eval(defaults_mod.defaults["calendar_light"][settingKey])
            darkDefault = ast.literal_eval(defaults_mod.defaults["calendar_dark"][settingKey])
            resetBtn.Bind(wx.EVT_BUTTON,
                lambda evt, lp=lightPicker, dp=darkPicker, ld=lightDefault, dd=darkDefault, k=settingKey:
                    self._onReset(lp, dp, ld, dd, k))

            self.addEntry(
                labelText,
                "",
                lightPicker,
                "",
                darkPicker,
                resetBtn,
                flags=[
                    wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                ],
            )

            self._colorSettings.append(("calendar_light", settingKey, lightPicker))
            self._colorSettings.append(("calendar_dark", settingKey, darkPicker))

        # --- Other Month Days BG (with "System" checkbox) ---
        lightOtherMonthColor = self.getvalue("calendar_light", "other_month_bg")
        darkOtherMonthColor = self.getvalue("calendar_dark", "other_month_bg")
        lightUseSystem = self.getboolean("calendar_light", "other_month_bg_system")
        darkUseSystem = self.getboolean("calendar_dark", "other_month_bg_system")

        self._otherMonthLightCheck = wx.CheckBox(self)
        self._otherMonthLightCheck.SetValue(lightUseSystem)

        # Light: panel containing both picker and N/A label (only one visible)
        self._otherMonthLightPanel = wx.Panel(self)
        lightPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self._otherMonthLightPicker = widgets.ColourPickerCtrl(
            self._otherMonthLightPanel, colour=wx.Colour(*lightOtherMonthColor))
        self._otherMonthLightNA = wx.StaticText(
            self._otherMonthLightPanel, label=_("N/A"),
            style=wx.ALIGN_CENTER_HORIZONTAL | wx.ST_NO_AUTORESIZE)
        self._otherMonthLightNA.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        lightPanelSizer.Add(self._otherMonthLightPicker, 0, wx.ALIGN_CENTER_VERTICAL)
        lightPanelSizer.Add(self._otherMonthLightNA, 1, wx.ALIGN_CENTER_VERTICAL)
        self._otherMonthLightPanel.SetSizer(lightPanelSizer)
        self._otherMonthLightPanel.SetMinSize(self._otherMonthLightPicker.GetBestSize())

        self._otherMonthDarkCheck = wx.CheckBox(self)
        self._otherMonthDarkCheck.SetValue(darkUseSystem)

        # Dark: panel containing both picker and N/A label (only one visible)
        self._otherMonthDarkPanel = wx.Panel(self)
        darkPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self._otherMonthDarkPicker = widgets.ColourPickerCtrl(
            self._otherMonthDarkPanel, colour=wx.Colour(*darkOtherMonthColor))
        self._otherMonthDarkNA = wx.StaticText(
            self._otherMonthDarkPanel, label=_("N/A"),
            style=wx.ALIGN_CENTER_HORIZONTAL | wx.ST_NO_AUTORESIZE)
        self._otherMonthDarkNA.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        darkPanelSizer.Add(self._otherMonthDarkPicker, 0, wx.ALIGN_CENTER_VERTICAL)
        darkPanelSizer.Add(self._otherMonthDarkNA, 1, wx.ALIGN_CENTER_VERTICAL)
        self._otherMonthDarkPanel.SetSizer(darkPanelSizer)
        self._otherMonthDarkPanel.SetMinSize(self._otherMonthDarkPicker.GetBestSize())

        # Set initial visibility based on system theme match:
        # - System checked + column matches current theme → show picker with system color
        # - System checked + column doesn't match → show N/A
        # - System unchecked → show picker with custom color
        lightShowNA = lightUseSystem and self._isDark  # light col, system checked, but we're in dark
        darkShowNA = darkUseSystem and not self._isDark  # dark col, system checked, but we're in light
        self._otherMonthLightPicker.Show(not lightShowNA)
        self._otherMonthLightNA.Show(lightShowNA)
        self._otherMonthDarkPicker.Show(not darkShowNA)
        self._otherMonthDarkNA.Show(darkShowNA)
        # When system is checked and theme matches, show the actual system color
        if lightUseSystem and not self._isDark:
            self._otherMonthLightPicker.SetColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
        if darkUseSystem and self._isDark:
            self._otherMonthDarkPicker.SetColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))

        self._otherMonthLightCheck.Bind(wx.EVT_CHECKBOX,
            lambda evt: self._onOtherMonthSystemToggle("light"))
        self._otherMonthDarkCheck.Bind(wx.EVT_CHECKBOX,
            lambda evt: self._onOtherMonthSystemToggle("dark"))
        self._otherMonthLightPicker.Bind(wx.EVT_COLOURPICKER_CHANGED,
            lambda evt: self._onOtherMonthColorPicked("light"))
        self._otherMonthDarkPicker.Bind(wx.EVT_COLOURPICKER_CHANGED,
            lambda evt: self._onOtherMonthColorPicked("dark"))

        otherMonthResetBtn = wx.Button(self, label=_("Reset"), size=(60, -1))
        otherMonthResetBtn.Bind(wx.EVT_BUTTON, self._onResetOtherMonth)

        self.addEntry(
            _("Other Months Days Background"),
            self._otherMonthLightCheck,
            self._otherMonthLightPanel,
            self._otherMonthDarkCheck,
            self._otherMonthDarkPanel,
            otherMonthResetBtn,
            flags=[
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
            ],
        )

        for settingKey, labelText in calendarRowsAfter:
            lightColor = self.getvalue("calendar_light", settingKey)
            darkColor = self.getvalue("calendar_dark", settingKey)

            lightPicker = widgets.ColourPickerCtrl(self, colour=wx.Colour(*lightColor))
            darkPicker = widgets.ColourPickerCtrl(self, colour=wx.Colour(*darkColor))

            lightPicker.Bind(wx.EVT_COLOURPICKER_CHANGED,
                lambda evt, s="calendar_light", k=settingKey, p=lightPicker:
                    self._onColourChanged(s, k, p))
            darkPicker.Bind(wx.EVT_COLOURPICKER_CHANGED,
                lambda evt, s="calendar_dark", k=settingKey, p=darkPicker:
                    self._onColourChanged(s, k, p))

            resetBtn = wx.Button(self, label=_("Reset"), size=(60, -1))
            lightDefault = ast.literal_eval(defaults_mod.defaults["calendar_light"][settingKey])
            darkDefault = ast.literal_eval(defaults_mod.defaults["calendar_dark"][settingKey])
            resetBtn.Bind(wx.EVT_BUTTON,
                lambda evt, lp=lightPicker, dp=darkPicker, ld=lightDefault, dd=darkDefault, k=settingKey:
                    self._onReset(lp, dp, ld, dd, k))

            self.addEntry(
                labelText,
                "",
                lightPicker,
                "",
                darkPicker,
                resetBtn,
                flags=[
                    wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                ],
            )

            self._colorSettings.append(("calendar_light", settingKey, lightPicker))
            self._colorSettings.append(("calendar_dark", settingKey, darkPicker))

        # --- Section: Spellcheck ---
        self.addLine()
        self.addEntry(
            _("Spellcheck"),
            "",
            _("Light"),
            "",
            _("Dark"),
            "",
            flags=[
                wx.ALL | wx.ALIGN_LEFT,
                wx.ALL,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL,
            ],
        )

        lightSquiggleColor = self.getvalue("spellcheck_light", "squiggle_color")
        darkSquiggleColor = self.getvalue("spellcheck_dark", "squiggle_color")

        lightSquigglePicker = widgets.ColourPickerCtrl(
            self, colour=wx.Colour(*lightSquiggleColor))
        darkSquigglePicker = widgets.ColourPickerCtrl(
            self, colour=wx.Colour(*darkSquiggleColor))

        lightSquigglePicker.Bind(wx.EVT_COLOURPICKER_CHANGED,
            lambda evt, s="spellcheck_light", k="squiggle_color", p=lightSquigglePicker:
                self._onSquiggleColourChanged(s, k, p))
        darkSquigglePicker.Bind(wx.EVT_COLOURPICKER_CHANGED,
            lambda evt, s="spellcheck_dark", k="squiggle_color", p=darkSquigglePicker:
                self._onSquiggleColourChanged(s, k, p))

        squiggleResetBtn = wx.Button(self, label=_("Reset"), size=(60, -1))
        squiggleLightDefault = ast.literal_eval(
            defaults_mod.defaults["spellcheck_light"]["squiggle_color"])
        squiggleDarkDefault = ast.literal_eval(
            defaults_mod.defaults["spellcheck_dark"]["squiggle_color"])
        squiggleResetBtn.Bind(wx.EVT_BUTTON,
            lambda evt, lp=lightSquigglePicker, dp=darkSquigglePicker,
                   ld=squiggleLightDefault, dd=squiggleDarkDefault:
                self._onResetSquiggle(lp, dp, ld, dd))

        self.addEntry(
            _("Scintilla (Squiggle)"),
            "",
            lightSquigglePicker,
            "",
            darkSquigglePicker,
            squiggleResetBtn,
            flags=[
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
            ],
        )

        self._colorSettings.append(("spellcheck_light", "squiggle_color", lightSquigglePicker))
        self._colorSettings.append(("spellcheck_dark", "squiggle_color", darkSquigglePicker))

        # Detect system theme changes while preferences are open
        self.Bind(wx.EVT_IDLE, self._onIdle)

        self.fit()

    def _onColourChanged(self, section, key, picker):
        colour = picker.GetColour()
        self.setvalue(section, key, colour)
        pub.sendMessage('calendar.colours.changed')

    def _onReset(self, lightPicker, darkPicker, lightDefault, darkDefault, key):
        lightPicker.SetColour(wx.Colour(*lightDefault))
        darkPicker.SetColour(wx.Colour(*darkDefault))
        self.setvalue("calendar_light", key, lightPicker.GetColour())
        self.setvalue("calendar_dark", key, darkPicker.GetColour())
        pub.sendMessage('calendar.colours.changed')

    def _onOtherMonthSystemToggle(self, theme):
        if theme == "light":
            checked = self._otherMonthLightCheck.IsChecked()
            self.setboolean("calendar_light", "other_month_bg_system", checked)
            # N/A only when system checked but we can't show the color (wrong theme)
            showNA = checked and self._isDark
            self._otherMonthLightPicker.Show(not showNA)
            self._otherMonthLightNA.Show(showNA)
            if checked and not self._isDark:
                # Matching theme: show system color in picker
                self._otherMonthLightPicker.SetColour(
                    wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
            self._otherMonthLightPanel.Layout()
        else:
            checked = self._otherMonthDarkCheck.IsChecked()
            self.setboolean("calendar_dark", "other_month_bg_system", checked)
            showNA = checked and not self._isDark
            self._otherMonthDarkPicker.Show(not showNA)
            self._otherMonthDarkNA.Show(showNA)
            if checked and self._isDark:
                # Matching theme: show system color in picker
                self._otherMonthDarkPicker.SetColour(
                    wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
            self._otherMonthDarkPanel.Layout()
        pub.sendMessage('calendar.colours.changed')

    def _onOtherMonthColorPicked(self, theme):
        if theme == "light":
            picked = self._otherMonthLightPicker.GetColour()
            self._otherMonthLightCheck.SetValue(False)
            self.setboolean("calendar_light", "other_month_bg_system", False)
            self.setvalue("calendar_light", "other_month_bg", picked)
        else:
            picked = self._otherMonthDarkPicker.GetColour()
            self._otherMonthDarkCheck.SetValue(False)
            self.setboolean("calendar_dark", "other_month_bg_system", False)
            self.setvalue("calendar_dark", "other_month_bg", picked)
        pub.sendMessage('calendar.colours.changed')

    def _onResetOtherMonth(self, event):
        from taskcoachlib.config import defaults as defaults_mod
        # Light: reset to system
        self._otherMonthLightCheck.SetValue(True)
        self.setboolean("calendar_light", "other_month_bg_system", True)
        lightShowNA = self._isDark  # can't show system color if we're in dark
        if not lightShowNA:
            self._otherMonthLightPicker.SetColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
        self._otherMonthLightPicker.Show(not lightShowNA)
        self._otherMonthLightNA.Show(lightShowNA)
        self._otherMonthLightPanel.Layout()
        # Dark: reset to specified default (custom color, system unchecked)
        darkDefault = ast.literal_eval(
            defaults_mod.defaults["calendar_dark"]["other_month_bg"])
        self._otherMonthDarkPicker.SetColour(wx.Colour(*darkDefault))
        self._otherMonthDarkCheck.SetValue(False)
        self.setvalue("calendar_dark", "other_month_bg",
                      self._otherMonthDarkPicker.GetColour())
        self.setboolean("calendar_dark", "other_month_bg_system", False)
        self._otherMonthDarkPicker.Show()
        self._otherMonthDarkNA.Hide()
        self._otherMonthDarkPanel.Layout()
        pub.sendMessage('calendar.colours.changed')

    def _onSquiggleColourChanged(self, section, key, picker):
        colour = picker.GetColour()
        self.setvalue(section, key, colour)
        pub.sendMessage('spellcheck.colours.changed')

    def _onResetSquiggle(self, lightPicker, darkPicker, lightDefault, darkDefault):
        lightPicker.SetColour(wx.Colour(*lightDefault))
        darkPicker.SetColour(wx.Colour(*darkDefault))
        self.setvalue("spellcheck_light", "squiggle_color", lightPicker.GetColour())
        self.setvalue("spellcheck_dark", "squiggle_color", darkPicker.GetColour())
        pub.sendMessage('spellcheck.colours.changed')

    def _onIdle(self, event):
        """Check if system theme changed and update UI accordingly."""
        from taskcoachlib.application.application import detect_dark_theme
        currentDark = detect_dark_theme()
        if currentDark != self._isDark:
            self._isDark = currentDark
            # Update detected label
            detected = _("Dark") if self._isDark else _("Light")
            self._detectedThemeLabel.SetLabel(_("(Detected: %s)") % detected)
            # Update Other Month picker/N/A visibility
            lightChecked = self._otherMonthLightCheck.IsChecked()
            darkChecked = self._otherMonthDarkCheck.IsChecked()
            lightShowNA = lightChecked and self._isDark
            darkShowNA = darkChecked and not self._isDark
            self._otherMonthLightPicker.Show(not lightShowNA)
            self._otherMonthLightNA.Show(lightShowNA)
            if lightChecked and not self._isDark:
                self._otherMonthLightPicker.SetColour(
                    wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
            self._otherMonthLightPanel.Layout()
            self._otherMonthDarkPicker.Show(not darkShowNA)
            self._otherMonthDarkNA.Show(darkShowNA)
            if darkChecked and self._isDark:
                self._otherMonthDarkPicker.SetColour(
                    wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
            self._otherMonthDarkPanel.Layout()
        event.Skip()


class LanguagePage(SettingsPage):
    pageName = "language"
    pageTitle = _("Regional")
    pageIcon = "person_talking_icon"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=3, *args, **kwargs)

        # === LANGUAGE SECTION ===
        # Restart warning above the dropdown (covers language and format changes)
        self._restartWarningBase = _("Changing the language or date/time format requires a restart of %s.") % meta.name
        self._restartWarning = wx.StaticText(self, label=self._restartWarningBase)
        self._restartWarningDefaultColor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        self._restartWarning.SetForegroundColour(self._restartWarningDefaultColor)
        self.addEntry("", self._restartWarning)

        languages = [
            ("ar", "الْعَرَبيّة (Arabic)"),
            ("eu_ES", "Euskal Herria (Basque)"),
            ("be_BY", "беларуская мова (Belarusian)"),
            ("bs_BA", "босански (Bosnian)"),
            ("pt_BR", "Português brasileiro (Brazilian Portuguese)"),
            ("br_FR", "Brezhoneg (Breton)"),
            ("bg_BG", "български (Bulgarian)"),
            ("ca_ES", "Català (Catalan)"),
            ("zh_CN", "简体中文 (Simplified Chinese)"),
            ("zh_TW", "正體字 (Traditional Chinese)"),
            ("cs_CS", "Čeština (Czech)"),
            ("da_DA", "Dansk (Danish)"),
            ("nl_NL", "Nederlands (Dutch)"),
            ("en_AU", "English (Australia)"),
            ("en_CA", "English (Canada)"),
            ("en_GB", "English (UK)"),
            ("en_US", "English (US)"),
            ("eo", "Esperanto"),
            ("et_EE", "Eesti keel (Estonian)"),
            ("fi_FI", "Suomi (Finnish)"),
            ("fr_FR", "Français (French)"),
            ("gl_ES", "Galego (Galician)"),
            ("de_DE", "Deutsch (German)"),
            ("nds_DE", "Niederdeutsche Sprache (Low German)"),
            ("el_GR", "ελληνικά (Greek)"),
            ("he_IL", "עברית (Hebrew)"),
            ("hi_IN", "हिन्दी, हिंदी (Hindi)"),
            ("hu_HU", "Magyar (Hungarian)"),
            ("id_ID", "Bahasa Indonesia (Indonesian)"),
            ("it_IT", "Italiano (Italian)"),
            ("ja_JP", "日本語 (Japanese)"),
            ("ko_KO", "한국어/조선말 (Korean)"),
            ("lv_LV", "Latviešu (Latvian)"),
            ("lt_LT", "Lietuvių kalba (Lithuanian)"),
            ("mr_IN", "मराठी Marāṭhī (Marathi)"),
            ("mn_CN", "Монгол бичиг (Mongolian)"),
            ("nb_NO", "Bokmål (Norwegian Bokmal)"),
            ("nn_NO", "Nynorsk (Norwegian Nynorsk)"),
            ("oc_FR", "Lenga d'òc (Occitan)"),
            ("pap", "Papiamentu (Papiamento)"),
            ("fa_IR", "فارسی (Persian)"),
            ("pl_PL", "Język polski (Polish)"),
            ("pt_PT", "Português (Portuguese)"),
            ("ro_RO", "Română (Romanian)"),
            ("ru_RU", "Русский (Russian)"),
            ("sk_SK", "Slovenčina (Slovak)"),
            ("sl_SI", "Slovenski jezik (Slovene)"),
            ("es_ES", "Español (Spanish)"),
            ("sv_SE", "Svenska (Swedish)"),
            ("te_IN", "తెలుగు (Telugu)"),
            ("th_TH", "ภาษาไทย (Thai)"),
            ("tr_TR", "Türkçe (Turkish)"),
            ("uk_UA", "украї́нська мо́ва (Ukranian)"),
            ("vi_VI", "tiếng Việt (Vietnamese)"),
        ]
        choices = [("", _("Let the system determine the language"))]
        allLanguages = dict(list(data.languages.values()))
        for code, label in languages:
            if code == "en_US":
                label = "English (US)"
                enabled = True
            elif code in allLanguages:
                enabled = allLanguages[code]
            elif "_" in code:
                enabled = allLanguages.get(code.split("_")[0], False)
            else:
                enabled = False
            if enabled:
                choices.append((code, label))
        # Don't use '_' as separator since we don't have different choice
        # controls for language and country (but maybe we should?)
        self.addChoiceSetting(
            "view",
            "language_set_by_user",
            _("Language"),
            "",
            choices,
            sep="-",
        )

        # Combined panel for locale warning and help text (single row to avoid GridBagSizer collapse issues)
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Locale warning - only shown when selected locale is not installed
        self._localeWarning = wx.StaticText(
            panel,
            label=_("WARNING: The selected language's locale is not installed on your system. "
                    "Some date and time formats may appear in your system's format instead.")
        )
        self._localeWarning.SetForegroundColour(wx.Colour(180, 0, 0))
        sizer.Add(self._localeWarning, 0, wx.BOTTOM, 10)

        # Help text
        text = wx.StaticText(
            panel,
            label=_(
                "Language missing or translation needs improving? Open an issue or pull request:"
            ),
        )
        text.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        sizer.Add(text)
        url = meta.github_url + "/issues"
        urlCtrl = HyperLinkCtrl(panel, -1, label=url, URL=url)
        sizer.Add(urlCtrl, 0, wx.TOP, 2)
        panel.SetSizer(sizer)
        self.addEntry("", panel)

        # Store original language to detect changes
        self._originalLanguage = self._getSelectedLanguageCode()

        # Check if current language has locale installed and update warning visibility
        self._updateLocaleWarning()

        # Bind to dropdown change to update warnings dynamically
        for section, setting, choiceCtrls in self._choiceSettings:
            if setting == "language_set_by_user":
                choiceCtrls[0].Bind(wx.EVT_CHOICE, self._onLanguageChange)

        # Separator line between language and date/time format sections
        self.addLine()

        # === DATE FORMAT SECTION ===
        # Date format dropdown with detected format label
        dateFormatPanel = wx.Panel(self)
        dateFormatSizer = wx.BoxSizer(wx.HORIZONTAL)

        # Date format choices: value is the format string (e.g., "YMD-", "MDY/")
        self._dateFormatChoice = wx.Choice(dateFormatPanel)
        dateFormats = [
            ("", _("Automatic (detect from system)")),
            ("YMD-", _("YYYY-MM-DD (ISO format)")),
            ("YMD/", _("YYYY/MM/DD (East Asian)")),
            ("MDY/", _("MM/DD/YYYY (US)")),
            ("DMY/", _("DD/MM/YYYY (European)")),
            ("DMY.", _("DD.MM.YYYY (German)")),
        ]
        currentFormat = self.gettext("view", "dateformat")
        selectedIdx = 0
        for i, (value, label) in enumerate(dateFormats):
            self._dateFormatChoice.Append(label, value)
            if value == currentFormat:
                selectedIdx = i
        self._dateFormatChoice.SetSelection(selectedIdx)
        self._dateFormatChoice.Bind(wx.EVT_CHOICE, self._onDateFormatChange)
        dateFormatSizer.Add(self._dateFormatChoice, 0, wx.ALIGN_CENTER_VERTICAL)

        # Detected format label
        from taskcoachlib.widgets.maskedtimectrl import getDetectedLocaleDateFormat
        detectedOrder, detectedSep = getDetectedLocaleDateFormat()
        detectedStr = self._formatOrderToString(detectedOrder, detectedSep)
        self._detectedFormatLabel = wx.StaticText(
            dateFormatPanel,
            label=_("Detected: %s") % detectedStr
        )
        self._detectedFormatLabel.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        dateFormatSizer.Add(self._detectedFormatLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 15)

        dateFormatPanel.SetSizer(dateFormatSizer)
        self.addEntry(_("Date format"), dateFormatPanel)

        # Demo DateCtrl4 showing the selected format (interactive, starts with today)
        from taskcoachlib.widgets.maskedtimectrl import DateCtrl4
        import datetime
        today = datetime.date.today()
        demoPanel = wx.Panel(self)
        demoSizer = wx.BoxSizer(wx.HORIZONTAL)
        demoLabel = wx.StaticText(demoPanel, label=_("Preview:"))
        demoSizer.Add(demoLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self._demoDateCtrl = DateCtrl4(
            demoPanel,
            year=today.year, month=today.month, day=today.day,
            dateFormat=currentFormat or None
        )
        demoSizer.Add(self._demoDateCtrl, 0, wx.ALIGN_CENTER_VERTICAL)
        demoPanel.SetSizer(demoSizer)
        self.addEntry("", demoPanel)

        # === TIME FORMAT SECTION ===
        # Time format dropdown with detected format label
        timeFormatPanel = wx.Panel(self)
        timeFormatSizer = wx.BoxSizer(wx.HORIZONTAL)

        self._timeFormatChoice = wx.Choice(timeFormatPanel)
        timeFormats = [
            ("", _("Automatic (detect from system)")),
            ("24", _("24-hour (14:30)")),
            ("12", _("12-hour (2:30 PM)")),
        ]
        currentTimeFormat = self.gettext("view", "timeformat")
        selectedTimeIdx = 0
        for i, (value, label) in enumerate(timeFormats):
            self._timeFormatChoice.Append(label, value)
            if value == currentTimeFormat:
                selectedTimeIdx = i
        self._timeFormatChoice.SetSelection(selectedTimeIdx)
        timeFormatSizer.Add(self._timeFormatChoice, 0, wx.ALIGN_CENTER_VERTICAL)

        # Detected time format label
        from taskcoachlib.widgets.maskedtimectrl import getDetectedLocaleTimeFormat
        detectedTimeFormat = getDetectedLocaleTimeFormat()
        detectedTimeStr = "24-hour" if detectedTimeFormat == "24" else "12-hour"
        self._detectedTimeFormatLabel = wx.StaticText(
            timeFormatPanel,
            label=_("Detected: %s") % detectedTimeStr
        )
        self._detectedTimeFormatLabel.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        timeFormatSizer.Add(self._detectedTimeFormatLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 15)

        timeFormatPanel.SetSizer(timeFormatSizer)
        self._timeFormatChoice.Bind(wx.EVT_CHOICE, self._onTimeFormatChange)
        self.addEntry(_("Time format"), timeFormatPanel)

        # Demo TimeCtrl showing the selected format (interactive, starts with current time)
        # TimeCtrl now has built-in defaults from settings, so no need to pass choices
        from taskcoachlib.widgets.maskedtimectrl import TimeCtrl
        timeDemoPanel = wx.Panel(self)
        timeDemoSizer = wx.BoxSizer(wx.HORIZONTAL)
        timeDemoLabel = wx.StaticText(timeDemoPanel, label=_("Preview:"))
        timeDemoSizer.Add(timeDemoLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        now = datetime.datetime.now()
        # Pass explicit timeFormat to preview the selected format (not yet saved to settings)
        effectiveFormat = currentTimeFormat if currentTimeFormat else "24"
        self._demoTimeCtrl = TimeCtrl(
            timeDemoPanel,
            hours=now.hour, minutes=now.minute,
            timeFormat=effectiveFormat
        )
        timeDemoSizer.Add(self._demoTimeCtrl, 0, wx.ALIGN_CENTER_VERTICAL)
        timeDemoPanel.SetSizer(timeDemoSizer)
        self.addEntry("", timeDemoPanel)

        # Note about 12-hour mode and working hours
        timeFormatNote = wx.StaticText(
            self,
            label=_("Note: In 12-hour mode, working hours (set in Features tab) are not used for hour suggestions.")
        )
        timeFormatNote.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        self.addEntry("", timeFormatNote)

        # Separator line between time format and spell check sections
        self.addLine()

        # === SPELL CHECK SECTION ===
        self._setupSpellCheckSection()

        # Store original formats to detect changes
        self._originalDateFormat = currentFormat
        self._originalTimeFormat = currentTimeFormat

        self.fit()

    def _setupSpellCheckSection(self):
        """Set up the spell check configuration section."""
        from taskcoachlib.widgets.textctrl import SpellCheckMixin, ENCHANT_AVAILABLE

        # Spell check enabled checkbox
        self._spellCheckEnabled = self.getboolean("spellcheck", "enabled")
        self._spellCheckEnabledCheck = wx.CheckBox(self, label=_("Enable spell checking"))
        self._spellCheckEnabledCheck.SetValue(self._spellCheckEnabled)
        self._spellCheckEnabledCheck.Bind(wx.EVT_CHECKBOX, self._onSpellCheckEnabledChange)
        self.addEntry(_("Spell check"), self._spellCheckEnabledCheck)

        # Show warning if enchant is not available
        if not ENCHANT_AVAILABLE:
            warningText = wx.StaticText(
                self,
                label=_("Warning: Spell checking is not available. Install pyenchant to enable this feature.")
            )
            warningText.SetForegroundColour(wx.Colour(180, 0, 0))
            self.addEntry("", warningText)
            self._spellCheckEnabledCheck.Enable(False)

        # Language dropdown for spell check
        spellLangPanel = wx.Panel(self)
        spellLangSizer = wx.BoxSizer(wx.HORIZONTAL)

        self._spellCheckLangChoice = wx.Choice(spellLangPanel)

        # Add automatic option first
        self._spellCheckLangChoice.Append(_("Automatic (detect from system)"), "")

        # Get available languages
        availableLangs = SpellCheckMixin.getAvailableLanguages() if ENCHANT_AVAILABLE else []
        currentSpellLang = self.gettext("spellcheck", "language")
        selectedIdx = 0

        for i, lang in enumerate(sorted(availableLangs)):
            self._spellCheckLangChoice.Append(lang, lang)
            if lang == currentSpellLang:
                selectedIdx = i + 1  # +1 because of "Automatic" option

        self._spellCheckLangChoice.SetSelection(selectedIdx)
        self._spellCheckLangChoice.Enable(self._spellCheckEnabled and ENCHANT_AVAILABLE)
        spellLangSizer.Add(self._spellCheckLangChoice, 0, wx.ALIGN_CENTER_VERTICAL)

        # Show detected language
        if ENCHANT_AVAILABLE:
            detectedLang = SpellCheckMixin._detectLanguage()
            detectedLabel = wx.StaticText(
                spellLangPanel,
                label=_("Detected: %s") % detectedLang
            )
            detectedLabel.SetForegroundColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
            )
            spellLangSizer.Add(detectedLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 15)

        spellLangPanel.SetSizer(spellLangSizer)
        self.addEntry(_("Spell check language"), spellLangPanel)

        # Note about dropdown and how to install more dictionaries
        if ENCHANT_AVAILABLE:
            import platform
            system = platform.system()

            if not availableLangs:
                # No dictionaries found - show note
                helpText = wx.StaticText(
                    self,
                    label=_("Language missing? Install hunspell packages for your language.")
                )
                helpText.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
                self.addEntry("", helpText)

            # Platform-specific note combining dropdown info and install instructions
            if system == "Linux":
                noteText = _("Dropdown shows installed dictionaries. Install via: apt install hunspell-en-us")
            elif system == "Darwin":
                noteText = _("Dropdown shows installed dictionaries. Install via: brew install hunspell")
            else:  # Windows
                noteText = _("Dropdown shows installed dictionaries. Additional languages must be prepackaged.")

            dictNote = wx.StaticText(self, label=noteText)
            dictNote.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
            dictNote.Wrap(500)
            self.addEntry("", dictNote)

    def _onSpellCheckEnabledChange(self, event):
        """Handle spell check enabled checkbox change."""
        from taskcoachlib.widgets.textctrl import ENCHANT_AVAILABLE
        enabled = event.IsChecked()
        self._spellCheckLangChoice.Enable(enabled and ENCHANT_AVAILABLE)
        event.Skip()

    def _formatOrderToString(self, field_order, separator):
        """Convert field order and separator to a human-readable format string."""
        field_map = {'year': 'YYYY', 'month': 'MM', 'date_day': 'DD'}
        parts = [field_map.get(f, '??') for f in field_order]
        return separator.join(parts)

    def _getSelectedLanguageCode(self):
        """Get the currently selected language code from the dropdown."""
        for section, setting, choiceCtrls in self._choiceSettings:
            if setting == "language_set_by_user":
                choice = choiceCtrls[0]
                return choice.GetClientData(choice.GetSelection())
        return ""

    def _onDateFormatChange(self, event):
        """Handle date format dropdown change - update demo control and restart warning."""
        choice = event.GetEventObject()
        newFormat = choice.GetClientData(choice.GetSelection())

        # Recreate the demo DateCtrl4 with new format, using today's date
        from taskcoachlib.widgets.maskedtimectrl import DateCtrl4
        import datetime
        today = datetime.date.today()
        parent = self._demoDateCtrl.GetParent()
        sizer = parent.GetSizer()

        # Destroy old and create new with today's date
        self._demoDateCtrl.Destroy()
        self._demoDateCtrl = DateCtrl4(
            parent,
            year=today.year,
            month=today.month,
            day=today.day,
            dateFormat=newFormat or None
        )
        sizer.Add(self._demoDateCtrl, 0, wx.ALIGN_CENTER_VERTICAL)
        parent.Layout()
        parent.Fit()

        # Update restart warning
        self._updateRestartWarning()

        event.Skip()

    def _onTimeFormatChange(self, event):
        """Handle time format dropdown change - update demo control and restart warning."""
        choice = event.GetEventObject()
        newFormat = choice.GetClientData(choice.GetSelection())

        # Recreate the demo TimeCtrl with new format, using current time
        # TimeCtrl has built-in defaults, just pass the format to preview
        from taskcoachlib.widgets.maskedtimectrl import TimeCtrl
        import datetime
        now = datetime.datetime.now()
        parent = self._demoTimeCtrl.GetParent()
        sizer = parent.GetSizer()

        # Determine effective format for preview
        effectiveFormat = newFormat if newFormat else "24"

        # Destroy old and create new with current time
        self._demoTimeCtrl.Destroy()
        self._demoTimeCtrl = TimeCtrl(
            parent,
            hours=now.hour, minutes=now.minute,
            timeFormat=effectiveFormat
        )
        sizer.Add(self._demoTimeCtrl, 0, wx.ALIGN_CENTER_VERTICAL)
        parent.Layout()
        parent.Fit()

        # Update restart warning
        self._updateRestartWarning()

        event.Skip()

    def _onLanguageChange(self, event):
        """Handle language dropdown change."""
        self._updateLocaleWarning()
        self._updateRestartWarning()
        event.Skip()

    def _updateRestartWarning(self):
        """Update restart warning to show change detected state."""
        selected_lang = self._getSelectedLanguageCode()
        selected_date_format = self._dateFormatChoice.GetClientData(
            self._dateFormatChoice.GetSelection()
        )
        selected_time_format = self._timeFormatChoice.GetClientData(
            self._timeFormatChoice.GetSelection()
        )

        # Check if any regional setting has changed
        language_changed = selected_lang != self._originalLanguage
        date_format_changed = selected_date_format != self._originalDateFormat
        time_format_changed = selected_time_format != self._originalTimeFormat

        if language_changed or date_format_changed or time_format_changed:
            # Change detected - show red warning
            self._restartWarning.SetLabel(
                self._restartWarningBase + " " + _("Change detected, restart required!")
            )
            self._restartWarning.SetForegroundColour(wx.Colour(180, 0, 0))
        else:
            # Reverted to original - restore normal state
            self._restartWarning.SetLabel(self._restartWarningBase)
            self._restartWarning.SetForegroundColour(self._restartWarningDefaultColor)
        self._restartWarning.Refresh()

    def _updateLocaleWarning(self):
        """Show or hide the locale warning based on selected language's locale availability."""
        from taskcoachlib import i18n
        # Check if the selected language's locale is available on the system
        selected_lang = self._getSelectedLanguageCode()
        showWarning = not i18n.isLocaleAvailable(selected_lang)
        self._localeWarning.Show(showWarning)
        # Re-layout the parent panel
        parent = self._localeWarning.GetParent()
        if parent:
            parent.Layout()
            parent.Fit()

    def ok(self):
        super().ok()
        self.set("view", "language", self.get("view", "language_set_by_user"))
        # Save date format setting
        selectedFormat = self._dateFormatChoice.GetClientData(
            self._dateFormatChoice.GetSelection()
        )
        self.set("view", "dateformat", selectedFormat)
        # Save time format setting
        selectedTimeFormat = self._timeFormatChoice.GetClientData(
            self._timeFormatChoice.GetSelection()
        )
        self.set("view", "timeformat", selectedTimeFormat)
        # Save spell check settings
        self.setboolean("spellcheck", "enabled", self._spellCheckEnabledCheck.IsChecked())
        selectedSpellLang = self._spellCheckLangChoice.GetClientData(
            self._spellCheckLangChoice.GetSelection()
        )
        self.set("spellcheck", "language", selectedSpellLang)


class TaskAppearancePage(SettingsPage):
    pageName = "appearance"
    pageTitle = _("Task appearance")
    pageIcon = "palette_icon"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=10, growableColumn=-1, *args, **kwargs)
        self._objectIcons = self._collectObjectIcons()
        self.addAppearanceHeader()
        for status in task.Task.possibleStatuses():
            setting = "%stasks" % status
            label = status.pluralLabel.replace(" tasks", "")
            self.addAppearanceSetting(
                "fgcolor",
                setting,
                "bgcolor",
                setting,
                "font",
                setting,
                "icon",
                setting,
                label,
            )
        # Bind validation to prevent selecting object-used icons
        for section, setting, iconEntry in self._iconSettings:
            iconEntry.Bind(wx.EVT_COMBOBOX,
                           lambda evt, ie=iconEntry: self._onStatusIconChanged(evt, ie))
        noteText = wx.StaticText(self, label=_(
            "These appearance settings can be overridden "
            "for individual tasks in the task edit dialog."
        ))
        noteText.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        self.addEntry("", noteText, flags=(wx.ALL | wx.ALIGN_LEFT, wx.ALL | wx.EXPAND))
        self.fit()

    def _collectObjectIcons(self):
        """Collect all icons currently used by tasks, categories, and notes."""
        icons = set()
        if self.taskFile is None:
            return icons
        for obj in self.taskFile.tasks():
            icon = obj.icon()
            if icon:
                icons.add(icon)
        for obj in self.taskFile.categories():
            icon = obj.icon()
            if icon:
                icons.add(icon)
        for obj in self.taskFile.notes():
            icon = obj.icon()
            if icon:
                icons.add(icon)
        return icons

    def _onStatusIconChanged(self, event, iconEntry):
        """Handle icon selection change. Excluded icons are handled by IconPicker."""
        # The new IconPicker prevents selection of excluded icons internally
        event.Skip()


class FeaturesPage(SettingsPage):
    pageName = "features"
    pageTitle = _("Features")
    pageIcon = "cogwheel_icon"
    _helpWidth = 500

    def __init__(self, *args, **kwargs):
        super().__init__(columns=3, growableColumn=-1, *args, **kwargs)
        self._restartWarningBase = _("All settings on this tab require a restart of %s to take effect.") % meta.name
        self._restartWarning = wx.StaticText(self, label=self._restartWarningBase)
        self._restartWarningDefaultColor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        self._restartWarning.SetForegroundColour(self._restartWarningDefaultColor)
        self.addEntry("", self._restartWarning)
        self.addChoiceSetting(
            "view",
            "weekstart",
            _("Start of work week"),
            " ",
            [("monday", _("Monday")), ("sunday", _("Sunday"))],
        )
        self.addWorkingHoursSetting(_("Working hours"))
        workingHoursNote = wx.StaticText(
            self,
            label=_("Note: Working hours are not used for hour suggestions when 12-hour (AM/PM) time format is selected in Regional settings.")
        )
        workingHoursNote.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        workingHoursNote.Wrap(700)
        self.addEntry("", workingHoursNote)

        self.addBooleanSetting(
            "calendarviewer",
            "gradient",
            _("Gradients in calendar views"),
            _("Using gradients in calendar views may slow down Task Coach"),
        )
        self.addChoiceSetting(
            "view",
            "effortminuteinterval",
            _("Minutes between suggested times"),
            _(
                "In popup-menus for time selection (e.g. for setting the start "
                "time of an effort) %(name)s will suggest times using this "
                "setting. The smaller the number of minutes, the more times "
                "are suggested. Of course, you can also enter any time you "
                "want beside the suggested times."
            )
            % meta.data.metaDict,
            [
                (minutes, minutes)
                for minutes in ("1", "2", "3", "4", "5", "6", "10", "12", "15", "20", "30")
            ],
        )
        self.addChoiceSetting(
            "view",
            "effortsecondinterval",
            _("Seconds between suggested times"),
            _(
                "In effort dialogs where seconds are shown, %(name)s will "
                "suggest second values using this setting."
            )
            % meta.data.metaDict,
            [
                (seconds, seconds)
                for seconds in ("1", "2", "3", "4", "5", "6", "10", "12", "15", "20", "30")
            ],
        )
        self.addIntegerSetting(
            "feature",
            "minidletime",
            _("Idle time notice"),
            helpText=_(
                "If there is no user input for this amount of time "
                "(in minutes), %(name)s will ask what to do about current "
                "efforts."
            )
            % meta.data.metaDict,
        )
        self.addBooleanSetting(
            "view",
            "descriptionpopups",
            _("Hoverover popups"),
            _("Show a popup with the description of an item when hovering over it"),
        )

        # Store original values to detect changes
        self._originalValues = {}
        for section, setting, checkBox in self._booleanSettings:
            self._originalValues[(section, setting)] = checkBox.IsChecked()
            checkBox.Bind(wx.EVT_CHECKBOX, self._onSettingChange)
        for section, setting, choiceCtrls in self._choiceSettings:
            self._originalValues[(section, setting)] = tuple(
                c.GetSelection() for c in choiceCtrls
            )
            for c in choiceCtrls:
                c.Bind(wx.EVT_CHOICE, self._onSettingChange)
        for section, setting, spinCtrl in self._integerSettings:
            self._originalValues[(section, setting)] = spinCtrl.GetValue()
            spinCtrl.Bind(wx.EVT_SPINCTRL, self._onSettingChange)
        # Working hours
        self._originalValues[("view", "efforthourstart")] = self._workingHourStartChoice.GetSelection()
        self._originalValues[("view", "efforthourend")] = self._workingHourEndChoice.GetSelection()
        self._originalValues[("view", "efforthourend_endofday")] = self._workingHourEndOfDayCheck.IsChecked()
        self._workingHourStartChoice.Bind(wx.EVT_CHOICE, self._onSettingChange)
        self._workingHourEndChoice.Bind(wx.EVT_CHOICE, self._onSettingChange)
        self._workingHourEndOfDayCheck.Bind(wx.EVT_CHECKBOX, self._onSettingChange)

        self.fit()

    def _onSettingChange(self, event):
        self._updateRestartWarning()
        event.Skip()

    def _updateRestartWarning(self):
        changed = False
        for section, setting, checkBox in self._booleanSettings:
            if checkBox.IsChecked() != self._originalValues.get((section, setting)):
                changed = True
                break
        if not changed:
            for section, setting, choiceCtrls in self._choiceSettings:
                current = tuple(c.GetSelection() for c in choiceCtrls)
                if current != self._originalValues.get((section, setting)):
                    changed = True
                    break
        if not changed:
            for section, setting, spinCtrl in self._integerSettings:
                if spinCtrl.GetValue() != self._originalValues.get((section, setting)):
                    changed = True
                    break
        if not changed:
            if (self._workingHourStartChoice.GetSelection() != self._originalValues[("view", "efforthourstart")]
                or self._workingHourEndChoice.GetSelection() != self._originalValues[("view", "efforthourend")]
                or self._workingHourEndOfDayCheck.IsChecked() != self._originalValues[("view", "efforthourend_endofday")]):
                changed = True

        if changed:
            self._restartWarning.SetLabel(
                self._restartWarningBase + " " + _("Change detected, restart required!")
            )
            self._restartWarning.SetForegroundColour(wx.Colour(180, 0, 0))
        else:
            self._restartWarning.SetLabel(self._restartWarningBase)
            self._restartWarning.SetForegroundColour(self._restartWarningDefaultColor)
        self._restartWarning.Refresh()

    def ok(self):
        super().ok()
        self._saveWorkingHoursSettings()
        calendar.setfirstweekday(
            dict(monday=0, sunday=6)[self.get("view", "weekstart")]
        )


class TaskDatesPage(SettingsPage):
    pageName = "task"
    pageTitle = _("Task dates")
    pageIcon = "calendar_icon"
    _helpWidth = 700

    def __init__(self, *args, **kwargs):
        super().__init__(columns=4, growableColumn=-1, *args, **kwargs)
        self.addBooleanSetting(
            "behavior",
            "markparentcompletedwhenallchildrencompleted",
            _("Mark parent task completed when all children are completed"),
            helpText="override",
        )
        self.addIntegerSetting(
            "behavior",
            "duesoonhours",
            _("Number of hours that tasks are considered to be 'due soon'"),
            minimum=0,
            maximum=9999,
        )
        choices = [
            ("", _("Nothing")),
            (
                "startdue",
                _("Changing the planned start date changes the due date"),
            ),
            (
                "duestart",
                _("Changing the due date changes the planned start date"),
            ),
        ]
        self.addChoiceSetting(
            "view",
            "datestied",
            _(
                "What to do with planned start and due date if the other one is changed"
            ),
            "",
            choices,
        )
        datestied_hint = wx.StaticText(
            self,
            label=_(
                'Deprecated: replaced by the duration mode in the task editor. '
                'Inline editing in the task list has not yet been refactored '
                'and still uses this legacy option. It will be removed eventually.'
            ),
        )
        datestied_hint.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        datestied_hint.Wrap(700)
        self.addText("", datestied_hint)

        check_choices = [("preset", _("Preset")), ("propose", _("Propose"))]
        day_choices = [
            ("today", _("Today")),
            ("tomorrow", _("Tomorrow")),
            ("dayaftertomorrow", _("Day after tomorrow")),
            ("nextfriday", _("Next Friday")),
            ("nextmonday", _("Next Monday")),
        ]
        time_choices = [
            ("startofday", _("Start of day")),
            ("startofworkingday", _("Start of working day")),
            ("currenttime", _("Current time")),
            ("endofworkingday", _("End of working day")),
            ("endofday", _("End of day")),
        ]
        self.addChoiceSetting(
            "view",
            "defaultplannedstartdatetime",
            _("Default planned start date and time"),
            "",
            check_choices,
            day_choices,
            time_choices,
        )
        self.addChoiceSetting(
            "view",
            "defaultduedatetime",
            _("Default due date and time"),
            "",
            check_choices,
            day_choices,
            time_choices,
        )
        self.addChoiceSetting(
            "view",
            "defaultactualstartdatetime",
            _("Default actual start date and time"),
            "",
            check_choices,
            day_choices,
            time_choices,
        )
        self.addChoiceSetting(
            "view",
            "defaultcompletiondatetime",
            _("Default completion date and time"),
            "",
            [check_choices[1]],
            day_choices,
            time_choices,
        )
        self.addChoiceSetting(
            "view",
            "defaultreminderdatetime",
            _("Default reminder date and time"),
            "",
            check_choices,
            day_choices,
            time_choices,
        )
        self.__add_help_text()
        self.fit()

    def __add_help_text(self):
        """Add help text for the default date and time settings."""
        help_text = wx.StaticText(
            self,
            label=_(
                """New tasks start with "Preset" dates and times filled in and checked. "Proposed" dates and times are filled in, but not checked.

"Start of day" is midnight and "End of day" is just before midnight. When using these, task viewers hide the time and show only the date.

"Start of working day" and "End of working day" use the working day as set in the Features tab of this preferences dialog."""
            )
            % meta.data.metaDict,
        )
        help_text.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        help_text.Wrap(700)
        self.addText("", help_text)


class TaskReminderPage(SettingsPage):
    pageName = "reminder"
    pageTitle = _("Reminders")
    pageIcon = "clock_alarm_icon"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=3, growableColumn=-1, *args, **kwargs)
        if operating_system.isMac() or operating_system.isGTK():
            self.addBooleanSetting(
                "feature",
                "sayreminder",
                _("Let the computer say the reminder"),
                _("(Needs espeak)") if operating_system.isGTK() else "",
            )
        snoozeChoices = [
            (str(choice[0]), choice[1]) for choice in date.snoozeChoices
        ]
        self.addChoiceSetting(
            "view",
            "defaultsnoozetime",
            _("Default snooze time to use after reminder"),
            "",
            snoozeChoices,
        )
        self.addMultipleChoiceSettings(
            "view",
            "snoozetimes",
            _("Snooze times to offer in task reminder dialog"),
            date.snoozeChoices[1:],
            flags=(None, wx.ALL | wx.EXPAND),
        )  # Don't offer "Don't snooze" as a choice
        self.fit()


class DurationPresetsPage(SettingsPage):
    """Preferences page for configuring duration presets."""

    pageName = "presets"
    pageTitle = _("Durations")
    pageIcon = "clock_icon"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, growableColumn=1, *args, **kwargs)

        # Preset field configurations: (setting_key, display_name, help_text)
        self._preset_fields = [
            (
                "task_duration_presets",
                _("Task Duration"),
                _("These presets appear when setting task duration in the task editor."),
            ),
            (
                "effort_duration_presets",
                _("Effort Duration"),
                _("These presets appear when setting effort duration in the effort editor."),
            ),
        ]

        self.__currentFieldIndex = 0
        self.__presets = {}  # Cache for all preset lists

        # Load all presets
        for setting_key, unused_name, unused_help in self._preset_fields:
            self.__presets[setting_key] = self.__loadPresets(setting_key)

        # Field selector row
        self.__fieldChoice = wx.Choice(self)
        for unused_key, display_name, unused_help in self._preset_fields:
            self.__fieldChoice.Append(display_name)
        self.__fieldChoice.SetSelection(0)
        self.__fieldChoice.Bind(wx.EVT_CHOICE, self.__onFieldChanged)
        self.addEntry(_("Configure presets for"), self.__fieldChoice)

        # Add row: DurationEntry + Add button
        self.__addPanel = wx.Panel(self)
        self.__addSizer = wx.BoxSizer(wx.HORIZONTAL)

        # Create duration control - initially without seconds (Task Due Date is default)
        self.__durationEntry = self.__createDurationCtrl(showSeconds=False)
        self.__addSizer.Add(self.__durationEntry, 0, wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, 5)

        self.__addBtn = wx.Button(self.__addPanel, wx.ID_ANY, _("Add"))
        self.__addBtn.SetBitmap(
            wx.ArtProvider.GetBitmap("symbol_plus_icon", wx.ART_BUTTON, (16, 16))
        )
        self.__addBtn.Bind(wx.EVT_BUTTON, self.__onAdd)
        self.__addSizer.Add(self.__addBtn, 0, wx.ALIGN_CENTRE_VERTICAL)

        self.__addPanel.SetSizer(self.__addSizer)
        self.addEntry(_("Add new preset"), self.__addPanel)

        # Preset list with 3 columns: short value, description, delete button
        # Using UltimateListCtrl to support embedded Delete buttons
        self.__listCtrl = ULC.UltimateListCtrl(
            self,
            agwStyle=wx.LC_REPORT | wx.LC_SINGLE_SEL | ULC.ULC_HAS_VARIABLE_ROW_HEIGHT
        )
        self.__listCtrl.InsertColumn(0, _("Short"), width=80, format=wx.LIST_FORMAT_RIGHT)
        self.__listCtrl.InsertColumn(1, _("Description"), width=310)
        self.__listCtrl.InsertColumn(2, _("Delete"), width=110)
        self.__listCtrl.SetMinSize((500, 120))
        self.__listCtrl.SetMaxSize((500, -1))
        # Track delete buttons for cleanup
        self.__deleteButtons = []
        self.addEntry(
            _("Current presets"), self.__listCtrl, growable=True,
            flags=(None, wx.EXPAND | wx.ALL)
        )

        # Help text
        self.__helpText = wx.StaticText(self, label="")
        self.__helpText.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        self.__helpText.Wrap(500)
        self.addEntry("", self.__helpText)

        # Populate initial list
        self.__populateList()
        self.__updateHelpText()

        self.fit()

    def __isEffortPreset(self, setting_key=None):
        """Check if the setting key is for effort presets (uses seconds)."""
        if setting_key is None:
            setting_key = self.__getCurrentSettingKey()
        return setting_key == "effort_duration_presets"

    def __loadPresets(self, setting_key):
        """Load presets from settings.

        Task presets are stored as minutes, effort presets as seconds.
        """
        value = self.gettext("feature", setting_key)
        if not value:
            return []
        presets = []
        for val_str in value.split(","):
            try:
                presets.append(int(val_str.strip()))
            except ValueError:
                pass
        return sorted(presets)

    def __savePresets(self, setting_key):
        """Save presets to settings."""
        presets = self.__presets[setting_key]
        value = ",".join(str(m) for m in sorted(presets))
        self.settext("feature", setting_key, value)

    def __getCurrentSettingKey(self):
        return self._preset_fields[self.__currentFieldIndex][0]

    def __getCurrentPresets(self):
        return self.__presets[self.__getCurrentSettingKey()]

    def __createDurationCtrl(self, showSeconds=False):
        """Create a duration control with or without seconds field."""
        if showSeconds:
            return widgets.MaskedDurationCtrl(
                self.__addPanel, days=0, hours=0, minutes=15, seconds=0,
                showSeconds=True
            )
        else:
            return widgets.MaskedDurationCtrl(
                self.__addPanel, days=0, hours=1, minutes=0
            )

    def __onFieldChanged(self, event):
        self.__currentFieldIndex = self.__fieldChoice.GetSelection()

        # Recreate duration control with/without seconds based on preset type
        is_effort = self.__isEffortPreset()
        self.__addSizer.Detach(self.__durationEntry)
        self.__durationEntry.Destroy()
        self.__durationEntry = self.__createDurationCtrl(showSeconds=is_effort)
        self.__addSizer.Insert(0, self.__durationEntry, 0, wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, 10)
        self.__addPanel.Layout()

        self.__populateList()
        self.__updateHelpText()

    def __updateHelpText(self):
        unused_key, unused_name, help_text = self._preset_fields[self.__currentFieldIndex]
        self.__helpText.SetLabel(help_text)
        self.__helpText.Wrap(500)
        self.Layout()

    def __populateList(self):
        """Rebuild the list with 3 columns: short value, description, delete button."""
        # Clean up existing buttons
        for btn in self.__deleteButtons:
            btn.Destroy()
        self.__deleteButtons = []

        self.__listCtrl.DeleteAllItems()
        presets = sorted(self.__getCurrentPresets())
        is_effort = self.__isEffortPreset()

        for value in presets:
            if is_effort:
                compact, description = self.__formatSecondsParts(value)
            else:
                compact, description = self.__formatMinutesParts(value)
            # UltimateListCtrl uses InsertStringItem instead of InsertItem
            index = self.__listCtrl.InsertStringItem(self.__listCtrl.GetItemCount(), compact)
            self.__listCtrl.SetStringItem(index, 1, description)
            self.__listCtrl.SetItemData(index, value)

            # Create a real Delete button for this row (same style as Add button)
            # Use wx.BU_EXACTFIT to reduce padding and make button smaller
            deleteBtn = wx.Button(
                self.__listCtrl, wx.ID_ANY, " " + _("Delete"),
                style=wx.BU_EXACTFIT
            )
            deleteBtn.SetBitmap(
                wx.ArtProvider.GetBitmap("cross_red_icon", wx.ART_BUTTON, (16, 16))
            )
            deleteBtn.presetValue = value  # Store preset value on button
            deleteBtn.Bind(wx.EVT_BUTTON, self.__onDeleteButton)
            self.__deleteButtons.append(deleteBtn)
            self.__listCtrl.SetItemWindow(index, 2, deleteBtn, expand=True)

    def __formatMinutesParts(self, total_minutes):
        """Format minutes as (compact_value, description) tuple."""
        days = total_minutes // (24 * 60)
        hours = (total_minutes % (24 * 60)) // 60
        minutes = total_minutes % 60

        # Compact format with 'd' suffix for days
        # e.g., "1d 06:30" for 1 day 6 hours 30 min, "2:15" for 2 hours 15 min
        if days > 0:
            compact = "%dd %02d:%02d" % (days, hours, minutes)
        elif hours > 0:
            compact = "%d:%02d" % (hours, minutes)
        else:
            compact = "%d" % minutes

        # Build plain English description
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

        if not parts:
            description = _("0 minutes")
        elif len(parts) == 1:
            description = parts[0]
        elif len(parts) == 2:
            description = _("%s and %s") % (parts[0], parts[1])
        else:
            description = _("%s, %s and %s") % (parts[0], parts[1], parts[2])

        return compact, description

    def __formatSecondsParts(self, total_seconds):
        """Format seconds as (compact_value, description) tuple for effort presets."""
        days = total_seconds // (24 * 60 * 60)
        hours = (total_seconds % (24 * 60 * 60)) // (60 * 60)
        minutes = (total_seconds % (60 * 60)) // 60
        seconds = total_seconds % 60

        # Compact format: "1d 06:30:15" or "2:15:30" or "0:45" or "30s"
        if days > 0:
            compact = "%dd %02d:%02d:%02d" % (days, hours, minutes, seconds)
        elif hours > 0:
            compact = "%d:%02d:%02d" % (hours, minutes, seconds)
        elif minutes > 0:
            compact = "%d:%02d" % (minutes, seconds)
        else:
            compact = "%ds" % seconds

        # Build plain English description
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
        if seconds > 0:
            if seconds == 1:
                parts.append(_("1 second"))
            else:
                parts.append(_("%d seconds") % seconds)

        if not parts:
            description = _("0 seconds")
        elif len(parts) == 1:
            description = parts[0]
        elif len(parts) == 2:
            description = _("%s and %s") % (parts[0], parts[1])
        elif len(parts) == 3:
            description = _("%s, %s and %s") % (parts[0], parts[1], parts[2])
        else:
            description = _("%s, %s, %s and %s") % (parts[0], parts[1], parts[2], parts[3])

        return compact, description

    def __onAdd(self, event):
        duration = self.__durationEntry.GetDuration()
        total_seconds = int(duration.total_seconds())

        # For effort presets, store in seconds; for task presets, store in minutes
        if self.__isEffortPreset():
            new_value = total_seconds
            if new_value <= 0:
                return
        else:
            new_value = total_seconds // 60
            if new_value <= 0:
                return

        presets = self.__getCurrentPresets()

        # Check for duplicates
        if new_value in presets:
            return

        presets.append(new_value)
        presets.sort()

        self.__savePresets(self.__getCurrentSettingKey())
        self.__populateList()

    def __onDeleteButton(self, event):
        """Handle Delete button click - remove the preset."""
        btn = event.GetEventObject()
        value = btn.presetValue
        presets = self.__getCurrentPresets()

        if value in presets:
            presets.remove(value)

        self.__savePresets(self.__getCurrentSettingKey())
        self.__populateList()


class Preferences(widgets.NotebookDialog):
    allPageNames = [
        "window",
        "save",
        "language",
        "task",
        "reminder",
        "presets",
        "theme",
        "appearance",
        "features",
    ]
    pages = dict(
        window=WindowBehaviorPage,
        theme=ThemePage,
        task=TaskDatesPage,
        reminder=TaskReminderPage,
        presets=DurationPresetsPage,
        save=SavePage,
        language=LanguagePage,
        appearance=TaskAppearancePage,
        features=FeaturesPage,
    )

    def __init__(self, settings=None, taskFile=None, *args, **kwargs):
        self.settings = settings
        self.taskFile = taskFile
        kwargs.setdefault("buttonTypes", wx.OK | wx.CANCEL | wx.APPLY)
        super().__init__(bitmap="wrench_icon", *args, **kwargs)
        if operating_system.isMac():
            self.CentreOnParent()

    def addPages(self):
        self._interior.SetMinSize((1250, 550))
        for page_name in self.allPageNames:
            page = self.createPage(page_name)
            self._interior.AddPage(page, page.pageTitle, page.pageIcon)

    def createPage(self, pageName):
        return self.pages[pageName](
            parent=self._interior, settings=self.settings,
            taskFile=self.taskFile
        )
