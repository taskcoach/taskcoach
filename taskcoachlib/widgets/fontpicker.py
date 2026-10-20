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
from taskcoachlib.widgets import skipfocus


class FontPickerCtrl(buttons.GenButton):
    """A button that displays the selected font and opens a font
    dialog on click. Uses GenButton to avoid native GTK hover/press
    rendering artifacts.

    Two modes:
    - fixed_width=None (default): button grows to fit the font
      description text.
    - fixed_width=N: button constrained to N pixels, label
      ellipsized to fit.
    """

    PADDING = 8

    def __init__(self, *args, **kwargs):
        self.__font = kwargs.pop("font")
        self.__colour = kwargs.pop("colour")
        self.__bg_colour = kwargs.pop("bg_colour", None)
        self.__read_only = kwargs.pop("read_only", False)
        self.__fixed_width = kwargs.pop("fixed_width", None)
        super().__init__(*args, **kwargs)
        self.SetBezelWidth(0)
        self.SetUseFocusIndicator(False)
        if self.__read_only:
            skipfocus.skip_focus(self)
        self.__update_button()
        self.Bind(wx.EVT_BUTTON, self.on_click)

    def AcceptsFocusFromKeyboard(self):
        """Read-only pickers are display, never tab stops."""
        if self.__read_only:
            return False
        return super().AcceptsFocusFromKeyboard()

    def DoGetBestSize(self):
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        tw, th = dc.GetTextExtent(self.GetLabel())
        height = th + 10
        if self.__fixed_width:
            return wx.Size(self.__fixed_width, height)
        return wx.Size(self.PADDING * 2 + tw, height)

    def DrawLabel(self, dc, width, height, dx=0, dy=0):
        """Override to draw text left-aligned with ellipsis if needed."""
        if self.hasFocus:
            focus_rect = wx.Rect(2, 2, width - 4, height - 4)
            wx.RendererNative.Get().DrawFocusRect(self, dc, focus_rect)
        dc.SetFont(self.GetFont())
        label = self.GetLabel()
        available_width = width - (self.PADDING * 2)
        if available_width > 0:
            label = wx.Control.Ellipsize(
                label, dc, wx.ELLIPSIZE_END, available_width
            )
        dc.DrawText(
            label, self.PADDING, (height - dc.GetTextExtent(label)[1]) // 2
        )

    def GetSelectedFont(self):
        return self.__font

    def SetSelectedFont(self, font):
        self.__font = font
        self.__update_button()

    def GetSelectedColour(self):
        return self.__colour

    def SetSelectedColour(self, colour):
        self.__colour = colour
        self.__update_button()

    def GetSelectedBgColour(self):
        return self.__bg_colour

    def SetSelectedBgColour(self, colour):
        self.__bg_colour = colour
        self.__update_button()

    def on_click(self, event):
        event.Skip(False)
        if self.__read_only:
            return
        dialog = wx.FontDialog(self, self.__new_font_data())
        if wx.ID_OK == dialog.ShowModal():
            self.__read_font_data(dialog.GetFontData())
            self.__update_button()
            self.__send_picker_event()

    def __new_font_data(self):
        font_data = wx.FontData()
        font_data.SetInitialFont(self.__font)
        font_data.SetColour(self.__colour)
        return font_data

    def __read_font_data(self, font_data):
        self.__font = font_data.GetChosenFont()
        self.__colour = font_data.GetColour()

    def __update_button(self):
        self.SetLabel(self.__font.GetNativeFontInfoUserDesc())
        self.SetFont(self.__font)
        self.SetForegroundColour(self.__colour)
        if self.__bg_colour:
            self.SetBackgroundColour(self.__bg_colour)
        else:
            self.SetBackgroundColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
            )
        self.InvalidateBestSize()
        if not self.__fixed_width:
            self.SetInitialSize()
            parent = self.GetParent()
            while parent and not isinstance(parent, wx.TopLevelWindow):
                parent.Layout()
                parent = parent.GetParent()
        self.Refresh(eraseBackground=True)
        self.Update()

    def GetBackgroundBrush(self, dc):
        """Override to ensure correct background color is used for painting."""
        bg_color = (
            self.__bg_colour
            if self.__bg_colour
            else wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        )
        return wx.Brush(bg_color, wx.BRUSHSTYLE_SOLID)

    def __send_picker_event(self):
        event = wx.FontPickerEvent(self, self.GetId(), self.__font)
        self.GetEventHandler().ProcessEvent(event)
