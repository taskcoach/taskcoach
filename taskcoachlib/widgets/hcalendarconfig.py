"""
Task Coach - Your friendly task manager
Copyright (C) 2014 Task Coach developers <developers@taskcoach.org>

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
from taskcoachlib.config import settings


class HierarchicalCalendarConfigDialog(sized_controls.SizedDialog):
    def __init__(self, settings_section, *args, **kwargs):
        self._options = settings.section(settings_section)
        kwargs.setdefault("style", wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        super().__init__(*args, **kwargs)
        pane = self.GetContentsPane()
        pane.SetSizerType("form")
        self.createInterior(pane)
        buttonSizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self.SetButtonSizer(buttonSizer)
        self.Fit()
        self.SetMinSize(self.GetSize())
        wxhelper.get_dialog_button(buttonSizer, wx.ID_OK).Bind(
            wx.EVT_BUTTON, self.ok
        )

    def createInterior(self, pane):
        self.createHeaderEntry(pane)
        self.createPeriodEntry(pane)
        self.createLineEntry(pane)
        self.createColorEntry(pane)

    def createHeaderEntry(self, pane):
        label = wx.StaticText(pane, label=_("Headers"))
        label.SetSizerProps(valign="center")
        hdr = self._options.headerformat
        panel = sized_controls.SizedPanel(pane)
        panel.SetSizerType("vertical")
        self._weekNumber = wx.CheckBox(panel, label=_("Week number"))
        self._weekNumber.SetValue(hdr & 1)
        self._weekNumber.SetSizerProps(valign="center")
        self._dates = wx.CheckBox(panel, label=_("Date"))
        self._dates.SetValue(hdr & 2)
        self._dates.SetSizerProps(valign="center")
        panel.SetSizerProps(valign="center")
        panel.Fit()

    def createPeriodEntry(self, pane):
        label = wx.StaticText(pane, label=_("Calendar span"))
        label.SetSizerProps(valign="center")
        periods = (_("Week"), _("Work week"), _("Month"))
        self._spanType = wx.Choice(
            pane, choices=periods
        )  # pylint: disable=W0201
        self._spanType.SetSizerProps(valign="center")
        self._spanType.SetSelection(self._options.calendarformat)

    def createLineEntry(self, pane):
        label = wx.StaticText(
            pane, label=_("Draw a line showing the current time")
        )
        label.SetSizerProps(valign="center")
        self._shownow = wx.CheckBox(pane)  # pylint: disable=W0201
        self._shownow.SetSizerProps(valign="center")
        self._shownow.SetValue(self._options.drawnow)

    def createColorEntry(self, pane):
        label = wx.StaticText(
            pane, label=_("Color used to highlight the current day")
        )
        label.SetSizerProps(valign="center")
        hcolor = self._options.todaycolor
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

    def ok(self, event=None):  # pylint: disable=W0613
        options = self._options
        options.calendarformat = self._spanType.GetSelection()
        options.drawnow = self._shownow.GetValue()
        color = self._highlight.GetColour()
        options.todaycolor = "%d,%d,%d" % (
            color.Red(),
            color.Green(),
            color.Blue(),
        )
        hdr = 0
        if self._weekNumber.GetValue():
            hdr |= 1
        if self._dates.GetValue():
            hdr |= 2
        options.headerformat = hdr
        self.EndModal(wx.ID_OK)
