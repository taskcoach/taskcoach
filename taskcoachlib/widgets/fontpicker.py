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

import wx
import wx.lib.buttons as buttons


class FontPickerCtrl(buttons.GenButton):
    """A button that displays the selected font and opens a font dialog on click.
    Uses GenButton to avoid native GTK hover/press rendering artifacts."""

    def __init__(self, *args, **kwargs):
        self.__font = kwargs.pop("font")
        self.__colour = kwargs.pop("colour")
        super().__init__(*args, **kwargs)
        self.SetBezelWidth(0)
        self.SetUseFocusIndicator(False)
        self.__updateButton()
        self.Bind(wx.EVT_BUTTON, self.onClick)

    def GetSelectedFont(self):
        return self.__font

    def SetSelectedFont(self, font):
        self.__font = font
        self.__updateButton()

    def GetSelectedColour(self):
        return self.__colour

    def SetSelectedColour(self, colour):
        self.__colour = colour
        self.__updateButton()

    def onClick(self, event):
        event.Skip(False)
        dialog = wx.FontDialog(self, self.__newFontData())
        if wx.ID_OK == dialog.ShowModal():
            self.__readFontData(dialog.GetFontData())
            self.__updateButton()
            self.__sendPickerEvent()

    def __newFontData(self):
        fontData = wx.FontData()
        fontData.SetInitialFont(self.__font)
        fontData.SetColour(self.__colour)
        return fontData

    def __readFontData(self, fontData):
        self.__font = fontData.GetChosenFont()
        self.__colour = fontData.GetColour()

    def __updateButton(self):
        self.SetLabel(self.__font.GetNativeFontInfoUserDesc())
        self.SetFont(self.__font)
        self.SetForegroundColour(self.__colour)

    def __sendPickerEvent(self):
        event = wx.FontPickerEvent(self, self.GetId(), self.__font)
        self.GetEventHandler().ProcessEvent(event)
