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

from taskcoachlib import operating_system, patterns
from taskcoachlib.config import settings
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
import wx
import textwrap


class ToolTipMixin(object):
    """Subclass this and override OnBeforeShowToolTip to provide
    dynamic tooltip over a control."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__tip_later = patterns.later.debounced(
            self, 200, self.__show_pending_tip
        )

        self.__tip = None
        self.__position = (0, 0)
        self.__pending_xy = (0, 0)
        self.__frozen = True

        self.GetMainWindow().Bind(wx.EVT_MOTION, self.__on_motion)
        self.GetMainWindow().Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)

    def PopupMenu(self, menu):
        self.__frozen = False
        # Hide any visible tooltip first to avoid Wayland popup parent conflict
        # (GTK bug #1785: popup menus fail when tooltip is visible)
        self.HideTip()
        super().PopupMenu(menu)
        self.__frozen = True

    def ShowTip(self, x, y):
        # Ensure we're not too big (in the Y direction anyway) for the
        # desktop display area. This doesn't work on Linux because
        # ClientDisplayRect() returns the whole display size, not
        # taking the taskbar into account...

        if self.__frozen:
            the_display = wx.Display(wx.Display.GetFromPoint(wx.Point(x, y)))
            display_x, display_y, display_width, display_height = (
                the_display.GetClientArea()
            )
            tip_width, tip_height = self.__tip.GetSize()

            if tip_height > display_height:
                # Too big. Take as much space as possible.
                y = 5
                tip_height = display_height - 10
            elif y + tip_height > display_y + display_height:
                # Adjust y so that the whole tip is visible.
                y = display_y + display_height - tip_height - 5

            if tip_width > display_width:
                x = 5
            elif x + tip_width > display_x + display_width:
                x = display_x + display_width - tip_width - 5

            self.__tip.Show(x, y, tip_width, tip_height)

    def DoShowTip(self, x, y, tip):
        self.__tip = tip
        self.ShowTip(x, y)

    def HideTip(self):
        if self.__tip:
            self.__tip.Hide()

    def cancel_tip(self):
        """Hide the tip and drop a pending one: the mouse moved on, or
        a window (an editor) opened over the control."""
        self.__tip_later.cancel()
        if self.__tip is not None:
            self.HideTip()
            self.__tip = None

    def OnBeforeShowToolTip(self, x, y):
        """Should return a wx.Frame instance that will be displayed as
        the tooltip, or None."""
        raise NotImplementedError  # pragma: no cover

    def __on_motion(self, event):
        x, y = event.GetPosition()
        self.cancel_tip()
        if settings.view.descriptionpopups:
            self.__position = (x + 20, y + 10)
            self.__pending_xy = (x, y)
            self.__tip_later()

        event.Skip()

    def __on_tip_motion(self, event):  # pylint: disable=W0613
        self.HideTip()

    def __on_leave(self, event):
        self.cancel_tip()
        event.Skip()

    def __show_pending_tip(self):
        x, y = self.__pending_xy
        new_tip = self.OnBeforeShowToolTip(x, y)
        if new_tip is not None:
            self.__tip = new_tip
            self.__tip.Bind(wx.EVT_MOTION, self.__on_tip_motion)
            self.ShowTip(
                *self.GetMainWindow().ClientToScreen(*self.__position)
            )


if operating_system.isWindows():

    class ToolTipBase(wx.MiniFrame):
        def __init__(self, parent):
            style = (
                wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.NO_BORDER
            )
            super().__init__(parent, wx.ID_ANY, "Tooltip", style=style)

        def Show(self, x, y, w, h):  # pylint: disable=W0221
            self.SetSize(x, y, w, h)
            super().Show()

elif operating_system.isMac():

    class ToolTipBase(wx.Frame):
        def __init__(self, parent):  # pylint: disable=E1003
            style = (
                wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.NO_BORDER
            )
            super().__init__(parent, wx.ID_ANY, "ToolTip", style=style)

            # There are some subtleties on Mac regarding multi-monitor
            # displays...

            self.__maxWidth, self.__maxHeight = 0, 0
            for index in range(wx.Display.GetCount()):
                x, y, width, height = wx.Display(index).GetGeometry()
                self.__maxWidth = max(self.__maxWidth, x + width)
                self.__maxHeight = max(self.__maxHeight, y + height)

            self.Move(self.__maxWidth, self.__maxHeight)
            super().Show()

        def Show(self, x, y, width, height):  # pylint: disable=W0221
            self.SetSize(x, y, width, height)

        def Hide(self):  # pylint: disable=W0221
            self.Move(self.__maxWidth, self.__maxHeight)

else:

    class ToolTipBase(wx.PopupWindow):
        def Show(self, x, y, width, height):  # pylint: disable=E1003,W0221
            self.SetSize(x, y, width, height)
            super().Show()


class SimpleToolTip(ToolTipBase):
    def __init__(self, parent):
        super().__init__(parent)
        self.data = []
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def SetData(self, data):
        self.data = self._wrapLongLines(data)
        self.SetSize(self._calculateSize())
        self.Refresh()  # Needed on Mac OS X

    def _wrapLongLines(self, data):
        wrapped_data = []
        wrapper = textwrap.TextWrapper(width=78)
        for icon_id, lines in data:
            wrapped_lines = []
            for line in lines:
                wrapped_lines.extend(wrapper.fill(line).split("\n"))
            wrapped_data.append((icon_id, wrapped_lines))
        return wrapped_data

    def _calculateSize(self):
        dc = wx.ClientDC(self)
        self._setFontBrushAndPen(dc)
        width, height = 0, 0
        for section_index in range(len(self.data)):
            section_width, section_height = self._calculateSectionSize(
                dc, section_index
            )
            width = max(width, section_width)
            height += section_height
        return wx.Size(width + 6, height + 6)

    def _calculateSectionSize(self, dc, section_index):
        icon_id, lines = self.data[section_index]
        section_width, section_height = 0, 0
        for line in lines:
            line_width, line_height = self._calculateLineSize(dc, line)
            section_height += line_height + 1
            section_width = max(section_width, line_width)
        if 0 < section_index < len(self.data) - 1:
            section_height += 3  # Horizontal space between sections
        if icon_id:
            section_width += 24  # Reserve width for icon(s)
        return section_width, section_height

    def _calculateLineSize(self, dc, line):
        return dc.GetTextExtent(line)

    def OnPaint(self, event):  # pylint: disable=W0613
        dc = wx.PaintDC(self)
        self._setFontBrushAndPen(dc)
        self._drawBorder(dc)
        self._drawSections(dc)

    def _setFontBrushAndPen(self, dc):
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        text_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOTEXT)
        background_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK)
        dc.SetFont(font)
        dc.SetTextForeground(text_colour)
        dc.SetBrush(wx.Brush(background_colour))
        dc.SetPen(wx.Pen(text_colour))

    def _drawBorder(self, dc):
        width, height = self.GetClientSize()
        dc.DrawRectangle(0, 0, width, height)

    def _drawSections(self, dc):
        y = 3
        for section_index in range(len(self.data)):
            y = self._drawSection(dc, y, section_index)

    def _drawSection(self, dc, y, section_index):
        icon_id, lines = self.data[section_index]
        if not lines:
            return y
        x = 3
        if section_index != 0:
            y = self._drawSectionSeparator(dc, x, y)
        if icon_id:
            x = self._drawIcon(dc, icon_id, x, y)
        top_of_section = y
        bottom_of_section = self._drawTextLines(dc, lines, x, y)
        if icon_id:
            self._drawIconSeparator(
                dc, x - 2, top_of_section, bottom_of_section
            )
        return bottom_of_section

    def _drawSectionSeparator(self, dc, x, y):
        y += 1
        width = self.GetClientSize()[0]
        dc.DrawLine(x, y, width - x, y)
        return y + 2

    def _drawIcon(self, dc, icon_id, x, y):
        bitmap = icon_catalog.get_bitmap(icon_id, LIST_ICON_SIZE)
        dc.DrawBitmap(bitmap, x, y, True)
        return 23  # New x

    def _drawTextLines(self, dc, text_lines, x, y):
        for text_line in text_lines:
            y = self._drawTextLine(dc, text_line, x, y)
        return y

    def _drawTextLine(self, dc, text_line, x, y):
        try:
            dc.DrawText(text_line, x, y)
        except Exception:
            raise RuntimeError("Could not draw text %s" % repr(text_line))
        text_height = dc.GetTextExtent(text_line)[1]
        return y + text_height + 1

    def _drawIconSeparator(self, dc, x, top, bottom):
        """Draw a vertical line between the icon and the text."""
        dc.DrawLine(x, top, x, bottom)
