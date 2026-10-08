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
from unittest import mock

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


class WindowsDateFieldTest(test.wxTestCase):
    """On Windows the date field is the native picker: it shows the
    date format of Preferences, as the lists do (docs/LOCALE.md)."""

    def format_shown(self):
        with mock.patch.object(wx, "Platform", "__WXMSW__"), mock.patch.object(
            maskedtimectrl, "getDateFormatFromSettings", return_value="YMD-"
        ), mock.patch.object(
            maskedtimectrl._NativeDateCtrl, "set_date_format"
        ) as set_date_format:
            maskedtimectrl.DateTimeComboCtrl(wx.Panel(self.frame))
        return [call.args for call in set_date_format.call_args_list]

    def test_an_editor_shows_the_format_of_preferences(self):
        self.assertEqual([("YMD-",)], self.format_shown())

    def test_the_preview_shows_the_format_it_is_given(self):
        with mock.patch.object(
            maskedtimectrl._NativeDateCtrl, "set_date_format"
        ) as set_date_format:
            maskedtimectrl._NativeDateCtrl(self.frame, date_format="DMY.")
        set_date_format.assert_called_once_with("DMY.")
