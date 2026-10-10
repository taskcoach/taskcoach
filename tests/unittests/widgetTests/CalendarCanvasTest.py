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

from unittest import mock

import test
import wx
from taskcoachlib.widgets import wxevents


class CalendarCanvasPaintTest(test.wxTestCase):
    """Laid out with less height than its scrollbar, the calendar draws
    nothing instead of failing."""

    def paint_errors(self, size):
        self.frame.Show()
        canvas = wxevents.CalendarCanvas(self.frame)
        canvas.SetSize(size)
        errors = []
        with mock.patch("sys.excepthook", lambda *info: errors.append(info)):
            canvas.Refresh()
            canvas.Update()
            test.settle()
        return errors

    def test_no_height_to_draw_in(self):
        self.assertEqual([], self.paint_errors((200, 3)))

    def test_room_to_draw_in(self):
        self.assertEqual([], self.paint_errors((400, 300)))


class CalendarCanvasChildrenTest(test.wxTestCase):
    def test_get_children_is_the_window_s_own(self):
        # Its events' children have another name (child_events): code
        # walking a window's children calls GetChildren() on every one
        canvas = wxevents.CalendarCanvas(self.frame)
        for child in canvas.GetChildren():
            self.assertIsInstance(child, wx.Window)
        self.assertRaises(NotImplementedError, canvas.child_events, None)
