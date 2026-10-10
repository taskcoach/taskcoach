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
from taskcoachlib import widgets
from taskcoachlib.gui import focus
from taskcoachlib.widgets import wxevents


class FocusTest(test.wxTestCase):
    """In a window, only the control with the focus shows a text
    selection, on every platform (docs/FOCUS_MANAGEMENT.md): a subject
    box, a number field, the search box and a spin box."""

    def setUp(self):
        super().setUp()
        self.subject = widgets.single_line_text_ctrl(self.frame, "Errands")
        self.number = wx.TextCtrl(self.frame, value="12")
        self.search = wx.SearchCtrl(self.frame, value="find")
        self.spin = widgets.SpinCtrl(self.frame, value=5)

    def select_everything(self):
        self.subject._textCtrl.SelectAll()
        for field in self.number, self.search, self.spin._textCtrl:
            field.SetSelection(-1, -1)

    def selected(self):
        box = self.subject._textCtrl
        return [
            box.GetSelectionStart() != box.GetSelectionEnd(),
            self.number.GetSelection()[0] != self.number.GetSelection()[1],
            self.search.GetSelection()[0] != self.search.GetSelection()[1],
            self.spin._textCtrl.GetSelection()[0]
            != self.spin._textCtrl.GetSelection()[1],
        ]

    def test_the_focused_control_keeps_its_selection_alone(self):
        self.select_everything()
        focus.drop_selections(self.frame, keep=self.number)
        self.assertEqual([False, True, False, False], self.selected())

    def test_the_subject_box_drops_its_selection(self):
        self.select_everything()
        focus.drop_selections(self.frame, keep=self.spin._textCtrl)
        self.assertEqual([False, False, False, True], self.selected())

    def test_the_caret_stays_where_it_was(self):
        self.number.SetSelection(0, 2)
        caret = self.number.GetInsertionPoint()
        focus.drop_selections(self.frame, keep=self.search)
        self.assertEqual((caret, caret), self.number.GetSelection())

    def test_a_dialog_of_the_window_keeps_its_selection(self):
        dialog = wx.Dialog(self.frame)  # Destroyed with the frame
        field = wx.TextCtrl(dialog, value="abc")
        field.SetSelection(0, 3)
        focus.drop_selections(self.frame, keep=self.number)
        self.assertEqual((0, 3), field.GetSelection())

    def test_a_calendar_in_the_window_does_not_stop_the_walk(self):
        # P254: the calendar had a GetChildren(task) of its own, which
        # raised when the walk asked for its child windows
        wxevents.CalendarCanvas(self.frame)
        field = wx.TextCtrl(self.frame, value="after")
        field.SetSelection(0, 5)
        focus.drop_selections(self.frame, keep=self.number)
        start, end = field.GetSelection()
        self.assertEqual(start, end)

    def test_installed_it_follows_each_focus_change(self):
        self.select_everything()
        app = wx.GetApp()
        focus.install(app)
        self.addCleanup(
            app.Unbind, wx.EVT_CHILD_FOCUS, handler=focus._on_child_focus
        )
        with mock.patch.object(
            wx.Window, "FindFocus", return_value=self.search
        ):
            self.search.GetEventHandler().ProcessEvent(
                wx.ChildFocusEvent(self.search)
            )
        self.assertEqual([False, False, True, False], self.selected())
