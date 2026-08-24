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

import test, wx
from unittests import dummy
from taskcoachlib import widgets


class VirtualListCtrlTestCase(test.wxTestCase):

    onSelect = lambda *args: None

    def createListCtrl(self):
        self.frame.get_item_with_index = lambda index: index
        self.frame.get_index_of_item = lambda item: (
            item if type(item) == type(0) else 0
        )
        self.frame.getItemText = lambda item, column: ""
        self.frame.getItemTooltipData = lambda item: []
        self.frame.getItemImages = lambda item, column: {
            wx.TreeItemIcon_Normal: -1
        }
        return widgets.VirtualListCtrl(
            self.frame, self.columns, self.onSelect, dummy.DummyUICommand()
        )

    def createColumns(self, nrColumns):
        columns = []
        for columnIndex in range(1, nrColumns + 1):
            name = "column%d" % columnIndex
            columns.append(widgets.Column(name, name, None, None))
        return columns

    def setUp(self):
        super().setUp()
        self.columns = self.createColumns(nrColumns=3)
        self.listctrl = self.createListCtrl()

    def testOneItem(self):
        self.listctrl.RefreshAllItems(1)
        self.assertEqual(1, self.listctrl.GetItemCount())

    def testNrOfColumns(self):
        self.assertEqual(3, self.listctrl.GetColumnCount())

    def testCurselection_EmptyList(self):
        self.assertEqual([], self.listctrl.curselection())

    def testShowColumn_Hide(self):
        self.listctrl.showColumn(self.columns[2], False)
        self.assertEqual(2, self.listctrl.GetColumnCount())

    def testShowColumn_HideAndShow(self):
        self.listctrl.showColumn(self.columns[2], False)
        self.listctrl.showColumn(self.columns[2], True)
        self.assertEqual(3, self.listctrl.GetColumnCount())

    def testShowColumn_ColumnOrderIsKept(self):
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

    def testShowColumn_HideTwice(self):
        self.listctrl.showColumn(self.columns[2], False)
        self.listctrl.showColumn(self.columns[2], False)
        self.assertEqual(2, self.listctrl.GetColumnCount())

    def testSelect(self):
        self.listctrl.RefreshAllItems(1)
        self.listctrl.select([0])
        self.assertEqual([0], self.listctrl.curselection())

    def testSelect_EmptySelection(self):
        self.listctrl.RefreshAllItems(1)
        self.listctrl.select([])
        self.assertEqual([], self.listctrl.curselection())

    def testSelect_MultipleSelection(self):
        self.listctrl.RefreshAllItems(2)
        self.listctrl.select([0, 1])
        self.assertEqual([0, 1], self.listctrl.curselection())

    def testSelect_DisjunctMultipleSelection(self):
        self.listctrl.RefreshAllItems(3)
        self.listctrl.select([0, 2])
        self.assertEqual([0, 2], self.listctrl.curselection())

    def testSelect_SetsFocus(self):
        self.listctrl.RefreshAllItems(1)
        self.listctrl.select([0])
        self.assertEqual(0, self.listctrl.GetFocusedItem())

    def testSelect_EmptySelection_SetsFocus(self):
        self.listctrl.RefreshAllItems(1)
        self.listctrl.select([])
        self.assertEqual(-1, self.listctrl.GetFocusedItem())

    def testSelect_MultipleSelection_SetsFocus(self):
        self.listctrl.RefreshAllItems(2)
        self.listctrl.select([0, 1])
        self.assertEqual(0, self.listctrl.GetFocusedItem())

    def testSelect_DisjunctMultipleSelection_SetsFocus(self):
        self.listctrl.RefreshAllItems(3)
        self.listctrl.select([0, 2])
        self.assertEqual(0, self.listctrl.GetFocusedItem())
