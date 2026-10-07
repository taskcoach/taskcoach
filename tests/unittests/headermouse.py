"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2026 Task Coach developers <developers@taskcoach.org>

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

# Mouse events sent to a view's column header, for the tests of moving
# columns (docs/LIST_MANAGEMENT.md, Moving Columns)

import wx
from taskcoachlib import widgets


class HeaderMouse:
    """Mouse events sent to a view's column header, at x."""

    def __init__(self, widget):
        self.widget = widget
        # A rebuild eats motion until the event loop, which tests do not
        # run, ends its settling (docs/LIST_MANAGEMENT.md)
        widgets.frame._input_filter.active = False  # pylint: disable=W0212

    def send(self, kind, x):
        header = self.widget.column_header()
        event = wx.MouseEvent(kind)
        event.SetPosition(wx.Point(x, 5))
        event.SetEventObject(header)
        header.GetEventHandler().ProcessEvent(event)

    def left(self, index):
        """Where the column at index starts."""
        return sum(self.widget.GetColumnWidth(each) for each in range(index))

    def middle(self, index):
        return self.left(index) + self.widget.GetColumnWidth(index) // 2

    def drag(self, index, x):
        """Drag the header of the column at index to x and drop it."""
        start = self.middle(index)
        self.send(wx.wxEVT_LEFT_DOWN, start)
        self.send(wx.wxEVT_MOTION, start + (10 if x > start else -10))
        self.send(wx.wxEVT_MOTION, x)
        self.send(wx.wxEVT_LEFT_UP, x)

    def click(self, index):
        self.send(wx.wxEVT_LEFT_DOWN, self.middle(index))
        self.send(wx.wxEVT_LEFT_UP, self.middle(index))
