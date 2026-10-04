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

    def test_unselect_all_clears_rows_highlighted_through_the_tree(self):
        # What restoring the selection after a rebuild relies on
        # (treectrl.select()): UnselectAll() clears the selection set
        # SetItemHilight() keeps, not rows highlighted on their own
        tree, item = self.tree_with_one_item()
        tree.GetMainWindow().SetItemHilight(item, True)
        tree.UnselectAll()
        self.assertFalse(item.IsSelected())
