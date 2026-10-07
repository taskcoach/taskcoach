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
import test, wx
from unittests import dummy
from taskcoachlib import widgets
from taskcoachlib.config import settings


class Row(int):
    """A row the list can paint, equal to its row number."""

    @staticmethod
    def shown_fg_color():
        return None

    shown_bg_color = shown_font = shown_fg_color


class VirtualListCtrlTestCase(test.wxTestCase):

    onSelect = lambda *args: None

    def createListCtrl(self):
        self.frame.get_item_with_index = Row
        self.frame.getItemText = lambda item, column: ""
        self.frame.getItemTooltipData = lambda item: []
        self.frame.getItemImages = lambda item, column: {
            wx.TreeItemIcon_Normal: -1
        }
        return widgets.VirtualListCtrl(
            self.frame, self.columns, self.onSelect, dummy.DummyUICommand()
        )

    def createColumns(self, nr_columns):
        columns = []
        for column_index in range(1, nr_columns + 1):
            name = "column%d" % column_index
            columns.append(widgets.Column(name, name, None, None))
        return columns

    def setUp(self):
        super().setUp()
        self.columns = self.createColumns(nr_columns=3)
        self.listctrl = self.createListCtrl()

    def test_one_item(self):
        self.listctrl.RefreshAllItems(1)
        self.assertEqual(1, self.listctrl.GetItemCount())

    def test_nr_of_columns(self):
        self.assertEqual(3, self.listctrl.GetColumnCount())

    def test_curselection_empty_list(self):
        self.assertEqual([], self.listctrl.curselection())

    def test_show_column_hide(self):
        self.listctrl.showColumn(self.columns[2], False)
        self.assertEqual(2, self.listctrl.GetColumnCount())

    def test_show_column_hide_and_show(self):
        self.listctrl.showColumn(self.columns[2], False)
        self.listctrl.showColumn(self.columns[2], True)
        self.assertEqual(3, self.listctrl.GetColumnCount())

    def test_show_column_column_order_is_kept(self):
        self.listctrl.showColumn(self.columns[1], False)
        self.listctrl.showColumn(self.columns[2], False)
        self.listctrl.showColumn(self.columns[1], True)
        self.listctrl.showColumn(self.columns[2], True)
        # pylint: disable=W0212
        self.assertEqual(
            self.columns[1].header(), self.listctrl._getColumnHeader(1)
        )
        self.assertEqual(
            self.columns[2].header(), self.listctrl._getColumnHeader(2)
        )

    def test_show_column_hide_twice(self):
        self.listctrl.showColumn(self.columns[2], False)
        self.listctrl.showColumn(self.columns[2], False)
        self.assertEqual(2, self.listctrl.GetColumnCount())

    def test_select(self):
        self.listctrl.RefreshAllItems(1)
        self.listctrl.select([0])
        self.assertEqual([0], self.listctrl.curselection())

    def test_select_empty_selection(self):
        self.listctrl.RefreshAllItems(1)
        self.listctrl.select([])
        self.assertEqual([], self.listctrl.curselection())

    def test_select_multiple_selection(self):
        self.listctrl.RefreshAllItems(2)
        self.listctrl.select([0, 1])
        self.assertEqual([0, 1], self.listctrl.curselection())

    def test_select_disjunct_multiple_selection(self):
        self.listctrl.RefreshAllItems(3)
        self.listctrl.select([0, 2])
        self.assertEqual([0, 2], self.listctrl.curselection())

    def test_select_sets_focus(self):
        self.listctrl.RefreshAllItems(1)
        self.listctrl.select([0])
        self.assertEqual(0, self.listctrl.GetFocusedItem())

    def test_select_empty_selection_sets_focus(self):
        self.listctrl.RefreshAllItems(1)
        self.listctrl.select([])
        self.assertEqual(-1, self.listctrl.GetFocusedItem())

    def test_select_multiple_selection_sets_focus(self):
        self.listctrl.RefreshAllItems(2)
        self.listctrl.select([0, 1])
        self.assertEqual(0, self.listctrl.GetFocusedItem())

    def test_select_disjunct_multiple_selection_sets_focus(self):
        self.listctrl.RefreshAllItems(3)
        self.listctrl.select([0, 2])
        self.assertEqual(0, self.listctrl.GetFocusedItem())

    def test_a_stable_viewport_selects_without_scrolling(self):
        # After a delete with auto-scroll off, as the trees
        settings.view.autoscrollselection = False
        self.listctrl.RefreshAllItems(3)
        # wx's Focus() scrolls to the row
        with mock.patch.object(
            self.listctrl, "Focus"
        ) as focus, self.listctrl.stable_viewport():
            self.listctrl.select([2])
        focus.assert_not_called()
        self.assertEqual(2, self.listctrl.GetFocusedItem())
        self.assertEqual([2], self.listctrl.curselection())


class WxOwnWindowsTest(test.wxTestCase):
    """The list keeps no wrapper of a window wx creates inside it (its
    header): wxPython would hand that stale wrapper out for whatever wx
    creates at its address after the list is destroyed (P113)."""

    onSelect = VirtualListCtrlTestCase.onSelect

    def test_the_header_window_is_not_kept(self):
        self.columns = VirtualListCtrlTestCase.createColumns(self, 3)
        listctrl = VirtualListCtrlTestCase.createListCtrl(self)
        listctrl.ToggleAutoResizing(False)
        listctrl.ToggleAutoResizing(True)  # Binds the header's motion
        kept = [
            name
            for name, value in vars(listctrl).items()
            if type(value) is wx.Window  # pylint: disable=C0123
        ]
        self.assertEqual([], kept)


class VirtualListCtrlPointerTest(test.wxTestCase):
    """Rows moving under a pointer at rest hide the tooltip and move the
    hover outline to the row now under it (P148)."""

    onSelect = VirtualListCtrlTestCase.onSelect

    def setUp(self):
        super().setUp()
        self.columns = VirtualListCtrlTestCase.createColumns(self, 3)
        self.listctrl = VirtualListCtrlTestCase.createListCtrl(self)
        self.listctrl.SetSize(400, 300)
        self.listctrl.RefreshAllItems(50)
        self.tips_cancelled = []
        self.listctrl.cancel_tip = lambda: self.tips_cancelled.append(True)

    def pointer_on(self, row):
        rect = self.listctrl.GetItemRect(row)  # In the control's terms
        point = self.listctrl.ClientToScreen(
            wx.Point(rect.x + 5, rect.y + rect.height // 2)
        )
        patcher = mock.patch("wx.GetMousePosition", return_value=point)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_scroll_moves_the_outline_to_the_row_under_the_pointer(self):
        self.pointer_on(3)
        self.listctrl._hover_row = 0  # Under the pointer before a scroll
        self.listctrl._draw_hover_outline()  # After the repaint
        self.assertEqual(3, self.listctrl._hover_row)
        self.assertEqual([True], self.tips_cancelled)

    def test_at_rest_the_outline_stays(self):
        self.pointer_on(3)
        self.listctrl._hover_row = 3
        self.listctrl._draw_hover_outline()
        self.assertEqual(3, self.listctrl._hover_row)
        self.assertEqual([], self.tips_cancelled)

    def test_refilling_the_list_hides_the_tooltip(self):
        self.pointer_on(3)
        self.listctrl._hover_row = 3
        self.listctrl.RefreshAllItems(50)  # Sorted again
        wx.Yield()
        self.assertEqual([True], self.tips_cancelled)
