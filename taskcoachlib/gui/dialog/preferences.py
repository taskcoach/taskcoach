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

from taskcoachlib import meta, patterns, widgets, operating_system
from taskcoachlib.config import settings
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from taskcoachlib.application.application import (
    detect_dark_theme,
    detect_system_dark_theme,
)
from taskcoachlib.domain import date, task
from taskcoachlib.meta import data
from taskcoachlib.i18n import _
from taskcoachlib.tools import wxhelper
from wx.lib.agw.hyperlink import HyperLinkCtrl
import ast
import wx
import calendar
import wx.lib.scrolledpanel
from wx.lib.agw import ultimatelistctrl as ULC


class FontColorSyncer(object):
    """The font color can be changed via the font color buttons and via the
    font button. The FontColorSyncer updates the one when the font color
    is changed via the other and vice versa."""

    def __init__(self, fg_color_button, bg_color_button, font_button):
        self._fgColorButton = fg_color_button
        self._bgColorButton = bg_color_button
        self._fontButton = font_button
        fg_color_button.Bind(wx.EVT_COLOURPICKER_CHANGED, self.onFgColorPicked)
        bg_color_button.Bind(wx.EVT_COLOURPICKER_CHANGED, self.onBgColorPicked)
        font_button.Bind(wx.EVT_FONTPICKER_CHANGED, self.onFontPicked)

    def onFgColorPicked(self, event):  # pylint: disable=W0613
        self._fontButton.SetSelectedColour(self._fgColorButton.GetColour())

    def onBgColorPicked(self, event):  # pylint: disable=W0613
        self._fontButton.SetSelectedBgColour(self._bgColorButton.GetColour())

    def onFontPicked(self, event):  # pylint: disable=W0613
        font_color = self._fontButton.GetSelectedColour()
        if (
            font_color != self._fgColorButton.GetColour()
            and font_color != wx.BLACK
        ):
            self._fgColorButton.SetColour(self._fontButton.GetSelectedColour())
        else:
            self._fontButton.SetSelectedColour(self._fgColorButton.GetColour())


