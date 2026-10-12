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
from taskcoachlib import patterns, widgets


class StubWindow(object):
    """Stands in for the window holding a focus event."""

    def __init__(self):
        self.navigations = []

    def Navigate(self, forward):
        self.navigations.append(forward)
        return True


class StubNavigationEvent(object):
    def __init__(self, event_object, direction):
        self.__event_object = event_object
        self.__direction = direction

    def GetEventObject(self):
        return self.__event_object

    def GetDirection(self):
        return self.__direction


class StubFocusEvent(object):
    def __init__(self, event_object):
        self.__event_object = event_object

    def GetEventObject(self):
        return self.__event_object


class ColourPickerReadOnlyTest(test.wxTestCase):
    """A read-only picker skips itself from the focus order.

    The handlers serve the outer control and its inner picker
    button, so they act on the window holding the event; acting
    on the outer control restarts the traversal inside it
    (issue #487).
    """

    def setUp(self):
        super().setUp()
        self.picker = widgets.ColourPickerCtrl(
            self.frame, colour=wx.BLACK, readOnly=True
        )
        self.navigations = []
        self.picker.Navigate = self.navigations.append

    def test_nav_key_navigates_from_event_object(self):
        window = StubWindow()
        self.picker._onNavKey(StubNavigationEvent(window, True))
        self.assertEqual([True], window.navigations)
        self.assertEqual([], self.navigations)

    def test_nav_key_preserves_backward_direction(self):
        window = StubWindow()
        self.picker._onNavKey(StubNavigationEvent(window, False))
        self.assertEqual([False], window.navigations)
        self.assertEqual([], self.navigations)

    def test_reject_focus_defers_navigate_from_event_object(self):
        window = StubWindow()
        calls = []
        original_soon = patterns.later.soon
        patterns.later.soon = lambda *args: calls.append(args)
        try:
            self.picker._onRejectFocus(StubFocusEvent(window))
        finally:
            patterns.later.soon = original_soon
        forward = not wx.GetKeyState(wx.WXK_SHIFT)
        self.assertEqual([(window, window.Navigate, forward)], calls)

    def test_read_only_picker_is_no_tab_stop(self):
        self.assertFalse(self.picker.AcceptsFocusFromKeyboard())

    def test_editable_picker_keeps_tab_stop(self):
        picker = widgets.ColourPickerCtrl(self.frame, colour=wx.BLACK)
        self.assertTrue(picker.AcceptsFocusFromKeyboard())
