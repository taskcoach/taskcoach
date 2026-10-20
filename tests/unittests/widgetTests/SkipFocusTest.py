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


class _ReadOnlyDisplayTests:
    """A read-only display between two fields."""

    def setUp(self):
        super().setUp()
        self.panel = wx.Panel(self.frame)
        self.before = wx.TextCtrl(self.panel)
        self.display = self.create_display(self.panel)
        self.after = wx.TextCtrl(self.panel)
        sizer = wx.BoxSizer(wx.VERTICAL)
        for window in (self.before, self.display, self.after):
            sizer.Add(window)
        self.panel.SetSizer(sizer)
        self.frame.Show()
        self.panel.Layout()
        test.settle()

    def tearDown(self):
        self.frame.Hide()
        super().tearDown()

    def create_display(self, parent):
        raise NotImplementedError

    def test_takes_no_tab_focus(self):
        self.assertFalse(self.display.AcceptsFocusFromKeyboard())

    def test_focus_moved_on_meanwhile_stays(self):
        """Focus reaching the display moves on later; moved by the user
        before then, it stays where the user put it."""
        event = wx.FocusEvent(wx.wxEVT_SET_FOCUS, self.display.GetId())
        event.SetEventObject(self.display)
        self.display.GetEventHandler().ProcessEvent(event)
        self.before.SetFocus()
        test.settle()
        self.assertIs(self.before, wx.Window.FindFocus())


class ReadOnlyColourPickerTest(_ReadOnlyDisplayTests, test.wxTestCase):
    def create_display(self, parent):
        return widgets.ColourPickerCtrl(parent, read_only=True)

    def test_tab_from_its_button_ends(self):
        """Windows and macOS: Tab from the inner button, or the button
        handing on focus it got, reaches the picker's handler; moving
        on from there must not come back to it (#487)."""
        button = self.display.GetPickerCtrl()
        with test.NavigateAsWindowsAndMac(focus=button) as navigate:
            button.Navigate(True)
        self.assertEqual(1, navigate.deepest)


class ReadOnlyFontPickerTest(_ReadOnlyDisplayTests, test.wxTestCase):
    def create_display(self, parent):
        return widgets.FontPickerCtrl(
            parent, font=wx.NORMAL_FONT, colour=wx.BLACK, read_only=True
        )