class SettingsPage(widgets.ScrolledBookPage):
    _label_width = 300
    # Max right edge (px from left of page) for help text
    _max_help_right = 1000

    @property
    def _columnGap(self):
        return self._borderWidth + self._hgap + self._borderWidth

    def _makeInlinePanel(self, *controls, help_text="", growable=False):
        """Create a panel with controls and an inline help label.
        Controls are laid out horizontally with _columnGap spacing.
        The helpCtrl is registered for dynamic wrapping in fit().
        If growable, the first control expands to fill the panel."""
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        for i, ctrl in enumerate(controls):
            ctrl.Reparent(panel)
            flags = wx.EXPAND if (growable and i == 0) else 0
            sizer.Add(ctrl, 0, flags | wx.RIGHT, self._columnGap)
        help_ctrl = wx.StaticText(panel, label=help_text)
        help_ctrl.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        sizer.Add(help_ctrl, 0)
        panel.SetSizer(sizer)
        self._inlineHelpCtrls.append((help_ctrl, panel))
        return panel

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
        self._syncers = []
        self._inlineHelpCtrls = []  # [(helpCtrl, panel)] for deferred wrapping

    def addBooleanSetting(
        self, section, setting, text, help_text="", **kwargs
    ):
        check_box = wx.CheckBox(self, -1)
        check_box.SetValue(settings.get(section, setting))
        panel = self._makeInlinePanel(check_box, help_text=help_text)
        self.addEntry(text, panel, **kwargs)
        self._booleanSettings.append((section, setting, check_box))
        return check_box

    def addChoiceSetting(
        self, section, setting, text, help_text, *lists_of_choices, **kwargs
    ):
        choice_ctrls = []
        current_value = str(settings.get(section, setting))
        sep = kwargs.pop("sep", "_")
        for choices, current_value_part in zip(
            lists_of_choices, current_value.split(sep)
        ):
            choice_ctrl = wx.Choice(self)
            choice_ctrls.append(choice_ctrl)
            for choice_value, choice_text in choices:
                choice_ctrl.Append(choice_text, choice_value)
                if choice_value == current_value_part:
                    choice_ctrl.SetSelection(choice_ctrl.GetCount() - 1)
            # Force a selection if necessary:
            if choice_ctrl.GetSelection() == wx.NOT_FOUND:
                choice_ctrl.SetSelection(0)
        panel = self._makeInlinePanel(*choice_ctrls, help_text=help_text)
        self.addEntry(text, panel, flags=kwargs.get("flags", None))
        self._choiceSettings.append((section, setting, choice_ctrls))
        return choice_ctrls

    def addMultipleChoiceSettings(
        self, section, setting, text, choices, help_text="", **kwargs
    ):
        # choices is a list of (number, text) tuples.
        multiple_choice = wx.CheckListBox(
            self, choices=[choice[1] for choice in choices]
        )
        checked_numbers = settings.get(section, setting)
        for index, choice in enumerate(choices):
            multiple_choice.Check(index, choice[0] in checked_numbers)
        panel = self._makeInlinePanel(
            multiple_choice,
            help_text=help_text,
            growable=kwargs.get("growable", True),
        )
        self.addEntry(
            text,
            panel,
            growable=kwargs.get("growable", True),
            flags=kwargs.get("flags", None),
        )
        self._multipleChoiceSettings.append(
            (
                section,
                setting,
                multiple_choice,
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
        help_text="",
        flags=None,
    ):
        int_value = settings.get(section, setting)
        spin = widgets.SpinCtrl(
            self, min=minimum, max=maximum, size=(65, -1), value=int_value
        )
        panel = self._makeInlinePanel(spin, help_text=help_text)
        self.addEntry(text, panel, flags=flags)
        self._integerSettings.append((section, setting, spin))

    def addWorkingHoursSetting(self, text):
        """Add a working hours setting with start/end dropdowns and end-of-day checkbox."""
        start_hour = settings.get("view", "efforthourstart")
        end_hour = settings.get("view", "efforthourend")
        end_of_day = settings.get("view", "efforthourend_endofday")

        # Migrate old sentinel value: if endHour >= 24, convert to new format
        if end_hour >= 24:
            end_hour = 23
            end_of_day = True

        hours = [str(h) for h in range(24)]
        gap = self._columnGap

        self._workingHourStartChoice = wx.Choice(self, choices=hours)
        self._workingHourStartChoice.SetSelection(start_hour)
        self._workingHourStartChoice.Bind(
            wx.EVT_CHOICE, self._onWorkingHourStartChanged
        )

        self._workingHourEndChoice = wx.Choice(self, choices=hours)
        self._workingHourEndChoice.SetSelection(end_hour)
        self._workingHourEndChoice.Bind(
            wx.EVT_CHOICE, self._onWorkingHourEndChanged
        )

        self._workingHourEndOfDayCheck = wx.CheckBox(
            self, label=_("End of day")
        )
        self._workingHourEndOfDayCheck.SetValue(end_of_day)
        self._workingHourEndOfDayCheck.Bind(
            wx.EVT_CHECKBOX, self._onEndOfDayChecked
        )

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._workingHourStartChoice.Reparent(panel)
        sizer.Add(self._workingHourStartChoice, 0, wx.RIGHT, gap)
        sizer.Add(wx.StaticText(panel, label=_("to")), 0, wx.RIGHT, gap)
        self._workingHourEndChoice.Reparent(panel)
        sizer.Add(self._workingHourEndChoice, 0, wx.RIGHT, gap)
        self._workingHourEndOfDayCheck.Reparent(panel)
        sizer.Add(self._workingHourEndOfDayCheck, 0)
        panel.SetSizer(sizer)

        if end_of_day:
            self._workingHourEndChoice.SetSelection(23)
            self._workingHourEndChoice.Enable(False)

        self.addEntry(text, panel)

    def _onWorkingHourStartChanged(self, event):
        """Ensure at least 1 hour gap when start hour changes."""
        if self._workingHourEndOfDayCheck.IsChecked():
            return  # End of day means midnight, any start hour is valid
        start_hour = self._workingHourStartChoice.GetSelection()
        end_hour = self._workingHourEndChoice.GetSelection()
        if start_hour >= end_hour:
            self._workingHourEndChoice.SetSelection(min(start_hour + 1, 23))

    def _onWorkingHourEndChanged(self, event):
        """Ensure at least 1 hour gap when end hour changes."""
        start_hour = self._workingHourStartChoice.GetSelection()
        end_hour = self._workingHourEndChoice.GetSelection()
        if end_hour <= start_hour:
            self._workingHourStartChoice.SetSelection(max(end_hour - 1, 0))

    def _onEndOfDayChecked(self, event):
        """Handle end of day checkbox toggle."""
        if event.IsChecked():
            self._workingHourEndChoice.SetSelection(23)
            self._workingHourEndChoice.Enable(False)
        else:
            self._workingHourEndChoice.Enable(True)

    def _working_hours_values(self):
        """The working hours, as values() lists them."""
        return [
            (
                "view",
                "efforthourstart",
                self._workingHourStartChoice.GetSelection(),
            ),
            (
                "view",
                "efforthourend",
                self._workingHourEndChoice.GetSelection(),
            ),
            (
                "view",
                "efforthourend_endofday",
                self._workingHourEndOfDayCheck.IsChecked(),
            ),
        ]

    def add_appearance_header(self):
        # Row 0: Group headers - only Light and Dark bold headers (cols 2-5, 6-9)
        light_label = wx.StaticText(self, label=_("Light Theme"))
        dark_label = wx.StaticText(self, label=_("Dark Theme"))
        bold_font = light_label.GetFont().Bold()
        light_label.SetFont(bold_font)
        dark_label.SetFont(bold_font)

        # Skip cols 0-1 (Label, Priority have no bold group header)
        self._position.next(1)
        self._position.next(1)
        pos = self._position.next(4)
        self._sizer.Add(
            light_label,
            pos,
            span=(1, 4),
            flag=wx.ALL | wx.ALIGN_CENTER,
            border=self._borderWidth,
        )
        pos = self._position.next(4)
        self._sizer.Add(
            dark_label,
            pos,
            span=(1, 4),
            flag=wx.ALL | wx.ALIGN_CENTER,
            border=self._borderWidth,
        )
        # Empty cell for reset column
        self._position.next(1)

        # Row 1: Separator lines under Label, Priority, Light and Dark
        self._sizer.Add(
            wx.StaticLine(self),
            (1, 0),
            span=(1, 1),
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=self._borderWidth,
        )
        self._sizer.Add(
            wx.StaticLine(self),
            (1, 1),
            span=(1, 1),
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=self._borderWidth,
        )
        self._sizer.Add(
            wx.StaticLine(self),
            (1, 2),
            span=(1, 4),
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=self._borderWidth,
        )
        self._sizer.Add(
            wx.StaticLine(self),
            (1, 6),
            span=(1, 4),
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=self._borderWidth,
        )
        # Advance cursor past the line row
        self._position.next(11)

        # Row 2: Sub-headers - Label left-aligned, Priority centered, rest centered
        self.addEntry(
            _("Label"),
            _("Priority"),
            _("Foreground"),
            _("Background"),
            _("Font"),
            _("Icon"),
            _("Foreground"),
            _("Background"),
            _("Font"),
            _("Icon"),
            "",
            flags=[
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,  # Label
                wx.ALL | wx.ALIGN_CENTER,  # Priority
            ]
            + [wx.ALL | wx.ALIGN_CENTER] * 9,
        )

    def _createIconEntry(self, exclude=None):
        """Create a searchable icon picker with fixed 120px width."""
        return widgets.IconPicker(self, "", exclude=exclude, fixed_width=120)

    def _createAppearanceControls(
        self,
        fg_color_section,
        fg_color_setting,
        bg_color_section,
        bg_color_setting,
        font_section,
        font_setting,
        icon_section,
        icon_setting,
    ):
        """Create a set of appearance controls (fg, bg, font, icon) for one theme."""
        current_fg_color = settings.get(fg_color_section, fg_color_setting)
        fg_color_button = widgets.ColourPickerCtrl(
            self, colour=wx.Colour(*current_fg_color)
        )
        current_bg_color = settings.get(bg_color_section, bg_color_setting)
        bg_color_button = widgets.ColourPickerCtrl(
            self, colour=wx.Colour(*current_bg_color)
        )
        default_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        native_info_string = settings.get(font_section, font_setting)
        current_font = wxhelper.font_from_native_info(native_info_string)
        font_button = widgets.FontPickerCtrl(
            self,
            font=current_font or default_font,
            colour=current_fg_color,
            bgColour=current_bg_color,
            fixedWidth=75,
        )
        icon_entry = self._createIconEntry(exclude="data")
        current_icon_id = settings.get(icon_section, icon_setting)
        icon_entry.SetValue(current_icon_id)

        self._colorSettings.append(
            (fg_color_section, fg_color_setting, fg_color_button)
        )
        self._colorSettings.append(
            (bg_color_section, bg_color_setting, bg_color_button)
        )
        self._iconSettings.append((icon_section, icon_setting, icon_entry))
        self._fontSettings.append((font_section, font_setting, font_button))
        self._syncers.append(
            FontColorSyncer(fg_color_button, bg_color_button, font_button)
        )

        return fg_color_button, bg_color_button, font_button, icon_entry

    def add_appearance_setting(
        self,
        fg_color_section,
        fg_color_setting,
        bg_color_section,
        bg_color_setting,
        font_section,
        font_setting,
        icon_section,
        icon_setting,
        text,
    ):
        # Priority dropdown
        priority_choice = wx.Choice(
            self, choices=[str(i) for i in range(1, 7)]
        )
        current_priority = settings.get("statussortpriority", fg_color_setting)
        priority_choice.SetSelection(current_priority - 1)
        self._priorityChoices.append((fg_color_setting, priority_choice))
        self._previousPriorities[priority_choice] = current_priority
        priority_choice.Bind(wx.EVT_CHOICE, self._on_priority_changed)

        # Light controls
        light_fg, light_bg, light_font, light_icon = (
            self._createAppearanceControls(
                fg_color_section,
                fg_color_setting,
                bg_color_section,
                bg_color_setting,
                font_section,
                font_setting,
                icon_section,
                icon_setting,
            )
        )
        # Dark controls
        dark_fg, dark_bg, dark_font, dark_icon = (
            self._createAppearanceControls(
                fg_color_section + "_dark",
                fg_color_setting,
                bg_color_section + "_dark",
                bg_color_setting,
                font_section + "_dark",
                font_setting,
                icon_section + "_dark",
                icon_setting,
            )
        )

        # Reset button (resets appearance only, not priority)
        reset_btn = wx.Button(self, label=_("Reset"), size=(60, -1))
        row = (
            fg_color_setting,
            light_fg,
            light_bg,
            light_font,
            light_icon,
            dark_fg,
            dark_bg,
            dark_font,
            dark_icon,
        )
        reset_btn.Bind(
            wx.EVT_BUTTON, lambda evt: self._onResetAppearanceRow(*row)
        )

        self.addEntry(
            text,
            priority_choice,
            light_fg,
            light_bg,
            light_font,
            light_icon,
            dark_fg,
            dark_bg,
            dark_font,
            dark_icon,
            reset_btn,
            flags=(
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL,
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

    def _onResetAppearanceRow(
        self,
        setting,
        light_fg,
        light_bg,
        light_font,
        light_icon,
        dark_fg,
        dark_bg,
        dark_font,
        dark_icon,
    ):
        """Reset appearance controls in a row to defaults (not priority)."""
        import ast
        from taskcoachlib.config import defaults as defaults_mod

        defs = defaults_mod.defaults
        default_sys_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)

        # Reset light theme
        lfg_color = wx.Colour(*ast.literal_eval(defs["fgcolor"][setting]))
        lbg_color = wx.Colour(*ast.literal_eval(defs["bgcolor"][setting]))
        light_fg.SetColour(lfg_color)
        light_bg.SetColour(lbg_color)
        light_font.SetSelectedFont(default_sys_font)
        light_font.SetSelectedColour(lfg_color)
        light_font.SetSelectedBgColour(lbg_color)
        light_icon.SetValue(defs["icon"][setting])

        # Reset dark theme
        dfg_color = wx.Colour(*ast.literal_eval(defs["fgcolor_dark"][setting]))
        dbg_color = wx.Colour(*ast.literal_eval(defs["bgcolor_dark"][setting]))
        dark_fg.SetColour(dfg_color)
        dark_bg.SetColour(dbg_color)
        dark_font.SetSelectedFont(default_sys_font)
        dark_font.SetSelectedColour(dfg_color)
        dark_font.SetSelectedBgColour(dbg_color)
        dark_icon.SetValue(defs["icon_dark"][setting])

    def addPathSetting(self, section, setting, text, help_text="", **kwargs):
        path_chooser = widgets.DirectoryChooser(
            self, wx.ID_ANY, gap=self._columnGap, help_text=help_text
        )
        path_chooser.SetPath(settings.get(section, setting))
        self._inlineHelpCtrls.append((path_chooser.helpCtrl, path_chooser))
        self.addEntry(text, path_chooser, **kwargs)
        self._pathSettings.append((section, setting, path_chooser))

    def addText(self, label, text, **kwargs):
        self.addEntry(label, text, **kwargs)

    def addHintRow(self, text):
        """Add a standalone gray hint row spanning all columns."""
        hint = wx.StaticText(self, label=text)
        hint.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        self._inlineHelpCtrls.append((hint, self))
        self.addText("", hint)

    def values(self):
        """What OK and Apply save: (section, option, value) for each
        setting on the page. Apply is enabled while they differ from
        those the page showed (docs/PREFERENCES.md, OK, Apply and
        Cancel)."""
        values = [
            (section, setting, check_box.IsChecked())
            for section, setting, check_box in self._booleanSettings
        ]
        for section, setting, choice_ctrls in self._choiceSettings:
            value = "_".join(
                [
                    choice.GetClientData(choice.GetSelection())
                    for choice in choice_ctrls
                ]
            )
            values.append(
                (section, setting, settings.from_text(section, setting, value))
            )
        for (
            section,
            setting,
            multiple_choice,
            choices,
        ) in self._multipleChoiceSettings:
            checked = [
                choices[index]
                for index in range(len(choices))
                if multiple_choice.IsChecked(index)
            ]
            values.append((section, setting, checked))
        for section, setting, spin in self._integerSettings:
            values.append((section, setting, spin.GetValue()))
        for section, setting, color_button in self._colorSettings:
            values.append((section, setting, color_button.GetColour()))
        default_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        for section, setting, font_button in self._fontSettings:
            selected_font = font_button.GetSelectedFont()
            font_info_desc = (
                ""
                if selected_font == default_font
                else selected_font.GetNativeFontInfoDesc()
            )
            values.append((section, setting, font_info_desc))
        for section, setting, icon_entry in self._iconSettings:
            values.append((section, setting, icon_entry.GetValue()))
        for section, setting, btn in self._pathSettings:
            values.append((section, setting, btn.GetPath()))
        return values

    def ok(self):
        for section, setting, value in self.values():
            settings.set(section, setting, value)

    def edited(self):
        """A change the dialog's watch does not see (a button made
        later): Apply follows."""
        wx.GetTopLevelParent(self).update_buttons_soon()

    def fit(self):
        """Wrap column 0 labels and inline help texts before final layout."""
        for item in self._sizer.GetChildren():
            window = item.GetWindow()
            # Asked of the sizer: wxPython may give an item as a plain
            # SizerItem, without GetPos() (seen in a test, 2026-10-07)
            if (
                isinstance(window, wx.StaticText)
                and self._sizer.GetItemPosition(window).GetCol() == 0
                and self._sizer.GetItemSpan(window).GetColspan() == 1
            ):
                window.Wrap(self._label_width)
        # First layout pass to compute actual positions
        super().fit()
        # Wrap inline help texts based on actual position
        if self._inlineHelpCtrls:
            for help_ctrl, panel in self._inlineHelpCtrls:
                help_x = (
                    help_ctrl.GetScreenPosition().x
                    - self.GetScreenPosition().x
                )
                wrap_width = max(self._max_help_right - help_x, 100)
                help_ctrl.SetLabel(
                    help_ctrl.GetLabel()
                )  # Reset any prior wrap
                help_ctrl.Wrap(wrap_width)
            # Re-layout after wrapping changed control sizes
            super().fit()

    def addEntry(self, text, *controls, **kwargs):  # pylint: disable=W0221
        kwargs.pop("help_text", "")  # Consumed by helpers; strip if passed
        super().addEntry(text, *controls, **kwargs)


class SavePage(SettingsPage):
    pageName = "save"
    pageTitle = _("Files")
    pageIcon = "nuvola_devices_media-floppy"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, *args, **kwargs)
        self.addBooleanSetting(
            "file",
            "autosave",
            _("Auto save after every change"),
        )
        self.addBooleanSetting(
            "file",
            "saveinifileinprogramdir",
            _("Save settings (%s.ini) in the same " "directory as the program")
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
        self.fit()


class WindowBehaviorPage(SettingsPage):
    pageName = "window"
    pageTitle = _("Windows")
    pageIcon = "nuvola_apps_window_list"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, growable_column=-1, *args, **kwargs)
        self.addBooleanSetting(
            "window",
            "tips",
            _("Show tips window on startup"),
        )
        self.addBooleanSetting(
            "version",
            "notify",
            _("Check for new version of %(name)s on startup")
            % meta.data.metaDict,
        )
        self.addBooleanSetting(
            "window",
            "blinktaskbariconwhentrackingeffort",
            _("Make clock in the task bar tick when tracking effort"),
        )
        self.fit()


class ThemePage(SettingsPage):
    """Saved by OK or Apply, as every page, so Cancel drops a change
    (docs/PREFERENCES.md, OK, Apply and Cancel)."""

    pageName = "theme"
    pageTitle = _("Theme")
    pageIcon = "nuvola_apps_fsview"

    _CALENDAR_KEYS = [
        (section, key)
        for section in ("calendar_light", "calendar_dark")
        for key in (
            "weekday_header_bg",
            "weekday_header_fg",
            "other_month_bg",
            "other_month_bg_system",
            "weekend_day_fg",
            "today_border",
        )
    ]
    _SQUIGGLE_KEYS = [
        ("spellcheck_light", "squiggle_color"),
        ("spellcheck_dark", "squiggle_color"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(columns=7, growable_column=6, *args, **kwargs)
        # Other month colours picked, saved by OK: theme -> wx.Colour
        self._other_month_picked = {}

        # --- Mode Dropdown ---
        # Colours as drawn now; the label shows the system setting,
        # which on Windows applies after a restart
        self._is_dark = detect_dark_theme()
        detected = _("Dark") if detect_system_dark_theme() else _("Light")

        theme_choice = wx.Choice(self)
        current_theme = settings.get("window", "theme")
        for choice_value, choice_text in [
            ("light", _("Light Theme (Forced)")),
            ("dark", _("Dark Theme (Forced)")),
            ("automatic", _("Automatic (detect from system)")),
        ]:
            theme_choice.Append(choice_text, choice_value)
            if choice_value == current_theme:
                theme_choice.SetSelection(theme_choice.GetCount() - 1)
        if theme_choice.GetSelection() == wx.NOT_FOUND:
            theme_choice.SetSelection(0)

        self._detected_theme_label = wx.StaticText(
            self, label=_("(Detected: %s)") % detected
        )
        self._detected_theme_label.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )

        mode_panel = wx.Panel(self)
        mode_sizer = wx.BoxSizer(wx.HORIZONTAL)
        theme_choice.Reparent(mode_panel)
        self._detected_theme_label.Reparent(mode_panel)
        mode_sizer.Add(theme_choice, 0, wx.ALIGN_CENTER_VERTICAL)
        mode_sizer.Add(
            self._detected_theme_label,
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
            10,
        )
        mode_panel.SetSizer(mode_sizer)

        self.addEntry(
            _("Mode"),
            mode_panel,
            flags=[
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
            ],
        )
        self._choiceSettings.append(("window", "theme", [theme_choice]))
        self._add_restart_note(theme_choice)

        self.addLine()

        # --- Section: Calendar ---
        self.addEntry(
            _("Calendar"),
            _("System"),
            _("Light"),
            _("System"),
            _("Dark"),
            "",
            "",
            flags=[
                wx.ALL | wx.ALIGN_LEFT,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL,
                wx.ALL,
            ],
        )

        from taskcoachlib.config import defaults as defaults_mod

        calendar_rows_before = [
            ("weekday_header_bg", _("Weekday Header Background")),
            ("weekday_header_fg", _("Weekday Header Foreground")),
        ]
        calendar_rows_after = [
            ("weekend_day_fg", _("Weekend Day Foreground")),
            ("today_border", _("Today Border")),
        ]

        for setting_key, label_text in calendar_rows_before:
            light_color = settings.get("calendar_light", setting_key)
            dark_color = settings.get("calendar_dark", setting_key)

            light_picker = widgets.ColourPickerCtrl(
                self, colour=wx.Colour(*light_color)
            )
            dark_picker = widgets.ColourPickerCtrl(
                self, colour=wx.Colour(*dark_color)
            )

            reset_btn = wx.Button(self, label=_("Reset"), size=(60, -1))
            light_default = ast.literal_eval(
                defaults_mod.defaults["calendar_light"][setting_key]
            )
            dark_default = ast.literal_eval(
                defaults_mod.defaults["calendar_dark"][setting_key]
            )
            bound = (
                light_picker,
                dark_picker,
                light_default,
                dark_default,
            )
            reset_btn.Bind(
                wx.EVT_BUTTON,
                lambda evt, a=bound: self._on_reset(*a),
            )

            self.addEntry(
                label_text,
                "",
                light_picker,
                "",
                dark_picker,
                reset_btn,
                "",
                flags=[
                    wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL,
                ],
            )

            self._colorSettings.append(
                ("calendar_light", setting_key, light_picker)
            )
            self._colorSettings.append(
                ("calendar_dark", setting_key, dark_picker)
            )

        # --- Other Month Days BG (with "System" checkbox) ---
        light_other_month_color = settings.get(
            "calendar_light", "other_month_bg"
        )
        dark_other_month_color = settings.get(
            "calendar_dark", "other_month_bg"
        )
        light_use_system = settings.get(
            "calendar_light", "other_month_bg_system"
        )
        dark_use_system = settings.get(
            "calendar_dark", "other_month_bg_system"
        )

        self._other_month_light_check = wx.CheckBox(self)
        self._other_month_light_check.SetValue(light_use_system)

        # Light: panel containing both picker and N/A label (only one visible)
        self._other_month_light_panel = wx.Panel(self)
        light_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._other_month_light_picker = widgets.ColourPickerCtrl(
            self._other_month_light_panel,
            colour=wx.Colour(*light_other_month_color),
        )
        self._other_month_light_na = wx.StaticText(
            self._other_month_light_panel,
            label=_("N/A"),
            style=wx.ALIGN_CENTER_HORIZONTAL | wx.ST_NO_AUTORESIZE,
        )
        self._other_month_light_na.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        light_panel_sizer.Add(
            self._other_month_light_picker, 0, wx.ALIGN_CENTER_VERTICAL
        )
        light_panel_sizer.Add(
            self._other_month_light_na, 1, wx.ALIGN_CENTER_VERTICAL
        )
        self._other_month_light_panel.SetSizer(light_panel_sizer)
        self._other_month_light_panel.SetMinSize(
            self._other_month_light_picker.GetBestSize()
        )

        self._other_month_dark_check = wx.CheckBox(self)
        self._other_month_dark_check.SetValue(dark_use_system)

        # Dark: panel containing both picker and N/A label (only one visible)
        self._other_month_dark_panel = wx.Panel(self)
        dark_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._other_month_dark_picker = widgets.ColourPickerCtrl(
            self._other_month_dark_panel,
            colour=wx.Colour(*dark_other_month_color),
        )
        self._other_month_dark_na = wx.StaticText(
            self._other_month_dark_panel,
            label=_("N/A"),
            style=wx.ALIGN_CENTER_HORIZONTAL | wx.ST_NO_AUTORESIZE,
        )
        self._other_month_dark_na.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        dark_panel_sizer.Add(
            self._other_month_dark_picker, 0, wx.ALIGN_CENTER_VERTICAL
        )
        dark_panel_sizer.Add(
            self._other_month_dark_na, 1, wx.ALIGN_CENTER_VERTICAL
        )
        self._other_month_dark_panel.SetSizer(dark_panel_sizer)
        self._other_month_dark_panel.SetMinSize(
            self._other_month_dark_picker.GetBestSize()
        )

        # Set initial visibility based on system theme match:
        # - System checked + column matches current theme → show picker
        #   with system color
        # - System checked + column doesn't match → show N/A
        # - System unchecked → show picker with custom color
        light_show_na = (
            light_use_system and self._is_dark
        )  # light col, system checked, but we're in dark
        dark_show_na = (
            dark_use_system and not self._is_dark
        )  # dark col, system checked, but we're in light
        self._other_month_light_picker.Show(not light_show_na)
        self._other_month_light_na.Show(light_show_na)
        self._other_month_dark_picker.Show(not dark_show_na)
        self._other_month_dark_na.Show(dark_show_na)
        # When system is checked and theme matches, show the actual system
        # color
        if light_use_system and not self._is_dark:
            self._other_month_light_picker.SetColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
            )
        if dark_use_system and self._is_dark:
            self._other_month_dark_picker.SetColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
            )

        self._other_month_light_check.Bind(
            wx.EVT_CHECKBOX,
            lambda evt: self._on_other_month_system_toggle("light"),
        )
        self._other_month_dark_check.Bind(
            wx.EVT_CHECKBOX,
            lambda evt: self._on_other_month_system_toggle("dark"),
        )
        self._other_month_light_picker.Bind(
            wx.EVT_COLOURPICKER_CHANGED,
            lambda evt: self._on_other_month_color_picked("light"),
        )
        self._other_month_dark_picker.Bind(
            wx.EVT_COLOURPICKER_CHANGED,
            lambda evt: self._on_other_month_color_picked("dark"),
        )

        other_month_reset_btn = wx.Button(
            self, label=_("Reset"), size=(60, -1)
        )
        other_month_reset_btn.Bind(wx.EVT_BUTTON, self._on_reset_other_month)

        self.addEntry(
            _("Other Months Days Background"),
            self._other_month_light_check,
            self._other_month_light_panel,
            self._other_month_dark_check,
            self._other_month_dark_panel,
            other_month_reset_btn,
            "",
            flags=[
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL,
            ],
        )

        for setting_key, label_text in calendar_rows_after:
            light_color = settings.get("calendar_light", setting_key)
            dark_color = settings.get("calendar_dark", setting_key)

            light_picker = widgets.ColourPickerCtrl(
                self, colour=wx.Colour(*light_color)
            )
            dark_picker = widgets.ColourPickerCtrl(
                self, colour=wx.Colour(*dark_color)
            )

            reset_btn = wx.Button(self, label=_("Reset"), size=(60, -1))
            light_default = ast.literal_eval(
                defaults_mod.defaults["calendar_light"][setting_key]
            )
            dark_default = ast.literal_eval(
                defaults_mod.defaults["calendar_dark"][setting_key]
            )
            bound = (
                light_picker,
                dark_picker,
                light_default,
                dark_default,
            )
            reset_btn.Bind(
                wx.EVT_BUTTON,
                lambda evt, a=bound: self._on_reset(*a),
            )

            self.addEntry(
                label_text,
                "",
                light_picker,
                "",
                dark_picker,
                reset_btn,
                "",
                flags=[
                    wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL,
                ],
            )

            self._colorSettings.append(
                ("calendar_light", setting_key, light_picker)
            )
            self._colorSettings.append(
                ("calendar_dark", setting_key, dark_picker)
            )

        # --- Section: Spellcheck ---
        self.addLine()
        self.addEntry(
            _("Spellcheck"),
            "",
            _("Light"),
            "",
            _("Dark"),
            "",
            "",
            flags=[
                wx.ALL | wx.ALIGN_LEFT,
                wx.ALL,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL,
                wx.ALL | wx.ALIGN_CENTER,
                wx.ALL,
                wx.ALL,
            ],
        )

        light_squiggle_color = settings.get(
            "spellcheck_light", "squiggle_color"
        )
        dark_squiggle_color = settings.get("spellcheck_dark", "squiggle_color")

        light_squiggle_picker = widgets.ColourPickerCtrl(
            self, colour=wx.Colour(*light_squiggle_color)
        )
        dark_squiggle_picker = widgets.ColourPickerCtrl(
            self, colour=wx.Colour(*dark_squiggle_color)
        )

        squiggle_reset_btn = wx.Button(self, label=_("Reset"), size=(60, -1))
        squiggle_light_default = ast.literal_eval(
            defaults_mod.defaults["spellcheck_light"]["squiggle_color"]
        )
        squiggle_dark_default = ast.literal_eval(
            defaults_mod.defaults["spellcheck_dark"]["squiggle_color"]
        )
        bound = (
            light_squiggle_picker,
            dark_squiggle_picker,
            squiggle_light_default,
            squiggle_dark_default,
        )
        squiggle_reset_btn.Bind(
            wx.EVT_BUTTON,
            lambda evt, a=bound: self._on_reset_squiggle(*a),
        )

        self.addEntry(
            _("Scintilla (Squiggle)"),
            "",
            light_squiggle_picker,
            "",
            dark_squiggle_picker,
            squiggle_reset_btn,
            "",
            flags=[
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL,
            ],
        )

        self._colorSettings.append(
            ("spellcheck_light", "squiggle_color", light_squiggle_picker)
        )
        self._colorSettings.append(
            ("spellcheck_dark", "squiggle_color", dark_squiggle_picker)
        )

        self.addLine()

        # --- Section: Hoverover Highlight ---
        self.addIntegerSetting(
            "window",
            "hoverlinewidth",
            _("Hoverover Highlight"),
            minimum=0,
            maximum=5,
            help_text=_(
                "Two-tone outline thickness per line in pixels when hovering "
                "over a row (0 to disable)"
            ),
        )

        # Follow system light/dark switches while preferences are open
        patterns.Publisher().registerObserver(
            self._on_system_theme_changed,
            eventType="system.theme_colour_changed",
        )
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)

        self.fit()

    def _on_reset(
        self, light_picker, dark_picker, light_default, dark_default
    ):
        light_picker.SetColour(wx.Colour(*light_default))
        dark_picker.SetColour(wx.Colour(*dark_default))

    def _on_other_month_system_toggle(self, theme):
        if theme == "light":
            checked = self._other_month_light_check.IsChecked()
            # N/A only when system checked but we can't show the color
            # (wrong theme)
            show_na = checked and self._is_dark
            self._other_month_light_picker.Show(not show_na)
            self._other_month_light_na.Show(show_na)
            if checked and not self._is_dark:
                # Matching theme: show system color in picker
                self._other_month_light_picker.SetColour(
                    wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
                )
            elif not checked:
                self._other_month_light_picker.SetColour(
                    self._other_month_colour("light")
                )
            self._other_month_light_panel.Layout()
        else:
            checked = self._other_month_dark_check.IsChecked()
            show_na = checked and not self._is_dark
            self._other_month_dark_picker.Show(not show_na)
            self._other_month_dark_na.Show(show_na)
            if checked and self._is_dark:
                # Matching theme: show system color in picker
                self._other_month_dark_picker.SetColour(
                    wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
                )
            elif not checked:
                self._other_month_dark_picker.SetColour(
                    self._other_month_colour("dark")
                )
            self._other_month_dark_panel.Layout()

    def _other_month_colour(self, theme):
        """The colour used without System: picked, else saved; the
        picker shows it once System is unchecked."""
        return wx.Colour(
            self._other_month_picked.get(
                theme, settings.get("calendar_" + theme, "other_month_bg")
            )
        )

    def _on_other_month_color_picked(self, theme):
        if theme == "light":
            picked = self._other_month_light_picker.GetColour()
            self._other_month_light_check.SetValue(False)
        else:
            picked = self._other_month_dark_picker.GetColour()
            self._other_month_dark_check.SetValue(False)
        self._other_month_picked[theme] = picked

    def _on_reset_other_month(self, event):
        from taskcoachlib.config import defaults as defaults_mod

        # Light: reset to system
        self._other_month_light_check.SetValue(True)
        light_show_na = (
            self._is_dark
        )  # can't show system color if we're in dark
        if not light_show_na:
            self._other_month_light_picker.SetColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
            )
        self._other_month_light_picker.Show(not light_show_na)
        self._other_month_light_na.Show(light_show_na)
        self._other_month_light_panel.Layout()
        # Dark: reset to specified default (custom color, system unchecked)
        dark_default = ast.literal_eval(
            defaults_mod.defaults["calendar_dark"]["other_month_bg"]
        )
        self._other_month_dark_picker.SetColour(wx.Colour(*dark_default))
        self._other_month_dark_check.SetValue(False)
        self._other_month_picked["dark"] = wx.Colour(*dark_default)
        self._other_month_dark_picker.Show()
        self._other_month_dark_na.Hide()
        self._other_month_dark_panel.Layout()

    def _on_reset_squiggle(
        self, light_picker, dark_picker, light_default, dark_default
    ):
        light_picker.SetColour(wx.Colour(*light_default))
        dark_picker.SetColour(wx.Colour(*dark_default))

    def values(self):
        values = super().values()
        for theme, check in (
            ("light", self._other_month_light_check),
            ("dark", self._other_month_dark_check),
        ):
            section = "calendar_" + theme
            values.append(
                (section, "other_month_bg_system", check.IsChecked())
            )
            values.append(
                (section, "other_month_bg", self._other_month_colour(theme))
            )
        return values

    def ok(self):
        calendar = [settings.get(*key) for key in self._CALENDAR_KEYS]
        squiggle = [settings.get(*key) for key in self._SQUIGGLE_KEYS]
        super().ok()
        # Open calendars, date pickers and text fields redraw
        if [settings.get(*key) for key in self._CALENDAR_KEYS] != calendar:
            patterns.Event("calendar.colours.changed", self).send()
        if [settings.get(*key) for key in self._SQUIGGLE_KEYS] != squiggle:
            patterns.Event("spellcheck.colours.changed", self).send()

    def _add_restart_note(self, theme_choice):
        """Add the restart note below Mode, if a restart is ever needed.

        Only Windows applies Mode to native controls, and only at startup
        (see apply_native_appearance), so the note is shown only there.
        It turns red while the selection differs from the Mode that was
        applied when the app started.
        """
        self._applied_theme = getattr(
            wx.GetApp(), "native_appearance_theme", None
        )
        if self._applied_theme is None:
            return
        self._theme_choice = theme_choice
        self._restart_note_base = (
            _(
                "Native controls (menus, buttons, scroll bars) switch to a "
                "new Mode after a restart of %s."
            )
            % meta.name
        )
        self._restart_note = wx.StaticText(self, label=self._restart_note_base)
        self._restart_note_default_colour = wx.SystemSettings.GetColour(
            wx.SYS_COLOUR_GRAYTEXT
        )
        self.addEntry(
            "",
            self._restart_note,
            flags=[
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
            ],
        )
        theme_choice.Bind(wx.EVT_CHOICE, self._on_theme_mode_change)
        self._update_restart_note()

    def _on_theme_mode_change(self, event):
        self._update_restart_note()
        event.Skip()

    def _update_restart_note(self):
        """Show the restart note in red while the Mode differs from the
        one applied at startup."""
        selected = self._theme_choice.GetClientData(
            self._theme_choice.GetSelection()
        )
        if selected != self._applied_theme:
            self._restart_note.SetLabel(
                self._restart_note_base
                + " "
                + _("Change detected, restart required!")
            )
            self._restart_note.SetForegroundColour(wx.Colour(180, 0, 0))
        else:
            self._restart_note.SetLabel(self._restart_note_base)
            self._restart_note.SetForegroundColour(
                self._restart_note_default_colour
            )
        self._restart_note.Refresh()
        self.Layout()

    def _on_destroy(self, event):
        if event.GetEventObject() is self:
            patterns.Publisher().removeObserver(
                self._on_system_theme_changed,
                eventType="system.theme_colour_changed",
            )
        event.Skip()

    def _on_system_theme_changed(self, event):  # pylint: disable=W0613
        """Update the detected theme and system colour pickers."""
        detected = _("Dark") if detect_system_dark_theme() else _("Light")
        self._detected_theme_label.SetLabel(_("(Detected: %s)") % detected)
        current_dark = detect_dark_theme()
        if current_dark != self._is_dark:
            self._is_dark = current_dark
            # Update Other Month picker/N/A visibility
            light_checked = self._other_month_light_check.IsChecked()
            dark_checked = self._other_month_dark_check.IsChecked()
            light_show_na = light_checked and self._is_dark
            dark_show_na = dark_checked and not self._is_dark
            self._other_month_light_picker.Show(not light_show_na)
            self._other_month_light_na.Show(light_show_na)
            if light_checked and not self._is_dark:
                self._other_month_light_picker.SetColour(
                    wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
                )
            self._other_month_light_panel.Layout()
            self._other_month_dark_picker.Show(not dark_show_na)
            self._other_month_dark_na.Show(dark_show_na)
            if dark_checked and self._is_dark:
                self._other_month_dark_picker.SetColour(
                    wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
                )
            self._other_month_dark_panel.Layout()


