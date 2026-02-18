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
        for icon_id in ["nuvola_actions_ledblue", "nuvola_mimetypes_inode-directory"]:
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
