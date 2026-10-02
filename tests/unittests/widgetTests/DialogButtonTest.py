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

import test
import wx
from taskcoachlib.tools import wxhelper


class DialogButtonTest(test.wxTestCase):
    """A dialog finds its buttons by their ids (P113)."""

    def setUp(self):
        super().setUp()
        self.dialog = wx.Dialog(self.frame)  # Destroyed with the frame's

    def test_found_by_its_id(self):
        sizer = self.dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        button = wxhelper.get_dialog_button(sizer, wx.ID_CANCEL)
        self.assertEqual(wx.ID_CANCEL, button.GetId())

    def test_found_when_given_as_a_plain_window(self):
        # wxPython can give a button through the stale wrapper of a
        # destroyed window at the same address, typed wx.Window
        sizer = wx.BoxSizer()
        window = wx.Window(self.dialog, wx.ID_OK)
        sizer.Add(window)
        self.assertIs(window, wxhelper.get_dialog_button(sizer, wx.ID_OK))

    def test_none_without_it(self):
        sizer = self.dialog.CreateStdDialogButtonSizer(wx.OK)
        self.assertIsNone(wxhelper.get_dialog_button(sizer, wx.ID_APPLY))