class LanguagePage(SettingsPage):
    pageName = "language"
    pageTitle = _("Regional")
    pageIcon = "nuvola_categories_applications-education-language"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, *args, **kwargs)

        # === LANGUAGE SECTION ===
        # Restart warning above the dropdown (covers language and format changes)
        self._restart_warning_base = (
            _(
                "Changing the language or date/time format requires a restart of %s."
            )
            % meta.name
        )
        self._restart_warning = wx.StaticText(
            self, label=self._restart_warning_base
        )
        self._restart_warning_default_color = wx.SystemSettings.GetColour(
            wx.SYS_COLOUR_GRAYTEXT
        )
        self._restart_warning.SetForegroundColour(
            self._restart_warning_default_color
        )
        self.addEntry("", self._restart_warning)

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
            ("da_DK", "Dansk (Danish)"),
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
        all_languages = dict(list(data.languages.values()))
        for code, label in languages:
            if code == "en_US":
                label = "English (US)"
                enabled = True
            elif code in all_languages:
                enabled = all_languages[code]
            elif "_" in code:
                enabled = all_languages.get(code.split("_")[0], False)
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
        self._locale_warning = wx.StaticText(
            panel,
            label=_(
                "WARNING: The selected language's locale is not installed on your system. "
                "Some date and time formats may appear in your system's format instead."
            ),
        )
        self._locale_warning.SetForegroundColour(wx.Colour(180, 0, 0))
        sizer.Add(self._locale_warning, 0, wx.BOTTOM, 10)

        # Help text
        text = wx.StaticText(
            panel,
            label=_(
                "Language missing or translation needs improving? Open an issue or pull request:"
            ),
        )
        text.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        sizer.Add(text)
        url = meta.github_url + "/issues"
        url_ctrl = HyperLinkCtrl(panel, -1, label=url, URL=url)
        sizer.Add(url_ctrl, 0, wx.TOP, 2)
        panel.SetSizer(sizer)
        self.addEntry("", panel)

        # Store original language to detect changes
        self._original_language = self._get_selected_language_code()

        # Check if current language has locale installed and update warning visibility
        self._update_locale_warning()

        # Bind to dropdown change to update warnings dynamically
        for section, setting, choice_ctrls in self._choiceSettings:
            if setting == "language_set_by_user":
                choice_ctrls[0].Bind(wx.EVT_CHOICE, self._on_language_change)

        # Separator line between language and spell check sections
        self.addLine()

        # === SPELL CHECK SECTION ===
        self._setupSpellCheckSection()

        # Separator line between spell check and date/time format sections
        self.addLine()

        # === DATE FORMAT SECTION ===
        # Date format dropdown with detected format label
        date_format_panel = wx.Panel(self)
        date_format_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Date format choices: value is the format string (e.g., "YMD-", "MDY/")
        self._date_format_choice = wx.Choice(date_format_panel)
        date_formats = [
            ("", _("Automatic (detect from system)")),
            ("YMD-", _("YYYY-MM-DD (ISO format)")),
            ("YMD/", _("YYYY/MM/DD (East Asian)")),
            ("MDY/", _("MM/DD/YYYY (US)")),
            ("DMY/", _("DD/MM/YYYY (European)")),
            ("DMY.", _("DD.MM.YYYY (German)")),
        ]
        current_format = settings.get("view", "dateformat")
        selected_idx = 0
        for i, (value, label) in enumerate(date_formats):
            self._date_format_choice.Append(label, value)
            if value == current_format:
                selected_idx = i
        self._date_format_choice.SetSelection(selected_idx)
        self._date_format_choice.Bind(
            wx.EVT_CHOICE, self._on_date_format_change
        )
        date_format_sizer.Add(
            self._date_format_choice, 0, wx.ALIGN_CENTER_VERTICAL
        )

        # Detected format label
        from taskcoachlib.widgets.maskedtimectrl import (
            getDetectedLocaleDateFormat,
        )

        detected_order, detected_sep = getDetectedLocaleDateFormat()
        detected_str = self._format_order_to_string(
            detected_order, detected_sep
        )
        self._detected_format_label = wx.StaticText(
            date_format_panel, label=_("Detected: %s") % detected_str
        )
        self._detected_format_label.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        date_format_sizer.Add(
            self._detected_format_label,
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
            15,
        )

        date_format_panel.SetSizer(date_format_sizer)
        self.addEntry(_("Date format"), date_format_panel)

        # Demo DateComboRouterCtrl showing the selected format (interactive, starts with today)
        demo_panel = wx.Panel(self)
        demo_sizer = wx.BoxSizer(wx.HORIZONTAL)
        demo_label = wx.StaticText(demo_panel, label=_("Preview:"))
        demo_sizer.Add(demo_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        demo_panel.SetSizer(demo_sizer)
        self._demo_date_panel = demo_panel
        self._demo_date_ctrl = None
        self._rebuild_demo_date_ctrl(current_format or None)
        self.addEntry("", demo_panel)

        # === DISPLAY OVERRIDE SECTION ===
        # Optional display-only override (does not affect date entry).
        display_override_panel = wx.Panel(self)
        display_override_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._display_override_choice = wx.Choice(display_override_panel)
        display_overrides = [
            ("", _("None")),
            ("LONG_DMY", _("Saturday, 28 March 2026")),
            ("ISO_ABBREV", _("2026-Mar-28-Sat")),
        ]
        current_override = settings.get("view", "dateformat_display_override")
        selected_override_idx = 0
        for i, (value, label) in enumerate(display_overrides):
            self._display_override_choice.Append(label, value)
            if value == current_override:
                selected_override_idx = i
        self._display_override_choice.SetSelection(selected_override_idx)
        self._display_override_choice.Bind(
            wx.EVT_CHOICE, self._on_display_override_change
        )
        display_override_sizer.Add(
            self._display_override_choice, 0, wx.ALIGN_CENTER_VERTICAL
        )
        display_override_panel.SetSizer(display_override_sizer)
        self.addEntry(_("Display override"), display_override_panel)

        # Preview below the override dropdown (empty when None).
        override_preview_panel = wx.Panel(self)
        override_preview_sizer = wx.BoxSizer(wx.HORIZONTAL)
        override_preview_label = wx.StaticText(
            override_preview_panel, label=_("Preview:")
        )
        override_preview_sizer.Add(
            override_preview_label,
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )
        override_preview_panel.SetSizer(override_preview_sizer)
        self._display_override_preview_panel = override_preview_panel
        self._display_override_preview_ctrl = None
        self._rebuild_display_override_preview(current_override)
        self.addEntry("", override_preview_panel)

        # === TIME FORMAT SECTION ===
        # Time format dropdown with detected format label
        time_format_panel = wx.Panel(self)
        time_format_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self._time_format_choice = wx.Choice(time_format_panel)
        time_formats = [
            ("", _("Automatic (detect from system)")),
            ("24", _("24-hour (14:30)")),
            ("12", _("12-hour (2:30 PM)")),
        ]
        current_time_format = settings.get("view", "timeformat")
        selected_time_idx = 0
        for i, (value, label) in enumerate(time_formats):
            self._time_format_choice.Append(label, value)
            if value == current_time_format:
                selected_time_idx = i
        self._time_format_choice.SetSelection(selected_time_idx)
        time_format_sizer.Add(
            self._time_format_choice, 0, wx.ALIGN_CENTER_VERTICAL
        )

        # Detected time format label
        from taskcoachlib.widgets.maskedtimectrl import (
            getDetectedLocaleTimeFormat,
        )

        detected_time_format = getDetectedLocaleTimeFormat()
        detected_time_str = (
            "24-hour" if detected_time_format == "24" else "12-hour"
        )
        self._detected_time_format_label = wx.StaticText(
            time_format_panel, label=_("Detected: %s") % detected_time_str
        )
        self._detected_time_format_label.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        time_format_sizer.Add(
            self._detected_time_format_label,
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
            15,
        )

        time_format_panel.SetSizer(time_format_sizer)
        self._time_format_choice.Bind(
            wx.EVT_CHOICE, self._on_time_format_change
        )
        self.addEntry(_("Time format"), time_format_panel)

        # Demo TimeCtrl showing the selected format (interactive, starts with current time)
        time_demo_panel = wx.Panel(self)
        time_demo_sizer = wx.BoxSizer(wx.HORIZONTAL)
        time_demo_label = wx.StaticText(time_demo_panel, label=_("Preview:"))
        time_demo_sizer.Add(
            time_demo_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10
        )
        time_demo_panel.SetSizer(time_demo_sizer)
        self._demo_time_panel = time_demo_panel
        self._demo_time_ctrl = None
        self._rebuild_demo_time_ctrl(
            current_time_format if current_time_format else "24"
        )
        self.addEntry("", time_demo_panel)

        # Note about 12-hour mode and working hours
        self.addHintRow(
            _(
                "Note: In 12-hour mode, working hours (set in Features tab) are not used for hour suggestions."
            )
        )

        # Separator line between time format and number format sections
        self.addLine()

        # === NUMBER FORMAT SECTION ===
        # Decimal separator dropdown
        dec_sep_panel = wx.Panel(self)
        dec_sep_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self._decimal_sep_choice = wx.Choice(dec_sep_panel)
        decimal_sep_formats = [
            ("", _("Automatic (detect from system)")),
            (".", _("Period (.)")),
            (",", _("Comma (,)")),
        ]
        current_dec_sep = settings.get("view", "decimal_separator")
        selected_dec_sep_idx = 0
        for i, (value, label) in enumerate(decimal_sep_formats):
            self._decimal_sep_choice.Append(label, value)
            if value == current_dec_sep:
                selected_dec_sep_idx = i
        self._decimal_sep_choice.SetSelection(selected_dec_sep_idx)
        self._decimal_sep_choice.Bind(
            wx.EVT_CHOICE, self._on_decimal_sep_change
        )
        dec_sep_sizer.Add(
            self._decimal_sep_choice, 0, wx.ALIGN_CENTER_VERTICAL
        )

        # Detected decimal separator label
        import locale as _locale

        detected_dec_sep = (
            _locale.localeconv().get("decimal_point", ".") or "."
        )
        self._detected_dec_sep_label = wx.StaticText(
            dec_sep_panel,
            label=_("Detected: %s") % ('"%s"' % detected_dec_sep),
        )
        self._detected_dec_sep_label.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        dec_sep_sizer.Add(
            self._detected_dec_sep_label,
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
            15,
        )

        dec_sep_panel.SetSizer(dec_sep_sizer)
        self.addEntry(_("Decimal separator"), dec_sep_panel)

        # Currency decimal places dropdown
        curr_dp_panel = wx.Panel(self)
        curr_dp_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self._currency_dp_choice = wx.Choice(curr_dp_panel)
        currency_dp_options = [
            ("", _("Automatic (from locale)")),
            ("0", _("0 (e.g. JPY, KRW)")),
            ("2", _("2 (e.g. USD, EUR)")),
            ("3", _("3 (e.g. BHD, KWD)")),
        ]
        current_curr_dp = settings.get("view", "currency_decimal_places")
        selected_curr_dp_idx = 0
        for i, (value, label) in enumerate(currency_dp_options):
            self._currency_dp_choice.Append(label, value)
            if value == current_curr_dp:
                selected_curr_dp_idx = i
        self._currency_dp_choice.SetSelection(selected_curr_dp_idx)
        self._currency_dp_choice.Bind(
            wx.EVT_CHOICE, self._on_currency_dp_change
        )
        curr_dp_sizer.Add(
            self._currency_dp_choice, 0, wx.ALIGN_CENTER_VERTICAL
        )

        # Detected currency decimal places label
        detected_frac = _locale.localeconv().get("frac_digits", 2)
        if detected_frac == 127:
            detected_frac = 2
        self._detected_curr_dp_label = wx.StaticText(
            curr_dp_panel, label=_("Detected: %d") % detected_frac
        )
        self._detected_curr_dp_label.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        curr_dp_sizer.Add(
            self._detected_curr_dp_label,
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
            15,
        )

        curr_dp_panel.SetSizer(curr_dp_sizer)
        self.addEntry(_("Currency decimal places"), curr_dp_panel)

        # Demo CurrencyCtrl showing the selected decimal separator and places (live update)
        from taskcoachlib.widgets.numericctrl import NumericCtrl

        curr_demo_panel = wx.Panel(self)
        curr_demo_sizer = wx.BoxSizer(wx.HORIZONTAL)
        curr_demo_label = wx.StaticText(curr_demo_panel, label=_("Preview:"))
        curr_demo_sizer.Add(
            curr_demo_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10
        )
        # Resolve effective decimal char and places for initial demo
        effective_dec_char = current_dec_sep or detected_dec_sep
        if current_curr_dp:
            effective_curr_dp = int(current_curr_dp)
        else:
            effective_curr_dp = detected_frac
        self._demo_currency_ctrl = NumericCtrl(
            curr_demo_panel,
            value=1234.56,
            decimal_places=effective_curr_dp,
            decimal_char=effective_dec_char,
        )
        curr_demo_sizer.Add(
            self._demo_currency_ctrl, 0, wx.ALIGN_CENTER_VERTICAL
        )
        curr_demo_panel.SetSizer(curr_demo_sizer)
        self.addEntry("", curr_demo_panel)

        # Store original formats to detect changes
        self._original_date_format = current_format
        self._original_display_override = current_override
        self._original_time_format = current_time_format
        self._original_decimal_sep = current_dec_sep
        self._original_currency_dp = current_curr_dp

        self.fit()

    def _setupSpellCheckSection(self):
        """Set up the spell check configuration section."""
        from taskcoachlib.widgets.textctrl import (
            SpellCheckMixin,
            ENCHANT_AVAILABLE,
        )

        # Spell check enabled checkbox
        self._spellCheckEnabledCheck = self.addBooleanSetting(
            "spellcheck",
            "enabled",
            _("Spell checking"),
            _("Enable spell checking"),
        )
        self._spellCheckEnabled = self._spellCheckEnabledCheck.GetValue()
        self._spellCheckEnabledCheck.Bind(
            wx.EVT_CHECKBOX, self._onSpellCheckEnabledChange
        )

        # Show warning if enchant is not available
        if not ENCHANT_AVAILABLE:
            warning_text = wx.StaticText(
                self,
                label=_(
                    "Warning: Spell checking is not available. Install pyenchant to enable this feature."
                ),
            )
            warning_text.SetForegroundColour(wx.Colour(180, 0, 0))
            self.addEntry("", warning_text)
            self._spellCheckEnabledCheck.Enable(False)

        # Language dropdown for spell check
        spell_lang_panel = wx.Panel(self)
        spell_lang_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self._spellCheckLangChoice = wx.Choice(spell_lang_panel)

        # Add automatic option first
        self._spellCheckLangChoice.Append(
            _("Automatic (detect from system)"), ""
        )

        # Get available languages
        available_langs = (
            SpellCheckMixin.getAvailableLanguages()
            if ENCHANT_AVAILABLE
            else []
        )
        current_spell_lang = settings.get("spellcheck", "language")
        selected_idx = 0

        for i, lang in enumerate(sorted(available_langs)):
            self._spellCheckLangChoice.Append(lang, lang)
            if lang == current_spell_lang:
                selected_idx = i + 1  # +1 because of "Automatic" option

        self._spellCheckLangChoice.SetSelection(selected_idx)
        self._spellCheckLangChoice.Enable(
            self._spellCheckEnabled and ENCHANT_AVAILABLE
        )
        spell_lang_sizer.Add(
            self._spellCheckLangChoice, 0, wx.ALIGN_CENTER_VERTICAL
        )

        # Show detected language
        if ENCHANT_AVAILABLE:
            detected_lang = SpellCheckMixin._detectLanguage()
            detected_label = wx.StaticText(
                spell_lang_panel, label=_("Detected: %s") % detected_lang
            )
            detected_label.SetForegroundColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
            )
            spell_lang_sizer.Add(
                detected_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 15
            )

        spell_lang_panel.SetSizer(spell_lang_sizer)
        self.addEntry(_("Spell check language"), spell_lang_panel)

        # Note about dropdown and how to install more dictionaries
        if ENCHANT_AVAILABLE:
            import platform

            system = platform.system()

            if not available_langs:
                self.addHintRow(
                    _(
                        "Language missing? Install hunspell packages for your language."
                    )
                )

            # Platform-specific note combining dropdown info and install instructions
            if system == "Linux":
                note_text = _(
                    "Dropdown shows installed dictionaries. Install via: apt install hunspell-en-us"
                )
            elif system == "Darwin":
                note_text = _(
                    "Dropdown shows installed dictionaries. Install via: brew install hunspell"
                )
            else:  # Windows
                note_text = _(
                    "Dropdown shows installed dictionaries. Additional languages must be prepackaged."
                )
            self.addHintRow(note_text)

    def _onSpellCheckEnabledChange(self, event):
        """Handle spell check enabled checkbox change."""
        from taskcoachlib.widgets.textctrl import ENCHANT_AVAILABLE

        enabled = event.IsChecked()
        self._spellCheckLangChoice.Enable(enabled and ENCHANT_AVAILABLE)
        event.Skip()

    def _format_order_to_string(self, field_order, separator):
        """Convert field order and separator to a human-readable format string."""
        field_map = {"year": "YYYY", "month": "MM", "date_day": "DD"}
        parts = [field_map.get(f, "??") for f in field_order]
        return separator.join(parts)

    def _get_selected_language_code(self):
        """Get the currently selected language code from the dropdown."""
        for section, setting, choice_ctrls in self._choiceSettings:
            if setting == "language_set_by_user":
                choice = choice_ctrls[0]
                return choice.GetClientData(choice.GetSelection())
        return ""

    def _rebuild_demo_date_ctrl(self, date_format):
        """(Re)create the demo DateComboRouterCtrl with the given format."""
        from taskcoachlib.widgets.maskedtimectrl import DateComboRouterCtrl
        import datetime

        today = datetime.date.today()
        parent = self._demo_date_panel
        sizer = parent.GetSizer()
        if self._demo_date_ctrl:
            self._demo_date_ctrl.Destroy()
        self._demo_date_ctrl = DateComboRouterCtrl(
            parent,
            year=today.year,
            month=today.month,
            day=today.day,
            date_format=date_format,
        )
        sizer.Add(self._demo_date_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        parent.Layout()
        parent.Fit()

    def _rebuild_demo_time_ctrl(self, time_format):
        """(Re)create the demo TimeCtrl with the given format."""
        from taskcoachlib.widgets.maskedtimectrl import TimeCtrl
        import datetime

        now = datetime.datetime.now()
        parent = self._demo_time_panel
        sizer = parent.GetSizer()
        if self._demo_time_ctrl:
            self._demo_time_ctrl.Destroy()
        self._demo_time_ctrl = TimeCtrl(
            parent, hours=now.hour, minutes=now.minute, time_format=time_format
        )
        sizer.Add(self._demo_time_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        parent.Layout()
        parent.Fit()

    def _on_date_format_change(self, event):
        """Handle date format dropdown change - update demo control and restart warning."""
        choice = event.GetEventObject()
        new_format = choice.GetClientData(choice.GetSelection())
        self._rebuild_demo_date_ctrl(new_format or None)
        self._update_restart_warning()
        event.Skip()

    def _rebuild_display_override_preview(self, override):
        """(Re)build the preview for the Display Override setting.

        Empty override renders no preview (clears the slot). A recognized
        override renders a static label formatted via strftime with today.
        An unrecognized non-empty value is logged and rendered as blank.
        """
        from taskcoachlib.render import _DISPLAY_ONLY_DATE_FORMATS
        import datetime

        parent = self._display_override_preview_panel
        sizer = parent.GetSizer()
        if self._display_override_preview_ctrl:
            self._display_override_preview_ctrl.Destroy()
            self._display_override_preview_ctrl = None
        if override in _DISPLAY_ONLY_DATE_FORMATS:
            self._display_override_preview_ctrl = wx.StaticText(
                parent,
                label=datetime.date.today().strftime(
                    _DISPLAY_ONLY_DATE_FORMATS[override]
                ),
            )
            sizer.Add(
                self._display_override_preview_ctrl,
                0,
                wx.ALIGN_CENTER_VERTICAL,
            )
        elif override:
            from taskcoachlib.meta.debug import log_step

            log_step(
                "unknown display override %r; no preview shown" % override,
                prefix="PREFS",
            )
        parent.Layout()
        parent.Fit()

    def _on_display_override_change(self, event):
        """Handle display-override dropdown change."""
        choice = event.GetEventObject()
        new_override = choice.GetClientData(choice.GetSelection())
        self._rebuild_display_override_preview(new_override)
        self._update_restart_warning()
        event.Skip()

    def _on_time_format_change(self, event):
        """Handle time format dropdown change - update demo control and restart warning."""
        choice = event.GetEventObject()
        new_format = choice.GetClientData(choice.GetSelection())
        self._rebuild_demo_time_ctrl(new_format if new_format else "24")
        self._update_restart_warning()
        event.Skip()

    def _on_decimal_sep_change(self, event):
        """Handle decimal separator dropdown change - update demo and restart warning."""
        self._update_currency_demo()
        self._update_restart_warning()
        event.Skip()

    def _on_currency_dp_change(self, event):
        """Handle currency decimal places dropdown change - update demo and restart warning."""
        self._update_currency_demo()
        self._update_restart_warning()
        event.Skip()

    def _update_currency_demo(self):
        """Recreate the demo NumericCtrl with current dropdown selections."""
        import locale as _locale
        from taskcoachlib.widgets.numericctrl import NumericCtrl

        # Resolve effective decimal char
        selected_dec_sep = self._decimal_sep_choice.GetClientData(
            self._decimal_sep_choice.GetSelection()
        )
        if not selected_dec_sep:
            selected_dec_sep = _locale.localeconv().get("decimal_point", ".")

        # Resolve effective currency decimal places
        selected_curr_dp = self._currency_dp_choice.GetClientData(
            self._currency_dp_choice.GetSelection()
        )
        if selected_curr_dp:
            effective_dp = int(selected_curr_dp)
        else:
            effective_dp = _locale.localeconv().get("frac_digits", 2)
            if effective_dp == 127:
                effective_dp = 2

        # Destroy old and create new
        parent = self._demo_currency_ctrl.GetParent()
        sizer = parent.GetSizer()
        self._demo_currency_ctrl.Destroy()
        self._demo_currency_ctrl = NumericCtrl(
            parent,
            value=1234.56,
            decimal_places=effective_dp,
            decimal_char=selected_dec_sep,
        )
        sizer.Add(self._demo_currency_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        parent.Layout()
        parent.Fit()

    def _on_language_change(self, event):
        """Handle language dropdown change."""
        self._update_locale_warning()
        self._update_restart_warning()
        event.Skip()

    def _update_restart_warning(self):
        """Update restart warning to show change detected state."""
        selected_lang = self._get_selected_language_code()
        selected_date_format = self._date_format_choice.GetClientData(
            self._date_format_choice.GetSelection()
        )
        selected_time_format = self._time_format_choice.GetClientData(
            self._time_format_choice.GetSelection()
        )

        selected_decimal_sep = self._decimal_sep_choice.GetClientData(
            self._decimal_sep_choice.GetSelection()
        )
        selected_currency_dp = self._currency_dp_choice.GetClientData(
            self._currency_dp_choice.GetSelection()
        )

        selected_display_override = (
            self._display_override_choice.GetClientData(
                self._display_override_choice.GetSelection()
            )
        )

        # Check if any regional setting has changed
        language_changed = selected_lang != self._original_language
        date_format_changed = (
            selected_date_format != self._original_date_format
        )
        display_override_changed = (
            selected_display_override != self._original_display_override
        )
        time_format_changed = (
            selected_time_format != self._original_time_format
        )
        decimal_sep_changed = (
            selected_decimal_sep != self._original_decimal_sep
        )
        currency_dp_changed = (
            selected_currency_dp != self._original_currency_dp
        )

        if (
            language_changed
            or date_format_changed
            or display_override_changed
            or time_format_changed
            or decimal_sep_changed
            or currency_dp_changed
        ):
            # Change detected - show red warning
            self._restart_warning.SetLabel(
                self._restart_warning_base
                + " "
                + _("Change detected, restart required!")
            )
            self._restart_warning.SetForegroundColour(wx.Colour(180, 0, 0))
        else:
            # Reverted to original - restore normal state
            self._restart_warning.SetLabel(self._restart_warning_base)
            self._restart_warning.SetForegroundColour(
                self._restart_warning_default_color
            )
        self._restart_warning.Refresh()
        self.Layout()

    def _update_locale_warning(self):
        """Show or hide the locale warning based on selected language's locale availability."""
        from taskcoachlib import i18n

        # Check if the selected language's locale is available on the system
        selected_lang = self._get_selected_language_code()
        show_warning = not i18n.isLocaleAvailable(selected_lang)
        self._locale_warning.Show(show_warning)
        self.Layout()

    def values(self):
        def selected(choice):
            return choice.GetClientData(choice.GetSelection())

        return super().values() + [
            ("view", "language", self._get_selected_language_code()),
            ("view", "dateformat", selected(self._date_format_choice)),
            # Applies only to rendering
            (
                "view",
                "dateformat_display_override",
                selected(self._display_override_choice),
            ),
            ("view", "timeformat", selected(self._time_format_choice)),
            ("view", "decimal_separator", selected(self._decimal_sep_choice)),
            (
                "view",
                "currency_decimal_places",
                selected(self._currency_dp_choice),
            ),
            ("spellcheck", "language", selected(self._spellCheckLangChoice)),
        ]


class StatusesPage(SettingsPage):
    pageName = "statuses"
    pageTitle = _("Statuses")
    pageIcon = "nuvola_apps_kcoloredit"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=11, growable_column=-1, *args, **kwargs)
        self._priorityChoices = []  # [(setting, choiceCtrl), ...]
        self._previousPriorities = {}  # choiceCtrl -> int
        self.add_appearance_header()
        for status in task.Task.possibleStatuses():
            setting = "%stasks" % status
            label = status.plural_label.replace(" tasks", "")
            self.add_appearance_setting(
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
        for section, setting, icon_entry in self._iconSettings:
            icon_entry.Bind(
                wx.EVT_COMBOBOX,
                lambda evt, ie=icon_entry: self._on_status_icon_changed(
                    evt, ie
                ),
            )
        # Separator lines under the table, matching header lines
        line_row = self._position.next(11)  # consume full row, get row number
        self._sizer.Add(
            wx.StaticLine(self),
            (line_row[0], 0),
            span=(1, 1),
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=self._borderWidth,
        )
        self._sizer.Add(
            wx.StaticLine(self),
            (line_row[0], 1),
            span=(1, 1),
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=self._borderWidth,
        )
        self._sizer.Add(
            wx.StaticLine(self),
            (line_row[0], 2),
            span=(1, 4),
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=self._borderWidth,
        )
        self._sizer.Add(
            wx.StaticLine(self),
            (line_row[0], 6),
            span=(1, 4),
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=self._borderWidth,
        )
        # Reset priorities button placed directly in col 1 (priority column)
        reset_priorities_btn = wx.Button(self, label=_("Reset"), size=(60, -1))
        reset_priorities_btn.Bind(wx.EVT_BUTTON, self._on_reset_priorities)
        reset_row = self._position.next(11)  # consume full row, get row number
        self._sizer.Add(
            reset_priorities_btn,
            (reset_row[0], 1),
            span=(1, 1),
            flag=wx.ALL | wx.ALIGN_CENTER,
            border=self._borderWidth,
        )
        # Note text spanning all columns, left-aligned
        note_text = wx.StaticText(
            self,
            label=_(
                "These appearance settings can be overridden "
                "for individual tasks in the task edit dialog."
            ),
        )
        note_text.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )
        note_row = self._position.next(11)  # consume full row
        self._sizer.Add(
            note_text,
            (note_row[0], 0),
            span=(1, 11),
            flag=wx.ALL | wx.ALIGN_LEFT,
            border=self._borderWidth,
        )
        # Where an item's style starts (docs/APPEARANCE_STYLES.md,
        # Appearance Flow); a dropdown, so a later variation is a choice
        self._add_divider()
        self.addChoiceSetting(
            "appearance",
            "flow",
            _("Appearance flow"),
            _(
                "Where the icon, colours and font of an item without its "
                "own come from: categories pass theirs to their items and "
                "subcategories, tasks and notes to their subtasks and "
                "subnotes. A task's status always shows."
            ),
            [
                ("all", _("From categories and tasks")),
                ("categories", _("From categories only")),
                ("tasks", _("From tasks only")),
                ("none", _("None")),
            ],
        )
        # Legacy status icon support, at the bottom
        self._add_divider()
        self.addBooleanSetting(
            "icon",
            "legacystatusicons",
            _("Legacy"),
            _(
                "All statuses must be reset to their defaults and this "
                "option must be enabled to make the INI settings file "
                "compatible with Task Coach < 2.0.1.72. "
                "The task data file may reference newer icons that older "
                "versions cannot display, but it will not crash, the icons "
                "simply won't appear in older versions of Task Coach."
            ),
        )
        self.fit()

    def _add_divider(self):
        """A line across the page's eleven columns."""
        row = self._position.next(11)
        self._sizer.Add(
            wx.StaticLine(self),
            (row[0], 0),
            span=(1, 11),
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=self._borderWidth,
        )

    def _on_status_icon_changed(self, event, icon_entry):
        """Handle icon selection change. Excluded icons are handled by IconPicker."""
        # The new IconPicker prevents selection of excluded icons internally
        event.Skip()

    def _on_priority_changed(self, event):
        """Handle priority dropdown change with insert-before semantics."""
        changed = event.GetEventObject()
        new_priority = changed.GetSelection() + 1  # 0-indexed -> 1-indexed
        old_priority = self._previousPriorities[changed]
        if new_priority == old_priority:
            return
        for setting, ctrl in self._priorityChoices:
            if ctrl is changed:
                continue
            p = ctrl.GetSelection() + 1
            if new_priority < old_priority:
                # Moving up: priorities in [new, old) get +1
                if new_priority <= p < old_priority:
                    ctrl.SetSelection(p)  # p+1 in 0-indexed = p
            else:
                # Moving down: priorities in (old, new] get -1
                if old_priority < p <= new_priority:
                    ctrl.SetSelection(p - 2)  # p-1 in 0-indexed = p-2
        # Update all previous priorities
        for setting, ctrl in self._priorityChoices:
            self._previousPriorities[ctrl] = ctrl.GetSelection() + 1

    def _on_reset_priorities(self, event):
        """Reset all priority dropdowns to their defaults."""
        from taskcoachlib.config import defaults as defaults_mod

        defs = defaults_mod.defaults
        for setting, ctrl in self._priorityChoices:
            default_priority = int(defs["statussortpriority"][setting])
            ctrl.SetSelection(default_priority - 1)
        for setting, ctrl in self._priorityChoices:
            self._previousPriorities[ctrl] = ctrl.GetSelection() + 1

    def values(self):
        return [
            ("statussortpriority", setting, ctrl.GetSelection() + 1)
            for setting, ctrl in self._priorityChoices
        ] + super().values()

    def ok(self):
        before = self.__priorities()
        super().ok()
        if self.__priorities() != before:
            patterns.Event("settings.statussortpriority.changed", self).send()

    def __priorities(self):
        return [
            settings.get("statussortpriority", setting)
            for setting, unused_ctrl in self._priorityChoices
        ]


class FeaturesPage(SettingsPage):
    pageName = "features"
    pageTitle = _("Features")
    pageIcon = "nuvola_apps_preferences-system-session-services"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, growable_column=-1, *args, **kwargs)
        # The other settings on this tab apply at once
        self._restart_warning_base = (
            _("Working hours reach calendar views after a restart of %s.")
            % meta.name
        )
        self._restart_warning = wx.StaticText(
            self, label=self._restart_warning_base
        )
        self._restart_warning_default_color = wx.SystemSettings.GetColour(
            wx.SYS_COLOUR_GRAYTEXT
        )
        self._restart_warning.SetForegroundColour(
            self._restart_warning_default_color
        )
        self.addEntry("", self._restart_warning)
        self.addChoiceSetting(
            "view",
            "weekstart",
            _("Start of work week"),
            " ",
            [("monday", _("Monday")), ("sunday", _("Sunday"))],
        )
        self.addWorkingHoursSetting(_("Working hours"))
        self.addHintRow(
            _(
                "Note: Working hours are not used for hour suggestions when "
                "12-hour (AM/PM) time format is selected in Regional settings."
            )
        )

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
                for minutes in (
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "10",
                    "12",
                    "15",
                    "20",
                    "30",
                )
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
                for seconds in (
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "10",
                    "12",
                    "15",
                    "20",
                    "30",
                )
            ],
        )
        self.addIntegerSetting(
            "feature",
            "minidletime",
            _("Idle time notice"),
            help_text=_(
                "If there is no user input for this amount of time "
                "(in minutes), %(name)s will ask what to do about current "
                "efforts."
            )
            % meta.data.metaDict,
        )
        self.addBooleanSetting(
            "feature",
            "decimal_time",
            _("Use decimal times for effort"),
            _(
                "Display one hour, fifteen minutes as 1.25 instead of 1:15. "
                "This is useful when creating invoices. It applies to effort "
                "and duration in reports, lists and exports, but not for data "
                "entry."
            ),
        )
        self.addBooleanSetting(
            "view",
            "descriptionpopups",
            _("Hoverover popups"),
            _(
                "Show a popup with the description of an item when hovering over it"
            ),
        )
        self.addBooleanSetting(
            "feature",
            "in_place_editing",
            _("Edit cells in place"),
            _(
                "Edit a cell of a task, category or note list in the list "
                "itself: F2 on the cell just clicked, or Edit in place on "
                "the right-click menu"
            ),
        )
        self.addBooleanSetting(
            "feature",
            "in_place_slow_double_click",
            _("Edit in place with a slow double click"),
            _(
                "Also edit a cell by clicking it, then clicking it again "
                "after a pause of up to two seconds (with cells edited in "
                "place)"
            ),
        )

        # Store the working hours to detect changes
        self._originalValues = {}
        self._originalValues[("view", "efforthourstart")] = (
            self._workingHourStartChoice.GetSelection()
        )
        self._originalValues[("view", "efforthourend")] = (
            self._workingHourEndChoice.GetSelection()
        )
        self._originalValues[("view", "efforthourend_endofday")] = (
            self._workingHourEndOfDayCheck.IsChecked()
        )
        self._workingHourStartChoice.Bind(wx.EVT_CHOICE, self._onSettingChange)
        self._workingHourEndChoice.Bind(wx.EVT_CHOICE, self._onSettingChange)
        self._workingHourEndOfDayCheck.Bind(
            wx.EVT_CHECKBOX, self._onSettingChange
        )

        self.fit()

    def _onSettingChange(self, event):
        self._update_restart_warning()
        event.Skip()

    def _update_restart_warning(self):
        changed = (
            self._workingHourStartChoice.GetSelection()
            != self._originalValues[("view", "efforthourstart")]
            or self._workingHourEndChoice.GetSelection()
            != self._originalValues[("view", "efforthourend")]
            or self._workingHourEndOfDayCheck.IsChecked()
            != self._originalValues[("view", "efforthourend_endofday")]
        )
        if changed:
            self._restart_warning.SetLabel(
                self._restart_warning_base
                + " "
                + _("Change detected, restart required!")
            )
            self._restart_warning.SetForegroundColour(wx.Colour(180, 0, 0))
        else:
            self._restart_warning.SetLabel(self._restart_warning_base)
            self._restart_warning.SetForegroundColour(
                self._restart_warning_default_color
            )
        self._restart_warning.Refresh()

    def values(self):
        return super().values() + self._working_hours_values()

    def ok(self):
        super().ok()
        calendar.setfirstweekday(
            dict(monday=0, sunday=6)[settings.get("view", "weekstart")]
        )


