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
from unittests import dummy
from taskcoachlib import widgets


class TreeCtrlTestCase(test.wxTestCase):
    onSelect = None

    def getFirstTreeItem(self):
        # pylint: disable=E1101
        return self.treeCtrl.GetFirstChild(self.treeCtrl.GetRootItem())[0]

    def setUp(self):
        super().setUp()
        self.children = dict()
        self.collapsedItems = []
        self.frame.children = lambda item: self.children.get(item, [])
        self.frame.getItemText = lambda item, column: item.subject()
        self.frame.hasColumnImages = lambda column: False
        self.frame.getItemImages = lambda item, column: {
            wx.TreeItemIcon_Normal: -1
        }
        self.frame.getIsItemChecked = lambda item: False
        self.frame.getItemExpanded = (
            lambda item: item not in self.collapsedItems
        )
        self.item0 = DummyDomainObject("item 0")
        self.item1 = DummyDomainObject("item 1")
        self.item0_0 = DummyDomainObject("item 0.0")
        self.item0_1 = DummyDomainObject("item 0.1")
        self.item1_0 = DummyDomainObject("item 1.0")


class DummyDomainObject(object):
    def __init__(self, subject):
        self.__subject = subject

    def subject(self):
        return self.__subject

    # pylint: disable=W0613

    def foregroundColor(self, recursive=False):
        return None

    def backgroundColor(self, recursive=False):
        return None

    def font(self, recursive=False):
        return None


