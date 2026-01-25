"""
Task Coach - Your friendly task manager
Copyright (C) 2011-2012 Task Coach developers <developers@taskcoach.org>

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

from taskcoachlib.tools import wxhelper
import wx
import wx.lib.colourselect as csel
from wx.lib import sized_controls
from taskcoachlib.i18n import _
from taskcoachlib.thirdparty.wxScheduler import (
    wxSCHEDULER_DAILY,
    wxSCHEDULER_WEEKLY,
    wxSCHEDULER_MONTHLY,
    wxSCHEDULER_HORIZONTAL,
    wxSCHEDULER_VERTICAL,
)


class CalendarConfigDialog(sized_controls.SizedDialog):
    VIEWTYPES = [wxSCHEDULER_DAILY, wxSCHEDULER_WEEKLY, wxSCHEDULER_MONTHLY]
    VIEWORIENTATIONS = [wxSCHEDULER_HORIZONTAL, wxSCHEDULER_VERTICAL]
    VIEWFILTERS = [
        (False, False, False),
        (False, True, False),
        (True, False, False),
        (True, True, False),
        (True, True, True),
    ]

    def __init__(self, settings, settingsSection, *args, **kwargs):
        self._settings = settings
        self._settingsSection = settingsSection
        kwargs.setdefault(
            "style", wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        super().__init__(*args, **kwargs)
        pane = self.GetContentsPane()
        pane.SetSizerType("form")
        self.createInterior(pane)
        buttonSizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self.SetButtonSizer(buttonSizer)
        self.Fit()
        self.SetMinSize(self.GetSize())
        wxhelper.getButtonFromStdDialogButtonSizer(buttonSizer, wx.ID_OK).Bind(
            wx.EVT_BUTTON, self.ok
        )

    def createInterior(self, pane):
        self.createPeriodEntry(pane)
        self.createOrientationEntry(pane)
        self.createDisplayEntry(pane)
        self.createLineEntry(pane)
        self.createColorEntry(pane)

    def createPeriodEntry(self, pane):
        label = wx.StaticText(
            pane, label=_("Kind of period displayed and its count")
        )
        label.SetSizerProps(valign="center")
        panel = sized_controls.SizedPanel(pane)
        panel.SetSizerType("horizontal")
        self._spanCount = wx.SpinCtrl(
            panel, value="1", min=1
        )  # pylint: disable=W0201
        self._spanCount.SetSizerProps(valign="center")
        periods = (_("Day(s)"), _("Week(s)"), _("Month"))
        self._spanType = wx.Choice(
            panel, choices=periods
        )  # pylint: disable=W0201
        self._spanType.SetSizerProps(valign="center")
        self._spanCount.SetValue(
            self._settings.getint(self._settingsSection, "periodcount")
        )
        selection = self.VIEWTYPES.index(
            self._settings.getint(self._settingsSection, "viewtype")
        )
        self._spanType.SetSelection(selection)
        panel.SetSizerProps(valign="center")
        panel.Fit()
        self._spanType.Bind(wx.EVT_CHOICE, self.onChangeViewType)

    def createOrientationEntry(self, pane):
        label = wx.StaticText(pane, label=_("Calendar orientation"))
        label.SetSizerProps(valign="center")
        orientations = (_("Horizontal"), _("Vertical"))
        self._orientation = wx.Choice(
            pane, choices=orientations
        )  # pylint: disable=W0201
        self._orientation.SetSizerProps(valign="center")
        selection = self.VIEWORIENTATIONS.index(
            self._settings.getint(self._settingsSection, "vieworientation")
        )
        self._orientation.SetSelection(selection)

    def createDisplayEntry(self, pane):
        label = wx.StaticText(pane, label=_("Which tasks to display"))
        label.SetSizerProps(valign="center")
        choices = (
            _("Tasks with a planned start date and a due date"),
            _("Tasks with a planned start date"),
            _("Tasks with a due date"),
            _("All tasks, except unplanned tasks"),
            _("All tasks"),
        )
        self._display = wx.Choice(
            pane, choices=choices
        )  # pylint: disable=W0201
        self._display.SetSizerProps(valign="center")
        selection = self.VIEWFILTERS.index(
            (
                self._settings.getboolean(
                    self._settingsSection, "shownostart"
                ),
                self._settings.getboolean(self._settingsSection, "shownodue"),
                self._settings.getboolean(
                    self._settingsSection, "showunplanned"
                ),
            )
        )
        self._display.SetSelection(selection)

    def createLineEntry(self, pane):
        label = wx.StaticText(
            pane, label=_("Draw a line showing the current time")
        )
        label.SetSizerProps(valign="center")
        self._shownow = wx.CheckBox(pane)  # pylint: disable=W0201
        self._shownow.SetSizerProps(valign="center")
        self._shownow.SetValue(
            self._settings.getboolean(self._settingsSection, "shownow")
        )

    def createColorEntry(self, pane):
        label = wx.StaticText(
            pane, label=_("Color used to highlight the current day")
        )
        label.SetSizerProps(valign="center")
        hcolor = self._settings.get(self._settingsSection, "highlightcolor")
        if not hcolor:
            # The highlight color is too dark
            color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
            color = wx.Colour(
                int((color.Red() + 255) / 2),
                int((color.Green() + 255) / 2),
                int((color.Blue() + 255) / 2),
            )
        else:
            color = wx.Colour(
                *tuple(map(int, hcolor.split(",")))
            )  # pylint: disable=W0141
        self._highlight = csel.ColourSelect(
            pane, size=(44, 24)
        )  # pylint: disable=W0201
        label.SetSizerProps(valign="center")
        self._highlight.SetColour(color)

    def onChangeViewType(self, event):  # pylint: disable=W0613
        if (
            self.VIEWTYPES[self._spanType.GetSelection()]
            == wxSCHEDULER_MONTHLY
        ):
            self._spanCount.SetValue(1)
            self._spanCount.Enable(False)
        else:
            self._spanCount.Enable(True)

    def ok(self, event=None):  # pylint: disable=W0613
        settings, section = self._settings, self._settingsSection
        settings.set(section, "periodcount", str(self._spanCount.GetValue()))
        settings.set(
            section,
            "viewtype",
            str(self.VIEWTYPES[self._spanType.GetSelection()]),
        )
        settings.set(
            section,
            "vieworientation",
            str(self.VIEWORIENTATIONS[self._orientation.GetSelection()]),
        )
        shownostart, shownodue, showunplanned = self.VIEWFILTERS[
            self._display.GetSelection()
        ]
        settings.set(section, "shownostart", str(shownostart))
        settings.set(section, "shownodue", str(shownodue))
        settings.set(section, "showunplanned", str(showunplanned))
        settings.set(section, "shownow", str(self._shownow.GetValue()))
        color = self._highlight.GetColour()
        settings.set(
            section,
            "highlightcolor",
            "%d,%d,%d" % (color.Red(), color.Green(), color.Blue()),
        )
        self.EndModal(wx.ID_OK)