class IconsPage(SettingsPage):
    pageName = "icons"
    pageTitle = _("Icons")
    pageIcon = "nuvola_apps_kview"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, growable_column=-1, *args, **kwargs)
        self.addBooleanSetting(
            "iconpicker",
            "theme_nuvola",
            _("Show Nuvola icons in picker"),
        )
        self.addBooleanSetting(
            "iconpicker",
            "theme_oxygen",
            _("Show Oxygen icons in picker"),
        )
        self.addBooleanSetting(
            "iconpicker",
            "theme_papirus",
            _("Show Papirus icons in picker"),
        )
        self.addBooleanSetting(
            "iconpicker",
            "theme_breeze",
            _("Show Breeze icons in picker"),
        )
        self.addBooleanSetting(
            "iconpicker",
            "theme_noto_emoji",
            _("Show Noto Emoji icons in picker"),
        )
        self.addBooleanSetting(
            "iconpicker",
            "theme_taskcoach",
            _("Show TaskCoach icons in picker"),
        )
        self.addBooleanSetting(
            "iconpicker",
            "search_include_theme",
            _("Include theme name in icon search"),
        )
        self.addBooleanSetting(
            "iconpicker",
            "search_include_context",
            _("Include context in icon search"),
        )
        self.addChoiceSetting(
            "icon",
            "iconsize",
            _("Icon size"),
            _(
                "Not yet implemented. Future: row height in tree/list views "
                "will scale with this setting."
            ),
            [("16", "16")],
        )
        self.fit()


