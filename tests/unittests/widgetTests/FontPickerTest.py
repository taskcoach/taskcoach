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

import test
from taskcoachlib import widgets


class FontPickerReadOnlyTest(test.wxTestCase):
    """A read-only picker is no tab stop; how the focus passes it by
    is tested in SkipFocusTest (issue #487)."""

    def setUp(self):
        super().setUp()
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self.picker = widgets.FontPickerCtrl(
            self.frame,
            font=font,
            colour=wx.BLACK,
            read_only=True,
        )

    def test_read_only_picker_is_no_tab_stop(self):
        self.assertFalse(self.picker.AcceptsFocusFromKeyboard())

    def test_editable_picker_keeps_tab_stop(self):
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        picker = widgets.FontPickerCtrl(self.frame, font=font, colour=wx.BLACK)
        self.assertTrue(picker.AcceptsFocusFromKeyboard())
