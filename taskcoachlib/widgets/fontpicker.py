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
    Uses GenButton to avoid native GTK hover/press rendering artifacts.

    Two modes:
    - fixedWidth=None (default): button grows to fit the font description text.
    - fixedWidth=N: button constrained to N pixels, label ellipsized to fit."""

    PADDING = 8

    def __init__(self, *args, **kwargs):
        self.__font = kwargs.pop("font")
        self.__colour = kwargs.pop("colour")
        self.__bgColour = kwargs.pop("bgColour", None)
        self.__readOnly = kwargs.pop("readOnly", False)
        self.__fixedWidth = kwargs.pop("fixedWidth", None)
        super().__init__(*args, **kwargs)
        self.SetBezelWidth(0)
        self.SetUseFocusIndicator(False)
        if self.__readOnly:
            self.Bind(wx.EVT_NAVIGATION_KEY, self.__onNavKey)
            self.Bind(wx.EVT_SET_FOCUS, self.__onRejectFocus)
        self.__updateButton()
        self.Bind(wx.EVT_BUTTON, self.onClick)

    def __onNavKey(self, event):
        """Skip this control during tab traversal, preserving direction."""
        self.Navigate(event.GetDirection())

    def __onRejectFocus(self, event):
        """Reject focus by navigating away, preserving Shift+Tab direction."""
        forward = not wx.GetKeyState(wx.WXK_SHIFT)
        wx.CallAfter(self.Navigate, forward)

    def DoGetBestSize(self):
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        tw, th = dc.GetTextExtent(self.GetLabel())
        height = th + 10
        if self.__fixedWidth:
            return wx.Size(self.__fixedWidth, height)
        return wx.Size(self.PADDING * 2 + tw, height)

    def DrawLabel(self, dc, width, height, dx=0, dy=0):
        """Override to draw text left-aligned with ellipsis if needed."""
        if self.hasFocus:
            focusRect = wx.Rect(2, 2, width - 4, height - 4)
            wx.RendererNative.Get().DrawFocusRect(self, dc, focusRect)
        dc.SetFont(self.GetFont())
        label = self.GetLabel()
        availableWidth = width - (self.PADDING * 2)
        if availableWidth > 0:
            label = wx.Control.Ellipsize(label, dc, wx.ELLIPSIZE_END, availableWidth)
        dc.DrawText(label, self.PADDING, (height - dc.GetTextExtent(label)[1]) // 2)

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

    def GetSelectedBgColour(self):
        return self.__bgColour

    def SetSelectedBgColour(self, colour):
        self.__bgColour = colour
        self.__updateButton()

    def onClick(self, event):
        event.Skip(False)
        if self.__readOnly:
            return
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
        if self.__bgColour:
            self.SetBackgroundColour(self.__bgColour)
        else:
            self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
        self.InvalidateBestSize()
        if not self.__fixedWidth:
            self.SetInitialSize()
            parent = self.GetParent()
            while parent and not isinstance(parent, wx.TopLevelWindow):
                parent.Layout()
                parent = parent.GetParent()
        self.Refresh(eraseBackground=True)
        self.Update()

    def GetBackgroundBrush(self, dc):
        """Override to ensure correct background color is used for painting."""
        bgColor = self.__bgColour if self.__bgColour else wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        return wx.Brush(bgColor, wx.BRUSHSTYLE_SOLID)

    def __sendPickerEvent(self):
        event = wx.FontPickerEvent(self, self.GetId(), self.__font)
        self.GetEventHandler().ProcessEvent(event)
