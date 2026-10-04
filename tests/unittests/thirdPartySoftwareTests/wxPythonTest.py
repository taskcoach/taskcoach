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

""" These are unittests of wxPython functionality. Of course, the goal is
not to test all wxPython functions, but rather to document platform
inconsistencies or surprising behaviour. """  # pylint: disable=W0105

import wx
import test
from taskcoachlib import operating_system


class TextCtrlTest(test.wxTestCase):
    def clear_events(self, text):
        events = []
        text_ctrl = wx.TextCtrl(self.frame)
        text_ctrl.ChangeValue(text)
        text_ctrl.Bind(wx.EVT_TEXT, events.append)
        text_ctrl.Clear()
        return events

    def test_clearing_text_emits_an_event(self):
        self.assertEqual(1, len(self.clear_events("text")))

    def test_clearing_an_empty_control_emits_no_event(self):
        # macOS always; GTK since wxWidgets 3.2
        if operating_system.isWindows():  # pragma: no cover
            self.skipTest("not checked on Windows")
        self.assertEqual([], self.clear_events(""))
