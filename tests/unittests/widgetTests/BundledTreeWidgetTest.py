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

import os
import test
import wx
import taskcoachlib
from wx.lib.agw import customtreectrl, hypertreelist

# Every key the tree handles itself (CustomTreeCtrl.OnKeyDown)
_TREE_KEYS = (
    ord("A"),
    ord("1"),
    ord("+"),
    ord("-"),
    ord("*"),
    wx.WXK_NUMPAD_ADD,
    wx.WXK_NUMPAD_SUBTRACT,
    wx.WXK_NUMPAD_MULTIPLY,
    wx.WXK_UP,
    wx.WXK_DOWN,
    wx.WXK_LEFT,
    wx.WXK_RIGHT,
    wx.WXK_HOME,
    wx.WXK_END,
    wx.WXK_PAGEUP,
    wx.WXK_PAGEDOWN,
    wx.WXK_RETURN,
    wx.WXK_SPACE,
    wx.WXK_MENU,
)


class BundledTreeWidgetTest(test.wxTestCase):
    """The tree views run on the bundled pair, never one bundled file
    over the installed wxPython's other
    (docs/BUNDLED_TREE_WIDGET.md)."""

    def test_both_modules_are_the_bundled_files(self):
        patches = os.path.join(
            os.path.dirname(taskcoachlib.__file__), "patches"
        )
        for module in customtreectrl, hypertreelist:
            self.assertEqual(patches, os.path.dirname(module.__file__))

    def test_the_copy_is_built_on_the_bundled_base(self):
        self.assertIs(
            customtreectrl.CustomTreeCtrl, hypertreelist.CustomTreeCtrl
        )

    def tree_with_one_item(self):
        tree = hypertreelist.HyperTreeList(
            self.frame,
            agwStyle=wx.TR_MULTIPLE | wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS,
        )
        tree.AddColumn("Subject")
        root = tree.AddRoot("root")
        return tree, tree.AppendItem(root, "item")

    def trees_with_no_row(self):
        """An empty view (its hidden root only), a view not filled yet
        (no root) and the plain tree both are built on."""
        style = wx.TR_MULTIPLE | wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS
        empty_view = hypertreelist.HyperTreeList(self.frame, agwStyle=style)
        empty_view.AddColumn("Subject")
        empty_view.AddRoot("root")
        not_filled = hypertreelist.HyperTreeList(self.frame, agwStyle=style)
        not_filled.AddColumn("Subject")
        return (
            empty_view.GetMainWindow(),
            not_filled.GetMainWindow(),
            customtreectrl.CustomTreeCtrl(self.frame),
        )

    def test_keys_on_a_tree_with_no_row_do_nothing(self):
        # P252: a letter or digit, +, -, *, Left, Right, Home and the
        # menu key raised AttributeError on the missing current row
        for tree in self.trees_with_no_row():
            for code in _TREE_KEYS:
                event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
                event.SetKeyCode(code)
                tree.OnKeyDown(event)
                self.assertTrue(event.GetSkipped())

    def test_unselect_all_clears_rows_highlighted_through_the_tree(self):
        # What restoring the selection after a rebuild relies on
        # (treectrl.select()): UnselectAll() clears the selection set
        # SetItemHilight() keeps, not rows highlighted on their own
        tree, item = self.tree_with_one_item()
        tree.GetMainWindow().SetItemHilight(item, True)
        tree.UnselectAll()
        self.assertFalse(item.IsSelected())
