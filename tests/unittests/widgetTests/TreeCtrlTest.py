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
        self.frame.get_is_item_checked = lambda item: False
        self.frame.get_item_expanded = (
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

    def id(self):
        return str(id(self))

    def shown_fg_color(self):
        return None

    def shown_bg_color(self):
        return None

    def shown_font(self):
        return None


class CommonTestsMixin(object):
    """Tests for all types of trees."""

    def test_create(self):
        self.assertEqual(0, len(self.treeCtrl.get_item_children()))

    def test_one_item(self):
        self.children[None] = [self.item0]
        self.treeCtrl.RefreshAllItems(1)
        self.assertEqual(1, len(self.treeCtrl.get_item_children()))

    def test_two_items(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        self.assertEqual(2, len(self.treeCtrl.get_item_children()))

    def test_remove_all_items(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        self.children[None] = []
        self.treeCtrl.RefreshAllItems(0)
        self.assertEqual(0, len(self.treeCtrl.get_item_children()))

    def test_one_parent_and_one_child(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        self.assertEqual(1, len(self.treeCtrl.get_item_children()))
        self.assertEqual(
            1, len(self.treeCtrl.get_item_children(self.getFirstTreeItem()))
        )

    def test_one_parent_and_two_children(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0, self.item0_1]
        self.treeCtrl.RefreshAllItems(3)
        self.assertEqual(1, len(self.treeCtrl.get_item_children()))
        self.assertEqual(
            2, len(self.treeCtrl.get_item_children(self.getFirstTreeItem()))
        )

    def test_add_one_child(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        self.children[self.item0] = [self.item0_0, self.item0_1]
        self.treeCtrl.RefreshAllItems(3)
        self.assertEqual(1, len(self.treeCtrl.get_item_children()))
        self.assertEqual(
            2, len(self.treeCtrl.get_item_children(self.getFirstTreeItem()))
        )

    def test_delete_one_child(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0, self.item0_1]
        self.treeCtrl.RefreshAllItems(3)
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        self.assertEqual(1, len(self.treeCtrl.get_item_children()))
        self.assertEqual(
            1, len(self.treeCtrl.get_item_children(self.getFirstTreeItem()))
        )

    def test_reorder_items(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        self.children[None] = [self.item1, self.item0]
        self.treeCtrl.RefreshAllItems(2)
        self.assertEqual(
            "item 1", self.treeCtrl.GetItemText(self.getFirstTreeItem())
        )

    def test_reorder_children(self):
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

    def test_reorder_parents_and_one_child(self):
        self.children[None] = [self.item0, self.item1]
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(3)
        self.children[None] = [self.item1, self.item0]
        self.treeCtrl.RefreshAllItems(3)
        self.assertEqual(
            "item 1", self.treeCtrl.GetItemText(self.getFirstTreeItem())
        )

    def test_reorder_parents_and_two_children(self):
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
            0, len(self.treeCtrl.get_item_children(self.getFirstTreeItem()))
        )

    def test_retain_selection_when_editing_task(self):
        self.children[None] = [self.item0]
        self.treeCtrl.RefreshAllItems(1)
        item = self.getFirstTreeItem()
        self.treeCtrl.SelectItem(item)
        self.assertTrue(self.treeCtrl.IsSelected(item))
        self.children[None] = [self.item0]
        self.treeCtrl.RefreshAllItems(1)
        item = self.getFirstTreeItem()
        self.assertTrue(self.treeCtrl.IsSelected(item))

    def test_retain_selection_when_editing_sub_task(self):
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

    def test_retain_selection_when_adding_sub_task(self):
        self.children[None] = [self.item0]
        self.treeCtrl.RefreshAllItems(1)
        item = self.getFirstTreeItem()
        self.treeCtrl.SelectItem(item)
        self.assertTrue(self.treeCtrl.IsSelected(item))
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        item = self.getFirstTreeItem()
        self.assertTrue(self.treeCtrl.IsSelected(item))

    def test_retain_selection_when_adding_sub_task_two_toplevel_tasks(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        item = self.getFirstTreeItem()
        self.treeCtrl.SelectItem(item)
        self.assertTrue(self.treeCtrl.IsSelected(item))
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(3)
        item = self.getFirstTreeItem()
        self.assertTrue(self.treeCtrl.IsSelected(item))

    def test_removing_a_selected_item_does_not_make_another_one_selected(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        item = self.getFirstTreeItem()
        self.treeCtrl.SelectItem(item)
        self.assertTrue(self.treeCtrl.IsSelected(item))
        self.children[None] = [self.item1]
        self.treeCtrl.RefreshAllItems(1)
        self.assertFalse(self.treeCtrl.curselection())

    def test_reorder_moves_the_rows(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        rows = self.treeCtrl.get_item_children()
        self.children[None] = [self.item1, self.item0]
        self.assertTrue(self.treeCtrl.reorder_items())
        self.assertEqual(rows[::-1], self.treeCtrl.get_item_children())

    def test_reorder_moves_the_children(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0, self.item0_1]
        self.treeCtrl.RefreshAllItems(3)
        parent = self.getFirstTreeItem()
        rows = self.treeCtrl.get_item_children(parent)
        self.children[self.item0] = [self.item0_1, self.item0_0]
        self.assertTrue(self.treeCtrl.reorder_items())
        self.assertEqual(rows[::-1], self.treeCtrl.get_item_children(parent))

    def test_reorder_keeps_the_selection(self):
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        self.treeCtrl.select([self.item1])
        self.children[None] = [self.item1, self.item0]
        self.treeCtrl.reorder_items()
        self.assertEqual([self.item1], self.treeCtrl.curselection())

    def test_a_new_row_is_left_to_the_refresh(self):
        self.children[None] = [self.item0]
        self.treeCtrl.RefreshAllItems(1)
        self.children[None] = [self.item1, self.item0]
        self.assertFalse(self.treeCtrl.reorder_items())

    def test_a_child_moved_to_another_parent_is_left_to_the_refresh(self):
        self.children[None] = [self.item0, self.item1]
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(3)
        self.children[self.item0] = []
        self.children[self.item1] = [self.item0_0]
        self.assertFalse(self.treeCtrl.reorder_items())

    def test_a_child_back_under_an_expanded_row_is_left_to_the_refresh(self):
        # The undo of a move: item 0 open and empty, item 1 collapsed
        self.children[None] = [self.item0, self.item1]
        self.children[self.item1] = [self.item0_0]
        self.collapsedItems = [self.item1]
        self.treeCtrl.RefreshAllItems(3)
        self.children[self.item1] = []
        self.children[self.item0] = [self.item0_0]
        self.assertFalse(self.treeCtrl.reorder_items())

    def test_a_collapsed_row_whose_child_left_is_left_to_the_refresh(self):
        # Its expander would open to nothing
        self.children[None] = [self.item0, self.item1]
        self.children[self.item1] = [self.item0_0]
        self.collapsedItems = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(3)
        self.children[self.item1] = []
        self.children[self.item0] = [self.item0_0]
        self.assertFalse(self.treeCtrl.reorder_items())

    def test_refresh_item(self):
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
        from taskcoachlib.gui.icons.icon_library import icon_catalog

        image_list = wx.ImageList(16, 16)
        for icon_id in [
            "nuvola_actions_ledblue",
            "nuvola_mimetypes_inode-directory",
        ]:
            image_list.Add(icon_catalog.get_bitmap(icon_id, 16))
        self.treeCtrl.AssignImageList(image_list)  # pylint: disable=E1101


class CheckTreeCtrlTest(TreeCtrlTestCase, CommonTestsMixin):
    def setUp(self):
        self.frame.get_item_parent_has_exclusive_children = (
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

    def test_check_parent_does_not_check_child(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(2)
        self.treeCtrl.ExpandAll()  # pylint: disable=E1101
        parent = self.getFirstTreeItem()
        self.treeCtrl.CheckItem(parent)
        child = self.treeCtrl.get_item_children(parent)[0]
        self.assertFalse(child.IsChecked())

    def test_check_parent_of_mutual_exclusive_children_unchecks_all_children(
        self,
    ):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.mutual1, self.mutual2]
        self.treeCtrl.RefreshAllItems(3)
        self.treeCtrl.ExpandAll()  # pylint: disable=E1101
        parent = self.getFirstTreeItem()
        children = self.treeCtrl.get_item_children(parent)
        self.treeCtrl.CheckItem(children[0])
        self.treeCtrl.CheckItem(parent)
        for child in children:
            self.assertFalse(child.IsChecked())

    def test_check_parent_of_exclusive_children_unchecks_all_recursively(
        self,
    ):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.mutual1, self.mutual2]
        self.children[self.mutual1] = [self.item1_0]
        self.treeCtrl.RefreshAllItems(4)
        self.treeCtrl.ExpandAll()  # pylint: disable=E1101
        parent = self.getFirstTreeItem()
        children = self.treeCtrl.get_item_children(parent, recursively=True)
        grandchild = children[1]
        self.treeCtrl.CheckItem(grandchild)
        self.treeCtrl.CheckItem(parent)
        self.assertFalse(grandchild.IsChecked())

    def test_check_mutual_exclusive_child_unchecks_parent(self):
        self.children[None] = [self.item0]
        self.children[self.item0] = [self.mutual1, self.mutual2]
        self.treeCtrl.RefreshAllItems(3)
        self.treeCtrl.ExpandAll()  # pylint: disable=E1101
        parent = self.getFirstTreeItem()
        children = self.treeCtrl.get_item_children(parent)
        self.treeCtrl.CheckItem(parent)
        self.treeCtrl.CheckItem(children[0])
        self.assertFalse(
            self.treeCtrl.IsItemChecked(parent)
        )  # pylint: disable=E1101
