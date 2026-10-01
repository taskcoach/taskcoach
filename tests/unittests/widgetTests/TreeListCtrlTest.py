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
from . import TreeCtrlTest
from unittests import dummy
from taskcoachlib import widgets


class TreeListCtrlTestCase(TreeCtrlTest.TreeCtrlTestCase):

    onSelect = getItemTooltipText = None

    def setUp(self):
        super().setUp()
        self._columns = self.createColumns()
        self.treeCtrl = widgets.TreeListCtrl(
            self.frame,
            self.columns(),
            self.getItemTooltipText,
            self.onSelect,
            dummy.DummyUICommand(),
            dummy.DummyUICommand(),
        )
        from taskcoachlib.gui.icons.icon_library import icon_catalog

        imageList = wx.ImageList(16, 16)
        for icon_id in [
            "nuvola_actions_ledblue",
            "nuvola_mimetypes_inode-directory",
        ]:
            imageList.Add(icon_catalog.get_bitmap(icon_id, 16))
        self.treeCtrl.AssignImageList(imageList)  # pylint: disable=E1101

    def createColumns(self):
        names = ["treeColumn"] + ["column%d" % index for index in range(1, 5)]
        return [
            widgets.Column(name, name, ("view", "whatever"), None)
            for name in names
        ]

    def columns(self):
        return self._columns


class TreeListCtrlTest(TreeListCtrlTestCase, TreeCtrlTest.CommonTestsMixin):
    pass


class TreeListCtrlColumnsTest(TreeListCtrlTestCase):
    def setUp(self):
        super().setUp()
        self.children[None] = [TreeCtrlTest.DummyDomainObject("item")]
        self.treeCtrl.RefreshAllItems(1)
        self.visibleColumns = self.columns()[1:]

    def assertColumns(self):
        # pylint: disable=E1101
        self.assertEqual(
            len(self.visibleColumns) + 1, self.treeCtrl.GetColumnCount()
        )
        item = self.treeCtrl.GetFirstChild(self.treeCtrl.GetRootItem())[0]
        for columnIndex in range(1, len(self.visibleColumns)):
            self.assertEqual(
                "item", self.treeCtrl.GetItemText(item, columnIndex)
            )

    def showColumn(self, name, show=True):
        column = widgets.Column(name, name, ("view", "whatever"), None)
        self.treeCtrl.showColumn(column, show)
        if show:
            index = self.columns()[1:].index(column)
            self.visibleColumns.insert(index, column)
        else:
            self.visibleColumns.remove(column)

    def testAllColumnsVisible(self):
        self.assertColumns()

    def first_row(self):
        return self.treeCtrl.GetFirstChild(self.treeCtrl.GetRootItem())[0]

    def test_a_hidden_column_takes_its_texts_and_icons_with_it(self):
        # The widget removes only the header; the row's values for the
        # columns after it move one place left
        row = self.first_row()
        self.treeCtrl.SetItemText(row, "column 2", 2)
        self.treeCtrl.SetItemImage(row, 0, column=2)
        self.showColumn("column1", False)
        self.assertEqual("column 2", self.treeCtrl.GetItemText(row, 1))
        self.assertEqual(0, self.treeCtrl.GetItemImage(row, column=1))
        self.assertEqual(-1, self.treeCtrl.GetItemImage(row, column=2))

    def test_a_shown_column_starts_without_icons(self):
        row = self.first_row()
        self.treeCtrl.SetItemImage(row, 0, column=3)
        self.showColumn("column2", False)
        self.assertEqual(0, self.treeCtrl.GetItemImage(row, column=2))
        self.showColumn("column2", True)
        self.assertEqual(-1, self.treeCtrl.GetItemImage(row, column=2))
        self.assertEqual(0, self.treeCtrl.GetItemImage(row, column=3))

    def test_several_icons_move_with_their_column(self):
        row = self.first_row()
        row.SetImages(3, [0, 1])
        self.showColumn("column1", False)
        self.assertEqual([0, 1], row.GetImages(2))
        self.assertEqual([], row.GetImages(3))
        self.showColumn("column1", True)
        self.assertEqual([0, 1], row.GetImages(3))

    def test_a_column_change_drops_the_rows_cached_text_sizes(self):
        row = self.first_row()
        row.GetExtents(wx.ClientDC(self.treeCtrl.GetMainWindow()))
        self.showColumn("column1", False)
        self.assertFalse(row.HasExtents(0))

    def testHideColumn(self):
        self.showColumn("column1", False)
        self.assertColumns()

    def testHideLastColumn(self):
        lastColumnHeader = "column%d" % len(self.visibleColumns)
        self.showColumn(lastColumnHeader, False)
        self.assertColumns()

    def testShowColumn(self):
        self.showColumn("column2", False)
        self.showColumn("column2", True)