class TaskDatesPage(SettingsPage):
    pageName = "task"
    pageTitle = _("Task dates")
    pageIcon = "nuvola_apps_date"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, growable_column=-1, *args, **kwargs)
        self.addBooleanSetting(
            "behavior",
            "markparentcompletedwhenallchildrencompleted",
            _("Mark parent task completed when all children are completed"),
            _(
                "This setting can be overridden for individual tasks "
                "in the task edit dialog."
            ),
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
        self.addHintRow(
            _(
                "Applies to a date typed in the task list, for tasks in "
                "Implicit mode; the other modes, and the task editor, follow "
                "each task's duration mode."
            )
        )

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
        self.addHintRow(
            _(
                """New tasks start with "Preset" dates and times filled in and checked. "Proposed" dates and times are filled in, but not checked.

"Start of day" is midnight and "End of day" is just before midnight. When using these, task viewers hide the time and show only the date.

"Start of working day" and "End of working day" use the working day as set in the Features tab of this preferences dialog."""
            )
            % meta.data.metaDict
        )


class TaskReminderPage(SettingsPage):
    pageName = "reminder"
    pageTitle = _("Reminders")
    pageIcon = "nuvola_apps_kalarm"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, growable_column=-1, *args, **kwargs)
        from taskcoachlib.sounds import choices as sound_choices, play

        choice_ctrls = self.addChoiceSetting(
            "feature",
            "reminder_sound",
            _("Reminder sound"),
            "",
            sound_choices(),
        )
        # Add a themed test button with icon next to the dropdown.
        # wx.Button.SetBitmap is suppressed by GTK3's gtk-button-images,
        # so use ThemedGenBitmapTextButton (same as IconPicker).
        from wx.lib.buttons import ThemedGenBitmapTextButton
        from taskcoachlib.gui.icons.icon_library import (
            icon_catalog,
            LIST_ICON_SIZE,
        )

        bmp = icon_catalog.get_bitmap("nuvola_apps_knotify", LIST_ICON_SIZE)
        parent_panel = choice_ctrls[0].GetParent()
        test_button = ThemedGenBitmapTextButton(
            parent_panel,
            wx.ID_ANY,
            bmp,
            _("Test"),
        )
        test_button.Bind(
            wx.EVT_BUTTON,
            lambda evt: play(
                choice_ctrls[0].GetClientData(choice_ctrls[0].GetSelection()),
            ),
        )
        parent_panel.GetSizer().Insert(
            1,
            test_button,
            0,
            wx.RIGHT,
            self._columnGap,
        )
        snooze_choices = [
            (str(choice[0]), choice[1]) for choice in date.snoozeChoices
        ]
        self.addChoiceSetting(
            "view",
            "defaultsnoozetime",
            _("Default snooze time to use after reminder"),
            "",
            snooze_choices,
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
    pageIcon = "nuvola_apps_clock"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, growable_column=1, *args, **kwargs)

        # Preset field configurations: (setting_key, display_name, help_text)
        self._preset_fields = [
            ("task_duration_presets", _("Task Duration")),
            ("effort_duration_presets", _("Effort Duration")),
        ]

        self.__currentFieldIndex = 0
        self.__presets = {}  # Cache for all preset lists

        # Load all presets
        for setting_key, unused_name in self._preset_fields:
            self.__presets[setting_key] = self.__loadPresets(setting_key)

        # Field selector row
        self.__fieldChoice = wx.Choice(self)
        for unused_key, display_name in self._preset_fields:
            self.__fieldChoice.Append(display_name)
        self.__fieldChoice.SetSelection(0)
        self.__fieldChoice.Bind(wx.EVT_CHOICE, self.__onFieldChanged)
        self.addEntry(_("Configure presets for"), self.__fieldChoice)

        # Add row: DurationEntry + Add button
        self.__addPanel = wx.Panel(self)
        self.__addSizer = wx.BoxSizer(wx.HORIZONTAL)

        # Create duration control - initially without seconds (Task Due Date is default)
        self.__durationEntry = self.__create_duration_ctrl(show_seconds=False)
        self.__addSizer.Add(
            self.__durationEntry, 0, wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, 5
        )

        self.__addBtn = wx.Button(self.__addPanel, wx.ID_ANY, _("Add"))
        self.__addBtn.SetBitmap(
            icon_catalog.get_bitmap("nuvola_actions_list-add", LIST_ICON_SIZE)
        )
        self.__addBtn.Bind(wx.EVT_BUTTON, self.__onAdd)
        self.__addSizer.Add(self.__addBtn, 0, wx.ALIGN_CENTRE_VERTICAL)

        self.__addPanel.SetSizer(self.__addSizer)
        self.addEntry(_("Add new preset"), self.__addPanel)

        # Preset list with 3 columns: short value, description, delete button
        # Using UltimateListCtrl to support embedded Delete buttons
        self.__listCtrl = ULC.UltimateListCtrl(
            self,
            agwStyle=wx.LC_REPORT
            | wx.LC_SINGLE_SEL
            | ULC.ULC_HAS_VARIABLE_ROW_HEIGHT,
        )
        self.__listCtrl.InsertColumn(
            0, _("Short"), width=80, format=wx.LIST_FORMAT_RIGHT
        )
        self.__listCtrl.InsertColumn(1, _("Description"), width=310)
        self.__listCtrl.InsertColumn(2, _("Delete"), width=110)
        self.__listCtrl.SetMinSize((500, 120))
        self.__listCtrl.SetMaxSize((500, -1))
        # Track delete buttons for cleanup
        self.__deleteButtons = []
        self.addEntry(
            _("Current presets"),
            self.__listCtrl,
            growable=True,
            flags=(None, wx.EXPAND | wx.ALL),
        )

        # Help text
        self.addHintRow(
            _(
                "These presets appear when setting duration in the task or effort editor."
            )
        )

        # Populate initial list
        self.__populateList()

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
        value = settings.get("feature", setting_key)
        if not value:
            return []
        presets = []
        for val_str in value.split(","):
            try:
                presets.append(int(val_str.strip()))
            except ValueError:
                pass
        return sorted(presets)

    def values(self):
        return super().values() + [
            (
                "feature",
                setting_key,
                ",".join(str(m) for m in sorted(self.__presets[setting_key])),
            )
            for setting_key, unused_name in self._preset_fields
        ]

    def __getCurrentSettingKey(self):
        return self._preset_fields[self.__currentFieldIndex][0]

    def __getCurrentPresets(self):
        return self.__presets[self.__getCurrentSettingKey()]

    def __create_duration_ctrl(self, show_seconds=False):
        """Create a duration control with or without seconds field."""
        if show_seconds:
            return widgets.MaskedDurationCtrl(
                self.__addPanel,
                days=0,
                hours=0,
                minutes=15,
                seconds=0,
                show_seconds=True,
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
        self.__durationEntry = self.__create_duration_ctrl(
            show_seconds=is_effort
        )
        self.__addSizer.Insert(
            0, self.__durationEntry, 0, wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, 10
        )
        self.__addPanel.Layout()

        self.__populateList()

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
            index = self.__listCtrl.InsertStringItem(
                self.__listCtrl.GetItemCount(), compact
            )
            self.__listCtrl.SetStringItem(index, 1, description)
            self.__listCtrl.SetItemData(index, value)

            # Create a real Delete button for this row (same style as Add button)
            # Use wx.BU_EXACTFIT to reduce padding and make button smaller
            delete_btn = wx.Button(
                self.__listCtrl,
                wx.ID_ANY,
                " " + _("Delete"),
                style=wx.BU_EXACTFIT,
            )
            delete_btn.SetBitmap(
                icon_catalog.get_bitmap(
                    "nuvola_status_dialog-error", LIST_ICON_SIZE
                )
            )
            delete_btn.presetValue = value  # Store preset value on button
            delete_btn.Bind(wx.EVT_BUTTON, self.__onDeleteButton)
            self.__deleteButtons.append(delete_btn)
            self.__listCtrl.SetItemWindow(index, 2, delete_btn, expand=True)

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
            description = _("%s, %s, %s and %s") % (
                parts[0],
                parts[1],
                parts[2],
                parts[3],
            )

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
        self.__populateList()
        self.edited()

    def __onDeleteButton(self, event):
        """Handle Delete button click - remove the preset."""
        btn = event.GetEventObject()
        value = btn.presetValue
        presets = self.__getCurrentPresets()

        if value in presets:
            presets.remove(value)
        self.__populateList()
        self.edited()


class Preferences(widgets.NotebookDialog):
    """OK and Cancel always enabled; Apply only while a page differs
    from what it showed (docs/PREFERENCES.md, OK, Apply and Cancel)."""

    # The event each kind of control sends when the user changes it
    _EDIT_EVENTS = (
        (wx.CheckListBox, wx.EVT_CHECKLISTBOX),
        (wx.CheckBox, wx.EVT_CHECKBOX),
        (wx.Choice, wx.EVT_CHOICE),
        (wx.TextCtrl, wx.EVT_TEXT),
        (wx.Button, wx.EVT_BUTTON),
        (wx.ColourPickerCtrl, wx.EVT_COLOURPICKER_CHANGED),
        (wx.DirPickerCtrl, wx.EVT_DIRPICKER_CHANGED),
        (widgets.SpinCtrl, wx.EVT_SPINCTRL),
        (widgets.FontPickerCtrl, wx.EVT_FONTPICKER_CHANGED),
        (widgets.IconPicker, wx.EVT_COMBOBOX),
    )

    all_page_names = [
        "window",
        "save",
        "language",
        "task",
        "reminder",
        "presets",
        "theme",
        "statuses",
        "features",
        "icons",
    ]
    pages = dict(
        window=WindowBehaviorPage,
        theme=ThemePage,
        task=TaskDatesPage,
        reminder=TaskReminderPage,
        presets=DurationPresetsPage,
        save=SavePage,
        language=LanguagePage,
        statuses=StatusesPage,
        features=FeaturesPage,
        icons=IconsPage,
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("buttonTypes", wx.OK | wx.CANCEL | wx.APPLY)
        super().__init__(icon_id="nuvola_actions_configure", *args, **kwargs)
        self.__update_pending = False
        self.__shown = self.__values()
        self.__apply_button = wxhelper.get_dialog_button(
            self._buttons, wx.ID_APPLY
        )
        self.__apply_button.Disable()
        self.__watch(self._interior)
        if operating_system.isMac():
            self.place()

    def __watch(self, window):
        """Follow every change: bound last, so it sees each event
        before the page's own handlers, which may not pass it on."""
        for kind, event_type in self._EDIT_EVENTS:
            if isinstance(window, kind):
                window.Bind(event_type, self.__on_edit)
                break
        for child in window.GetChildren():
            self.__watch(child)

    def __on_edit(self, event):
        event.Skip()
        self.update_buttons_soon()

    def update_buttons_soon(self):
        """Once the change's handlers ran: they may change other
        controls (a status's priorities, the working hours)."""
        if not self.__update_pending:
            self.__update_pending = True
            patterns.later.soon(self, self.__update_buttons)

    def __update_buttons(self):
        self.__update_pending = False
        self.__apply_button.Enable(self.__values() != self.__shown)

    def __values(self):
        return [
            [
                (section, option, str(value))
                for section, option, value in values
            ]
            for values in (page.values() for page in self._interior)
        ]

    def apply(self, event=None):
        super().apply(event)
        self.__shown = self.__values()
        self.__update_buttons()

    def addPages(self):
        # The first size; at most 80% of the screen, the pages scroll
        self._interior.SetMinSize((1250, 650))
        for page_name in self.all_page_names:
            page = self.createPage(page_name)
            self._interior.AddPage(page, page.pageTitle, page.pageIcon)

    def createPage(self, page_name):
        return self.pages[page_name](parent=self._interior)
