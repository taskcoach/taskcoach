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
import wx
from . import TreeCtrlTest
from unittests import dummy
from taskcoachlib import widgets
from taskcoachlib.config import settings2
from taskcoachlib.widgets import treectrl
from taskcoachlib.widgets.treectrl import customtree


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


class TreeListCtrlPointerTest(TreeListCtrlTestCase):
    """Rows moving under a pointer at rest hide the tooltip and move the
    hover outline to the row now under it."""

    def setUp(self):
        super().setUp()
        self.treeCtrl.SetSize(400, 300)
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        self.main = self.treeCtrl.GetMainWindow()
        self.main.CalculatePositions()
        self.tips_cancelled = []
        self.treeCtrl.cancel_tip = lambda: self.tips_cancelled.append(True)

    def rows(self):
        return self.treeCtrl.GetItemChildren(recursively=True)

    def pointer_on(self, row):
        # Where the pointer rests: on the row's label
        rect = self.treeCtrl.GetBoundingRect(row, textOnly=True)
        point = self.main.ClientToScreen(
            rect.GetPosition() + wx.Point(2, rect.height // 2)
        )
        patcher = mock.patch("wx.GetMousePosition", return_value=point)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_after_a_rebuild_the_outline_is_on_the_row_under_the_pointer(
        self,
    ):
        self.pointer_on(self.rows()[0])
        self.main.SetHoverItem(self.rows()[0])
        self.children[None] = [self.item1, self.item0]  # Sorted again
        self.treeCtrl.RefreshAllItems(2)
        wx.Yield()  # Once the change settles
        hovered = self.treeCtrl.GetItemPyData(self.main._hoverItem)
        self.assertIs(self.item1, hovered)
        self.assertEqual([True], self.tips_cancelled)

    def test_a_collapse_moves_the_outline_off_the_rows_gone(self):
        self.children[self.item0] = [self.item0_0]
        self.treeCtrl.RefreshAllItems(3)
        self.main.CalculatePositions()
        self.pointer_on(self.rows()[1])  # item 0.0
        self.main.SetHoverItem(self.rows()[1])
        self.treeCtrl.Collapse(self.rows()[0])
        wx.Yield()
        hovered = self.treeCtrl.GetItemPyData(self.main._hoverItem)
        self.assertIs(self.item1, hovered)
        self.assertEqual([True], self.tips_cancelled)

    def test_once_for_several_changes(self):
        self.pointer_on(self.rows()[0])
        self.treeCtrl.follow_pointer()
        self.treeCtrl.follow_pointer()
        wx.Yield()
        self.assertEqual([True], self.tips_cancelled)


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
        hidden = self.treeCtrl.GetColumnCount()
        self.showColumn("column2", True)
        self.assertEqual(hidden + 1, self.treeCtrl.GetColumnCount())
        # Filled by the refresh the viewer then makes
        self.treeCtrl.RefreshAllItems(1)
        self.assertColumns()


class TreeListCtrlInPlaceEditTest(TreeListCtrlTestCase):
    """A cell is edited in place only at an explicit request: a slow
    double click, F2 on the cell just clicked, or the right-click menu
    (docs/LIST_MANAGEMENT.md#in-place-editing)."""

    def setUp(self):
        super().setUp()
        self.treeCtrl.selectCommand = lambda: None
        self.treeCtrl.SetSize(400, 300)
        self.children[None] = [self.item0, self.item1]
        self.treeCtrl.RefreshAllItems(2)
        self.main = self.treeCtrl.GetMainWindow()
        self.main.CalculatePositions()
        for column in (0, 1):
            self.treeCtrl.SetColumnEditable(column, True)
        self.treeCtrl.SetColumnEditable(2, False)
        self.set_option("in_place_editing", True)
        self.set_option("in_place_slow_double_click", True)
        self.now = 0.0
        patcher = mock.patch.object(treectrl, "_clock", lambda: self.now)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.edits = []
        self.main.EditLabel = lambda item, column: self.edits.append(
            (self.treeCtrl.GetItemPyData(item), column)
        )

    def set_option(self, option, value):
        settings = settings2._instance._settings
        old = settings.getboolean("feature", option)
        settings.setboolean("feature", option, value)
        settings2.refresh_now()
        self.addCleanup(self.restore_option, option, old)

    @staticmethod
    def restore_option(option, value):
        settings2._instance._settings.setboolean("feature", option, value)
        settings2.refresh_now()

    def rows(self):
        return self.treeCtrl.GetItemChildren(recursively=True)

    def point(self, row, column):
        rect = self.treeCtrl.GetBoundingRect(self.rows()[row], textOnly=True)
        x = rect.x + 2
        if column > 0:
            x = sum(self.treeCtrl.GetColumnWidth(i) for i in range(column))
            x += 5
        return wx.Point(x, rect.y + rect.height // 2)

    def press(self, row, column, at, event_type=wx.wxEVT_LEFT_DOWN):
        self.now = at
        event = wx.MouseEvent(event_type)
        event.SetPosition(self.point(row, column))
        event.SetEventObject(self.main)
        self.main.GetEventHandler().ProcessEvent(event)

    def key(self, key_code):
        event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        event.SetKeyCode(key_code)
        event.SetEventObject(self.main)
        self.main.GetEventHandler().ProcessEvent(event)

    def leave(self):
        event = wx.FocusEvent(wx.wxEVT_KILL_FOCUS)
        event.SetWindow(None)
        event.SetEventObject(self.main)
        self.main.GetEventHandler().ProcessEvent(event)

    def timer_edit_allowed(self, row=0, column=0):
        """Whether the tree's own timer, which starts the edit after a
        click, gets to edit the cell."""
        event = customtree.TreeEvent(
            wx.wxEVT_COMMAND_TREE_BEGIN_LABEL_EDIT, self.treeCtrl.GetId()
        )
        event.SetItem(self.rows()[row])
        event.SetInt(column)
        self.treeCtrl.on_begin_edit(event)
        return event.IsAllowed()

    def test_a_slow_double_click_edits(self):
        self.press(0, 0, at=0.0)
        self.press(0, 0, at=1.0)
        self.assertTrue(self.timer_edit_allowed())

    def test_two_quick_clicks_do_not(self):
        # Within the double-click time: a double click
        self.press(0, 0, at=0.0)
        self.press(0, 0, at=0.1)
        self.assertFalse(self.timer_edit_allowed())

    def test_two_clicks_too_far_apart_do_not(self):
        self.press(0, 0, at=0.0)
        self.press(0, 0, at=3.0)
        self.assertFalse(self.timer_edit_allowed())

    def test_a_click_elsewhere_in_between_ends_it(self):
        self.press(0, 0, at=0.0)
        self.press(1, 0, at=0.5)
        self.press(0, 0, at=1.0)
        self.assertFalse(self.timer_edit_allowed())

    def test_a_key_in_between_ends_it(self):
        self.press(0, 0, at=0.0)
        self.key(wx.WXK_DOWN)
        self.press(0, 0, at=1.0)
        self.assertFalse(self.timer_edit_allowed())

    def test_leaving_the_list_in_between_ends_it(self):
        self.press(0, 0, at=0.0)
        self.leave()
        self.press(0, 0, at=1.0)
        self.assertFalse(self.timer_edit_allowed())

    def test_only_with_its_option_on(self):
        self.set_option("in_place_slow_double_click", False)
        self.press(0, 0, at=0.0)
        self.press(0, 0, at=1.0)
        self.assertFalse(self.timer_edit_allowed())

    def test_only_with_editing_in_place_on(self):
        self.set_option("in_place_editing", False)
        self.press(0, 0, at=0.0)
        self.press(0, 0, at=1.0)
        self.assertFalse(self.timer_edit_allowed())

    def test_f2_edits_the_cell_just_clicked(self):
        self.press(1, 1, at=0.0)
        self.key(wx.WXK_F2)
        self.assertEqual([(self.item1, 1)], self.edits)

    def test_f2_after_a_key_edits_nothing(self):
        self.press(0, 0, at=0.0)
        self.key(wx.WXK_DOWN)
        self.key(wx.WXK_F2)
        self.assertEqual([], self.edits)

    def test_f2_after_leaving_the_list_edits_nothing(self):
        self.press(0, 0, at=0.0)
        self.leave()
        self.key(wx.WXK_F2)
        self.assertEqual([], self.edits)

    def test_f2_on_a_cell_that_cannot_be_edited_edits_nothing(self):
        self.press(0, 2, at=0.0)
        self.key(wx.WXK_F2)
        self.assertEqual([], self.edits)

    def test_f2_with_editing_in_place_off_edits_nothing(self):
        self.set_option("in_place_editing", False)
        self.press(0, 0, at=0.0)
        self.key(wx.WXK_F2)
        self.assertEqual([], self.edits)

    def test_the_right_click_menu_edits_the_cell_clicked(self):
        self.press(1, 1, at=0.0, event_type=wx.wxEVT_RIGHT_DOWN)
        self.assertTrue(self.treeCtrl.can_edit_clicked_cell())
        self.treeCtrl.edit_clicked_cell()
        self.assertEqual([(self.item1, 1)], self.edits)

    def test_the_right_click_menu_cannot_edit_a_fixed_cell(self):
        self.press(1, 2, at=0.0, event_type=wx.wxEVT_RIGHT_DOWN)
        self.assertFalse(self.treeCtrl.can_edit_clicked_cell())

    def test_editing_leaves_only_the_cells_row_selected(self):
        self.treeCtrl.select([self.item0, self.item1])
        self.press(1, 1, at=0.0, event_type=wx.wxEVT_RIGHT_DOWN)
        self.treeCtrl.edit_clicked_cell()
        selected = [
            self.treeCtrl.GetItemPyData(item)
            for item in self.treeCtrl.GetSelections()
        ]
        self.assertEqual([self.item1], selected)

    def test_beside_the_subjects_text_is_its_cell(self):
        # The tree reports no column there
        right_of_text = wx.Point(
            self.treeCtrl.GetColumnWidth(0) - 3, self.point(1, 0).y
        )
        self.assertEqual(-1, self.treeCtrl.HitTest(right_of_text)[2])
        event = wx.MouseEvent(wx.wxEVT_RIGHT_DOWN)
        event.SetPosition(right_of_text)
        self.main.GetEventHandler().ProcessEvent(event)
        self.treeCtrl.edit_clicked_cell()
        self.assertEqual([(self.item1, 0)], self.edits)
