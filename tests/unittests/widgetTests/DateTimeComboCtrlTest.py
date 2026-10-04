# -*- coding: UTF-8 -*-
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

import datetime

import test
import wx
from wx import siplib
from taskcoachlib.widgets import maskedtimectrl


class DateTimeComboCtrlTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.panel = wx.Panel(self.frame)
        self.ctrl = maskedtimectrl.DateTimeComboCtrl(self.panel)
        self.changes = []
        self.ctrl.Bind(
            maskedtimectrl.EVT_VALUE_CHANGED,
            lambda event: self.changes.append(self.ctrl.GetValue()),
        )

    def test_a_change_is_posted(self):
        self.ctrl.ActivateValue(datetime.datetime(2026, 9, 30, 9, 30))
        wx.Yield()
        self.assertEqual(1, len(self.changes))

    def test_what_it_posted_goes_with_its_widgets(self):
        # Not a window, it outlives them: a change still pending when
        # its editor closes must not reach the editor
        self.ctrl.ActivateValue(datetime.datetime(2026, 9, 30, 9, 30))
        self.panel.Destroy()
        wx.Yield()
        self.ctrl.NotifyValueChanged()
        wx.Yield()
        self.assertEqual([], self.changes)

    def test_it_goes_with_its_widgets(self):
        # Not a window, and the handlers bound on it hold it: nothing
        # else would free it, nor its editor's page
        self.panel.Destroy()
        test.settle()
        self.assertTrue(siplib.isdeleted(self.ctrl))