class CommonTestsMixin(object):
    """Tests for all types of trees."""

    def testCreate(self):
        self.assertEqual(0, len(self.treeCtrl.GetItemChildren()))

    def testOneItem(self):
        self.children[None] = [self.item0]
        self.treeCtrl.RefreshAllItems(1)
        self.assertEqual(1, len(self.treeCtrl.GetItemChildren()))

    def testTwoItems(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        self.assertEqual(2, len(self.treeCtrl.GetItemChildren()))

    def testRemoveAllItems(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        self.children[None] = []
        self.treeCtrl.RefreshAllItems(0)
        self.assertEqual(0, len(self.treeCtrl.GetItemChildren()))

    def testOneParentAndOneChild(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        self.assertEqual(1, len(self.treeCtrl.GetItemChildren()))
        self.assertEqual(
            1, len(self.treeCtrl.GetItemChildren(self.getFirstTreeItem()))
        )

    def testOneParentAndTwoChildren(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0, self.item0_1]
        self.treeCtrl.RefreshAllItems(3)
        self.assertEqual(1, len(self.treeCtrl.GetItemChildren()))
        self.assertEqual(
            2, len(self.treeCtrl.GetItemChildren(self.getFirstTreeItem()))
        )

    def testAddOneChild(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        self.children[self.item0] = [self.item0_0, self.item0_1]
        self.treeCtrl.RefreshAllItems(3)
        self.assertEqual(1, len(self.treeCtrl.GetItemChildren()))
        self.assertEqual(
            2, len(self.treeCtrl.GetItemChildren(self.getFirstTreeItem()))
        )

    def testDeleteOneChild(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0, self.item0_1]
        self.treeCtrl.RefreshAllItems(3)
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        self.assertEqual(1, len(self.treeCtrl.GetItemChildren()))
        self.assertEqual(
            1, len(self.treeCtrl.GetItemChildren(self.getFirstTreeItem()))
        )

    def testReorderItems(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        self.children[None] = [self.item1, self.item0]
        self.treeCtrl.RefreshAllItems(2)
        self.assertEqual(
            "item 1", self.treeCtrl.GetItemText(self.getFirstTreeItem())
        )

    def testReorderChildren(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0, self.item0_1]
        self.treeCtrl.RefreshAllItems(3)
        self.children[self.item0] = [self.item0_1, self.item0_0]
        self.treeCtrl.RefreshAllItems(3)
        self.assertEqual(
            "item 0.1",
            self.treeCtrl.GetItemText(
                self.treeCtrl.GetFirstChild(self.getFirstTreeItem())[0]
            ),
        )

    def testReorderParentsAndOneChild(self):
        self.children[None] = [self.item0, self.item1]
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(3)
        self.children[None] = [self.item1, self.item0]
        self.treeCtrl.RefreshAllItems(3)
        self.assertEqual(
            "item 1", self.treeCtrl.GetItemText(self.getFirstTreeItem())
        )

    def testReorderParentsAndTwoChildren(self):
        self.children[None] = [self.item0, self.item1]
        self.children[self.item0] = [self.item0_0, self.item0_1]
        self.treeCtrl.RefreshAllItems(4)
        self.children[None] = [self.item1, self.item0]
        self.children[self.item0] = [self.item0_1, self.item0_0]
        self.treeCtrl.RefreshAllItems(4)
        self.assertEqual(
            "item 1", self.treeCtrl.GetItemText(self.getFirstTreeItem())
        )
        self.assertEqual(
            0, len(self.treeCtrl.GetItemChildren(self.getFirstTreeItem()))
        )

    def testRetainSelectionWhenEditingTask(self):
        self.children[None] = [self.item0]
        self.treeCtrl.RefreshAllItems(1)
        item = self.getFirstTreeItem()
        self.treeCtrl.SelectItem(item)
        self.assertTrue(self.treeCtrl.IsSelected(item))
        self.children[None] = [self.item0]
        self.treeCtrl.RefreshAllItems(1)
        item = self.getFirstTreeItem()
        self.assertTrue(self.treeCtrl.IsSelected(item))

    def testRetainSelectionWhenEditingSubTask(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        item = self.getFirstTreeItem()
        self.treeCtrl.SelectItem(item)
        self.assertTrue(self.treeCtrl.IsSelected(item))
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        item = self.getFirstTreeItem()
        self.assertTrue(self.treeCtrl.IsSelected(item))

    def testRetainSelectionWhenAddingSubTask(self):
        self.children[None] = [self.item0]
        self.treeCtrl.RefreshAllItems(1)
        item = self.getFirstTreeItem()
        self.treeCtrl.SelectItem(item)
        self.assertTrue(self.treeCtrl.IsSelected(item))
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        item = self.getFirstTreeItem()
        self.assertTrue(self.treeCtrl.IsSelected(item))

    def testRetainSelectionWhenAddingSubTask_TwoToplevelTasks(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        item = self.getFirstTreeItem()
        self.treeCtrl.SelectItem(item)
        self.assertTrue(self.treeCtrl.IsSelected(item))
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(3)
        item = self.getFirstTreeItem()
        self.assertTrue(self.treeCtrl.IsSelected(item))

    def testRemovingASelectedItemDoesNotMakeAnotherOneSelected(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        item = self.getFirstTreeItem()
        self.treeCtrl.SelectItem(item)
        self.assertTrue(self.treeCtrl.IsSelected(item))
        self.children[None] = [self.item1]
        self.treeCtrl.RefreshAllItems(1)
        self.assertFalse(self.treeCtrl.curselection())

    def testRefreshItem(self):
        self.children[None] = [self.item0]
        self.treeCtrl.RefreshAllItems(1)
        self.treeCtrl.RefreshItems(self.item0)
        item = self.getFirstTreeItem()
        self.assertEqual("item 0", self.treeCtrl.GetItemText(item))


class TreeListCtrlTest(TreeCtrlTestCase, CommonTestsMixin):
    def setUp(self):
        super().setUp()
        columns = [widgets.Column("subject", "Subject")]
        self.treeCtrl = widgets.TreeListCtrl(
            self.frame,
            columns,
            self.onSelect,
            dummy.DummyUICommand(),
            dummy.DummyUICommand(),
            dummy.DummyUICommand(),
        )
        imageList = wx.ImageList(16, 16)
        for bitmapName in ["led_blue_icon", "folder_blue_icon"]:
            imageList.Add(
                wx.ArtProvider.GetBitmap(bitmapName, wx.ART_MENU, (16, 16))
            )
        self.treeCtrl.AssignImageList(imageList)  # pylint: disable=E1101


class CheckTreeCtrlTest(TreeCtrlTestCase, CommonTestsMixin):
    def setUp(self):
        self.frame.getItemParentHasExclusiveChildren = (
            lambda item: item.subject().startswith("mutual")
        )
        super().setUp()
        columns = [widgets.Column("subject", "Subject")]
        self.treeCtrl = widgets.CheckTreeCtrl(
            self.frame,
            columns,
            self.onSelect,
            self.onCheck,
            dummy.DummyUICommand(),
            dummy.DummyUICommand(),
        )
        self.mutual1 = DummyDomainObject("mutual 1")
        self.mutual2 = DummyDomainObject("mutual 2")

    def onCheck(self, event, final):
        pass

    def testCheckParentDoesNotCheckChild(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        self.treeCtrl.ExpandAll()  # pylint: disable=E1101
        parent = self.getFirstTreeItem()
        self.treeCtrl.CheckItem(parent)
        child = self.treeCtrl.GetItemChildren(parent)[0]
        self.assertFalse(child.IsChecked())

    def testCheckParentOfMutualExclusiveChildrenUnchecksAllChildren(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.mutual1, self.mutual2]
        self.treeCtrl.RefreshAllItems(3)
        self.treeCtrl.ExpandAll()  # pylint: disable=E1101
        parent = self.getFirstTreeItem()
        children = self.treeCtrl.GetItemChildren(parent)
        self.treeCtrl.CheckItem(children[0])
        self.treeCtrl.CheckItem(parent)
        for child in children:
            self.assertFalse(child.IsChecked())

    def testCheckParentOfMutualExclusiveChildrenUnchecksAllChildrenRecursively(
        self,
    ):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.mutual1, self.mutual2]
        self.children[self.mutual1] = [self.item1_0]
        self.treeCtrl.RefreshAllItems(4)
        self.treeCtrl.ExpandAll()  # pylint: disable=E1101
        parent = self.getFirstTreeItem()
        children = self.treeCtrl.GetItemChildren(parent, recursively=True)
        grandchild = children[1]
        self.treeCtrl.CheckItem(grandchild)
        self.treeCtrl.CheckItem(parent)
        self.assertFalse(grandchild.IsChecked())

    def testCheckMutualExclusiveChildUnchecksParent(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.mutual1, self.mutual2]
        self.treeCtrl.RefreshAllItems(3)
        self.treeCtrl.ExpandAll()  # pylint: disable=E1101
        parent = self.getFirstTreeItem()
        children = self.treeCtrl.GetItemChildren(parent)
        self.treeCtrl.CheckItem(parent)
        self.treeCtrl.CheckItem(children[0])
        self.assertFalse(
            self.treeCtrl.IsItemChecked(parent)
        )  # pylint: disable=E1101
